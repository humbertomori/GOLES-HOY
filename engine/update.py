"""GOLES HOY: publishes only real, supported, pre-match over-2.5 picks."""
import os,json,math,urllib.request,urllib.parse,urllib.error,datetime,pathlib,statistics
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
TZ=ZoneInfo('America/Asuncion')
def poisson_over25(total):
 return 1-math.exp(-total)*(1+total+total*total/2)

def total_for_prob(p):
 lo,hi=0.1,8.
 for _ in range(55):
  mid=(lo+hi)/2
  if poisson_over25(mid)<p: lo=mid
  else: hi=mid
 return (lo+hi)/2

def odds_for_fixture(odds):
 offers=[]
 for book in odds.get('bookmakers',[]):
  for bet in book.get('bets',[]):
   label=bet.get('name','').lower()
   if 'over/under' not in label and 'goals over/under' not in label: continue
   for val in bet.get('values',[]):
    if val.get('value','').lower().strip() in ('over 2.5','over 2,5'):
     try:
      price=float(val['odd'])
      if 1.1<=price<=10: offers.append((price,book.get('name','Casa no indicada')))
     except (ValueError,TypeError,KeyError): pass
 return max(offers,default=None)

def reds(stats):
 """Season red-card total: null means unknown, never claim safe."""
 try:
  cards=stats['cards']['red']
  values=[v.get('total') for v in cards.values() if isinstance(v,dict)]
  if not values or any(v is None for v in values): return None
  return sum(values)
 except (KeyError,TypeError,AttributeError): return None

def played(stats):
 try:return int(stats['fixtures']['played']['total'])
 except (KeyError,TypeError,ValueError):return 0

def avg_goals(stats):
 try:
  f=float(stats['goals']['for']['average']['total']); a=float(stats['goals']['against']['average']['total'])
  return f,a
 except (KeyError,TypeError,ValueError):return None

def league_priority(name):
 n=name.lower()
 if any(w in n for w in ('friendly','amistos','friendlies','u17','u19','u20','u21','reserve','women friendly')):return -100
 if any(w in n for w in ('premier league','la liga','serie a','bundesliga','ligue 1','champions league','europa league','libertadores','sudamericana','brasileirão','primera división')):return 2
 return 0

def status_live_or_done(code):return code not in ('NS','TBD','PST','CANC')

def fetch_json(url, timeout=12):
 req=urllib.request.Request(url,headers={'User-Agent':'GOLES-HOY/2.0 (contact: repository owner)','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as res:
  return json.load(res)

def fetch_schedule(today):
 """Public TheSportsDB free API is a partial schedule, NOT full match coverage."""
 url='https://www.thesportsdb.com/api/v1/json/123/eventsday.php?'+urllib.parse.urlencode({'d':today,'s':'Soccer'})
 raw=fetch_json(url)
 return [e for e in (raw.get('events') or []) if e.get('strSport')=='Soccer' and league_priority((e.get('strLeague') or '')+' '+(e.get('strEvent') or ''))>=0]

def external_fixtures(today):
 """Owner-provided exports from sources with permission; no scraping or fabricated data.
 data/fixture_sources.json: {fecha, fuentes:[{nombre, partidos:[{id,hora,liga,pais,local,visitante}]}]}.
 """
 path=DATA/'fixture_sources.json'
 if not path.exists():return [],[]
 raw=json.loads(path.read_text(encoding='utf8'))
 if raw.get('fecha')!=today:return [],[]
 fixtures=[];sources=[]
 for source in raw.get('fuentes',[]):
  name=str(source.get('nombre','')).strip()
  if not name or not isinstance(source.get('partidos'),list):continue
  sources.append(name)
  for item in source['partidos']:
   try:
    start=datetime.datetime.fromisoformat(str(item['hora']).replace('Z','+00:00'))
    if start.tzinfo is None or start.astimezone(TZ).date().isoformat()!=today:continue
    home=str(item['local']).strip();away=str(item['visitante']).strip()
    if not home or not away:continue
    league=str(item.get('liga') or 'Liga sin indicar')
    if league_priority(league)<0:continue
    fixtures.append({'idEvent':str(item.get('id') or home+'-'+away+'-'+start.isoformat()),
     'strTimestamp':start.isoformat(),'strHomeTeam':home,'strAwayTeam':away,
     'strLeague':league,'strCountry':str(item.get('pais') or 'País sin indicar'),
     '_source':name})
   except (KeyError,TypeError,ValueError):continue
 return fixtures,sources

def fixture_key(row):
 """Deduplicate same matchup/time across feeds without merging different games."""
 import unicodedata,re
 def norm(v):
  s=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode().lower()
  return re.sub(r'[^a-z0-9]','',s)
 try:
  dt=datetime.datetime.fromisoformat(str(row['strTimestamp']).replace('Z','+00:00'))
  return (norm(row['strHomeTeam']),norm(row['strAwayTeam']),dt.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M'))
 except (KeyError,ValueError,TypeError):return ('invalid',str(row.get('idEvent')))

def combine_fixtures(*feeds):
 combined={}
 for feed in feeds:
  for row in feed:
   key=fixture_key(row)
   if key not in combined:combined[key]=dict(row)
   elif row.get('_source'):
    old=combined[key]
    old['_source']=', '.join(dict.fromkeys(filter(None,[old.get('_source'),row['_source']])))
 return list(combined.values())

def validated_feed(today):
 """Optional owner-supplied, licensed analysis feed. No guessed odds/probabilities.
 Format: data/authorized_analysis.json {fecha, partidos:[{id,hora,liga,pais,local,visitante,
 probabilidad,cuota,riesgo_rojas}]}.
 """
 path=DATA/'authorized_analysis.json'
 if not path.exists():return []
 raw=json.loads(path.read_text(encoding='utf8'))
 if raw.get('fecha')!=today:return []
 picks=[];seen=set()
 for row in raw.get('partidos',[]):
  try:
   id_=str(row['id']);prob=float(row['probabilidad']);price=float(row['cuota'])
   hour=datetime.datetime.fromisoformat(str(row['hora']).replace('Z','+00:00'))
   if hour.tzinfo is None:continue
   if hour.astimezone(TZ).date().isoformat()!=today:continue
   if hour.astimezone(TZ)<=datetime.datetime.now(TZ):continue
   league=str(row['liga']);risk=str(row['riesgo_rojas'])
   if league_priority(league)<0 or risk.lower() in ('alto','desconocido','sin datos',''):continue
   if not (62<=prob<=95 and 1.1<=price<=10 and (prob/100)*price>=1.03):continue
   if id_ in seen:continue
   seen.add(id_)
   picks.append({k:row[k] for k in ('id','hora','liga','pais','local','visitante','probabilidad','riesgo_rojas')})
   picks[-1]['probabilidad']=round(prob,1)
   picks[-1]['estado']='pendiente';picks[-1]['resultado']=None
   picks[-1]['_edge']=(prob/100)*price-1
  except (KeyError,ValueError,TypeError,OverflowError):continue
 picks.sort(key=lambda r:(r['_edge'],r['probabilidad'],league_priority(r['liga'])),reverse=True)
 for row in picks:row.pop('_edge')
 return picks[:10]

def visible_schedule(events, now):
 """Real upcoming fixtures, clearly separate from verified predictions."""
 fixtures=[];seen=set()
 for e in events:
  try:
   start=datetime.datetime.fromisoformat(str(e['strTimestamp']).replace('Z','+00:00'))
   if start.tzinfo is None or start.astimezone(TZ)<=now:continue
   if start.astimezone(TZ).date()!=now.date():continue
   home=str(e['strHomeTeam']).strip();away=str(e['strAwayTeam']).strip()
   if not home or not away:continue
   id_=str(e.get('idEvent') or home+'-'+away)
   if id_ in seen:continue
   seen.add(id_)
   fixtures.append({'id':id_,'hora':start.isoformat(),'liga':e.get('strLeague') or 'Liga sin indicar',
     'pais':e.get('strCountry') or 'País sin indicar','local':home,'visitante':away})
  except (KeyError,TypeError,ValueError):continue
 return sorted(fixtures,key=lambda x:x['hora'])

def run():
 now=datetime.datetime.now(TZ);today=now.date().isoformat()
 errors=[];events=[];external=[];source_names=[]
 try:external,source_names=external_fixtures(today)
 except (ValueError,OSError,TypeError) as exc:errors.append('Fuentes complementarias: '+str(exc))
 try:events=fetch_schedule(today)
 except (urllib.error.URLError,TimeoutError,ValueError,OSError) as exc:errors.append('TheSportsDB: '+str(exc))
 events=combine_fixtures(events,external)
 try:picks=validated_feed(today)
 except (ValueError,OSError) as exc:picks=[];errors.append('Fuente autorizada: '+str(exc))
 previous=load_history();indexed={(str(x.get('fecha')),str(x.get('id'))):x for x in previous}
 for row in picks:indexed.setdefault((today,str(row['id'])),dict(row,fecha=today))
 # Free day schedule does not supply comprehensive final scores. Never mark a result guessed.
 history=sorted(indexed.values(),key=lambda x:(x.get('fecha',''),x.get('hora','')),reverse=True)[:2000]
 warning=('Sin pronósticos verificados: la API gratuita ofrece cartelera parcial, no cuotas ni historial suficientes. '
          'Para generar selecciones se necesita análisis y cuotas verificables; la cartelera sola no permite calcular probabilidades.' if not picks else
          'Pronósticos de fuente autorizada; cobertura sujeta a disponibilidad.')
 if errors:warning+=' Fallos de fuentes: '+'; '.join(errors)
 out={'fecha':today,'actualizado':now.isoformat(),'zona':'America/Asuncion',
      'fuente':('TheSportsDB (parcial)' + (' + '+', '.join(source_names) if source_names else '') + (' + análisis autorizado' if picks else '')),
      'mercado':'Más de 2.5 goles','partidos':picks,'cartelera':visible_schedule(events,now),'analizados':len(events),
      'advertencia':warning,'consultas':int(not errors)}
 # Always publish a CURRENT status, including when a source is unavailable.
 # Never re-display yesterday's predictions as current.
 atomic_write('source_health.json',{'consultado':now.isoformat(),'fuente':'TheSportsDB + fuentes complementarias',
  'eventos_muestra':len(events),'fuentes_complementarias':source_names,'estado':'error' if errors else 'cobertura parcial',
  'pronosticos_nuevos':len(picks),'errores':errors})
 atomic_write('history.json',{'partidos':history})
 atomic_write('latest.json',out)
 print('Actualización:',today,'eventos en muestra:',len(events),'pronósticos verificados:',len(picks),
       'errores:',errors)

def free_mode():
 """Legacy entry point for tests; use run() for production."""
 return run()

def atomic_write(name,obj):
 tmp=DATA/(name+'.tmp')
 tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
 tmp.replace(DATA/name)

def load_history():
 path=DATA/'history.json'
 if not path.exists():return []
 try:return json.loads(path.read_text(encoding='utf8')).get('partidos',[])
 except (ValueError,OSError):return []

if __name__=='__main__':
 run()
