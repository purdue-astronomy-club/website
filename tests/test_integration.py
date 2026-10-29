"""Build realistic CMS-shaped fixtures in an isolated temporary checkout."""
from pathlib import Path
from html.parser import HTMLParser
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from content import ROOT
from build_calendar import generate
from optimize_images import optimize
from validate_public_output import validate, Links

class IntegrationTests(unittest.TestCase):
    def test_publish_all_models_then_move_cancel_and_draft_event(self):
        hugo=os.environ.get('HUGO_BIN') or shutil.which('hugo')
        if not hugo:self.skipTest('Hugo is needed for full integration build')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ['content','data','assets','layouts','static']:
                ignore=shutil.ignore_patterns('uploads','media','astronomy','events','events.json','months.json','calendar.ics') if folder=='static' else None
                shutil.copytree(ROOT/folder,root/folder,ignore=ignore)
            # Keep the site's layouts and section pages, but populate collections
            # and settings with fixtures rather than the club's current CMS data.
            for entry in (root/'content').glob('*/**/*.md'):
                if not entry.name.startswith('_'):
                    entry.unlink()
            (root/'static/uploads').mkdir(parents=True,exist_ok=True)
            (root/'data/calendar/banners.yml').write_text('[]\n')
            (root/'data/home.yml').write_text('show_gallery: true\n')
            (root/'data/site.yml').write_text('{}\n')
            shutil.copy(ROOT/'hugo.yaml',root/'hugo.yaml')
            (root/'data/astronomy.yml').write_text('enabled: false\n')
            def write(section,slug,record):
                path=root/'content'/section/f'{slug}.md'
                path.parent.mkdir(parents=True,exist_ok=True)
                body='Fixture rich text body.'
                if section=='announcements':body+='\n\n![Fixture inline photo](/uploads/events/november/fixture-0.jpg)\n\n[Fixture link](/photo-prep/)'
                if section=='events':body+='\n\n![](/uploads/events/november/fixture-0.jpg)'
                path.write_text('---\n'+yaml.safe_dump(record)+'---\n'+body)
            photos=[]
            for i in range(3):
                extension = ['jpg', 'tif', 'png'][i]
                image=f'/uploads/'+('events/november/' if i==0 else '')+f'fixture-{i}.{extension}'
                (root/'static'/image.lstrip('/')).parent.mkdir(parents=True,exist_ok=True)
                Image.new('RGB',(800,600),(30+i*50,40,80)).save(root/'static'/image.lstrip('/'))
                photos.append({'image':image,'alt':f'Fixture image {i}','caption':f'Fixture caption {i}','credit':f'Test contributor {i}'})
            event={'title':'Fixture event','summary':'Fixture summary','draft':False,'category':'workshop','calendar_type':'joint','status':'scheduled','start_date':'2040-10-22','start_time':'19:00','end_time':'21:00','all_day':False,'cover_image':photos[0]['image'],'related_album_slug':'fixture-album'}
            event_slug='fixture-event'
            write('events',event_slug,event)
            astro_alt=photos[1]['alt']
            photos[0].pop('alt')
            photos[1]['alt']=''
            write('albums','fixture-album',{'title':'Fixture album','draft':False,'event_date':'2040-10-22','featured':False,'permission_to_publish':True,'cover_image':photos[0]['image'],'photos':photos,'related_event_slug':'fixture-event'})
            write('astrophotography','fixture-image',{'title':'Fixture image','draft':False,'featured':False,'image':photos[1]['image'],'alt':astro_alt,'photographer':'Test contributor','permission_to_publish':True})
            write('officers','fixture-officer',{'title':'Test officer','role':'Test role','draft':False,'active':True,'display_order':1,'image':photos[2]['image'],'image_alt':photos[2]['alt']})
            write('sponsors','fixture-sponsor',{'title':'Test sponsor','draft':False,'logo':photos[2]['image'],'logo_alt':photos[2]['alt'],'website':'https://example.com/','display_order':1})
            write('announcements','fixture-news',{'title':'Fixture announcement','draft':False,'publish_date':'2020-01-01','summary':'Fixture news','image':photos[1]['image'],'image_alt':astro_alt})
            write('announcements','future-news',{'title':'Future fixture','draft':False,'publish_date':'2099-01-01','summary':'Should be scheduled'})
            def build():
                optimize(root);generate(root)
                subprocess.run([hugo,'--source',str(root),'--minify','--cleanDestinationDir'],check=True,capture_output=True)
                validate(root/'public')
            build()
            self.assertEqual([r['id'] for r in json.loads((root/'public/events.json').read_text())],['events/fixture-event'])
            homepage=(root/'public/index.html').read_text()
            self.assertIn('Fixture event',homepage)
            self.assertEqual(homepage.count('carousel-slide'),4)
            for i in range(3):
                self.assertIn(f'Fixture caption {i}',homepage)
                self.assertIn(f'Test contributor {i}',homepage)
            self.assertIn('Fixture image',homepage)
            self.assertIn('Joint event',(root/'public/events/fixture-event/index.html').read_text())
            album=(root/'public/albums/fixture-album/index.html').read_text()
            album_images=[]
            class AlbumImages(HTMLParser):
                def handle_starttag(self,tag,attrs):
                    attrs=dict(attrs)
                    if tag=='img' and attrs.get('src','').startswith('/media/'):
                        album_images.append(attrs)
            AlbumImages().feed(album)
            self.assertEqual(len(album_images),3)
            self.assertTrue(all('alt' in image for image in album_images))
            self.assertEqual([image['alt'] or '' for image in album_images],['','','Fixture image 2'])
            metadata=json.loads((root/'data/generated/images.json').read_text())
            self.assertIn(metadata['/uploads/fixture-1.tif']['full'],album)
            self.assertFalse((root/'public/uploads/fixture-1.tif').exists())
            with Image.open(root/'public'/metadata['/uploads/fixture-1.tif']['full'].lstrip('/')) as full:
                self.assertEqual(full.size,(800,600))
            for i in range(3):
                self.assertIn(f'Fixture caption {i}',album)
                self.assertIn(f'Test contributor {i}',album)
            self.assertIn('Fixture album',(root/'public/gallery/index.html').read_text())
            self.assertIn('Fixture image',(root/'public/gallery/index.html').read_text())
            self.assertFalse((root/'public/announcements/future-news/index.html').exists())
            self.assertIn('Fixture announcement',(root/'public/announcements/index.html').read_text())
            self.assertIn('alt="Fixture image 2"',(root/'public/officers/index.html').read_text())
            profile=(root/'public/officers/fixture-officer/index.html').read_text()
            self.assertIn('alt="Fixture image 2"',profile)
            self.assertIn('Test role',profile)
            self.assertIn('Meet all officers',profile)
            # CMS Rename may change folders without changing the saved filename.
            event_slug='November 2040/fixture-event'
            destination=root/'content/events'/f'{event_slug}.md'
            destination.parent.mkdir(parents=True)
            (root/'content/events/fixture-event.md').rename(destination)
            build()
            records=json.loads((root/'public/events.json').read_text())
            self.assertEqual(records[0]['id'],'events/fixture-event')
            self.assertEqual(records[0]['url'],'/events/fixture-event/')
            self.assertTrue((root/'public/events/fixture-event/event.ics').is_file())
            self.assertIn('Fixture event',(root/'public/events/fixture-event/index.html').read_text())
            self.assertIn('View the event',(root/'public/albums/fixture-album/index.html').read_text())
            # Reproduce a repository hosted below /website/, where root-relative
            # CSS, media, links, browser feeds and invitations used to break.
            with patch.dict(os.environ, {'HUGO_BASEURL':'https://example.github.io/website/'}):
                build()
                parser=Links();parser.feed((root/'public/index.html').read_text())
                self.assertTrue(any(url.startswith('/website/css/') for url in parser.links))
                self.assertTrue(any(url.startswith('/website/media/') for url in parser.links))
                self.assertTrue(any(url.startswith('/website/events/?v=') for url in parser.links))
                records=json.loads((root/'public/events.json').read_text())
                self.assertEqual(records[0]['url'],'/website/events/fixture-event/')
                self.assertTrue(records[0]['coverImage'].startswith('/website/media/'))
                self.assertIn('https://example.github.io/website/events/fixture-event/',(root/'public/calendar.ics').read_text())
                news=Links();news.feed((root/'public/announcements/fixture-news/index.html').read_text())
                self.assertIn('/website/photo-prep/',news.links)
                redirect=(root/'public/calendar/index.html').read_text()
                self.assertIn('/website/events/',redirect)
                # A file existing at the output root must not hide a broken URL
                # that points outside the actual deployed repository path.
                (root/'public/broken.html').write_text('<img src="/favicon.svg">')
                with self.assertRaisesRegex(ValueError,'escapes the website deployment path'):
                    validate(root/'public')
                (root/'public/broken.html').unlink()
            event['start_date']='2040-11-23';write('events',event_slug,event);build()
            self.assertIn('2040-11-23',(root/'public/events.json').read_text())
            self.assertNotIn('20401022',(root/'public/calendar.ics').read_text())
            event['status']='cancelled';write('events',event_slug,event);build()
            self.assertNotIn('Fixture event',(root/'public/index.html').read_text())
            self.assertIn('Cancelled',(root/'public/events/fixture-event/index.html').read_text())
            self.assertIn('STATUS:CANCELLED',(root/'public/calendar.ics').read_text())
            event['draft']=True;write('events',event_slug,event)
            # Remove reverse reference before archiving; the public album may remain published.
            build()
            self.assertEqual(json.loads((root/'public/events.json').read_text()),[])
            self.assertFalse((root/'public/events/fixture-event/index.html').exists())
