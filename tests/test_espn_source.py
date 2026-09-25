import unittest
from unittest import mock
import engine.update as e

class ESPNSourceTests(unittest.TestCase):
 def test_primary_scoreboard_parses_real_fixture_and_history(self):
  scoreboard={'events':[{'id':'99','date':'2026-09-25T18:30:00Z','league':{'name':'LaLiga 2'},'competitions':[{'competitors':[{'homeAway':'home','team':{'id':'1','displayName':'Girona'}},{'homeAway':'away','team':{'id':'2','displayName':'Albacete'}}]}]}]}
  def history_for(team_id):
   events=[]
   for i in range(8):
    events.append({'date':f'2026-09-{10+i:02d}T18:00:00Z','competitions':[
     {'status':{'type':{'completed':True}},'competitors':[
      {'homeAway':'home','team':{'id':team_id},'score':2},
      {'homeAway':'away','team':{'id':'opp'},'score':1}]}]})
   return {'events':events}
  def fake(url,timeout=10):
   if 'scoreboard?' in url:return scoreboard
   team_id=url.split('/teams/',1)[1].split('/',1)[0]
   return history_for(team_id)
  with mock.patch.object(e,'ESPN_LEAGUES',{'esp.2':('LaLiga 2','Spain')}),mock.patch.object(e,'fetch_json',side_effect=fake):
   fixtures,analyses,errors=e.fetch_espn('2026-09-25')
  self.assertEqual(len(fixtures),1)
  self.assertEqual(fixtures[0]['_source'],'ESPN')
  self.assertEqual(fixtures[0]['strHomeTeam'],'Girona')
  self.assertEqual(len(analyses),1)
  self.assertGreaterEqual(analyses[0]['muestra'],8)
  self.assertEqual(errors,[])

 def test_one_league_failure_does_not_zero_other_leagues(self):
  good={'events':[{'id':'1','date':'2026-09-25T16:00:00Z','competitions':[{'competitors':[{'homeAway':'home','team':{'id':'a','displayName':'A'}},{'homeAway':'away','team':{'id':'b','displayName':'B'}}]}]}]}
  def fake(url,timeout=10):
   if '/bad/' in url:raise TimeoutError('timeout')
   if 'scoreboard?' in url:return good
   return {'events':[]}
  with mock.patch.object(e,'ESPN_LEAGUES',{'bad':('Bad','X'),'par.1':('Paraguay','Paraguay')}),mock.patch.object(e,'fetch_json',side_effect=fake):
   fixtures,_,errors=e.fetch_espn('2026-09-25')
  self.assertEqual(len(fixtures),1)
  self.assertTrue(errors)

 def test_source_list_contains_today_relevant_competitions(self):
  for slug in ('par.1','bra.2','esp.2','uefa.nations','caf.nations_qual','concacaf.nations.league'):
   self.assertIn(slug,e.ESPN_LEAGUES)

if __name__=='__main__':unittest.main()
