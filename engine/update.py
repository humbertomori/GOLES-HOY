"""GOLES HOY: publishes only real, supported, pre-match over-2.5 picks."""
import os,json,math,urllib.request,urllib.parse,urllib.error,datetime,pathlib,statistics
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
TZ=ZoneInfo('America/Asuncion')
API='https://v3.football.api-sports.io/'
KEY=os.getenv('API_FOOTBALL_KEY','')
MAX_CALLS=int(os.getenv('MAX_API_CALLS','44'))
COUNT=0

def get(endpoint,params):
 global COUNT
 if not KEY: raise RuntimeError('Falta API_FOOTBALL_KEY (GitHub Actions secret)')
 if COUNT>=MAX_CALLS: raise RuntimeError('Presupuesto de consultas agotado; se conserva publicación anterior')
 url=API+endpoint+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'x-apisports-key':KEY,'Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=24) as res: raw=json.load(res)
 COUNT+=1
 if raw.get('errors'): raise RuntimeError('API-FOOTBALL: '+str(raw['errors']))
 return raw

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

def run():
 now=datetime.datetime.now(TZ); today=now.date().isoformat()
 fixtures=get('fixtures',{'date':today,'timezone':'America/Asuncion'}).get('response',[])
 upcoming=[]
 for item in fixtures:
  fix=item.get('fixture',{}); lg=item.get('league',{}); teams=item.get('teams',{})
  if fix.get('status',{}).get('short')!='NS' or league_priority(lg.get('name',''))<0:continue
  if not (teams.get('home',{}).get('id') and teams.get('away',{}).get('id')):continue
  upcoming.append(item)
 # Pre-screen using country/competition priority; evaluate only a capped candidate pool to respect API limits.
 upcoming.sort(key=lambda x:(league_priority(x['league'].get('name','')),x['fixture'].get('date','')),reverse=True)
 upcoming=upcoming[:max(0,(MAX_CALLS-4)//3)]
 # Fetch odds by fixture for shortlisted matches; API free tier cannot cover entire global slate exhaustively.
 candidates=[]
 for item in upcoming:
  f=item['fixture']; league=item['league']; home=item['teams']['home']; away=item['teams']['away']
  try:
   odds_raw=get('odds',{'fixture':f['id']}).get('response',[])
   best=max((offer for row in odds_raw if (offer:=odds_for_fixture(row))),default=None)
   if not best:continue
   hs=get('teams/statistics',{'league':league['id'],'season':league['season'],'team':home['id']}).get('response',{})
   aw=get('teams/statistics',{'league':league['id'],'season':league['season'],'team':away['id']}).get('response',{})
   hp,ap=played(hs),played(aw)
   hr,ar=reds(hs),reds(aw)
   hga,aga=avg_goals(hs),avg_goals(aw)
   if min(hp,ap)<6 or hr is None or ar is None or hga is None or aga is None:continue
   # Conservative discipline screen: >0.20 red cards / match combined excluded.
   if hr/hp+ar/ap>0.20:continue
   lam=(hga[0]+aga[1]+aga[0]+hga[1])/2
   if not (1.5<=lam<=5.5):continue
   p=poisson_over25(lam)
   price,book=best
   edge=p*price-1
   if p<0.62 or edge<0.03:continue
   candidates.append({'id':f['id'],'hora':f['date'],'liga':league['name'],'pais':league.get('country',''),
    'local':home['name'],'visitante':away['name'],'probabilidad':round(p*100,1),'cuota':price,
    'casa':book,'valor_estimado':round(edge*100,1),'riesgo_rojas':'Filtrado por rojas de temporada',
    'rojas_por_partido':round(hr/hp+ar/ap,3),'goles_esperados':round(lam,2),
    'estado':'pendiente','resultado':None,'prioridad':league_priority(league['name'])})
  except (TimeoutError,urllib.error.URLError,KeyError,ValueError,TypeError,RuntimeError) as exc:
   print('Omitido fixture',f.get('id'),str(exc))
 # Keep best value among qualifying matches; competition priority is a tiebreaker.
 candidates.sort(key=lambda x:(x['valor_estimado'],x['probabilidad'],x['prioridad']),reverse=True)
 selected=candidates[:10]
 old={}
 historyfile=DATA/'history.json'
 if historyfile.exists():
  old=json.loads(historyfile.read_text(encoding='utf8'))
 history=old.get('partidos',[])
 indexed={(x['fecha'],x['id']):x for x in history}
 for x in selected:
  record={k:v for k,v in x.items() if k!='prioridad'}
  record['fecha']=today
  indexed.setdefault((today,x['id']),record)
 # Check results for previous picks and same-day picks with one batch fixture call per 20 ids.
 pending=[x for x in indexed.values() if x.get('estado')=='pendiente']
 for pos in range(0,min(len(pending),40),20):
  batch=pending[pos:pos+20]
  if COUNT>=MAX_CALLS:break
  try:
   rows=get('fixtures',{'ids':'-'.join(str(x['id']) for x in batch)}).get('response',[])
   for row in rows:
    fix=row['fixture']; score=row.get('goals',{}); code=fix['status']['short']
    if code not in ('FT','AET','PEN'):continue
    if score.get('home') is None or score.get('away') is None:continue
    key=(datetime.datetime.fromisoformat(fix['date'].replace('Z','+00:00')).astimezone(TZ).date().isoformat(),fix['id'])
    rec=indexed.get(key)
    if rec:
     total=score['home']+score['away'];rec['estado']='acertado' if total>=3 else 'fallido'
     rec['resultado']=f"{score['home']}-{score['away']}"
  except (urllib.error.URLError,ValueError,KeyError,TypeError,RuntimeError) as exc:print('Historial no actualizado:',exc)
 history=sorted(indexed.values(),key=lambda x:(x['fecha'],x['hora']),reverse=True)[:2000]
 # Write atomically, only after all mandatory upstream queries succeeded.
 out={'fecha':today,'actualizado':now.isoformat(),'zona':'America/Asuncion','fuente':'API-FOOTBALL',
  'mercado':'Más de 2.5 goles','partidos':[{k:v for k,v in x.items() if k!='prioridad'} for x in selected],
  'analizados':len(upcoming),'advertencia':('Menos de 10 partidos superaron los filtros o tuvieron datos completos' if len(selected)<10 else ''),
  'consultas':COUNT}
 for name,obj in [('history.json',{'partidos':history}),('latest.json',out)]:
  tmp=DATA/(name+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(DATA/name)
 print('Publicado',len(selected),'partidos; consultas',COUNT)
def free_mode():
 """Real fixtures from TheSportsDB; NO predictions without verified odds/history."""
 now=datetime.datetime.now(TZ);today=now.date().isoformat()
 url='https://www.thesportsdb.com/api/v1/json/123/eventsday.php?'+urllib.parse.urlencode({'d':today,'s':'Soccer'})
 req=urllib.request.Request(url,headers={'User-Agent':'GolesHoy/1.0'})
 with urllib.request.urlopen(req,timeout=18) as res: raw=json.load(res)
 events=raw.get('events') or []
 valid=[e for e in events if e.get('strSport')=='Soccer' and league_priority((e.get('strLeague') or '')+' '+(e.get('strEvent') or ''))>=0]
 # A fallback must NEVER replace valid picks with an empty selection.
 # Keep the previous publication, and expose source health in a separate file.
 health={'consultado':now.isoformat(),'fuente':'TheSportsDB','eventos_muestra':len(valid),
         'estado':'solo respaldo; cobertura parcial; sin cuotas verificadas',
         'pronosticos_nuevos':0}
 atomic_write('source_health.json',health)
 if not (DATA/'latest.json').exists():
  out={'fecha':today,'actualizado':now.isoformat(),'zona':'America/Asuncion',
       'fuente':'TheSportsDB (modo gratuito)','mercado':'Más de 2.5 goles',
       'partidos':[],'analizados':len(valid),
       'advertencia':'Sin pronósticos verificados: falta fuente autorizada de cuotas e historial suficiente. La cartelera gratuita es parcial.',
       'consultas':1}
  atomic_write('latest.json',out)
 print('Respaldo consultado:',len(valid),'eventos; no se reemplazan pronósticos previos')

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
 if KEY:run()
 else:free_mode()
