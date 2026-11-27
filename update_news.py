import json, re, urllib.request, xml.etree.ElementTree as ET, html, datetime, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
FEEDS=[('Xbox','Xbox Wire','https://news.xbox.com/en-us/feed/'),('PlayStation','PlayStation Blog','https://blog.playstation.com/feed/'),('Nintendo','Nintendo Life','https://www.nintendolife.com/feeds/latest'),('PC','PC Gamer','https://www.pcgamer.com/feeds.xml'),('Noticias','IGN','https://www.ign.com/rss/v2/articles/feed'),('Noticias','GameSpot','https://www.gamespot.com/feeds/mashup/')]
ns={'media':'http://search.yahoo.com/mrss/','content':'http://purl.org/rss/1.0/modules/content/','atom':'http://www.w3.org/2005/Atom'}
def clean(t):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',t or ''))).strip()
def pic(item):
 for el in item.iter():
  tag=el.tag.split('}')[-1].lower()
  if tag in ('thumbnail','content') and el.tag.startswith('{http://search.yahoo.com/mrss/'):
   u=el.get('url','')
   if u.startswith('https://'):return u
  if tag=='enclosure' and el.get('type','').startswith('image/') and el.get('url','').startswith('https://'):return el.get('url')
 for name in ('description','{http://purl.org/rss/1.0/modules/content/}encoded'):
  raw=item.findtext(name,'')
  m=re.search(r'<img[^>]+src=["\'](https://[^"\']+)',raw)
  if m:return html.unescape(m.group(1))
 return ''
def fetch(category,source,url):
 req=urllib.request.Request(url,headers={'User-Agent':'CraftiGamingNewsBot/1.0 (+public RSS aggregator)'})
 with urllib.request.urlopen(req,timeout=18) as response: raw=response.read(2_000_000)
 doc=ET.fromstring(raw); items=doc.findall('.//item')
 if not items:
  items=doc.findall('.//{http://www.w3.org/2005/Atom}entry')
 out=[]
 for item in items[:20]:
  title=clean(item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title'))
  link=item.findtext('link','')
  if not link:
   l=item.find('{http://www.w3.org/2005/Atom}link');link=l.get('href','') if l is not None else ''
  if not title or not link.startswith('https://'):continue
  desc=clean(item.findtext('description') or item.findtext('summary') or item.findtext('{http://www.w3.org/2005/Atom}summary'))[:220]
  pub=clean(item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}updated'))
  out.append({'id':hashlib.sha256(link.encode()).hexdigest()[:16],'title':title,'url':link,'summary':desc,'image':pic(item),'source':source,'category':category,'published':pub})
 return out
news=[]; errors=[]
for category,source,url in FEEDS:
 try: news+=fetch(category,source,url);print(source,'OK')
 except Exception as exc: errors.append(f'{source}: {exc}');print(source,'ERROR',exc)
oldpath=ROOT/'news.json'
if oldpath.exists():
 try:
  old=json.loads(oldpath.read_text(encoding='utf8'))
  existing={x['id'] for x in news}
  news += [x for x in old.get('articles',[]) if x.get('id') not in existing][:40]
 except Exception:pass
seen=set();unique=[]
for a in news:
 if a['id'] not in seen:seen.add(a['id']);unique.append(a)
if not unique:raise SystemExit('No news retrieved and no cached news available; preserving previous data')
(ROOT/'news.json').write_text(json.dumps({'updated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'articles':unique[:150],'feed_errors':errors},ensure_ascii=False,indent=2),encoding='utf8')
print('Saved',len(unique),'articles')
