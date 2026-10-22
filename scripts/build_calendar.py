"""Generate Hugo data, browser JSON and RFC 5545 feeds from validated records."""
from datetime import datetime, date, timezone
from pathlib import Path
import json
import shutil
from icalendar import Calendar, Event
from content import ROOT, BASE, collect
from automatic_sky import automatic_events


def calendar_bytes(events, records_root=ROOT):
    cal = Calendar()
    cal.add('prodid', '-//Purdue Astronomy Club//Public Calendar//EN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'Purdue Astronomy Club')
    cal.add('x-wr-timezone', 'America/Indiana/Indianapolis')
    for r in events:
        e = Event()
        e.add('uid', r['id'] + '@purdueastro.club')
        # Source mtime is deterministic in one checkout; Actions checkout time gives a fresh revision.
        source = records_root/'content'/f"{r['id']}.md"
        modified = datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).replace(microsecond=0) if source.exists() else datetime.now(timezone.utc).replace(microsecond=0)
        e.add('dtstamp', modified)
        e.add('last-modified', modified)
        e.add('sequence', int(modified.timestamp()))
        title = r['title']
        if r['status'] in {'cancelled', 'postponed', 'tentative'}:
            title = r['status'].title() + ': ' + title
        e.add('summary', title)
        e.add('description', r['summary'] + '\n' + BASE + r['url'])
        e.add('location', r['location'])
        e.add('url', BASE + r['url'])
        parse = date.fromisoformat if r['allDay'] else datetime.fromisoformat
        start, end = parse(r['start']), parse(r['end'])
        if not r['allDay']:
            start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        e.add('dtstart', start)
        e.add('dtend', end)
        # A postponement retracts the original slot until a replacement is scheduled.
        e.add('status', 'CANCELLED' if r['status'] in {'cancelled', 'postponed'} else ('TENTATIVE' if r['status'] == 'tentative' else 'CONFIRMED'))
        e.add('categories', r['categoryLabel'])
        cal.add_component(e)
    return cal.to_ical()


def generate(root=ROOT):
    events, months = collect(root)
    auto, status = automatic_events(root, events)
    events = sorted([*events, *auto], key=lambda r:r['start'])
    generated = root/'data/generated'
    generated.mkdir(parents=True, exist_ok=True)
    (generated/'sky.json').write_text(json.dumps(status))
    (generated/'events.json').write_text(json.dumps(events, indent=2, ensure_ascii=False))
    (root/'static/events.json').write_text(json.dumps(events, ensure_ascii=False))
    for section in ['events', 'astronomy']:
        shutil.rmtree(root/'static'/section, ignore_errors=True)
    (root/'static/calendar.ics').write_bytes(calendar_bytes(events, root))
    for e in events:
        target = root/'static'/e['id']/'event.ics'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(calendar_bytes([e], root))
    safe_months = []
    for m in months:
        n = dict(m)
        if not (n.get('permission_to_publish') and n.get('banner_image')):
            for key in ['banner_image', 'banner_alt', 'photographer']:
                n.pop(key, None)
        safe_months.append(n)
    (root/'static/months.json').write_text(json.dumps(safe_months, default=str))
    print(f'Validated and generated {len(events)} published calendar records; {len(months)} month settings.')


if __name__ == '__main__':
    generate()
