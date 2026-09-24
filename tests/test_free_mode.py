import unittest,sys,pathlib,json,io,unittest.mock as mock,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import engine.update as e
class FreeModeTests(unittest.TestCase):
 def test_free_mode_no_fabricated_picks(self):
  class Resp:
   def __enter__(self):return io.BytesIO(json.dumps({'events':[{'strSport':'Soccer','strLeague':'Premier League'}]}).encode())
   def __exit__(self,*a):pass
  with tempfile.TemporaryDirectory() as td, mock.patch.object(e,'DATA',pathlib.Path(td)), mock.patch.object(e.urllib.request,'urlopen',return_value=Resp()):
   e.free_mode();result=json.loads((pathlib.Path(td)/'latest.json').read_text());self.assertEqual(result['partidos'],[]);self.assertEqual(result['analizados'],1)
 def test_fallback_keeps_previous_picks(self):
  class Resp:
   def __enter__(self):return io.BytesIO(json.dumps({'events':[]}).encode())
   def __exit__(self,*a):pass
  with tempfile.TemporaryDirectory() as td, mock.patch.object(e,'DATA',pathlib.Path(td)), mock.patch.object(e.urllib.request,'urlopen',return_value=Resp()):
   old={'fecha':'2026-09-24','partidos':[{'id':123,'local':'A','visitante':'B'}]}
   (pathlib.Path(td)/'latest.json').write_text(json.dumps(old))
   e.free_mode()
   self.assertEqual(json.loads((pathlib.Path(td)/'latest.json').read_text()),old)
   self.assertEqual(json.loads((pathlib.Path(td)/'source_health.json').read_text())['pronosticos_nuevos'],0)
 def test_network_failure_does_not_publish_fake_data(self):
  with tempfile.TemporaryDirectory() as td, mock.patch.object(e,'DATA',pathlib.Path(td)), mock.patch.object(e.urllib.request,'urlopen',side_effect=TimeoutError('timeout')):
   with self.assertRaises(TimeoutError):e.free_mode()
   self.assertFalse((pathlib.Path(td)/'latest.json').exists())
if __name__=='__main__':unittest.main()
