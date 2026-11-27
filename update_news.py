"""Build the public news catalog from reviewed articles and Spanish RSS links."""
import argparse
import gzip
import hashlib
import html
import io
import json
import re
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urlencode
from html.parser import HTMLParser
from functools import lru_cache
import os
import textwrap
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MAX_FEED_BYTES = 4_000_000
FEEDS = (
    ("Xbox", "Xbox Wire", "https://news.xbox.com/es-latam/feed/"),
    ("PlayStation", "PlayStation Blog", "https://blog.es.playstation.com/feed/"),
    ("Videojuegos", "3DJuegos", "https://www.3djuegos.com/index.xml"),
    ("Videojuegos", "Vandal", "https://vandal.elespanol.com/xml.cgi"),
    ("Tecnología", "Xataka", "https://www.xataka.com/index.xml"),
)
COVER = {
    "Xbox": 3, "PlayStation": 3, "Nintendo": 3, "PC Gaming": 5,
    "GOTY": 1, "Lanzamientos": 6, "Tecnología": 5,
    "Inteligencia artificial": 4, "Videojuegos": 0,
}
TOPICS = (
    ("GOTY", r"\bgoty\b|the game awards|juego del año"),
    ("Inteligencia artificial", r"inteligencia artificial|\bia\b|chatgpt|openai"),
    ("Nintendo", r"nintendo|pokémon|zelda|\bswitch\b"),
    ("PlayStation", r"playstation|\bps[45]\b"),
    ("Xbox", r"xbox|game pass"),
    ("PC Gaming", r"steam|\bgpu\b|nvidia|radeon|\bpc\b"),
    ("Lanzamientos", r"lanzamiento|fecha de estreno"),
)


def canonical_url(url):
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return ""
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/") or "/",
                       parts.query, ""))


def publication(value):
    try:
        date = datetime.fromisoformat(value)
    except ValueError:
        date = parsedate_to_datetime(value)
    return date.replace(tzinfo=date.tzinfo or timezone.utc).astimezone(timezone.utc)


def classify(title, default):
    if default in ("PlayStation", "Xbox"):
        return default
    return next((category for category, pattern in TOPICS
                 if re.search(pattern, title, re.IGNORECASE)), default)


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def plain(value):
    parser = PlainText(); parser.feed(value or "")
    return " ".join(" ".join(parser.parts).split())

def factual_note(title, description, source, date, category):
    # No reproduce el texto de terceros ni inventa detalles.
    context = title + " " + description
    platforms = [x for x in ("PS5", "PS4", "Xbox Series", "Xbox One", "Nintendo Switch 2", "Steam") if re.search(r"\b"+re.escape(x)+r"\b", context, re.I)]
    versions = re.search(r"(?:versión|actualización|parche)\s+(\d+(?:\.\d+){1,3})", context, re.I)
    facts = [f"{source} publicó esta novedad el {date:%d/%m/%Y}. La información corresponde a la sección {category}."]
    if platforms: facts.append("Plataformas o servicios mencionados: " + ", ".join(platforms) + ".")
    if versions: facts.append("Número de versión mencionado: " + versions.group(1) + ".")
    facts.append("Ficha automática basada en los datos de la fuente; todavía no es un artículo editorial revisado.")
    return "\n\n".join(facts)

def fetch_feed(default, source, url):
    request = Request(url, headers={"User-Agent": "CraftiGaming/1.0"})
    with urlopen(request, timeout=15) as response:
        raw = response.read(MAX_FEED_BYTES + 1)
    if raw.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_FEED_BYTES + 1)
    if len(raw) > MAX_FEED_BYTES:
        raise ValueError("El feed excede el tamaño permitido")
    items = ET.fromstring(raw).findall("./channel/item")
    now = datetime.now(timezone.utc)
    articles = []
    for item in items[:25]:
        title = " ".join(html.unescape(item.findtext("title", "")).split())
        if not title or re.search(r"patrocinado|publirreportaje|black friday|cyber monday", title, re.I):
            continue
        try:
            date = publication(item.findtext("pubDate", ""))
            link = canonical_url(item.findtext("link", ""))
        except (ValueError, TypeError, OverflowError):
            continue
        if not link or date > now:
            continue
        articles.append({
            "title": title, "url": link, "source": source,
            "category": classify(title, default), "published": date.isoformat(),
            "summary": factual_note(title, plain(item.findtext("description", "")), source, date, classify(title, default)).split("\n\n")[0],
            "contenido": factual_note(title, plain(item.findtext("description", "")), source, date, classify(title, default)),
            "tipo_contenido": "Ficha automática · sin revisión editorial",
        })
    if not articles:
        raise ValueError("Sin entradas RSS válidas")
    return articles


def collect_feed(feed):
    try:
        return fetch_feed(*feed)
    except (OSError, ValueError, ET.ParseError, EOFError) as error:
        print(f"{feed[1]}: {error}")
        return []


# Consultas específicas; las fotografías de hardware son referenciales, no capturas del juego.
SUBJECTS = ((r"nintendo switch 2", "Nintendo Switch 2 console"), (r"nintendo|switch", "Nintendo Switch console"), (r"playstation|ps5", "PlayStation 5 console"), (r"xbox", "Xbox Series X console"), (r"steam", "Steam Deck console"), (r"fortnite", "Fortnite at Gamescom cosplay"), (r"dragon ball", "Dragon Ball cosplay"), (r"game awards", "The Game Awards trophy"), (r"hounded", "dog portrait"))

@lru_cache(maxsize=24)
def commons_image(subject):
    params = dict(action="query", generator="search", gsrsearch=subject+" filetype:bitmap", gsrnamespace=6, gsrlimit=5, prop="imageinfo", iiprop="url|extmetadata|mime", iiurlwidth=1000, format="json")
    try:
        req = Request("https://commons.wikimedia.org/w/api.php?"+urlencode(params), headers={"User-Agent":"CraftiGaming/2.1 (https://simonnaupe-ux.github.io/crafti-gaming/)"})
        with urlopen(req, timeout=8) as response: data=json.load(response)
        for page in sorted(data.get("query",{}).get("pages",{}).values(), key=lambda x:x.get("index",99)):
            info=page["imageinfo"][0]; meta=info.get("extmetadata",{})
            license=plain(meta.get("LicenseShortName",{}).get("value",""))
            author=plain(meta.get("Artist",{}).get("value",""))
            if not re.fullmatch(r"(?:CC BY(?:-SA)? [234]\.[05]|CC0|Public domain)",license,re.I) or not author: continue
            url=info.get("thumburl",info.get("url",""))
            if urlsplit(url).hostname != "upload.wikimedia.org" or info.get("mime") not in ("image/jpeg","image/png","image/webp"): continue
            return dict(image=url, imagen_autor=author, imagen_licencia=license, imagen_fuente=info["descriptionurl"], imagen_tipo="Fotografía referencial de Wikimedia Commons")
    except (OSError, ValueError, KeyError, TypeError): pass
    return None

OUTPUT_DIR = ROOT
OFFLINE = False

def original_cover(article):
    # Portada editorial única, no pretende ser una captura oficial.
    title=article["title"]; key=hashlib.sha256(article["url"].encode()).hexdigest()[:16]
    hue=int(key[:4],16)%360
    lines=textwrap.wrap(title, width=35)[:4]
    if len(textwrap.wrap(title,width=35))>4: lines[-1]=lines[-1].rstrip()+"…"
    words="".join(f'<text x="65" y="{220+i*65}" font-size="48" font-weight="bold">{html.escape(line)}</text>' for i,line in enumerate(lines))
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675"><defs><linearGradient id="g"><stop stop-color="#090e22"/><stop offset="1" stop-color="hsl({hue},65%,30%)"/></linearGradient></defs><rect width="1200" height="675" fill="url(#g)"/><g fill="none" stroke="hsl({hue},90%,70%)" opacity=".65" stroke-width="5"><circle cx="1020" cy="240" r="170"/><circle cx="1020" cy="240" r="120"/><path d="M850 540L1130 260M870 600L1170 300M50 110H1150M50 575H1150"/></g><g fill="white" font-family="sans-serif"><text x="65" y="85" font-size="26">CRAFTI GAMING / {html.escape(article['category'].upper())}</text>{words}<text x="65" y="625" font-size="22">PORTADA EDITORIAL · NO ES UNA CAPTURA DEL JUEGO</text></g></svg>'''
    path=f"portadas/noticia-{key}.svg"; target=OUTPUT_DIR/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(svg,encoding="utf-8")
    return dict(article,image=path,imagen_autor="Crafti Gaming",imagen_tipo="Portada editorial original",imagen_licencia="",imagen_fuente="")

def with_image(article, bank):
    title=article["title"].casefold(); category=article["category"]
    for entry in bank:
        if entry["categoria"] == category and all(entry.get(k) for k in ("autor","licencia","fuente","imagen")) and any(t.casefold() in title for t in entry["palabras_clave"]) and not any(t.casefold() in title for t in entry.get("excluir",[])):
            return dict(article,image=entry["imagen"],imagen_autor=entry["autor"],imagen_licencia=entry["licencia"],imagen_fuente=entry["fuente"],imagen_tipo=entry["tipo"])
    if not OFFLINE:
        for pattern,subject in SUBJECTS:
            if re.search(pattern,title,re.I):
                result=commons_image(subject)
                if result: return dict(article,**result)
                break
    return original_cover(article)

def build_catalog(reviewed, automatic, bank):
    articles = []
    seen = set()
    for article in [*reviewed, *automatic]:
        url = canonical_url(article["url"])
        title_key = re.sub(r"\W+", " ", article["title"].casefold()).strip()
        if not url or not title_key or url in seen or title_key in seen:
            continue
        seen.update((url, title_key))
        articles.append(with_image(dict(article, url=url,
                                       id=hashlib.sha256(url.encode()).hexdigest()[:16]), bank))
    articles.sort(key=lambda article: publication(article["published"]), reverse=True)
    return {"articles": articles}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "news.json")
    parser.add_argument("--offline", action="store_true", help="Usar solo noticias revisadas")
    args = parser.parse_args()
    global OUTPUT_DIR, OFFLINE
    OUTPUT_DIR = args.output.resolve().parent
    OFFLINE = args.offline

    seed = json.loads((ROOT / "news.json").read_text(encoding="utf-8-sig"))
    bank = json.loads((ROOT / "imagenes_autorizadas.json").read_text(encoding="utf-8-sig"))
    reviewed = [article for article in seed["articles"]
                if article.get("tipo_contenido") == "Noticia propia"]
    if not reviewed:
        raise SystemExit("El catálogo revisado está vacío")

    automatic = []
    if not args.offline:
        with ThreadPoolExecutor(max_workers=len(FEEDS)) as executor:
            for articles in executor.map(collect_feed, FEEDS):
                automatic.extend(articles)
        if not automatic:
            print("Fuentes indisponibles. Se publica el catálogo revisado.")
    automatic.sort(key=lambda article: publication(article["published"]), reverse=True)
    catalog = build_catalog(reviewed, automatic[:80], bank["imagenes"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                     dir=args.output.parent) as output:
        json.dump(catalog, output, ensure_ascii=False, indent=2)
        output.write("\n")
    output_path = Path(output.name)
    output_path.chmod(0o644)
    output_path.replace(args.output)
    print(f"Catálogo preparado: {len(catalog['articles'])} entradas")


if __name__ == "__main__":
    main()
