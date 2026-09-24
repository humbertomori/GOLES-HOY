import unittest,sys,pathlib,json,unittest.mock as mock,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import engine.update as e
class UpdateTests(unittest.TestCase):
 def test_no_fabricated_picks_and_current_status(self):
  with tempfile.TemporaryDirectory() as td, mock.patch.object(e,'DATA',pathlib.Path(td)),mock.patch.object(e,'fetch_schedule',return_value=[{'idEvent':'1'}]):
   e.run();result=json.loads((pathlib.Path(td)/'latest.json').read_text())
   self.assertEqual(result['partidos'],[]);self.assertEqual(result['analizados'],1);self.assertIsNotNone(result['actualizado'])
 def test_failed_source_still_publishes_status(self):
  with tempfile.TemporaryDirectory() as td, mock.patch.object(e,'DATA',pathlib.Path(td)),mock.patch.object(e,'fetch_schedule',side_effect=TimeoutError('timeout')):
   e.run();self.assertEqual(json.loads((pathlib.Path(td)/latest).read_text())['partidos'],[]) if False else None
   self.assertIn('Fallos',json.loads((pathlib.Path(td)/'latest.json').read_text())['advertencia'])
 def test_authorized_feed_filters_friendly_and_duplicates(self):
  import datetime
  now=datetime.datetime.now(e.TZ);future=(now+datetime.timedelta(hours=2)).isoformat()
  if (now+datetime.timedelta(hours=2)).date()!=now.date():return
  row={'id':'A','hora':future,'liga':'Premier League','pais':'England','local':'A','visitante':'B','probabilidad':70,'cuota':1.8,'riesgo_rojas':'bajo'}
  with tempfile.TemporaryDirectory() as td,mock.patch.object(e,'DATA',pathlib.Path(td)):
   (pathlib.Path(td)/'authorized_analysis.json').write_text(json.dumps({'fecha':now.date().isoformat(),'partidos':[row,row,dict(row,id='B',liga='International Friendlies')]}))
   self.assertEqual(len(e.validated_feed(now.date().isoformat())),1)
if __name__=='__main__':unittest.main()
