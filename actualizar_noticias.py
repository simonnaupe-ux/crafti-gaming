
import json
import re
import html
import calendar
import feedparser
from pathlib import Path
from datetime import datetime, timezone

FUENTES = [
    ("Videojuegos", "3DJuegos",
     "https://www.3djuegos.com/index.xml", "🎮"),

    ("Videojuegos", "Vandal",
     "https://vandal.elespanol.com/xml.cgi", "🎮"),

    ("PlayStation", "PlayStation Blog",
     "https://blog.es.playstation.com/feed/", "🎮"),

    ("Xbox", "Xbox Wire",
     "https://news.xbox.com/es-latam/feed/", "🎮"),

    ("Tecnología", "Xataka",
     "https://www.xataka.com/index.xml", "⚡"),

    ("PC Gaming", "Steam",
     "https://store.steampowered.com/feeds/news.xml", "🖥️")
]

COLORES = {
    "Fortnite": "#5734a8",
    "Nintendo": "#b0204c",
    "PlayStation": "#124b9a",
    "Xbox": "#166b3c",
    "PC Gaming": "#14678b",
    "Tecnología": "#6134a8",
    "Lanzamientos": "#a83280",
    "Videojuegos": "#5734a8"
}

ARCHIVO = Path("noticias.json")
noticias = []
vistos = set()

def limpiar(texto):
    texto = re.sub(r"<[^>]+>", "", texto)
    return html.unescape(texto).strip()

def clasificar(titulo, categoria):
    texto = titulo.lower()

    if "fortnite" in texto:
        return "Fortnite"

    if any(p in texto for p in [
        "nintendo", "mario", "zelda", "pokémon"
    ]):
        return "Nintendo"

    if any(p in texto for p in [
        "playstation", "ps5", "ps4"
    ]):
        return "PlayStation"

    if "xbox" in texto:
        return "Xbox"

    if any(p in texto for p in [
        "lanzamiento", "fecha de estreno"
    ]):
        return "Lanzamientos"

    return categoria

def relevancia(titulo):
    palabras = [
        "nuevo", "nueva", "oficial", "gratis",
        "actualización", "lanzamiento", "fortnite",
        "nintendo", "steam", "playstation",
        "xbox", "tráiler", "inteligencia artificial"
    ]

    return sum(
        1 for palabra in palabras
        if palabra in titulo.lower()
    )

for categoria, fuente, url, icono in FUENTES:
    try:
        feed = feedparser.parse(url)

        print(f"{fuente}: {len(feed.entries)} entradas")

        for entrada in feed.entries[:20]:
            titulo = limpiar(entrada.get("title", ""))
            enlace = entrada.get("link", "")

            if not titulo or not enlace.startswith(
                ("https://", "http://")
            ):
                continue

            clave = titulo.lower()

            if clave in vistos or enlace in vistos:
                continue

            vistos.add(clave)
            vistos.add(enlace)

            fecha = (
                entrada.get("published_parsed")
                or entrada.get("updated_parsed")
            )

            timestamp = (
                calendar.timegm(fecha) if fecha else 0
            )

            categoria_final = clasificar(
                titulo, categoria
            )

            noticia = {
                "titulo": titulo,
                "categoria": categoria_final,
                "descripcion": f"Consulta la noticia original en {fuente}.",
                "fuente": fuente,
                "url": enlace,
                "icono": icono,
                "color": COLORES.get(
                    categoria_final, "#8455ff"
                ),
                "timestamp": timestamp,
                "relevancia": relevancia(titulo),
                "destacada": False
            }

            noticias.append(noticia)

    except Exception as error:
        print(f"Error en {fuente}: {error}")

if not noticias:
    raise SystemExit(
        "No se obtuvieron noticias. Se conserva el archivo anterior."
    )

noticias.sort(
    key=lambda n: n["timestamp"],
    reverse=True
)

noticias = noticias[:60]

destacadas = sorted(
    noticias[:30],
    key=lambda n: (
        n["relevancia"],
        n["timestamp"]
    ),
    reverse=True
)[:6]

for noticia in destacadas:
    noticia["destacada"] = True

resultado = {
    "actualizado": datetime.now(
        timezone.utc
    ).isoformat(),
    "noticias": noticias
}

ARCHIVO.write_text(
    json.dumps(
        resultado,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(f"Noticias guardadas: {len(noticias)}")
print("Crafti Gaming actualizado correctamente.")
