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
from urllib.parse import urlsplit, urlunsplit
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
            "summary": f"Consulta la publicación de {source} para conocer los detalles.",
            "tipo_contenido": "Titular de la fuente",
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


def with_image(article, bank):
    title = article["title"].casefold()
    category = article["category"]
    for image in bank:
        if (image["categoria"] == category
                and all(image.get(key) for key in ("autor", "licencia", "fuente", "imagen"))
                and any(term.casefold() in title for term in image["palabras_clave"])
                and not any(term.casefold() in title for term in image.get("excluir", []))):
            return dict(article, image=image["imagen"], imagen_autor=image["autor"],
                        imagen_licencia=image["licencia"], imagen_fuente=image["fuente"],
                        imagen_tipo=image["tipo"])
    path = f"portadas/categoria-{COVER[category]}.svg"
    if not (ROOT / path).is_file():
        raise ValueError(f"Falta {path}")
    return dict(article, image=path, imagen_autor="Crafti Gaming",
                imagen_tipo="Ilustración temática propia")


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
