import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
import yaml
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from content import ROOT, TZ, collect, normalize, local_datetime, public_url, read_record
from build_calendar import calendar_bytes, generate
from optimize_images import optimize
from icalendar import Calendar

BASE_EVENT = {'title':'Test observing event', 'summary':'Test fixture only', 'draft':False, 'calendar_type':'pac','category':'observing','status':'scheduled','start_date':'2026-11-12','start_time':'19:00','end_time':'21:00','all_day':False}

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for folder in ['content/events','content/astronomy','content/albums','content/astrophotography','data/calendar','static/uploads']:
            (self.root/folder).mkdir(parents=True)
        (self.root/'data/calendar/banners.yml').write_text('[]')
        (self.root/'data/home.yml').write_text('{}')
        (self.root/'data/site.yml').write_text('{}')
        self.now=datetime(2026,10,22,tzinfo=TZ)
    def tearDown(self):
        self.temp.cleanup()
    def write(self, r, section='events', slug='test-event'):
        path=self.root/'content'/section/f'{slug}.md'
        path.write_text('---\n'+yaml.safe_dump(r)+'---\nFixture body.')
        return path
    def norm(self, **changes):
        return normalize(dict(BASE_EVENT, **changes),'events','test-event',self.now)
    def test_cms_unquoted_clock_values_remain_text(self):
        record=dict(BASE_EVENT,start_time='18:45',end_time='20:15',display_order=10)
        path=self.write(record)
        path.write_text(path.read_text().replace("'18:45'",'18:45').replace("'20:15'",'20:15'))
        parsed,_=read_record(path)
        self.assertEqual(parsed['start_time'],'18:45')
        self.assertEqual(parsed['end_time'],'20:15')
        self.assertIs(parsed['draft'],False)
        self.assertEqual(parsed['display_order'],10)
        events,_=collect(self.root,self.now)
        self.assertEqual(events[0]['start'],'2026-11-12T18:45:00-05:00')
        self.assertEqual(events[0]['end'],'2026-11-12T20:15:00-05:00')
    def test_draft_not_in_feed(self):
        self.write(dict(BASE_EVENT,draft=True))
        self.assertEqual(collect(self.root)[0],[])
    def test_publish_and_single_source_month_change(self):
        self.write(BASE_EVENT)
        generate(self.root)
        before=(self.root/'static/calendar.ics').read_bytes()
        self.write(dict(BASE_EVENT,start_date='2026-12-12'))
        generate(self.root)
        self.assertNotEqual(before,(self.root/'static/calendar.ics').read_bytes())
        events=collect(self.root)[0]
        self.assertTrue(events[0]['start'].startswith('2026-12-12'))
        self.assertEqual(events[0]['url'],'/events/test-event/')
        self.assertEqual(events[0]['id'],'events/test-event')
    def test_summer_and_winter_dst(self):
        self.assertTrue(self.norm(start_date='2026-07-12')['start'].endswith('-04:00'))
        self.assertTrue(self.norm(start_date='2026-12-12')['start'].endswith('-05:00'))
    def test_event_across_dst_change(self):
        r=self.norm(start_date='2026-10-31',start_time='23:30',end_date='2026-11-01',end_time='02:30')
        self.assertTrue(r['start'].endswith('-04:00'))
        self.assertTrue(r['end'].endswith('-05:00'))
        parsed=Calendar.from_ical(calendar_bytes([r])).walk('VEVENT')[0]
        self.assertEqual((parsed.decoded('dtend')-parsed.decoded('dtstart')).total_seconds(),4*3600)
    def test_nonexistent_dst_time_rejected(self):
        with self.assertRaisesRegex(ValueError,'does not exist'):
            local_datetime('2026-03-08','02:30')
    def test_ambiguous_dst_time_rejected(self):
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            local_datetime('2026-11-01','01:30')
    def test_leap_day(self):
        self.norm(start_date='2028-02-29')
        with self.assertRaises(ValueError): self.norm(start_date='2027-02-29')
    def test_all_day_exclusive_end(self):
        r=self.norm(start_date='2026-12-31',end_date='2027-01-02',all_day=True)
        self.assertEqual(r['end'],'2027-01-03')
        event=Calendar.from_ical(calendar_bytes([r])).walk('VEVENT')[0]
        self.assertEqual(str(event.decoded('dtend')),'2027-01-03')
    def test_overnight(self):
        r=self.norm(start_time='23:00',end_date='2026-11-13',end_time='01:00')
        self.assertEqual(r['endDate'],'2026-11-13')
    def test_end_before_start_rejected(self):
        with self.assertRaises(ValueError): self.norm(end_time='18:00')
        with self.assertRaises(ValueError): self.norm(end_date='2026-11-11')
    def test_timed_end_date_needs_time(self):
        with self.assertRaises(ValueError): self.norm(end_date='2026-11-13',end_time='')
    def test_bad_clock_rejected(self):
        for clock in ['7 PM','24:00','19:65','7:00','']:
            with self.assertRaises(ValueError): self.norm(start_time=clock)
    def test_statuses_not_upcoming(self):
        for status in ['cancelled','postponed','tentative']:
            r=self.norm(status=status)
            self.assertFalse(r['upcoming'])
    def test_ics_cancellation_stable_uid(self):
        a=Calendar.from_ical(calendar_bytes([self.norm()])).walk('VEVENT')[0]
        b=Calendar.from_ical(calendar_bytes([self.norm(status='cancelled',title='Changed title')])).walk('VEVENT')[0]
        self.assertEqual(a['uid'],b['uid'])
        self.assertEqual(b['status'],'CANCELLED')
    def test_postponed_retracts_original_time(self):
        parsed=Calendar.from_ical(calendar_bytes([self.norm(status='postponed')])).walk('VEVENT')[0]
        self.assertEqual(parsed['status'],'CANCELLED')
    def test_ics_escaping_crlf_folding(self):
        title='Stars, planets; questions \\ '+('é'*100)
        raw=calendar_bytes([self.norm(title=title,summary='Line one\nLine two; text, more')])
        self.assertIn(b'\r\n',raw)
        self.assertTrue(all(len(line)<=75 for line in raw.split(b'\r\n')))
        self.assertEqual(str(Calendar.from_ical(raw).walk('VEVENT')[0]['summary']),title)
    def test_ics_utc_conversion(self):
        parsed=Calendar.from_ical(calendar_bytes([self.norm()])).walk('VEVENT')[0]
        self.assertEqual(parsed.decoded('dtstart').hour,0)
        self.assertEqual(parsed.decoded('dtstart').day,13)
    def test_astronomy_requires_verification(self):
        self.write(dict(BASE_EVENT,kind='meteor_shower'),section='astronomy')
        with self.assertRaisesRegex(ValueError,'source URL'): collect(self.root)
    def test_astronomy_once_and_not_upcoming(self):
        self.write(dict(BASE_EVENT,kind='other',source_url='https://science.nasa.gov/',last_verified='2026-10-22'),section='astronomy')
        records=collect(self.root)[0]
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['calendarType'],'astronomy')
        self.assertFalse(records[0]['upcoming'])
    def test_joint_category(self):
        self.assertEqual(self.norm(calendar_type='joint')['categoryLabel'],'Joint event')
    def test_image_alt_missing_rejected(self):
        Image.new('RGB',(20,20)).save(self.root/'static/uploads/test.jpg')
        self.write(dict(BASE_EVENT,cover_image='/uploads/test.jpg',cover_alt=''))
        with self.assertRaisesRegex(ValueError,'alt text'):collect(self.root)
    def test_missing_image_rejected(self):
        self.write(dict(BASE_EVENT,cover_image='/uploads/missing.webp',cover_alt='A description'))
        with self.assertRaisesRegex(ValueError,'missing'):collect(self.root)
    def test_unsafe_url_rejected(self):
        for url in ['javascript:alert(1)','http://example.com','https://10.0.0.1/test','//example.com']:
            with self.assertRaises(ValueError): public_url(url)
    def test_duplicate_month_rejected(self):
        (self.root/'data/calendar/banners.yml').write_text(yaml.safe_dump([{'month':'2026-10'},{'month':'2026-10'}]))
        with self.assertRaisesRegex(ValueError,'unique'):collect(self.root)
    def test_missing_permission_banner_uses_fallback(self):
        (self.root/'data/calendar/banners.yml').write_text(yaml.safe_dump([{'month':'2026-10','banner_image':'/uploads/no.webp','permission_to_publish':False}]))
        generate(self.root)
        self.assertNotIn('no.webp',(self.root/'static/months.json').read_text())
    def test_unverified_month_notes_rejected(self):
        (self.root/'data/calendar/banners.yml').write_text(yaml.safe_dump([{'month':'2026-10','night_sky_notes':'Unverified claim'}]))
        with self.assertRaisesRegex(ValueError,'source URL'):collect(self.root)
    def test_album_three_images_and_pipeline(self):
        photos=[]
        for i in range(3):
            path=f'/uploads/test{i}.'+('png' if i==2 else 'jpg')
            Image.new('RGBA' if i==2 else 'RGB',(800,600),(160,30,50,0) if i==2 else (i*80,30,50)).save(self.root/'static'/path.lstrip('/'))
            photos.append({'image':path,'alt':f'Fixture {i}','credit':'Test photographer','caption':f'Caption {i}'})
        self.write({'title':'Fixture album','draft':False,'event_date':'2026-10-20','photos':photos,'permission_to_publish':True},'albums','fixture-album')
        collect(self.root)
        (self.root/'data/generated').mkdir()
        optimize(self.root)
        import json
        images=json.loads((self.root/'data/generated/images.json').read_text())
        self.assertEqual(len(images),3)
        self.assertIn('360w',images['/uploads/test0.jpg']['srcset'])
        with Image.open(self.root/'static'/images['/uploads/test2.png']['src'].lstrip('/')) as transparent:
            self.assertEqual(transparent.getpixel((0,0))[3],0)
        with Image.open(self.root/'.generated/uploads/test0.jpg') as clean:
            self.assertFalse(clean.getexif())
    def test_album_missing_permission_rejected(self):
        self.write({'title':'Test','draft':False,'event_date':'2026-10-22','photos':[]},'albums','test-album')
        with self.assertRaisesRegex(ValueError,'permission'):collect(self.root)
    def test_new_title_keeps_filename_url(self):
        a=self.norm();b=self.norm(title='An edited title')
        self.assertEqual(a['url'],b['url'])
        self.assertEqual(a['id'],b['id'])
    def test_cms_collections_and_safe_defaults(self):
        config=yaml.safe_load((ROOT/'.pages.yml').read_text())
        entries={e['name']:e for e in config['content']}
        self.assertTrue({'events','astronomy','calendar_months','albums','astrophotography','officers','sponsors','announcements','home','site','about','contact'}<=entries.keys())
        for entry in entries.values():
            if entry['type']=='collection':
                self.assertTrue(next(f for f in entry['fields'] if f['name']=='draft')['default'])
                self.assertFalse(entry['operations']['rename'])
        self.assertEqual(config['media']['output'],'/uploads')
        self.assertEqual(next(f for f in entries['albums']['fields'] if f['name']=='photos')['type'],'object')
        self.assertEqual(config['actions'][0]['workflow'],'export-calendar.yml')

if __name__=='__main__':unittest.main()
