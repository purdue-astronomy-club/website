"""Create metadata-free responsive derivatives; never mutate officers' source files."""
from hashlib import file_digest
import json
import shutil
from PIL import Image
from content import ROOT
from gallery_images import EXTENSIONS, MAX_BYTES, read_image, save_full, preview_image


def optimize(root=ROOT):
    target = root/'static/media'
    originals = root/'.generated/uploads'
    shutil.rmtree(target, ignore_errors=True)
    shutil.rmtree(originals, ignore_errors=True)
    target.mkdir(parents=True)
    metadata = {}
    for source in sorted((root/'static/uploads').rglob('*')):
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
            continue
        # Imported copies already passed the original-file limit; lossless
        # conversion may produce a larger file than the uploaded JPEG/TIFF.
        if source.stat().st_size > MAX_BYTES and source.parent != root/'static/uploads/drive-gallery':
            raise ValueError(f'{source.name}: maximum image size is 200 MB; use a smaller processed export')
        with read_image(source) as photo:
            with source.open('rb') as stream:
                digest = file_digest(stream, 'sha256').hexdigest()[:16]
            destination = originals/source.relative_to(root/'static/uploads')
            if source.parent == root/'static/uploads/drive-gallery':
                # materialize() supplies sanitized, oriented copies from our
                # importer/snapshot. Reuse their exact bytes and color profile.
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                clean_path = destination
            else:
                clean_path = save_full(photo, destination)
            full = '/uploads/'+clean_path.relative_to(originals).as_posix()
            sizes = sorted(set(min(w, photo.width) for w in [360, 720, 1200, 1800, 2400, 3600]))
            variants = []
            preview = preview_image(photo)
            for width in sizes:
                file = f'{digest}-{width}.webp'
                # Very tall panoramas can exceed WebP's dimension limit even
                # at thumbnail widths; constrain previews, never the full copy.
                ratio = min(width / photo.width, 16383 / photo.height, 1)
                size = (max(1, round(photo.width * ratio)), max(1, round(photo.height * ratio)))
                resized = preview.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
                options = {'icc_profile': photo.info['icc_profile']} if photo.info.get('icc_profile') else {}
                resized.save(target/file, 'WEBP', quality=90, method=4, **options)
                variants.append({'url': '/media/'+file, 'width': resized.width})
                resized.close()
            # Browser can select the full source on large/high-DPI screens.
            srcset = {v['width']: v['url'] for v in variants}
            srcset[photo.width] = full
            metadata['/uploads/'+source.relative_to(root/'static/uploads').as_posix()] = {
                'src': variants[-1]['url'],
                'full': full,
                'srcset': ', '.join(f'{url} {width}w' for width, url in sorted(srcset.items())),
                'width': photo.width, 'height': photo.height,
            }
            if preview is not photo:
                preview.close()
    (root/'data/generated').mkdir(parents=True, exist_ok=True)
    (root/'data/generated/images.json').write_text(json.dumps(metadata))
    print(f'Image pipeline passed: {len(metadata)} images prepared.')

if __name__ == '__main__':
    optimize()
