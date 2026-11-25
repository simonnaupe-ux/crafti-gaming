
import json
import re
import html
import calendar
import feedparser
from pathlib import Path
from datetime import datetime, timezone

FUENTES = [
    ("Videojuegos", "3DJuegos",
     "https://www.3djuegos.com/index.xml"),

    ("Videojuegos", "Vandal",
     "https://vandal.elespanol.com/xml.cgi"),

    ("PlayStation", "PlayStation Blog",
     "https://blog.es.playstation.com/feed/"),

    ("Xbox", "Xbox Wire",
     "https://news.xbox.com/es-latam/feed/"),

    ("Tecnología", "Xataka",
     "https://www.xataka.com/index.xml"),

    ("PC Gaming", "Steam",
     "https://store.steampowered.com/feeds/news.xml")
]

ESTILOS = {
    "Fortnite": ("#5734a8", "🎮"),
    "Nintendo": ("#b0204c", "🍄"),
    "PlayStation": ("#124b9a", "🎮"),
    "Xbox": ("#166b3c", "✖"),
    "PC Gaming": ("#14678b", "🖥️"),
    "Tecnología": ("#6134a8", "⚡"),
    "Lanzamientos": ("#a83280", "🚀"),
    "Videojuegos": ("#5734a8", "🎮")
}

ARCHIVO = Path("noticias.json")
CARPETA = Path("portadas")
CARPETA.mkdir(exist_ok=True)

# Añadir aquí imágenes con permiso de reutilización.
IMAGENES_AUTORIZADAS = {}

noticias = []
vistos = set()

def limpiar(texto):
    return html.unescape(
        re.sub(r"<[^>]+>", "", texto)
    ).strip()

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

    if any(p in texto for p in [
        "steam", "pc gaming", "tarjeta gráfica"
    ]):
        return "PC Gaming"

    return categoria

def es_publicidad(titulo):
    palabras = [
        "black friday",
        "cyber monday",
        "contenido patrocinado",
        "publirreportaje",
        "caixabank",
        "cupón",
        "código descuento",
        "oferta exclusiva",
        "chollo",
        "mejor precio"
    ]

    return any(
        palabra in titulo.lower()
        for palabra in palabras
    )

def relevancia(titulo):
    palabras = [
        "nuevo", "nueva", "oficial",
        "actualización", "lanzamiento",
        "fortnite", "nintendo", "steam",
        "playstation", "xbox", "tráiler",
        "inteligencia artificial",
        "temporada", "anuncio", "innovación"
    ]

    return sum(
        palabra in titulo.lower()
        for palabra in palabras
    )

def crear_portada(categoria):
    color, icono = ESTILOS.get(
        categoria, ("#8455ff", "🎮")
    )

    nombre = list(ESTILOS).index(categoria)
    ruta = CARPETA / f"categoria-{nombre}.svg"

    etiqueta = html.escape(categoria.upper())

    svg = f'''
    <svg xmlns="http://www.w3.org/2000/svg"
         width="1280" height="720"
         viewBox="0 0 1280 720">

      <defs>
        <linearGradient id="fondo">
          <stop stop-color="#090b16"/>
          <stop offset="1" stop-color="{color}"/>
        </linearGradient>

        <linearGradient id="rgb">
          <stop stop-color="#00eaff"/>
          <stop offset=".5" stop-color="#8455ff"/>
          <stop offset="1" stop-color="#ff32a8"/>
        </linearGradient>

        <pattern id="grid" width="65" height="65"
                 patternUnits="userSpaceOnUse">
          <path d="M65 0H0V65"
                fill="none"
                stroke="#ffffff"
                stroke-opacity=".06"/>
        </pattern>
      </defs>

      <rect width="1280" height="720"
            fill="url(#fondo)"/>

      <rect width="1280" height="720"
            fill="url(#grid)"/>

      <circle cx="980" cy="340" r="240"
              fill="none" stroke="url(#rgb)"
              stroke-width="4" opacity=".4"/>

      <circle cx="980" cy="340" r="195"
              fill="none" stroke="url(#rgb)"
              stroke-width="2" opacity=".3"/>

      <path d="M0 650L650 0H720L0 720Z"
            fill="#8455ff" opacity=".12"/>

      <path d="M1280 100L650 720H720L1280 170Z"
            fill="#00eaff" opacity=".15"/>

      <text x="980" y="425"
            text-anchor="middle"
            font-size="240">{icono}</text>

      <text x="65" y="85"
            font-family="Arial"
            font-weight="bold"
            font-size="30"
            fill="#ffffff">CRAFTI GAMING</text>

      <text x="65" y="620"
            font-family="Arial"
            font-weight="bold"
            font-size="42"
            fill="url(#rgb)">{etiqueta}</text>

      <rect x="0" y="710"
            width="1280" height="10"
            fill="url(#rgb)"/>
    </svg>
    '''

    ruta.write_text(svg, encoding="utf-8")
    return str(ruta)

PORTADAS = {
    categoria: crear_portada(categoria)
    for categoria in ESTILOS
}

for categoria, fuente, url in FUENTES:
    try:
        feed = feedparser.parse(url)

        print(f"{fuente}: {len(feed.entries)} entradas")

        for entrada in feed.entries[:25]:

            titulo = limpiar(
                entrada.get("title", "")
            )

            enlace = entrada.get("link", "")

            if not titulo or not enlace.startswith(
                ("https://", "http://")
            ):
                continue

            if es_publicidad(titulo):
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
                calendar.timegm(fecha)
                if fecha else 0
            )

            categoria_final = clasificar(
                titulo, categoria
            )

            color, icono = ESTILOS.get(
                categoria_final,
                ("#8455ff", "🎮")
            )

            imagen = IMAGENES_AUTORIZADAS.get(
                enlace,
                PORTADAS[categoria_final]
            )

            noticia = {
                "titulo": titulo,
                "categoria": categoria_final,
                "descripcion":
                    f"Consulta la noticia original en {fuente}.",
                "fuente": fuente,
                "url": enlace,
                "imagen": imagen,
                "icono": icono,
                "color": color,
                "timestamp": timestamp,
                "relevancia": relevancia(titulo),
                "destacada": False
            }

            noticias.append(noticia)

    except Exception as error:
        print(f"Error en {fuente}: {error}")

if not noticias:
    raise SystemExit(
        "No se obtuvieron noticias."
    )

noticias.sort(
    key=lambda n: n["timestamp"],
    reverse=True
)

noticias = noticias[:60]

candidatas = sorted(
    noticias[:30],
    key=lambda n: (
        n["relevancia"],
        n["timestamp"]
    ),
    reverse=True
)

destacadas = []
categorias_usadas = set()

for noticia in candidatas:
    categoria = noticia["categoria"]

    if categoria not in categorias_usadas:
        destacadas.append(noticia)
        categorias_usadas.add(categoria)

    if len(destacadas) == 6:
        break

for noticia in candidatas:
    if len(destacadas) == 6:
        break

    if noticia not in destacadas:
        destacadas.append(noticia)

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
print("Portadas RGB generadas.")
print("Crafti Gaming actualizado.")
