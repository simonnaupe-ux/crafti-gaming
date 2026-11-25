import json
import re
import html
import calendar
import feedparser
from pathlib import Path
from datetime import datetime, timezone

FUENTES = [
    ('Videojuegos', '3DJuegos', 'https://www.3djuegos.com/index.xml'),
    ('Videojuegos', 'Vandal', 'https://vandal.elespanol.com/xml.cgi'),
    ('PlayStation', 'PlayStation Blog', 'https://blog.es.playstation.com/feed/'),
    ('Xbox', 'Xbox Wire', 'https://news.xbox.com/es-latam/feed/'),
    ('Tecnología', 'Xataka', 'https://www.xataka.com/index.xml'),
    ('PC Gaming', 'Steam', 'https://store.steampowered.com/feeds/news.xml'),
]
ESTILOS = {
    'Fortnite': ('#5734a8', '🎮'), 'Nintendo': ('#b0204c', '🍄'),
    'PlayStation': ('#124b9a', '🎮'), 'Xbox': ('#166b3c', '✖'),
    'PC Gaming': ('#14678b', '🖥️'), 'Tecnología': ('#6134a8', '⚡'),
    'Lanzamientos': ('#a83280', '🚀'), 'Videojuegos': ('#5734a8', '🎮'),
}
CARPETA = Path('portadas')
CARPETA.mkdir(exist_ok=True)

def cargar(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        print(f'{ruta}: {error}')
        return defecto

def limpiar(texto):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', str(texto))).split())

def contiene(texto, palabras):
    return any(re.search(r'(?<!\w)' + re.escape(p.casefold()) + r'(?!\w)', texto.casefold()) for p in palabras if p)

TEMAS = {
    'Fortnite': ['fortnite'],
    'Nintendo': ['nintendo', 'nintendo switch', 'super mario', 'zelda', 'pokémon', 'pokemon'],
    'PlayStation': ['playstation', 'ps5', 'ps4'],
    'Xbox': ['xbox', 'game pass'],
    'PC Gaming': ['steam', 'pc gaming', 'tarjeta gráfica', 'gpu', 'geforce', 'radeon'],
    'Lanzamientos': ['lanzamiento', 'fecha de estreno'],
}
GAMER = ['videojuego', 'videojuegos', 'juego', 'juegos', 'gaming', 'gamer', 'consola', 'consolas', 'gta', 'skate', 'esports', 'minecraft', 'tráiler', 'dlc']
TECNO = ['tecnología', 'procesador', 'procesadores', 'smartphone', 'móvil', 'ordenador', 'portátil', 'inteligencia artificial', 'software', 'hardware', 'alexa', 'echo dot', 'android', 'iphone', 'robot', 'robots', 'chip', 'chips', 'monitor', 'internet']
PUBLICIDAD = ['black friday', 'cyber monday', 'contenido patrocinado', 'publirreportaje', 'cupón', 'código descuento', 'chollo', 'mejor precio']

def clasificar(titulo, origen):
    for categoria, palabras in TEMAS.items():
        if categoria != 'Lanzamientos' and contiene(titulo, palabras):
            return categoria
    if contiene(titulo, GAMER):
        return 'Lanzamientos' if contiene(titulo, TEMAS['Lanzamientos']) else 'Videojuegos'
    if contiene(titulo, TECNO):
        return 'Tecnología'
    if origen in ('PlayStation', 'Xbox', 'PC Gaming'):
        return origen
    return None

def crear_portada(categoria):
    color, icono = ESTILOS[categoria]
    ruta = CARPETA / f'categoria-{list(ESTILOS).index(categoria)}.svg'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
    <defs><linearGradient id="f"><stop stop-color="#090b16"/><stop offset="1" stop-color="{color}"/></linearGradient><linearGradient id="r"><stop stop-color="#00eaff"/><stop offset=".5" stop-color="#8455ff"/><stop offset="1" stop-color="#ff32a8"/></linearGradient></defs>
    <rect width="1280" height="720" fill="url(#f)"/>
    <circle cx="980" cy="340" r="240" fill="none" stroke="url(#r)" stroke-width="4" opacity=".4"/>
    <circle cx="980" cy="340" r="195" fill="none" stroke="url(#r)" stroke-width="2" opacity=".3"/>
    <path d="M0 650L650 0H720L0 720Z" fill="#8455ff" opacity=".12"/>
    <text x="980" y="425" text-anchor="middle" font-size="240">{icono}</text>
    <text x="65" y="85" font-family="Arial" font-weight="bold" font-size="30" fill="white">CRAFTI GAMING</text>
    <text x="65" y="620" font-family="Arial" font-weight="bold" font-size="42" fill="url(#r)">{html.escape(categoria.upper())}</text>
    <rect y="710" width="1280" height="10" fill="url(#r)"/></svg>'''
    ruta.write_text(svg, encoding='utf-8')
    return ruta.as_posix()

PORTADAS = {c: crear_portada(c) for c in ESTILOS}
BANCO = cargar('imagenes_autorizadas.json', {}).get('imagenes', [])
EDITORIAL = cargar('articulos_propios.json', {}).get('articulos', [])

def seleccionar_imagen(titulo, categoria):
    for foto in BANCO:
        if foto.get('categoria') != categoria or not foto.get('licencia'):
            continue
        if contiene(titulo, foto.get('excluir', [])):
            continue
        if contiene(titulo, foto.get('palabras_clave', [])) and foto.get('imagen', '').startswith('https://'):
            return foto
    return {'imagen': PORTADAS[categoria], 'autor': 'Crafti Gaming', 'tipo': 'Portada RGB'}

def noticia_base(titulo, categoria, fuente, enlace, timestamp, contenido='', tipo='Enlace a fuente'):
    foto = seleccionar_imagen(titulo, categoria)
    color, icono = ESTILOS[categoria]
    return dict(titulo=titulo, categoria=categoria, fuente=fuente, url=enlace,
        descripcion=contenido.split('\n')[0][:240] if contenido else f'Consulta la noticia original en {fuente}.',
        contenido=contenido, tipo_contenido=tipo, imagen=foto['imagen'],
        imagen_autor=foto.get('autor', ''), imagen_licencia=foto.get('licencia', ''),
        imagen_tipo=foto.get('tipo', ''), imagen_fuente=foto.get('fuente', ''),
        color=color, icono=icono, timestamp=timestamp, destacada=False,
        relevancia=sum(contiene(titulo, [p]) for p in ['nuevo', 'nueva', 'oficial', 'actualización', 'lanzamiento', 'temporada', 'anuncio', 'fortnite']))

noticias = []
vistos = set()
# Solo contenido editorial propio o resúmenes revisados y autorizados.
for articulo in EDITORIAL:
    titulo = limpiar(articulo.get('titulo', ''))
    contenido = articulo.get('contenido', '').strip()
    categoria = articulo.get('categoria', 'Videojuegos')
    enlace = articulo.get('url', '')
    if not titulo or not contenido or categoria not in ESTILOS:
        continue
    try:
        fecha = datetime.fromisoformat(articulo['fecha'].replace('Z', '+00:00'))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        timestamp = int(fecha.timestamp())
    except (KeyError, ValueError):
        timestamp = 0
    noticias.append(noticia_base(titulo, categoria, articulo.get('fuente', 'Crafti Gaming'), enlace, timestamp, contenido, 'Editorial'))
    vistos.add(titulo.casefold())
    if enlace:
        vistos.add(enlace)

for origen, fuente, url in FUENTES:
    try:
        feed = feedparser.parse(url)
        print(f'{fuente}: {len(feed.entries)} entradas')
        for entrada in feed.entries[:25]:
            titulo = limpiar(entrada.get('title', ''))
            enlace = entrada.get('link', '')
            if not titulo or not enlace.startswith(('https://', 'http://')) or contiene(titulo, PUBLICIDAD):
                continue
            if titulo.casefold() in vistos or enlace in vistos:
                continue
            categoria = clasificar(titulo, origen)
            if not categoria:
                continue
            fecha = entrada.get('published_parsed') or entrada.get('updated_parsed')
            timestamp = calendar.timegm(fecha) if fecha else 0
            noticias.append(noticia_base(titulo, categoria, fuente, enlace, timestamp))
            vistos.update([titulo.casefold(), enlace])
    except Exception as error:
        print(f'Error en {fuente}: {error}')

if not noticias:
    raise SystemExit('No se obtuvieron noticias.')
noticias.sort(key=lambda n: n['timestamp'], reverse=True)
noticias = noticias[:60]
candidatas = sorted(noticias[:30], key=lambda n: (n['relevancia'], n['timestamp']), reverse=True)
destacadas = []
categorias = set()
for n in candidatas:
    if n['categoria'] not in categorias:
        destacadas.append(n)
        categorias.add(n['categoria'])
    if len(destacadas) == 6:
        break
for n in candidatas:
    if len(destacadas) == 6:
        break
    if n not in destacadas:
        destacadas.append(n)
for n in destacadas:
    n['destacada'] = True
Path('noticias.json').write_text(json.dumps({'actualizado': datetime.now(timezone.utc).isoformat(), 'noticias': noticias}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Noticias guardadas: {len(noticias)}')
print('Crafti Gaming actualizado.')
