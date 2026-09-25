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

ESPN_LEAGUES = {
 # Europe first divisions / strong second divisions
 'eng.1':('Premier League','England'),'eng.2':('Championship','England'),
 'esp.1':('LaLiga','Spain'),'esp.2':('LaLiga 2','Spain'),
 'ger.1':('Bundesliga','Germany'),'ger.2':('2. Bundesliga','Germany'),
 'ita.1':('Serie A','Italy'),'ita.2':('Serie B','Italy'),
 'fra.1':('Ligue 1','France'),'fra.2':('Ligue 2','France'),
 'ned.1':('Eredivisie','Netherlands'),'ned.2':('Eerste Divisie','Netherlands'),
 'por.1':('Primeira Liga','Portugal'),'sco.1':('Premiership','Scotland'),'sco.2':('Championship','Scotland'),
 'bel.1':('First Division A','Belgium'),'tur.1':('Super Lig','Turkey'),'gre.1':('Super League','Greece'),
 'den.1':('Superliga','Denmark'),'nor.1':('Eliteserien','Norway'),'swe.1':('Allsvenskan','Sweden'),
 # Americas
 'usa.1':('MLS','USA'),'bra.1':('Serie A','Brazil'),'bra.2':('Serie B','Brazil'),
 'arg.1':('Primera Division','Argentina'),'par.1':('Division Profesional','Paraguay'),
 'col.1':('Primera A','Colombia'),'uru.1':('Primera Division','Uruguay'),'chi.1':('Primera Division','Chile'),
 # international / continental
 'uefa.champions':('Champions League','Europe'),'uefa.europa':('Europa League','Europe'),
 'uefa.europa.conf':('Conference League','Europe'),'uefa.nations':('UEFA Nations League','Europe'),
 'conmebol.libertadores':('Copa Libertadores','South America'),'conmebol.sudamericana':('Copa Sudamericana','South America'),
 'concacaf.nations.league':('CONCACAF Nations League','CONCACAF'),'caf.nations_qual':('Africa Cup of Nations Qualifying','Africa'),
 'rsa.1':('Premiership','South Africa'),'per.1':('Liga 1','Peru'),'bol.1':('Liga Profesional','Bolivia'),'ecu.1':('LigaPro','Ecuador'),
 'irl.1':('Premier Division','Ireland'),'aut.1':('Bundesliga','Austria'),'mex.1':('Liga MX','Mexico'),
 'fifa.friendly':('International Friendly','International'),
}

OPENFOOTBALL_DATASETS = {
 'Premier League':'en.1.json','Championship':'en.2.json','League One':'en.3.json','League Two':'en.4.json',
 'Bundesliga':'de.1.json','2. Bundesliga':'de.2.json','3. Liga':'de.3.json',
 'La Liga':'es.1.json','Segunda División':'es.2.json','Serie A':'it.1.json','Serie B':'it.2.json',
 'Ligue 1':'fr.1.json','Ligue 2':'fr.2.json','Eredivisie':'nl.1.json','Primeira Liga':'pt.1.json',
}

def _season_for(day):
 d=datetime.date.fromisoformat(day)
 return f'{d.year}-{str(d.year+1)[-2:]}' if d.month>=7 else f'{d.year-1}-{str(d.year)[-2:]}'

def _team_stats(matches, team, before):
 rows=[]
 for m in matches:
  if str(m.get('date',''))>=before: continue
  ft=(m.get('score') or {}).get('ft')
  if not isinstance(ft,list) or len(ft)!=2: continue
  if team not in (m.get('team1'),m.get('team2')): continue
  try:a,b=float(ft[0]),float(ft[1])
  except (TypeError,ValueError):continue
  gf,ga=(a,b) if m.get('team1')==team else (b,a)
  rows.append((str(m.get('date','')),gf,ga))
 rows.sort(reverse=True)
 return rows[:8]

def _probabilities(home_rows, away_rows):
 if len(home_rows)<4 or len(away_rows)<4:return None
 rows=home_rows+away_rows
 avg_total=sum(gf+ga for _,gf,ga in rows)/len(rows)
 p_poisson=poisson_over25(avg_total)
 p_over=sum((gf+ga)>2.5 for _,gf,ga in rows)/len(rows)
 p_btts=sum(gf>0 and ga>0 for _,gf,ga in rows)/len(rows)
 completeness=min(1.0,len(rows)/16)
 over=(0.55*p_over+0.45*p_poisson)*(0.92+0.08*completeness)
 btts=p_btts*(0.92+0.08*completeness)
 return round(over*100,1),round(btts*100,1),len(rows)

def _espn_competitors(event):
 try:comps=event['competitions'][0]['competitors']
 except (KeyError,IndexError,TypeError):return None
 out={}
 for c in comps:
  side=c.get('homeAway')
  team=c.get('team') or {}
  if side in ('home','away') and team.get('displayName'):
   out[side]={'id':str(team.get('id') or ''),'name':str(team['displayName']).strip()}
 return out if 'home' in out and 'away' in out else None

def _score_number(c):
 v=c.get('score')
 if isinstance(v,dict):v=v.get('value',v.get('displayValue'))
 try:return float(v)
 except (TypeError,ValueError):return None

def _espn_recent(league, team_id, before_iso):
 """Recent completed team matches from ESPN public site feed; no key/token."""
 if not team_id:return []
 url=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/schedule'
 raw=fetch_json(url,timeout=10);rows=[]
 for ev in raw.get('events') or []:
  if str(ev.get('date') or '')>=before_iso:continue
  try:comp=ev['competitions'][0]
  except (KeyError,IndexError,TypeError):continue
  status=((comp.get('status') or {}).get('type') or {})
  if not status.get('completed'):continue
  mine=None;opp=None
  for c in comp.get('competitors') or []:
   if str((c.get('team') or {}).get('id') or '')==team_id:mine=c
   else:opp=c
  if not mine or not opp:continue
  gf,ga=_score_number(mine),_score_number(opp)
  if gf is None or ga is None:continue
  rows.append((str(ev.get('date') or ''),gf,ga))
 rows.sort(reverse=True)
 return rows[:8]

def fetch_espn(today):
 """Primary daily fixture feed. ESPN site JSON requires no API key; failures are isolated per competition."""
 ymd=today.replace('-','');fixtures=[];analyses=[];errors=[]
 for slug,(fallback_name,country) in ESPN_LEAGUES.items():
  url=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={ymd}'
  try:raw=fetch_json(url,timeout=10)
  except Exception as exc:
   errors.append(f'ESPN {slug}: {type(exc).__name__}');continue
  for ev in raw.get('events') or []:
   teams=_espn_competitors(ev)
   if not teams:continue
   start=str(ev.get('date') or '')
   try:
    dt=datetime.datetime.fromisoformat(start.replace('Z','+00:00'))
    if dt.astimezone(TZ).date().isoformat()!=today:continue
   except ValueError:continue
   league=((ev.get('league') or {}).get('name') or fallback_name)
   if league_priority(league)<0:continue
   ident='espn:'+str(ev.get('id') or slug+':'+teams['home']['name']+':'+teams['away']['name'])
   fixtures.append({'idEvent':ident,'strDate':today,'strTimestamp':start,'strHomeTeam':teams['home']['name'],
    'strAwayTeam':teams['away']['name'],'strLeague':league,'strCountry':country,'_source':'ESPN'})
   # Do not guess. Analyze only when both teams have enough completed history.
   try:
    hr=_espn_recent(slug,teams['home']['id'],start); ar=_espn_recent(slug,teams['away']['id'],start)
    probs=_probabilities(hr,ar)
   except Exception as exc:
    errors.append(f'ESPN historial {slug}: {type(exc).__name__}');probs=None
   if probs:
    po,pb,n=probs
    analyses.append({'id':ident,'hora':start,'liga':league,'pais':country,'local':teams['home']['name'],
     'visitante':teams['away']['name'],'prob_mas_2_5':po,'prob_btts':pb,'muestra':n,'fuente':'ESPN'})
 return fixtures,analyses,errors

def fetch_openfootball(today):
 """Fallback fixture/history source. Public-domain JSON, no key."""
 season=_season_for(today);fixtures=[];analyses=[];errors=[]
 base=f'https://raw.githubusercontent.com/openfootball/football.json/master/{season}/'
 for league,filename in OPENFOOTBALL_DATASETS.items():
  try:raw=fetch_json(base+filename)
  except Exception as exc:errors.append(f'OpenFootball {league}: {type(exc).__name__}');continue
  matches=raw.get('matches') or []
  for m in matches:
   if str(m.get('date',''))!=today:continue
   home=str(m.get('team1') or '').strip();away=str(m.get('team2') or '').strip()
   if not home or not away:continue
   ident=f'openfootball:{filename}:{today}:{home}:{away}'
   fixtures.append({'idEvent':ident,'strDate':today,'strTimestamp':None,'strHomeTeam':home,'strAwayTeam':away,
    'strLeague':league,'strCountry':'','_source':'OpenFootball'})
   probs=_probabilities(_team_stats(matches,home,today),_team_stats(matches,away,today))
   if probs:
    po,pb,n=probs
    analyses.append({'id':ident,'hora':today+'T12:00:00-03:00','liga':league,'pais':'','local':home,'visitante':away,
     'prob_mas_2_5':po,'prob_btts':pb,'muestra':n,'fuente':'OpenFootball'})
 return fixtures,analyses,errors

def fetch_schedule(today):
 """Compatibility wrapper: ESPN primary + OpenFootball fallback, both without paid API/key."""
 ef,ea,ee=fetch_espn(today)
 of,oa,oe=fetch_openfootball(today)
 fixtures=combine_fixtures(ef,of)
 # Prefer ESPN analyses; OpenFootball fills competitions ESPN did not analyze.
 seen={(x['local'].lower(),x['visitante'].lower()) for x in ea}
 analyses=ea+[x for x in oa if (x['local'].lower(),x['visitante'].lower()) not in seen]
 return fixtures,analyses,ee+oe

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
 fixtures=[];seen=set()
 for e in events:
  try:
   date=str(e.get('strDate') or '')
   ts=e.get('strTimestamp')
   if ts:
    start=datetime.datetime.fromisoformat(str(ts).replace('Z','+00:00'))
    if start.tzinfo:
     local=start.astimezone(TZ)
     if local.date()!=now.date() or local<=now:continue
     hour=local.strftime('%H:%M')
    else:
     if start.date()!=now.date() or start<=now.replace(tzinfo=None):continue
     hour=start.strftime('%H:%M')
   else:
    if date!=now.date().isoformat():continue
    hour='Horario no disponible'
   home=str(e['strHomeTeam']).strip();away=str(e['strAwayTeam']).strip()
   id_=str(e.get('idEvent') or home+'-'+away)
   if not home or not away or id_ in seen:continue
   seen.add(id_)
   fixtures.append({'id':id_,'hora':hour,'liga':e.get('strLeague') or 'Liga sin indicar',
    'pais':e.get('strCountry') or '','local':home,'visitante':away,'fuente':e.get('_source','OpenFootball')})
  except (KeyError,TypeError,ValueError):continue
 return fixtures

def run():
 now=datetime.datetime.now(TZ);today=now.date().isoformat();errors=[]
 try:events,analyses,source_errors=fetch_schedule(today);errors.extend(source_errors)
 except Exception as exc:events=[];analyses=[];errors.append('Fuentes automáticas: '+str(exc))
 try:external,source_names=external_fixtures(today)
 except Exception as exc:external=[];source_names=[];errors.append('Fuentes complementarias: '+str(exc))
 events=combine_fixtures(events,external)
 # Automatic ranking: separate +2.5 and BTTS. Do not fill artificially.
 candidates=[]
 for r in analyses:
  best=max(r['prob_mas_2_5'],r['prob_btts'])
  if best<62:continue
  market='Más de 2.5' if r['prob_mas_2_5']>=r['prob_btts'] else 'Ambos marcan'
  prob=r['prob_mas_2_5'] if market=='Más de 2.5' else r['prob_btts']
  x=dict(r,mercado=market,probabilidad=prob,estado='pendiente',resultado=None)
  candidates.append(x)
 candidates.sort(key=lambda x:(x['probabilidad'],x['muestra']),reverse=True)
 # diversity caps: max 2 per competition, max 4 per country when country is known
 picks=[];by_league={};by_country={}
 for x in candidates:
  lg=x['liga'];ct=x.get('pais') or ''
  if by_league.get(lg,0)>=2 or (ct and by_country.get(ct,0)>=4):continue
  picks.append(x);by_league[lg]=by_league.get(lg,0)+1
  if ct:by_country[ct]=by_country.get(ct,0)+1
  if len(picks)>=10:break
 warning=('Análisis automático calculado con datos públicos disponibles de ESPN/OpenFootball. '
          'Las probabilidades son estimaciones estadísticas, no garantías. No se inventan cuotas: si no hay una fuente verificable, no se muestran.')
 if not events: warning+=' No se encontraron partidos en las ligas cubiertas; esto no significa que no haya fútbol hoy.'
 if errors: warning+=' Incidencias de fuentes: '+'; '.join(errors[:5])
 out={'fecha':today,'actualizado':now.isoformat(),'zona':'America/Asuncion','fuente':'ESPN + OpenFootball (respaldo)',
      'mercados':['Más de 2.5 goles','Ambos marcan'],'partidos':picks,'cartelera':visible_schedule(events,now),
      'recibidos':len(events),'analizados':len(analyses),'seleccionados':len(picks),'advertencia':warning}
 atomic_write('source_health.json',{'consultado':now.isoformat(),'fuente':'ESPN + OpenFootball','recibidos':len(events),
  'analizados':len(analyses),'seleccionados':len(picks),'estado':'error' if not events and errors else ('sin partidos cubiertos' if not events else 'ok'),
  'errores':errors[:20]})
 atomic_write('latest.json',out)
 print('Actualización:',today,'recibidos:',len(events),'analizados:',len(analyses),'seleccionados:',len(picks))
 return out

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
