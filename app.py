import os, csv, io, json, math, sqlite3, threading, time, hmac
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from flask import Flask, request, jsonify, render_template_string

app=Flask(__name__)
DB=os.getenv('DB_PATH','pronosticos.sqlite3'); TZ=ZoneInfo('America/Asuncion')
# Feed autorizado JSON: lista de encuentros con disponibilidad Apostala confirmada, cuotas y promedios contrastados.
FEED=os.getenv('APOSTALA_FEED_URL',''); TOKEN=os.getenv('APOSTALA_FEED_TOKEN','')
ADMIN_TOKEN=os.getenv('ADMIN_TOKEN','')
def admin_required():
 provided=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
 return bool(ADMIN_TOKEN) and hmac.compare_digest(provided,ADMIN_TOKEN)
SCHEMA='''CREATE TABLE IF NOT EXISTS fixtures (id TEXT PRIMARY KEY, day TEXT, home TEXT, away TEXT, league TEXT, country TEXT, kickoff TEXT, source TEXT, verified_at TEXT, odd_o25 REAL, odd_btts REAL, odd_draw REAL, home_scored REAL, home_conceded REAL, away_scored REAL, away_conceded REAL, n_home INTEGER, n_away INTEGER, red_risk REAL, final_home INTEGER, final_away INTEGER); CREATE TABLE IF NOT EXISTS picks (id TEXT PRIMARY KEY, day TEXT, fixture_id TEXT, market TEXT, probability REAL, odd REAL, edge REAL, status TEXT, created_at TEXT); CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, status TEXT, details TEXT);'''
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 with db() as c:c.executescript(SCHEMA)
def now():return datetime.now(TZ).isoformat(timespec='seconds')
def today():return datetime.now(TZ).date().isoformat()
def pois(k,lam):return math.exp(-lam)*lam**k/math.factorial(k)
def prob(h,a,market):
 if market=='o25':return 1-sum(pois(k,h+a) for k in range(3))
 if market=='btts':return (1-math.exp(-h))*(1-math.exp(-a))
 return sum(pois(k,h)*pois(k,a) for k in range(12))
def analyze(row):
 r=dict(row)
 if not all(r.get(k) is not None for k in ('home_scored','home_conceded','away_scored','away_conceded')):return []
 if min(r.get('n_home') or 0,r.get('n_away') or 0)<5:return []
 h=max(.1,min(4.5,(r['home_scored']+r['away_conceded'])/2*1.07))
 a=max(.1,min(4.5,(r['away_scored']+r['home_conceded'])/2*.94))
 risk=min(.25,max(0,r.get('red_risk') or 0))
 out=[]
 for m,od in [('o25',r['odd_o25']),('btts',r['odd_btts']),('draw',r['odd_draw'])]:
  if not od or od<=1:continue
  p=prob(h,a,m)*(1-risk*.20)
  # Reducción conservadora por incertidumbre muestral; no se declara calibración histórica.
  p=max(0,p-min(.08,1/math.sqrt(min(r['n_home'],r['n_away']))*.12))
  edge=p-1/od
  out.append(dict(id=r['id']+'|'+m,fixture_id=r['id'],day=r['day'],market=m,probability=round(p,4),odd=od,edge=round(edge,4),home=r['home'],away=r['away'],league=r['league'],country=r['country'],kickoff=r['kickoff'],source=r['source'],verified_at=r['verified_at']))
 return out
def ingest(items):
 count=0; rejected=[]
 with db() as c:
  for x in items:
   try:
    if x.get('apostala_confirmed') is not True:raise ValueError('Sin confirmación Apostala')
    if x.get('day')!=today():raise ValueError('Fecha diferente de hoy')
    for k in ('id','home','away','league','country','kickoff','source'):assert x.get(k),'Falta '+k
    vals=[x.get(k) for k in ('id','day','home','away','league','country','kickoff','source')]+[now()]+[x.get(k) for k in ('odd_o25','odd_btts','odd_draw','home_scored','home_conceded','away_scored','away_conceded','n_home','n_away','red_risk')]
    c.execute('''INSERT INTO fixtures(id,day,home,away,league,country,kickoff,source,verified_at,odd_o25,odd_btts,odd_draw,home_scored,home_conceded,away_scored,away_conceded,n_home,n_away,red_risk) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET day=excluded.day,home=excluded.home,away=excluded.away,league=excluded.league,country=excluded.country,kickoff=excluded.kickoff,source=excluded.source,verified_at=excluded.verified_at,odd_o25=excluded.odd_o25,odd_btts=excluded.odd_btts,odd_draw=excluded.odd_draw,home_scored=excluded.home_scored,home_conceded=excluded.home_conceded,away_scored=excluded.away_scored,away_conceded=excluded.away_conceded,n_home=excluded.n_home,n_away=excluded.n_away,red_risk=excluded.red_risk''',vals)
    count+=1
   except Exception as e:rejected.append({'id':x.get('id'),'reason':str(e)})
 return {'accepted':count,'rejected':rejected}
def refresh():
 if not FEED:return {'status':'NO_FEED','details':'Falta configurar feed autorizado de Apostala; no se inventan partidos.'}
 try:
  headers={'Accept':'application/json'}
  if TOKEN:headers['Authorization']='Bearer '+TOKEN
  with urlopen(Request(FEED,headers=headers),timeout=25) as resp:items=json.load(resp)
  if isinstance(items,dict):items=items['fixtures']
  result=ingest(items)
  status='OK' if result['accepted'] else 'EMPTY'
  return {'status':status,'details':result}
 except Exception as e:return {'status':'ERROR','details':str(e)}
def publish():
 day=today()
 with db() as c:
  rows=c.execute('SELECT * FROM fixtures WHERE day=? AND final_home IS NULL',(day,)).fetchall()
  allp=[p for r in rows for p in analyze(r)]
  # Probabilidad + valor, sin inventar una supuesta tasa del 90%; top sin cupos forzosos.
  goals=sorted([p for p in allp if p['market']!='draw' and p['probability']>=.62 and p['edge']>=.015],key=lambda p:(p['probability'],p['edge']),reverse=True)
  draws=sorted([p for p in allp if p['market']=='draw' and p['edge']>=.015],key=lambda p:(p['edge'],p['probability']),reverse=True)
  def diverse(arr,limit):
   out=[]; leagues={};countries={};fixtures=set()
   for p in arr:
    if p['fixture_id'] in fixtures or leagues.get(p['league'],0)>=2 or countries.get(p['country'],0)>=4:continue
    out.append(p);fixtures.add(p['fixture_id']);leagues[p['league']]=leagues.get(p['league'],0)+1;countries[p['country']]=countries.get(p['country'],0)+1
    if len(out)>=limit:break
   return out
  chosen=diverse(goals,10)+diverse(draws,5)
  for p in chosen:
   c.execute('INSERT OR IGNORE INTO picks VALUES (?,?,?,?,?,?,?,?,?)',(p['id']+'|'+day,day,p['fixture_id'],p['market'],p['probability'],p['odd'],p['edge'],'pending',now()))
  return {'goals':len([p for p in chosen if p['market']!='draw']),'draws':len([p for p in chosen if p['market']=='draw']),'reviewed':len(rows)}
def run():
 a=refresh();b=publish()
 with db() as c:c.execute('INSERT INTO runs(at,status,details) VALUES (?,?,?)',(now(),a['status'],json.dumps({'feed':a['details'],'selection':b},ensure_ascii=False)))
 return {'feed':a,'selection':b}
def schedule_loop():
 last=''
 while True:
  n=datetime.now(TZ)
  if n.hour==8 and n.minute<5 and n.date().isoformat()!=last:
   run();last=n.date().isoformat()
  time.sleep(25)
@app.get('/api/status')
def status():
 with db() as c:
  r=c.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
  return jsonify({'today':today(),'time':now(),'feed_configured':bool(FEED),'last_run':dict(r) if r else None})
@app.get('/api/picks')
def picks():
 day=request.args.get('day',today())
 with db() as c:
  data=c.execute('''SELECT p.*,f.home,f.away,f.league,f.country,f.kickoff,f.source,f.verified_at,f.final_home,f.final_away FROM picks p JOIN fixtures f ON f.id=p.fixture_id WHERE p.day=? ORDER BY p.probability DESC''',(day,)).fetchall()
  return jsonify([dict(r) for r in data])
@app.get('/api/history')
def history_api():
 with db() as c:
  data=c.execute('''SELECT p.*,f.home,f.away,f.league,f.country,f.kickoff,f.final_home,f.final_away FROM picks p JOIN fixtures f ON f.id=p.fixture_id WHERE p.day<? ORDER BY p.day DESC,p.created_at DESC LIMIT 200''',(today(),)).fetchall()
  return jsonify([dict(r) for r in data])

@app.post('/api/import')
def imp():
 if not admin_required():return jsonify({'error':'No autorizado'}),401
 if request.content_type and 'text/csv' in request.content_type:
  items=list(csv.DictReader(io.StringIO(request.get_data(as_text=True))))
  for x in items:
   x['apostala_confirmed']=x.get('apostala_confirmed','').lower()=='true'
   for k in ('odd_o25','odd_btts','odd_draw','home_scored','home_conceded','away_scored','away_conceded','n_home','n_away','red_risk'):
    x[k]=float(x[k]) if x.get(k) else None
 else:items=request.get_json(force=True)
 res=ingest(items);res['selection']=publish();return jsonify(res)
@app.post('/api/refresh')
def manual():
 if not admin_required():return jsonify({'error':'No autorizado; la consulta pública solo recarga datos publicados'}),401
 return jsonify(run())
@app.post('/api/result')
def result():
 if not admin_required():return jsonify({'error':'No autorizado'}),401
 x=request.get_json(force=True);h=int(x['home']);a=int(x['away'])
 with db() as c:
  c.execute('UPDATE fixtures SET final_home=?,final_away=? WHERE id=?',(h,a,x['fixture_id']))
  rows=c.execute('SELECT id,market FROM picks WHERE fixture_id=?',(x['fixture_id'],)).fetchall()
  for r in rows:
   won={'o25':h+a>=3,'btts':h>0 and a>0,'draw':h==a}[r['market']]
   c.execute('UPDATE picks SET status=? WHERE id=?',('won' if won else 'lost',r['id']))
 return jsonify({'ok':True})
HTML='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#071426"><meta name="description" content="Análisis diario de goles y empates, con historial verificable"><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/icon.svg" type="image/svg+xml"><title>GOLES & EMPATES · Diario</title><style>\n:root{color-scheme:dark;--bg:#071426;--card:#101f36;--stroke:#273954;--muted:#9db0c9;--mint:#5ef1b3;--gold:#ffd584;--white:#f3f8ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% 0%,#19365a 0%,transparent 45%),var(--bg);font:15px system-ui,-apple-system,Segoe UI,sans-serif;color:var(--white);min-height:100vh}main{max-width:780px;margin:auto;padding:26px 18px 100px}.brand{display:flex;gap:14px;align-items:center}.logo{width:58px;height:58px;display:grid;place-items:center;border-radius:20px;background:linear-gradient(135deg,#50edaf,#1789c8);font-size:29px;box-shadow:0 12px 38px #27cfae33}.eyebrow{font-size:11px;font-weight:800;letter-spacing:2.2px;color:var(--mint)}h1{margin:2px 0;font-size:26px;letter-spacing:-1px}h2{font-size:21px;margin:0 0 6px}.sub,.muted{color:var(--muted)}.sub{margin:18px 0 22px;line-height:1.6}.hero,.card{border:1px solid var(--stroke);background:linear-gradient(145deg,#142b46,#101d33);border-radius:22px;padding:20px;margin:15px 0;box-shadow:0 14px 30px #0002}.hero{background:linear-gradient(120deg,#123b45,#142640 70%)}.row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.pill{font-size:11px;font-weight:800;border-radius:30px;padding:7px 10px;background:#243b51;color:#d6e9fa}.pill.good{color:var(--mint);background:#16483d}.pill.warn{color:var(--gold);background:#483b23}.statgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}.stat{padding:14px 9px;background:#071b2c8c;border:1px solid #35506a;border-radius:15px;text-align:center}.stat strong{display:block;font-size:23px}.stat span{font-size:11px;color:var(--muted)}.tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#0c1b2e;padding:6px;border-radius:17px;margin:22px 0}.tabs button{border:0;background:transparent;color:var(--muted);padding:14px 8px;font-weight:800;border-radius:12px;font-size:14px}.tabs button.active{background:#234b58;color:#79f7c2}.tabs button.draw.active{background:#4a3b5b;color:#e5b7ff}.section{display:none}.section.active{display:block}.pick{border:1px solid var(--stroke);background:var(--card);border-radius:18px;padding:17px;margin:12px 0}.pick .teams{font-weight:800;font-size:17px;margin:12px 0}.meta{font-size:12px;color:var(--muted);line-height:1.6}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.metric{background:#08182b;border-radius:12px;padding:11px 7px;text-align:center}.metric strong{display:block;color:var(--mint);font-size:17px}.metric span{font-size:10px;color:var(--muted)}.empty{text-align:center;padding:40px 17px;border:1px dashed #476079;border-radius:19px;background:#10213a}.empty .emoji{font-size:42px}.empty p{line-height:1.6}.action{width:100%;border:0;border-radius:15px;padding:15px;background:linear-gradient(90deg,#59ecb0,#63c8eb);color:#082035;font-size:15px;font-weight:900;cursor:pointer;margin-top:15px}.action:disabled{opacity:.6}.notice{font-size:12px;line-height:1.65;color:var(--muted);padding:14px;border-left:3px solid #e6c17c;background:#152338;border-radius:9px}.error{color:#ffc4a9}.history{display:flex;gap:12px;flex-wrap:wrap}.history b{color:var(--mint)}.foot{font-size:12px;color:var(--muted);line-height:1.6;margin-top:26px}a{color:#7bdaf5}@media(max-width:380px){h1{font-size:22px}.metrics{gap:4px}.metric{padding:10px 3px}}\n</style></head><body><main><header class="brand"><div class="logo">⚽</div><div><div class="eyebrow">LAROSKA · ANÁLISIS DIARIO</div><h1>GOLES <span style="color:var(--mint)">&</span> EMPATES</h1><div class="muted" style="font-size:12px">Dos mercados. Un solo lugar.</div></div></header><p class="sub">Buscamos oportunidades estadísticas, no partidos al azar. Selecciones sujetas a disponibilidad confirmada en Apostala.</p><section class="hero"><div class="row"><span class="pill" id="day">Cargando fecha…</span><span class="pill warn" id="source">Verificando fuente…</span></div><h2 style="margin-top:20px">Tu análisis del día</h2><div class="muted" id="updated">Hora de actualización programada: 08:00 · Paraguay</div><div class="statgrid"><div class="stat"><strong id="ng">—</strong><span>Goles</span></div><div class="stat"><strong id="nd">—</strong><span>Empates</span></div><div class="stat"><strong id="hit">—</strong><span>Aciertos cerrados</span></div></div><button class="action" id="refresh" onclick="refreshNow()">↻ Consultar datos publicados</button></section><nav class="tabs" aria-label="Mercados"><button class="active" id="tg" onclick="tab(\'g\')">⚽ GOLES HOY</button><button class="draw" id="td" onclick="tab(\'d\')">🤝 EMPATES HOY</button></nav><section id="g" class="section active"><div class="row"><div><h2>⚽ Goles hoy</h2><div class="muted">Más de 2.5 · Ambos marcan</div></div><span class="pill">Hasta 10</span></div><div id="goals"></div></section><section id="d" class="section"><div class="row"><div><h2>🤝 Empates hoy</h2><div class="muted">Equilibrio · Modelo Poisson</div></div><span class="pill">Hasta 5</span></div><div id="draws"></div></section><section class="card"><h2>📊 Historial real</h2><div id="history" class="muted">Cargando…</div></section><div class="notice" id="notice">La programación de las 08:00 requiere servidor activo y una fuente autorizada de Apostala. Sin fuente confirmada no se inventan pronósticos.</div><footer class="foot">Las probabilidades son estimaciones, no garantías de ganar. Cuotas y disponibilidad pueden variar; verificá Apostala antes de tomar decisiones.</footer></main><script>\nconst names={o25:\'Más de 2.5 goles\',btts:\'Ambos marcan\',draw:\'Empate\'};const esc=x=>String(x??\'\').replace(/[&<>"\']/g,c=>({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',"\'":\'&#39;\'}[c]));function tab(t){for(const id of [\'g\',\'d\']){document.getElementById(id).classList.toggle(\'active\',id===t);document.getElementById(\'t\'+id).classList.toggle(\'active\',id===t)}}function empty(){return \'<div class="empty"><div class="emoji">🔎</div><h2>Sin selecciones verificadas</h2><p class="muted">Aún no hay encuentros que cumplan el modelo y estén confirmados en Apostala. No rellenamos la lista con partidos al azar.</p></div>\'}function cards(arr){return arr.length?arr.map((x,i)=>`<article class="pick"><div class="row"><span class="pill">#${i+1} · ${esc(names[x.market])}</span><span class="pill ${x.status===\'won\'?\'good\':x.status===\'lost\'?\'warn\':\'\'}">${x.status===\'won\'?\'🟢 Acertado\':x.status===\'lost\'?\'🔴 Fallado\':\'🟡 Pendiente\'}</span></div><div class="teams">${esc(x.home)} <span class="muted">vs</span> ${esc(x.away)}</div><div class="meta">${esc(x.league)} · ${esc(x.country)}<br>🕒 ${esc(x.kickoff)} · Verificado: ${esc(x.verified_at||\'sin dato\')}</div><div class="metrics"><div class="metric"><strong>${(x.probability*100).toFixed(1)}%</strong><span>Modelo*</span></div><div class="metric"><strong>${Number(x.odd).toFixed(2)}</strong><span>Cuota registrada</span></div><div class="metric"><strong>${x.edge>=0?\'+\':\'\'}${(x.edge*100).toFixed(1)} pp</strong><span>Diferencia vs cuota</span></div></div></article>`).join(\'\'):empty()}async function load(){try{const [sr,pr]=await Promise.all([fetch(\'/api/status\',{cache:\'no-store\'}),fetch(\'/api/picks\',{cache:\'no-store\'})]);if(!sr.ok||!pr.ok)throw Error(\'No responde el servidor\');const s=await sr.json(),p=await pr.json(),past=hr.ok?await hr.json():[];let g=p.filter(x=>x.market!==\'draw\'),d=p.filter(x=>x.market===\'draw\'),done=p.filter(x=>x.status!==\'pending\'),wins=done.filter(x=>x.status===\'won\').length;document.getElementById(\'day\').textContent=\'📅 \'+s.today;document.getElementById(\'source\').textContent=s.feed_configured?\'● Fuente configurada\':\'● Falta conectar Apostala\';document.getElementById(\'source\').className=\'pill \'+(s.feed_configured?\'good\':\'warn\');document.getElementById(\'updated\').textContent=\'Última ejecución: \'+(s.last_run?s.last_run.at+\' · \'+s.last_run.status:\'pendiente\')+\' · 08:00 PY\';document.getElementById(\'ng\').textContent=g.length;document.getElementById(\'nd\').textContent=d.length;document.getElementById(\'hit\').textContent=done.length?(100*wins/done.length).toFixed(0)+\'%\':\'—\';document.getElementById(\'goals\').innerHTML=cards(g);document.getElementById(\'draws\').innerHTML=cards(d);document.getElementById(\'history\').innerHTML=done.length?`<div class="history"><span>🟢 <b>${wins}</b> aciertos</span><span>🔴 ${done.length-wins} fallos</span><span>${done.length} pronósticos cerrados</span></div>`:\'Todavía no hay resultados cerrados.\';document.getElementById(\'notice\').textContent=!s.feed_configured?\'⚠️ Falta conectar una fuente autorizada que confirme partidos en Apostala. La programación diaria por sí sola no puede generar selecciones reales.\':s.last_run?.status===\'ERROR\'?\'⚠️ La última actualización falló. Revisar el proveedor de datos y el servidor.\':\'Actualización programada a las 08:00, hora de Paraguay, mientras el servidor esté activo. Verificá cuotas antes de apostar.\'}catch(e){document.getElementById(\'notice\').textContent=\'⚠️ No se pudo conectar con el servidor: \'+e.message}}async function refreshNow(){let b=document.getElementById(\'refresh\');b.disabled=true;b.textContent=\'Comprobando…\';try{let r=await fetch(\'/api/refresh\',{method:\'POST\'});if(!r.ok)throw Error(\'Error de actualización\');await load()}catch(e){document.getElementById(\'notice\').textContent=\'⚠️ \'+e.message}finally{b.disabled=false;b.textContent=\'↻ Consultar datos publicados\'}}load();setInterval(load,60000);if(\'serviceWorker\'in navigator)navigator.serviceWorker.register(\'/sw.js\').catch(()=>{});\n</script></body></html>'
@app.get('/')
def index():return render_template_string(HTML)
init()
if __name__=='__main__':
 if os.getenv('ENABLE_SCHEDULER','1')=='1':threading.Thread(target=schedule_loop,daemon=True).start()
 app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')),use_reloader=False)

@app.get('/manifest.webmanifest')
def manifest():
 return jsonify({'name':'Goles & Empates Hoy','short_name':'Goles & Empates','start_url':'/','display':'standalone','background_color':'#071426','theme_color':'#071426','icons':[{'src':'/icon.svg','sizes':'any','type':'image/svg+xml','purpose':'any maskable'}]})
@app.get('/icon.svg')
def icon():
 return app.response_class('<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192"><defs><linearGradient id="a"><stop stop-color="#5ef1b3"/><stop offset="1" stop-color="#1789c8"/></linearGradient></defs><rect width="192" height="192" rx="43" fill="#071426"/><circle cx="96" cy="94" r="69" fill="url(#a)"/><text x="96" y="119" font-size="85" text-anchor="middle">⚽</text></svg>',mimetype='image/svg+xml')
@app.get('/sw.js')
def sw():
 return app.response_class("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));",mimetype='application/javascript')
