"""Reject broken internal links/media, draft leaks and unintended infrastructure references."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import os
import re
from content import ROOT, read_record
from site_config import base_url

MAX_SITE_BYTES = 1_000_000_000  # GitHub Pages published-site limit.

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'src', 'href', 'poster'} and value:
                self.links.append(value)
            if key == 'srcset' and value:
                self.links.extend(x.strip().split()[0] for x in value.split(','))

def validate(public=ROOT/'public'):
    errors = []
    deployment = urlsplit(base_url(public.parent))
    prefix = deployment.path
    banned = ['10.0.0.141', 'r410', 'authentik', 'copyparty', 'snipe-it', 'member dashboard']
    banned += [s.strip().lower() for s in os.environ.get('FORBIDDEN_PUBLIC_HOSTS', '').split(',') if s.strip()]
    draft_paths = []
    for file in (ROOT/'content').glob('*/*.md'):
        if not file.name.startswith('_') and read_record(file)[0].get('draft', True):
            draft_paths.append('/'+file.parent.name+'/'+file.stem+'/')
    files = list(public.rglob('*'))
    total_bytes = sum(file.stat().st_size for file in files if file.is_file())
    if total_bytes > MAX_SITE_BYTES:
        errors.append('Published site exceeds the GitHub Pages 1 GB limit; archive photos or move full-resolution images to larger hosting.')
    for file in files:
        if not file.is_file() or file.suffix not in {'.html', '.js', '.json', '.xml', '.txt', '.css', '.ics'}:
            continue
        text = file.read_text(errors='replace')
        for token in banned + draft_paths:
            if token.lower() in text.lower():
                errors.append(f'{file.relative_to(public)}: forbidden/draft reference {token}')
        if file.suffix != '.html':
            continue
        parser = Links()
        parser.feed(text)
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.netloc == deployment.netloc:
                path = parsed.path
            elif parsed.netloc or parsed.scheme or link.startswith('#'):
                continue
            else:
                path = parsed.path
            if not path:
                continue
            if path.startswith('/'):
                if not path.startswith(prefix):
                    errors.append(f'{file.relative_to(public)}: URL escapes the website deployment path {link}')
                    continue
                target = public/unquote(path[len(prefix):])
            else:
                target = file.parent/unquote(path)
            if target.is_dir():
                target = target/'index.html'
            if not target.exists():
                errors.append(f'{file.relative_to(public)}: broken link/image {link}')
    if errors:
        raise ValueError('\n'.join(errors[:100]))
    print(f'Public output checks passed: {len(files)} files, {total_bytes / 1_000_000:.1f} MB; no broken internal links or draft/private references.')

if __name__ == '__main__':
    validate()
