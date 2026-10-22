"""Import peak-night facts only from AMS's public calendar; retain a last-good cache."""
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
from content import ROOT

AMS_URL = 'https://www.amsmeteors.org/calendar/'
MONTHS = {name: i for i, name in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}

class MeteorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.heading = False
        self.records = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'shower-card' in attrs.get('class', '').split():
            self.current = {'id':attrs.get('id', ''), 'name':'', 'text':[]}
        if self.current is not None and tag == 'h2':
            self.heading = True
    def handle_endtag(self, tag):
        if tag == 'h2': self.heading = False
        if tag == 'article' and self.current is not None:
            self.records.append(self.current)
            self.current = None
    def handle_data(self, text):
        if self.current is not None:
            self.current['text'].append(text)
            if self.heading: self.current['name'] += text


def parse_meteors(html):
    parser = MeteorParser(); parser.feed(html)
    records = []
    for entry in parser.records:
        text = ' '.join(' '.join(entry['text']).split())
        match = re.search(r'on peak night \(\s*([A-Z][a-z]{2})\s+(\d{1,2})\s*[–−-]\s*(?:([A-Z][a-z]{2})\s+)?(\d{1,2}),?\s+(\d{4})\s*\)', text)
        if not match or not re.fullmatch(r'[a-z0-9-]+', entry['id']) or not entry['name'].strip():
            raise ValueError('AMS peak-night markup changed; refusing to guess meteor dates')
        month, first, end_month, last, year = match.groups()
        start = date(int(year), MONTHS[month], int(first))
        end = date(int(year), MONTHS[end_month or month], int(last))
        if end < start: end = end.replace(year=end.year+1)
        if end-start > timedelta(days=2): raise ValueError('Unexpected meteor peak window')
        records.append({'id':entry['id'], 'name':entry['name'].strip(), 'start_date':start.isoformat(), 'end_date':end.isoformat()})
    if not 3 <= len(records) <= 30 or len({r['id'] for r in records}) != len(records):
        raise ValueError('Unexpected AMS calendar; retaining the last verified data')
    return records


def load_snapshot(root=ROOT):
    paths = [root/'.generated/meteor-cache.json', root/'data/astronomy/meteor-showers.json']
    candidates = []
    for path in paths:
        if path.is_file():
            data = json.loads(path.read_text())
            if data.get('source_url') != AMS_URL or not data.get('records'):
                raise ValueError(f'Invalid meteor source snapshot: {path}')
            date.fromisoformat(data['checked_on'])
            for record in data['records']:
                if not re.fullmatch(r'[a-z0-9-]+', record.get('id','')) or not isinstance(record.get('name'),str) or not 1<=len(record['name'])<=100:
                    raise ValueError('Invalid cached meteor identity')
                start, end = date.fromisoformat(record['start_date']), date.fromisoformat(record['end_date'])
                if end < start or end-start > timedelta(days=2):
                    raise ValueError('Invalid cached meteor peak window')
            candidates.append(data)
    return max(candidates, key=lambda x:x['checked_on']) if candidates else {'source_url':AMS_URL,'checked_on':'','records':[]}


def refresh(root=ROOT):
    cache=root/'.generated/meteor-cache.json'
    if cache.is_file():
        prior=load_snapshot(root)
        if prior['checked_on']==datetime.now(timezone.utc).date().isoformat():
            print('AMS meteor forecasts were already checked today; reusing the dated cache.')
            return True
    try:
        request = Request(AMS_URL, headers={'User-Agent':'Purdue-Astronomy-Club-Calendar/1.0 (+https://purdueastro.club/)'})
        with urlopen(request, timeout=20) as response:
            html = response.read(2_000_001)
        if len(html)>2_000_000: raise ValueError('AMS response exceeded expected size')
        records = parse_meteors(html.decode('utf-8'))
        current_year = datetime.now(timezone.utc).year
        if not all(current_year-1 <= int(r['start_date'][:4]) <= current_year+2 for r in records):
            raise ValueError('AMS forecast years are outside the current import window')
        # Keep prior dated peaks as the rolling official calendar advances.
        old = load_snapshot(root)
        merged = {(r['id'],r['start_date'][:4]):r for r in old['records']}
        merged.update({(r['id'],r['start_date'][:4]):r for r in records})
        data = {'source_url':AMS_URL,'checked_on':datetime.now(timezone.utc).date().isoformat(),
                'records': sorted((r for r in merged.values() if int(r['start_date'][:4])>=current_year-1), key=lambda r:r['start_date'])}
        path = root/'.generated/meteor-cache.json';path.parent.mkdir(parents=True,exist_ok=True)
        staging=path.with_suffix('.tmp')
        staging.write_text(json.dumps(data,indent=2)+'\n');staging.replace(path)
        print(f'Refreshed {len(records)} AMS meteor forecasts; {len(data["records"])} dated peaks retained.')
        return True
    except (OSError, ValueError, KeyError) as exc:
        prior = load_snapshot(root)
        print(f'Warning: meteor refresh unavailable ({exc}); using {len(prior["records"])} source-backed cached forecasts checked {prior["checked_on"] or "never"}.')
        return False

if __name__=='__main__': refresh()
