import unittest,datetime
from zoneinfo import ZoneInfo
from engine.update import visible_schedule
class ScheduleTests(unittest.TestCase):
 def test_upcoming_real_fixture_only(self):
  now=datetime.datetime(2026,9,24,8,tzinfo=ZoneInfo('America/Asuncion'))
  events=[{'idEvent':'1','strTimestamp':'2026-09-24T15:00:00+00:00','strHomeTeam':'A','strAwayTeam':'B','strLeague':'Liga','strCountry':'PY'}, {'idEvent':'2','strTimestamp':'2026-09-24T09:00:00+00:00','strHomeTeam':'C','strAwayTeam':'D'}]
  self.assertEqual([x['id'] for x in visible_schedule(events,now)],['1'])
