# crafti-gaming
Portal de noticias, lanzamientos y entretenimiento gamer.

## Noticias y publicación

`news.json` contiene las noticias propias revisadas. Cada una incluye el
enlace directo a la fuente, la fecha y el texto original en español.
Para añadir una nota, usa `tipo_contenido: "Noticia propia"` y completa
`title`, `summary`, `contenido`, `published`, `category`, `source` y `url`.

GitHub Actions construye el catálogo público a los minutos 7 y 37 de cada
hora UTC y también admite una ejecución manual. Los enlaces RSS aparecen
como titulares de la fuente. Las imágenes de los feeds se omiten. El
catálogo usa ilustraciones de Crafti Gaming y las imágenes documentadas
en `imagenes_autorizadas.json`, con sus créditos en el lector.

Para generar un catálogo de prueba, ejecuta
`python update_news.py --offline --output /tmp/crafti/news.json`.
Para probar también los feeds, quita `--offline`. Abre el sitio a través
de HTTP, por ejemplo con `python -m http.server 3000`.

En GitHub, la fuente de publicación de Pages debe ser **GitHub Actions**.
