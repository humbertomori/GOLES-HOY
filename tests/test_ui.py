import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class UI(unittest.TestCase):
 def test_odds_hidden(self):
  for path in [ROOT/'web/index.html',ROOT/'android/app/src/main/assets/index.html']:
   html=path.read_text(encoding='utf8')
   self.assertNotIn('Cuota ${esc(p.cuota)}',html)
   self.assertNotIn('Valor ${esc(p.valor_estimado)}',html)
 def test_ui_synced(self):
  self.assertEqual((ROOT/'web/index.html').read_bytes(),(ROOT/'android/app/src/main/assets/index.html').read_bytes())
 def test_build_has_gradle_setup(self):
  self.assertIn('setup-gradle@v4',(ROOT/'.github/workflows/android.yml').read_text())
