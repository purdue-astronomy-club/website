"""Protect full-size pixels, TIFF conversion, metadata stripping and format limits."""
from io import BytesIO
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from gallery_images import read_image
from optimize_images import optimize
from sync_drive_gallery import prepare_image, parse_filename
from validate_public_output import validate


class GalleryImageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.uploads = self.root/'static/uploads'
        self.uploads.mkdir(parents=True)

    def images(self):
        optimize(self.root)
        return json.loads((self.root/'data/generated/images.json').read_text())

    def test_every_upload_format_preserves_source_dimensions_and_pixels(self):
        for extension, format in [('jpg', 'JPEG'), ('png', 'PNG'), ('tif', 'TIFF'), ('TIFF', 'TIFF'), ('webp', 'WEBP')]:
            with self.subTest(extension=extension):
                source = self.uploads/f'photo.{extension}'
                photo = Image.new('RGB', (4200, 64), (20, 40, 160))
                photo.putpixel((120, 30), (255, 10, 200))
                photo.save(source, format)
                self.assertEqual(parse_filename(f'jane_doe_M31.{extension}')['title'], 'M31')
                metadata = self.images()[f'/uploads/{source.name}']
                with Image.open(source) as original, Image.open(self.root/'.generated'/metadata['full'].lstrip('/')) as full:
                    self.assertEqual(full.size, original.size)
                    self.assertEqual(full.tobytes(), original.tobytes())
                self.assertIn(f"{metadata['full']} 4200w", metadata['srcset'])
                self.assertEqual((metadata['width'], metadata['height']), (4200, 64))

    def test_transparency_and_color_profile_survive_but_private_metadata_does_not(self):
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        photo = Image.new('RGBA', (80, 60), (50, 90, 200, 0))
        photo.putpixel((10, 20), (255, 80, 30, 127))
        exif = Image.Exif()
        exif[270] = 'PRIVATE CAMERA NOTE'
        photo.save(self.uploads/'transparent.png', icc_profile=profile, exif=exif)
        metadata = self.images()['/uploads/transparent.png']
        with Image.open(self.root/'.generated'/metadata['full'].lstrip('/')) as full:
            self.assertEqual(full.tobytes(), photo.tobytes())
            self.assertEqual(full.info.get('icc_profile'), profile)
            self.assertFalse(full.getexif())
            self.assertNotIn('exif', full.info)

    def test_tiff_orientation_and_full_resolution_survive_drive_import(self):
        payload = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'PRIVATE CAMERA NOTE'
        Image.new('RGB', (4200, 64), 'navy').save(payload, 'TIFF', exif=exif)
        full_path = prepare_image(payload.getvalue(), self.root/'imported')
        with Image.open(full_path) as full:
            self.assertEqual(full.size, (64, 4200))
            self.assertFalse(full.getexif())

    def test_images_beyond_webp_dimensions_use_full_size_png(self):
        Image.new('RGB', (17000, 10), 'navy').save(self.uploads/'panorama.png')
        metadata = self.images()['/uploads/panorama.png']
        self.assertTrue(metadata['full'].endswith('.png'))
        with Image.open(self.root/'.generated'/metadata['full'].lstrip('/')) as full:
            self.assertEqual(full.size, (17000, 10))
        self.assertIn('17000w', metadata['srcset'])

    def test_tall_previews_have_accurate_unique_srcset_widths(self):
        Image.new('RGB', (20, 20000), 'navy').save(self.uploads/'tall.png')
        metadata = self.images()['/uploads/tall.png']
        widths = []
        for candidate in metadata['srcset'].split(', '):
            url, width = candidate.rsplit(' ', 1)
            widths.append(width)
            base = '.generated' if url.startswith('/uploads/') else 'static'
            with Image.open(self.root/base/url.lstrip('/')) as photo:
                self.assertEqual(photo.width, int(width[:-1]))
        self.assertEqual(len(widths), len(set(widths)))

    def test_16_bit_grayscale_tiff_keeps_levels_in_full_png(self):
        photo = Image.new('I;16', (3, 1))
        photo.putdata([0, 32768, 65535])
        photo.save(self.uploads/'levels.tif')
        metadata = self.images()['/uploads/levels.tif']
        self.assertTrue(metadata['full'].endswith('.png'))
        with Image.open(self.root/'.generated'/metadata['full'].lstrip('/')) as full:
            self.assertEqual(list(full.getdata()), [0, 32768, 65535])
        with Image.open(self.root/'static'/metadata['src'].lstrip('/')) as preview:
            self.assertLess(preview.getpixel((0, 0))[0], 10)
            self.assertGreater(preview.getpixel((2, 0))[0], 240)

    def test_big_endian_16_bit_tiff_keeps_levels(self):
        Image.frombytes('I;16B', (3, 1), b'\x00\x00\x80\x00\xff\xff').save(self.uploads/'big-endian.tif')
        metadata = self.images()['/uploads/big-endian.tif']
        with Image.open(self.root/'.generated'/metadata['full'].lstrip('/')) as full:
            self.assertEqual(list(full.getdata()), [0, 32768, 65535])

    def test_build_rejects_site_above_hosting_limit(self):
        public = self.root/'public'
        public.mkdir()
        (public/'photo.webp').write_bytes(b'12345')
        with patch('validate_public_output.MAX_SITE_BYTES', 4), self.assertRaisesRegex(ValueError, 'GitHub Pages 1 GB'):
            validate(public)

    def test_animated_multipage_corrupt_and_excessive_images_fail_clearly(self):
        frames = [Image.new('RGB', (20, 20), color) for color in ['red', 'blue']]
        for format in ['PNG', 'TIFF', 'WEBP']:
            payload = BytesIO()
            frames[0].save(payload, format, save_all=True, append_images=frames[1:])
            with self.subTest(format=format), self.assertRaisesRegex(ValueError, 'still'):
                read_image(BytesIO(payload.getvalue()))
        with self.assertRaises(Exception):
            read_image(BytesIO(b'not an image'))
        payload = BytesIO()
        frames[0].save(payload, 'PNG')
        with patch('gallery_images.MAX_PIXELS', 100), self.assertRaisesRegex(ValueError, '120 megapixels'):
            read_image(BytesIO(payload.getvalue()))
        (self.uploads/'too-big.jpg').write_bytes(payload.getvalue())
        with patch('optimize_images.MAX_BYTES', 1), self.assertRaisesRegex(ValueError, '200 MB'):
            self.images()
