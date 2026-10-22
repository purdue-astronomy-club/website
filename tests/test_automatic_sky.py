from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import sys
import tempfile
import unittest
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from content import ROOT, TZ, normalize
from automatic_sky import automatic_events, settings, calculate, instant_record
import astronomy
from build_calendar import calendar_bytes
from refresh_meteors import parse_meteors, refresh, AMS_URL
from icalendar import Calendar

class AutomaticSkyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'data/astronomy').mkdir(parents=True)
        shutil.copy(ROOT/'data/astronomy/meteor-showers.json',self.root/'data/astronomy/meteor-showers.json')
        self.config={'enabled':True,'moon_phases':True,'planetary_oppositions':True,'meteor_showers':True,'seasons':True,'years_past':0,'years_ahead':0,'hidden_events':[]}
        self.now=datetime(2026,10,22,tzinfo=TZ)
        self.save()
    def tearDown(self):self.temp.cleanup()
    def save(self):(self.root/'data/astronomy.yml').write_text(yaml.safe_dump(self.config))
    def get(self,manual=()):return automatic_events(self.root,manual,self.now)
    def test_all_2026_phases_match_independent_usno_within_five_minutes(self):
        records,_=self.get()
        data=json.loads((ROOT/'tests/fixtures/usno-moon-2026.json').read_text())
        expected=data['phasedata']
        phases=[r for r in records if r['category'] in {'new_moon','first_quarter','full_moon','last_quarter'}]
        self.assertEqual(len(phases),len(expected))
        for record,usno in zip(phases,expected):
            actual=datetime.fromisoformat(record['start']).astimezone(timezone.utc)
            target=datetime(usno['year'],usno['month'],usno['day'],int(usno['time'][:2]),int(usno['time'][3:]),tzinfo=timezone.utc)
            self.assertLess(abs((actual-target).total_seconds()),300)
    def test_midnight_phase_is_on_indiana_date(self):
        records,_=self.get()
        new=[r for r in records if r['category']=='new_moon' and r['startDate'].startswith('2026-12')][0]
        self.assertEqual(new['startDate'],'2026-12-08')
        self.assertTrue(new['start'].endswith('-05:00'))
    def test_automatic_types_icons_and_never_club_upcoming(self):
        records,_=self.get()
        self.assertTrue(any(r['category']=='opposition' and r['planet']=='Saturn' and r['icon']=='saturn' for r in records))
        self.assertTrue(any(r['category']=='meteor_shower' and r['icon']=='meteor' for r in records))
        self.assertTrue(any(r['category']=='season' and r['icon']=='sun' for r in records))
        self.assertTrue(all(not r['upcoming'] and r['calendarType']=='astronomy' for r in records))
        self.assertTrue(all(r['sourceUrl'].startswith('https://') for r in records))
    def test_hide_and_published_manual_replacement(self):
        records,_=self.get();moon=next(r for r in records if r['category']=='new_moon')
        self.config['hidden_events']=[moon['slug']];self.save()
        self.assertNotIn(moon['id'],{r['id'] for r in self.get()[0]})
        self.config['hidden_events']=[];self.save()
        manual=normalize({'title':'Officer highlight','summary':'Verified note','kind':'new_moon','start_date':moon['startDate'],'all_day':True,'replaces_auto_event':moon['slug']},'astronomy','officer-note',self.now)
        self.assertNotIn(moon['id'],{r['id'] for r in self.get([manual])[0]})
    def test_same_kind_date_avoids_duplicate(self):
        records,_=self.get();moon=next(r for r in records if r['category']=='full_moon')
        manual=normalize({'title':'Officer full moon','summary':'Note','kind':'full_moon','start_date':moon['startDate'],'all_day':True},'astronomy','full-note',self.now)
        self.assertNotIn(moon['id'],{r['id'] for r in self.get([manual])[0]})
    def test_disabling_removes_generated_pages(self):
        self.get();self.assertTrue(list((self.root/'.generated/content/astronomy').glob('*.md')))
        self.config['enabled']=False;self.save()
        records,status=self.get();self.assertEqual(records,[])
        self.assertFalse(status['enabled']);self.assertFalse(list((self.root/'.generated/content/astronomy').glob('*.md')))
    def test_category_switches_and_rolling_range(self):
        self.config.update(moon_phases=False,planetary_oppositions=False,seasons=False,years_ahead=1);self.save()
        records,status=self.get();self.assertTrue(all(r['category']=='meteor_shower' for r in records))
        self.assertEqual(status['endYear'],2027)
        self.assertFalse(any(r['startDate'].startswith('2028') for r in records))
    def test_no_meteor_dates_are_guessed_in_later_years(self):
        self.now=datetime(2029,2,1,tzinfo=TZ)
        records,_=self.get()
        self.assertFalse(any(r['category']=='meteor_shower' for r in records))
        self.assertTrue(any(r['category']=='new_moon' for r in records))
    def test_meteor_parser_uses_explicit_year_and_peak_night(self):
        pieces=[]
        for slug,title,month,first,last,year in [('orionids','Orionids','Oct',21,22,2026),('geminids','Geminids','Dec',13,14,2026),('quadrantids','Quadrantids','Jan',3,4,2027)]:
            pieces.append(f'<article id="{slug}" class="shower-card"><h2>{title}</h2><p>on peak night ({month} {first}–{last}, {year}).</p></article>')
        records=parse_meteors(''.join(pieces))
        self.assertEqual(records[-1]['start_date'],'2027-01-03')
        with self.assertRaises(ValueError):parse_meteors('<html>No calendar data</html>')
    def test_source_failure_keeps_snapshot(self):
        with patch('refresh_meteors.urlopen',side_effect=OSError('Source offline')):
            self.assertFalse(refresh(self.root))
        self.assertTrue(any(r['category']=='meteor_shower' for r in self.get()[0]))
    def test_invitations_keep_calculated_instant_in_utc(self):
        records,_=self.get();moon=next(r for r in records if r['category']=='new_moon')
        event=Calendar.from_ical(calendar_bytes([moon],self.root)).walk('VEVENT')[0]
        self.assertEqual(event.decoded('dtstart'),datetime.fromisoformat(moon['start']).astimezone(timezone.utc))
    def test_precise_utc_events_survive_repeated_dst_hour(self):
        event=instant_record('Test instant','other',astronomy.Time.Parse('2026-11-01T05:59:30Z'),'dst-test','Test only','2026-10-22')
        start=datetime.fromisoformat(event['start']).astimezone(timezone.utc)
        end=datetime.fromisoformat(event['end']).astimezone(timezone.utc)
        self.assertEqual((end-start).total_seconds(),60)
        self.assertTrue(event['start'].endswith('-04:00'))
        self.assertTrue(event['end'].endswith('-05:00'))
        self.assertFalse(event['allDay'])
    def test_invalid_huge_window_fails(self):
        self.config['years_ahead']=99;self.save()
        with self.assertRaisesRegex(ValueError,'0, 1, or 2'):self.get()
