"""Create metadata-free responsive derivatives; never mutate officers' source files."""
from hashlib import sha256
from pathlib import Path
import json
import shutil
from PIL import Image, ImageOps
from content import ROOT


def optimize(root=ROOT):
    target = root/'static/media'
    originals = root/'.generated/uploads'
    shutil.rmtree(target, ignore_errors=True)
    shutil.rmtree(originals, ignore_errors=True)
    target.mkdir(parents=True)
    metadata = {}
    for source in sorted((root/'static/uploads').rglob('*')):
        if source.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            continue
        if source.stat().st_size > 15 * 1024 * 1024:
            raise ValueError(f'{source.name}: please prepare this photo before upload (maximum 15 MB)')
        with Image.open(source) as opened:
            photo = ImageOps.exif_transpose(opened).convert('RGBA' if 'A' in opened.getbands() or 'transparency' in opened.info else 'RGB')
            digest = sha256(source.read_bytes()).hexdigest()[:16]
            sizes = sorted(set(min(w, photo.width) for w in [360, 720, 1200, 1800]))
            variants = []
            for width in sizes:
                resized = photo.copy()
                resized.thumbnail((width, 10000), Image.Resampling.LANCZOS)
                file = f'{digest}-{width}.webp'
                resized.save(target/file, 'WEBP', quality=85, method=6)
                variants.append({'url': '/media/'+file, 'width': resized.width})
            metadata['/uploads/'+source.relative_to(root/'static/uploads').as_posix()] = {
                'src': variants[-1]['url'],
                'srcset': ', '.join(f"{v['url']} {v['width']}w" for v in variants),
                'width': photo.width, 'height': photo.height,
            }
            clean_path = originals/source.relative_to(root/'static/uploads')
            clean_path.parent.mkdir(parents=True, exist_ok=True)
            photo.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            photo.save(clean_path, quality=90)
    (root/'data/generated/images.json').write_text(json.dumps(metadata))
    print(f'Image pipeline passed: {len(metadata)} images prepared.')

if __name__ == '__main__':
    optimize()
