"""Exercise Drive listing/import failures and the real gallery build without credentials."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from content import ROOT, read_record
from sync_drive_gallery import DriveClient, DriveError, MAX_BYTES, parse_filename, sync
from build_calendar import generate
from optimize_images import optimize
from validate_public_output import validate


def photo_bytes():
    buffer = BytesIO()
    exif = Image.Exif()
    exif[270] = 'PRIVATE EMBEDDED CAMERA NOTE'
    exif[274] = 6
    Image.new('RGB', (80, 60), (20, 35, 70)).save(buffer, 'JPEG', exif=exif)
    return buffer.getvalue()


def metadata(file_id='photo-one', filename='jane_doe_andromeda_galaxy.jpg'):
    return {'id': file_id, 'name': filename, 'mimeType': 'image/jpeg', 'modifiedTime': '2026-10-22T10:00:00Z',
            'md5Checksum': 'fixture-checksum', 'size': '1000', 'capabilities': {'canDownload': True}}


class FakeDrive:
    def __init__(self, files=None):
        self.files = [metadata()] if files is None else files
        self.downloads = []
        self.fail = False

    def list_photos(self, folder_id):
        if self.fail:
            raise DriveError('Provider unavailable')
        return deepcopy(self.files)

    def download(self, file_id):
        self.downloads.append(file_id)
        if self.fail:
            raise DriveError('Download unavailable')
        return photo_bytes()


class FilenameTests(unittest.TestCase):
    def test_target_and_credit(self):
        self.assertEqual(parse_filename('jane_doe_andromeda_galaxy.jpg'),
                         {'title': 'Andromeda Galaxy', 'photographer': 'Jane Doe'})

    def test_catalog_names_and_intended_case(self):
        self.assertEqual(parse_filename('anna-marie_McDonald_M31_NGC_7000.JPEG'),
                         {'title': 'M31 NGC 7000', 'photographer': 'Anna-Marie McDonald'})
        self.assertEqual(parse_filename('josé_o’neill_orion_nebula.webp')['photographer'], 'José O’Neill')
        self.assertEqual(parse_filename('jane_doe_ISS_transit.png')['title'], 'ISS Transit')

    def test_reject_ambiguous_or_unsupported_names(self):
        for filename in ['image.jpg', 'jane_doe.jpg', 'jane__M31.jpg', 'jane_doe_M31_.jpg',
                         '../jane_doe_M31.jpg', 'jane_doe_M31.svg', 'jane_doe_M31\n.jpg']:
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                parse_filename(filename)


class DriveGalleryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'data').mkdir()
        (self.root/'static/uploads').mkdir(parents=True)
        (self.root/'static/uploads/cms-photo.jpg').write_bytes(photo_bytes())
        self.config = {'enabled': True, 'folder_id': 'selected-folder', 'featured': False, 'photos': []}
        self.client = FakeDrive()
        self.save_config()

    def save_config(self):
        (self.root/'data/drive_gallery.yml').write_text(yaml.safe_dump(self.config))

    def run_sync(self):
        return sync(self.root, self.client, offline=False)

    def test_import_creates_credited_content_and_strips_original_metadata(self):
        record = self.run_sync()[0]
        content = self.root/'.generated/content/drive-gallery'/f"{record['reference']}.md"
        frontmatter, _ = read_record(content)
        self.assertEqual(frontmatter['title'], 'Andromeda Galaxy')
        self.assertEqual(frontmatter['photographer'], 'Jane Doe')
        self.assertFalse(frontmatter['draft'])
        self.assertNotIn('filename', frontmatter)
        with Image.open(self.root/'static'/record['image'].lstrip('/')) as photo:
            self.assertEqual(photo.size, (60, 80))
            self.assertEqual(dict(photo.getexif()), {})
            self.assertNotIn('exif', photo.info)
        self.assertTrue((self.root/'static/uploads/cms-photo.jpg').exists())

    def test_cache_reuses_unchanged_image_and_renames_keep_the_same_url(self):
        first = self.run_sync()[0]
        self.client.files[0]['name'] = 'jane_McDonald_M31.jpg'
        second = self.run_sync()[0]
        self.assertEqual(first['reference'], second['reference'])
        self.assertEqual(second['title'], 'M31')
        self.assertEqual(second['photographer'], 'Jane McDonald')
        self.assertEqual(self.client.downloads, ['photo-one'])
        self.client.files[0]['md5Checksum'] = 'new-image'
        self.run_sync()
        self.assertEqual(self.client.downloads, ['photo-one', 'photo-one'])

    def test_removed_photos_are_withdrawn_after_a_complete_sync(self):
        self.run_sync()
        self.client.files = []
        self.assertEqual(self.run_sync(), [])
        self.assertEqual(list((self.root/'.generated/content/drive-gallery').glob('*.md')), [])
        self.assertEqual(list((self.root/'static/uploads/drive-gallery').glob('*')), [])
        self.assertTrue((self.root/'static/uploads/cms-photo.jpg').exists())

    def test_cms_corrections_and_hidden_photos(self):
        self.client.files.append(metadata('photo-two', 'alex_smith_orion_nebula.jpg'))
        self.config['photos'] = [
            {'filename': self.client.files[0]['name'], 'title': 'M31 — Andromeda', 'photographer': 'J. Doe',
             'alt': 'A spiral galaxy with a bright core and dust lanes.', 'caption': 'A club photograph.', 'featured': True},
            {'filename': self.client.files[1]['name'], 'hidden': True},
        ]
        self.save_config()
        records = self.run_sync()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['title'], 'M31 — Andromeda')
        self.assertEqual(records[0]['photographer'], 'J. Doe')
        self.assertEqual(records[0]['alt'], self.config['photos'][0]['alt'])
        self.assertTrue(records[0]['featured'])
        self.assertEqual(self.client.downloads, ['photo-one'])

    def test_failed_listing_or_download_preserves_last_complete_snapshot(self):
        first = self.run_sync()[0]
        manifest = self.root/'.generated/drive-gallery/manifest.json'
        original = manifest.read_bytes()
        self.client.fail = True
        with self.assertRaises(DriveError):
            self.run_sync()
        self.assertEqual(manifest.read_bytes(), original)
        self.client.fail = False
        self.client.files[0]['md5Checksum'] = 'changed'
        self.client.download = Mock(side_effect=DriveError('Download unavailable'))
        with self.assertRaises(DriveError):
            self.run_sync()
        self.assertEqual(manifest.read_bytes(), original)
        self.assertTrue((self.root/'static'/first['image'].lstrip('/')).exists())

    def test_invalid_names_and_non_images_do_not_publish(self):
        self.client.files = [metadata(filename='uncredited.jpg'), dict(metadata('shortcut'), mimeType='application/vnd.google-apps.shortcut')]
        self.assertEqual(self.run_sync(), [])
        self.assertEqual(self.client.downloads, [])

    def test_duplicate_names_get_distinct_stable_pages(self):
        self.client.files.append(metadata('different-photo'))
        records = self.run_sync()
        self.assertEqual(len({r['reference'] for r in records}), 2)

    def test_size_download_and_image_validation(self):
        for change in [{'size': str(MAX_BYTES+1)}, {'capabilities': {'canDownload': False}}]:
            self.client.files = [dict(metadata(), **change)]
            with self.assertRaises(DriveError):
                self.run_sync()
        self.client.files = [metadata()]
        self.client.download = Mock(return_value=b'not an image')
        with self.assertRaises(DriveError):
            self.run_sync()

    def test_full_size_drive_original_is_reduced_before_the_cms_image_pipeline(self):
        buffer = BytesIO()
        Image.new('RGB', (3600, 1800), (20, 35, 70)).save(buffer, 'JPEG')
        payload = buffer.getvalue() + b'\0' * (16 * 1024 * 1024)
        self.client.files[0]['size'] = str(len(payload))
        self.client.download = Mock(return_value=payload)
        record = self.run_sync()[0]
        prepared = self.root/'static'/record['image'].lstrip('/')
        with Image.open(prepared) as photo:
            self.assertEqual(photo.size, (2400, 1200))
        self.assertLess(prepared.stat().st_size, 15 * 1024 * 1024)

    def test_disabled_and_offline_withdraw_only_imported_pages(self):
        self.run_sync()
        sync(self.root, self.client, offline=True)
        self.assertEqual(list((self.root/'.generated/content/drive-gallery').glob('*.md')), [])
        self.config['enabled'] = False
        self.save_config()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sync(self.root), [])
        self.assertTrue((self.root/'static/uploads/cms-photo.jpg').exists())

    def test_missing_credentials_fail_with_actionable_message(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(DriveError, 'Actions secret'):
            sync(self.root)

    def make_snapshot(self):
        records = self.run_sync()
        shutil.copytree(self.root/'.generated/drive-gallery', self.root/'assets/drive-gallery-snapshot')
        self.config.update(enabled=False, use_snapshot=True)
        self.save_config()
        return records

    def test_initial_photos_work_without_credentials_or_a_generated_cache(self):
        expected = self.make_snapshot()[0]
        shutil.rmtree(self.root/'.generated')
        shutil.rmtree(self.root/'static/uploads/drive-gallery')
        with patch.dict(os.environ, {}, clear=True):
            records = sync(self.root)
        self.assertEqual(records[0]['reference'], expected['reference'])
        self.assertTrue((self.root/'static'/records[0]['image'].lstrip('/')).exists())
        self.assertTrue((self.root/'.generated/content/drive-gallery'/f"{expected['reference']}.md").exists())

    def test_initial_photo_corrections_and_hiding_work_in_cms(self):
        self.client.files.append(metadata('two', 'alex_smith_orion_nebula.jpg'))
        self.make_snapshot()
        self.config['photos'] = [
            {'filename': self.client.files[0]['name'], 'title': 'M31', 'photographer': 'J. Doe', 'featured': True},
            {'filename': self.client.files[1]['name'], 'hidden': True},
        ]
        self.save_config()
        records = sync(self.root, offline=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['alt'], 'Astrophotograph of M31 by J. Doe.')
        self.assertTrue(records[0]['featured'])

    def test_live_folder_replaces_initial_photos_and_removals_do_not_reappear(self):
        self.make_snapshot()
        self.config['enabled'] = True
        self.save_config()
        self.client.files = []
        self.assertEqual(self.run_sync(), [])
        self.assertEqual(list((self.root/'.generated/content/drive-gallery').glob('*.md')), [])
        self.assertTrue((self.root/'assets/drive-gallery-snapshot/manifest.json').exists())

    def test_initial_gallery_can_be_disabled_and_cannot_follow_a_different_folder(self):
        self.make_snapshot()
        self.config['folder_id'] = 'different-folder'
        self.save_config()
        with self.assertRaisesRegex(DriveError, 'different folder'):
            sync(self.root)
        self.config['use_snapshot'] = False
        self.save_config()
        self.assertEqual(sync(self.root), [])

    def test_complete_real_hugo_gallery_has_target_credit_and_no_drive_credentials(self):
        hugo = os.environ.get('HUGO_BIN') or shutil.which('hugo')
        if not hugo:
            self.skipTest('Hugo is needed for full gallery integration')
        for folder in ['content', 'data', 'assets', 'layouts', 'static']:
            shutil.copytree(ROOT/folder, self.root/folder, dirs_exist_ok=True)
        shutil.copy(ROOT/'hugo.yaml', self.root/'hugo.yaml')
        (self.root/'data/astronomy.yml').write_text('enabled: false\n')
        self.config['photos'] = [{'filename': self.client.files[0]['name'], 'caption': 'Spiral arms & a bright core.'}]
        self.save_config()
        record = self.run_sync()[0]
        def build():
            generate(self.root)
            optimize(self.root)
            subprocess.run([hugo, '--source', str(self.root), '--minify', '--cleanDestinationDir'], check=True, capture_output=True)
            shutil.copytree(self.root/'.generated/uploads', self.root/'public/uploads', dirs_exist_ok=True)
            validate(self.root/'public')
        build()
        gallery = (self.root/'public/gallery/index.html').read_text()
        self.assertIn('Andromeda Galaxy', gallery)
        self.assertIn('Image by Jane Doe', gallery)
        detail = self.root/'public/astrophotography'/record['reference']/'index.html'
        self.assertIn('data-credit="Jane Doe"', detail.read_text())
        self.assertIn('Spiral arms', detail.read_text())
        self.assertNotIn('selected-folder', detail.read_text())
        self.assertNotIn('PRIVATE EMBEDDED CAMERA NOTE', detail.read_text())
        self.client.files = []
        self.run_sync(); build()
        self.assertFalse(detail.exists())
        self.assertNotIn(record['reference'], (self.root/'public/gallery/index.html').read_text())


class DriveListingTests(unittest.TestCase):
    def test_pagination_is_confined_to_the_selected_shared_folder(self):
        client = DriveClient.__new__(DriveClient)
        calls = []
        pages = iter([{'files': [metadata()], 'nextPageToken': 'next'}, {'files': [metadata('two')]}])
        def get(file_id='', params=None):
            calls.append((file_id, deepcopy(params)))
            return {'mimeType': 'application/vnd.google-apps.folder', 'driveId': 'shared-drive'} if file_id else next(pages)
        client.get = get
        self.assertEqual(len(client.list_photos('only-this-folder')), 2)
        query = calls[1][1]
        self.assertEqual(query['q'], "'only-this-folder' in parents and trashed = false")
        self.assertEqual(query['driveId'], 'shared-drive')
        self.assertEqual(calls[2][1]['pageToken'], 'next')

    def test_incomplete_or_repeated_pages_abort(self):
        for page in [{'files': [], 'incompleteSearch': True}, {'files': [], 'nextPageToken': 'same'}]:
            client = DriveClient.__new__(DriveClient)
            client.get = Mock(side_effect=lambda file_id='', params=None:
                              {'mimeType': 'application/vnd.google-apps.folder'} if file_id else page)
            with self.assertRaises(DriveError):
                client.list_photos('selected-folder')

    def test_keys_cannot_redirect_authentication_to_another_host(self):
        with self.assertRaisesRegex(DriveError, 'Actions secret'):
            DriveClient(json.dumps({'token_uri': 'https://example.com/token'}))
