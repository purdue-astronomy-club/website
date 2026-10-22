"""Import only the designated Drive folder; keep credentials and originals out of output."""
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import os
import re
import shutil
import tempfile
import unicodedata
import warnings

from PIL import Image, ImageOps
import yaml
from content import ROOT

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
MIMES = {'image/jpeg', 'image/png', 'image/webp'}
# Drive keeps full-size originals; CMS uploads retain their separate 15 MB limit.
MAX_BYTES = 200 * 1024 * 1024
MAX_PIXELS = 120_000_000
MAX_PHOTOS = 1000


class DriveError(RuntimeError):
    pass


def display_word(word):
    if re.fullmatch(r'(?:m|ngc|ic|sh2)\d*', word, re.I) or word.lower() in {'ha', 'oiii', 'sii', 'rgb', 'lrgb'}:
        return word.upper()
    return word.title() if word.islower() else word


def parse_filename(filename):
    """The first two underscore-separated fields are names; all remaining fields are target."""
    if any(unicodedata.category(c).startswith('C') for c in filename) or '/' in filename or '\\' in filename:
        raise ValueError('Use a plain photo filename')
    if Path(filename).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise ValueError('Use JPEG, PNG or WebP')
    parts = [part.strip() for part in unicodedata.normalize('NFC', Path(filename).stem).split('_')]
    if len(parts) < 3 or not all(parts):
        raise ValueError('Use firstname_lastname_target.jpg, with underscores between target words')
    return {
        'title': ' '.join(display_word(p) for p in parts[2:]),
        'photographer': ' '.join(display_word(p) for p in parts[:2]),
    }


class DriveClient:
    def __init__(self, credentials_json):
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        try:
            info = json.loads(credentials_json)
            if info.get('token_uri') != 'https://oauth2.googleapis.com/token':
                raise ValueError('Unexpected token endpoint')
            credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            self.session = AuthorizedSession(credentials, refresh_timeout=30)
        except Exception:
            raise DriveError('Check the DRIVE_GALLERY_CREDENTIALS_JSON Actions secret; use a Google service-account JSON key.') from None

    def get(self, file_id='', params=None, binary=False):
        if file_id and not re.fullmatch(r'[A-Za-z0-9_-]+', file_id):
            raise DriveError('Invalid Drive file ID')
        url = 'https://www.googleapis.com/drive/v3/files' + ('/'+file_id if file_id else '')
        try:
            with self.session.get(url, params=params, timeout=(15, 60), stream=True, allow_redirects=False) as response:
                if response.status_code != 200:
                    raise DriveError(f'Drive request failed (HTTP {response.status_code}). Check folder sharing, downloads, credentials and Drive API access.')
                limit = MAX_BYTES if binary else 5 * 1024 * 1024
                chunks, length = [], 0
                for chunk in response.iter_content(64 * 1024):
                    length += len(chunk)
                    if length > limit:
                        raise DriveError('Drive response exceeded the allowed size; prepare smaller web images.')
                    chunks.append(chunk)
                payload = b''.join(chunks)
                return payload if binary else json.loads(payload)
        except DriveError:
            raise
        except Exception:
            # Provider exceptions can contain request details. Never log credentials or tokens.
            raise DriveError('Could not read Drive. The build has stopped; the previous deployed website stays live.') from None

    def list_photos(self, folder_id):
        folder = self.get(folder_id, {'fields': 'id,mimeType,trashed,driveId', 'supportsAllDrives': 'true'})
        if folder.get('mimeType') != 'application/vnd.google-apps.folder' or folder.get('trashed'):
            raise DriveError('The gallery folder is missing, trashed or not a folder.')
        params = {
            'q': f"'{folder_id}' in parents and trashed = false",
            'fields': 'nextPageToken,incompleteSearch,files(id,name,mimeType,modifiedTime,md5Checksum,size,capabilities(canDownload))',
            'pageSize': 100, 'spaces': 'drive', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true',
            'corpora': 'drive' if folder.get('driveId') else 'user',
        }
        if folder.get('driveId'):
            params['driveId'] = folder['driveId']
        files, tokens = [], set()
        while True:
            page = self.get(params=params)
            if page.get('incompleteSearch') or not isinstance(page.get('files'), list):
                raise DriveError('Drive returned an incomplete listing; no gallery removals have been applied.')
            files.extend(page['files'])
            if len(files) > MAX_PHOTOS:
                raise DriveError(f'The gallery supports at most {MAX_PHOTOS} direct files; split or archive the folder first.')
            token = page.get('nextPageToken')
            if not token:
                return files
            if token in tokens:
                raise DriveError('Drive pagination repeated; no gallery removals have been applied.')
            tokens.add(token)
            params['pageToken'] = token

    def download(self, file_id):
        return self.get(file_id, {'alt': 'media', 'supportsAllDrives': 'true'}, binary=True)


def prepare_image(payload, destination):
    """Only an oriented, resized, metadata-free still image survives the import."""
    if len(payload) > MAX_BYTES:
        raise DriveError('A Drive photo exceeds 200 MB. Prepare a smaller JPEG, PNG or WebP.')
    with warnings.catch_warnings():
        # Check our explicit ceiling before decoding; Pillow's default warning
        # begins below that ceiling and its larger hard limit remains active.
        warnings.simplefilter('ignore', Image.DecompressionBombWarning)
        try:
            with Image.open(BytesIO(payload)) as opened:
                if opened.format not in {'JPEG', 'PNG', 'WEBP'} or getattr(opened, 'n_frames', 1) != 1:
                    raise ValueError('Use a still JPEG, PNG or WebP')
                if opened.width * opened.height > MAX_PIXELS:
                    raise ValueError('Photo exceeds 120 megapixels')
                mode = 'RGBA' if 'A' in opened.getbands() or 'transparency' in opened.info else 'RGB'
                if opened.format == 'JPEG':
                    opened.draft(mode, (2400, 2400))
                oriented = ImageOps.exif_transpose(opened)
                oriented.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                oriented = oriented.convert(mode)
                # A new image has no inherited EXIF, comments or other embedded metadata.
                clean = Image.new(mode, oriented.size)
                clean.paste(oriented)
                clean.save(destination, 'WEBP', quality=90, method=6)
        except Exception:
            raise DriveError('A gallery photo could not be prepared. Use a valid still JPEG/PNG/WebP, at most 200 MB and 120 megapixels.') from None


def settings(root):
    path = root/'data/drive_gallery.yml'
    config = yaml.safe_load(path.read_text()) if path.exists() else {}
    config = config or {}
    if not isinstance(config, dict) or not isinstance(config.get('enabled', False), bool):
        raise DriveError('Drive Gallery Settings needs an enabled on/off value.')
    return config


def materialize(root, records, cache):
    content = root/'.generated/content/drive-gallery'
    uploads = root/'static/uploads/drive-gallery'
    shutil.rmtree(content, ignore_errors=True)
    shutil.rmtree(uploads, ignore_errors=True)
    content.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)
    for record in records:
        ref = record['reference']
        shutil.copy2(cache/'images'/f'{ref}.webp', uploads/f'{ref}.webp')
        frontmatter = {k: v for k, v in record.items() if k not in {'reference', 'fingerprint', 'filename'}}
        (content/f'{ref}.md').write_text('---\n'+yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)+'---\n')


def photo_overrides(config):
    overrides = config.get('photos') or []
    if not isinstance(overrides, list) or any(not isinstance(p, dict) or not p.get('filename') for p in overrides):
        raise DriveError('Every Drive photo correction needs its exact filename, including the extension.')
    by_name = {p['filename']: p for p in overrides}
    if len(by_name) != len(overrides):
        raise DriveError('Use one correction per Drive filename.')
    return by_name


def use_snapshot(root, config):
    """Ship approved web copies so the first deployment needs no Drive credentials."""
    snapshot = root/'assets/drive-gallery-snapshot'
    manifest_path = snapshot/'manifest.json'
    if not manifest_path.is_file():
        raise DriveError('Initial gallery photos are missing; restore assets/drive-gallery-snapshot or turn off the initial-photo setting.')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('folder_id') != config.get('folder_id'):
        raise DriveError('The initial photos belong to a different folder. Turn off the initial-photo setting before changing folders.')
    by_name = photo_overrides(config)
    records = []
    for source in manifest['photos']:
        override = by_name.get(source['filename'], {})
        if override.get('hidden'):
            continue
        record = dict(source)
        if not re.fullmatch(r'drive-[a-f0-9]{20}', record['reference']):
            raise DriveError('An initial gallery photo has an invalid reference.')
        title = str(override.get('title') or source['title'])
        photographer = str(override.get('photographer') or source['photographer'])
        original_alt = f"Astrophotograph of {source['title']} by {source['photographer']}."
        alt = source.get('alt')
        if not alt or alt == original_alt:
            alt = f'Astrophotograph of {title} by {photographer}.'
        record.update(title=title, photographer=photographer,
                      alt=str(override.get('alt') or alt),
                      caption=str(override.get('caption') or source.get('caption') or ''),
                      featured=bool(override.get('featured', config.get('featured', False))))
        records.append(record)
    materialize(root, records, snapshot)
    print(f'Drive gallery: using {len(records)} included photos; live sync is disabled or offline.')
    return records


def sync(root=ROOT, client=None, offline=None):
    config = settings(root)
    cache = root/'.generated/drive-gallery'
    offline = bool(os.environ.get('PAC_OFFLINE')) if offline is None else offline
    if not config.get('enabled') or offline:
        if config.get('use_snapshot', False):
            return use_snapshot(root, config)
        materialize(root, [], cache)
        print('Drive gallery: disabled or offline; CMS photography remains available.')
        return []
    folder_id = str(config.get('folder_id', ''))
    if not re.fullmatch(r'[A-Za-z0-9_-]+', folder_id):
        raise DriveError('Set a valid folder ID in Drive Gallery Settings.')
    if client is None:
        secret = os.environ.get('DRIVE_GALLERY_CREDENTIALS_JSON')
        if not secret:
            raise DriveError('Drive gallery is enabled. Add the DRIVE_GALLERY_CREDENTIALS_JSON Actions secret, or disable the connection in CMS.')
        client = DriveClient(secret)
    by_name = photo_overrides(config)
    files = client.list_photos(folder_id)  # Complete listing before modifying any generated files.
    previous = {}
    if (cache/'manifest.json').exists():
        manifest = json.loads((cache/'manifest.json').read_text())
        if manifest.get('folder_id') == folder_id:
            previous = {p['reference']: p for p in manifest['photos']}
    root.joinpath('.generated').mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='drive-stage-', dir=root/'.generated') as tmp:
        stage = Path(tmp)
        (stage/'images').mkdir()
        records, seen = [], set()
        for file in sorted(files, key=lambda f: (f.get('name', ''), f.get('id', ''))):
            filename = file.get('name', '')
            if file.get('mimeType') not in MIMES:
                print(f'Drive gallery: skipped unsupported file {filename!r}')
                continue
            try:
                parsed = parse_filename(filename)
            except ValueError as error:
                print(f'Drive gallery: skipped {filename!r}: {error}')
                continue
            override = by_name.get(filename, {})
            if override.get('hidden'):
                continue
            file_id = str(file.get('id', ''))
            if not re.fullmatch(r'[A-Za-z0-9_-]+', file_id) or file_id in seen:
                raise DriveError('Drive returned an invalid or duplicate photo ID.')
            seen.add(file_id)
            if not file.get('capabilities', {}).get('canDownload'):
                raise DriveError(f'Downloads are disabled for {filename!r}; enable downloading for the gallery reader.')
            if int(file.get('size', 0)) > MAX_BYTES:
                raise DriveError(f'{filename!r} exceeds 200 MB; prepare a smaller copy.')
            ref = 'drive-'+sha256(file_id.encode()).hexdigest()[:20]
            fingerprint = sha256(json.dumps([file.get('md5Checksum'), file.get('modifiedTime'), file.get('size')]).encode()).hexdigest()
            output = stage/'images'/f'{ref}.webp'
            old = previous.get(ref, {})
            if file.get('md5Checksum') and old.get('fingerprint') == fingerprint and (cache/'images'/output.name).is_file():
                shutil.copy2(cache/'images'/output.name, output)
            else:
                prepare_image(client.download(file_id), output)
            title = str(override.get('title') or parsed['title'])
            photographer = str(override.get('photographer') or parsed['photographer'])
            records.append({
                'reference': ref, 'filename': filename, 'fingerprint': fingerprint,
                'title': title, 'photographer': photographer,
                'alt': str(override.get('alt') or f'Astrophotograph of {title} by {photographer}.'),
                'caption': str(override.get('caption') or ''),
                'image': f'/uploads/drive-gallery/{ref}.webp',
                'draft': False, 'permission_to_publish': True,
                'featured': bool(override.get('featured', config.get('featured', False))),
            })
        manifest = {'folder_id': folder_id, 'synced_at': datetime.now(timezone.utc).isoformat(), 'photos': records}
        (stage/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        # Publish/cache only the complete sanitized snapshot, never a partial download.
        backup = cache.with_name('drive-gallery-previous')
        shutil.rmtree(backup, ignore_errors=True)
        if cache.exists():
            cache.rename(backup)
        try:
            stage.rename(cache)
        except Exception:
            if backup.exists():
                backup.rename(cache)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        materialize(root, records, cache)
    print(f'Drive gallery: prepared {len(records)} credited photos.')
    return records


if __name__ == '__main__':
    sync()
