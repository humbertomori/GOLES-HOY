import unittest,tempfile,pathlib,json,datetime
from unittest import mock
from zoneinfo import ZoneInfo
import engine.update as e
class MultiSourceTests(unittest.TestCase):
 def test_external_source_real_rows_only(self):
  now=datetime.datetime.now(e.TZ)
  with tempfile.TemporaryDirectory() as tmp,mock.patch.object(e,'DATA',pathlib.Path(tmp)):
   (pathlib.Path(tmp)/'fixture_sources.json').write_text(json.dumps({'fecha':now.date().isoformat(),'fuentes':[{'nombre':'Apostala (exportación autorizada)','partidos':[{'id':'123','hora':now.isoformat(),'liga':'Primera','pais':'PY','local':'A','visitante':'B'}, {'hora':'invalid','local':'C','visitante':'D'}]}]}))
   rows,sources=e.external_fixtures(now.date().isoformat())
   self.assertEqual(len(rows),1)
   self.assertEqual(len(sources),1)
 def test_dedup_across_sources(self):
  row={'idEvent':'1','strTimestamp':'2026-09-24T15:00:00+00:00','strHomeTeam':'São Paulo','strAwayTeam':'Flamengo'}
  other=dict(row,idEvent='other',strHomeTeam='Sao Paulo',_source='Apostala')
  self.assertEqual(len(e.combine_fixtures([row],[other])),1)
 def test_no_guess_from_fixture(self):
  with tempfile.TemporaryDirectory() as tmp,mock.patch.object(e,'DATA',pathlib.Path(tmp)),mock.patch.object(e,'fetch_schedule',return_value=[]):
   now=datetime.datetime.now(e.TZ)
   (pathlib.Path(tmp)/'fixture_sources.json').write_text(json.dumps({'fecha':now.date().isoformat(),'fuentes':[{'nombre':'Diario (exportación autorizada)','partidos':[{'hora':(now+datetime.timedelta(hours=1)).isoformat(),'liga':'Primera','local':'A','visitante':'B'}]}]}))
   e.run()
   result=json.loads((pathlib.Path(tmp)/'latest.json').read_text())
   self.assertEqual(result['partidos'],[])
   self.assertEqual(len(result['cartelera']),1)
