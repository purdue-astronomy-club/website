"""Full-size, metadata-free browser images plus bounded responsive previews."""
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, ImageCms, ImageOps

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'}
FORMATS = {'JPEG', 'PNG', 'WEBP', 'TIFF'}
MAX_BYTES = 200 * 1024 * 1024
MAX_PIXELS = 120_000_000
PIPELINE_VERSION = 2


def read_image(source):
    """Decode one still image without discarding any spatial resolution."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', Image.DecompressionBombWarning)
        with Image.open(source) as opened:
            if opened.format not in FORMATS or getattr(opened, 'n_frames', 1) != 1:
                raise ValueError('Use a still JPEG, PNG, TIFF or WebP image')
            if opened.width * opened.height > MAX_PIXELS:
                raise ValueError('Photo exceeds 120 megapixels')
            profile = opened.info.get('icc_profile')
            oriented = ImageOps.exif_transpose(opened)
            if profile and oriented.mode == 'CMYK':
                srgb = ImageCms.createProfile('sRGB')
                oriented = ImageCms.profileToProfile(oriented, ImageCms.ImageCmsProfile(BytesIO(profile)), srgb, outputMode='RGB')
                profile = ImageCms.ImageCmsProfile(srgb).tobytes()
            # Keep 16-bit grayscale PNG/TIFF data in PNG. Pillow decodes
            # multichannel TIFF into 8-bit RGB/RGBA; dimensions stay intact.
            mode = oriented.mode if oriented.mode in {'I;16', 'I;16L', 'I;16B'} else (
                'RGBA' if 'A' in oriented.getbands() or 'transparency' in oriented.info else 'RGB')
            converted = oriented.convert(mode)
            clean = Image.new(mode, converted.size)
            clean.paste(converted)
            if profile:
                clean.info['icc_profile'] = profile
            return clean


def save_full(photo, destination):
    """Lossless pixels; PNG also handles images beyond WebP's 16,383px limit."""
    webp = photo.mode in {'RGB', 'RGBA'} and max(photo.size) <= 16383
    path = Path(str(destination) + ('.webp' if webp else '.png'))
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {'icc_profile': photo.info['icc_profile']} if photo.info.get('icc_profile') else {}
    if webp:
        photo.save(path, 'WEBP', lossless=True, exact=True, method=4, **options)
    else:
        if photo.mode in {'I;16B', 'I;16L'}:
            with photo.convert('I').convert('I;16') as little_endian:
                little_endian.save(path, 'PNG', **options)
        else:
            photo.save(path, 'PNG', **options)
    return path


def preview_image(photo):
    if photo.mode.startswith('I;16'):
        return photo.convert('I').point(lambda value: value / 257).convert('RGB')
    return photo
