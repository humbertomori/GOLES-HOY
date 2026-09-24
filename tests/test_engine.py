import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from engine.update import poisson_over25,odds_for_fixture,reds,league_priority
class EngineTests(unittest.TestCase):
 def test_poisson(self):self.assertAlmostEqual(poisson_over25(3),0.5768099189,places=8)
 def test_odds(self):
  data={'bookmakers':[{'name':'Test','bets':[{'name':'Goals Over/Under','values':[{'value':'Over 2.5','odd':'1.92'}]}]}]}
  self.assertEqual(odds_for_fixture(data),(1.92,'Test'))
 def test_no_red_data(self):self.assertIsNone(reds({'cards':{'red':{'0-15':{'total':None}}}}))
 def test_friendly(self):self.assertLess(league_priority('International Friendlies'),0)
if __name__=='__main__':unittest.main()
