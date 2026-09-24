import unittest,datetime
from unittest import mock
import engine.update as e

class SportmonksTests(unittest.TestCase):
 def test_real_fixture_normalization(self):
  today='2026-09-24'
  payload={'data':[{'id':123,'starting_at':'2026-09-24 15:00:00','participants':[
   {'name':'Local','meta':{'location':'home'}},{'name':'Visita','meta':{'location':'away'}}],
   'league':{'name':'Segunda Division'}},{'id':124,'starting_at':'2026-09-24 15:00:00','participants':[]}]}
  rows=e.sportmonks_rows(payload,today)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['idEvent'],'sportmonks:123')
 def test_no_token_no_network(self):
  with mock.patch.dict('os.environ',{'SPORTMONKS_API_TOKEN':''}),mock.patch.object(e,'fetch_json') as fetch:
   rows,status=e.fetch_sportmonks('2026-09-24')
   self.assertEqual(rows,[])
   self.assertIn('falta',status)
   fetch.assert_not_called()
 def test_two_utc_dates_and_pagination(self):
  urls=[]
  def fake(url):
   urls.append(url)
   return {'data':[],'pagination':{'has_more':False}}
  with mock.patch.object(e,'fetch_json',side_effect=fake):
   rows,status=e.fetch_sportmonks('2026-09-24',token='dummy')
  self.assertEqual(len(urls),2)
  self.assertIn('/date/2026-09-24?',urls[0]);self.assertIn('/date/2026-09-25?',urls[1])
  self.assertEqual(rows,[])
 def test_api_failure_does_not_leak_token(self):
  from urllib.error import HTTPError
  with mock.patch.object(e,'fetch_json',side_effect=HTTPError('secret',401,'bad',None,None)):
   with self.assertRaisesRegex(RuntimeError,'HTTP 401') as err:
    e.fetch_sportmonks('2026-09-24',token='PRIVATE')
   self.assertNotIn('PRIVATE',str(err.exception))
