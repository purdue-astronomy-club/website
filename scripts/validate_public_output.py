"""Reject broken internal links/media, draft leaks and unintended infrastructure references."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import os
import re
from content import ROOT, BASE, read_record

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
    banned = ['10.0.0.141', 'r410', 'authentik', 'copyparty', 'snipe-it', 'member dashboard']
    banned += [s.strip().lower() for s in os.environ.get('FORBIDDEN_PUBLIC_HOSTS', '').split(',') if s.strip()]
    draft_paths = []
    for file in (ROOT/'content').glob('*/*.md'):
        if not file.name.startswith('_') and read_record(file)[0].get('draft', True):
            draft_paths.append('/'+file.parent.name+'/'+file.stem+'/')
    files = list(public.rglob('*'))
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
            if parsed.netloc == urlsplit(BASE).netloc:
                path = parsed.path
            elif parsed.netloc or parsed.scheme or link.startswith('#'):
                continue
            else:
                path = parsed.path
            if not path:
                continue
            target = public/unquote(path.lstrip('/')) if path.startswith('/') else file.parent/unquote(path)
            if target.is_dir():
                target = target/'index.html'
            if not target.exists():
                errors.append(f'{file.relative_to(public)}: broken link/image {link}')
    if errors:
        raise ValueError('\n'.join(errors[:100]))
    print(f'Public output checks passed: {len(files)} files; no broken internal links or draft/private references.')

if __name__ == '__main__':
    validate()
