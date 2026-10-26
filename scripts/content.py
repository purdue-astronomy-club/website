"""Content validation and the single canonical calendar representation."""
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import re
import yaml
from sky_icons import PLANETS, icon_for
from gallery_images import EXTENSIONS

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('America/Indiana/Indianapolis')
BASE = 'https://purdueastro.club'
TYPES = {'pac': 'PAC event', 'joint': 'Joint event', 'astronomy': 'Astronomy'}


class ContentLoader(yaml.SafeLoader):
    """Keep CMS clock strings instead of YAML 1.1's obsolete base-60 integers."""


def integer_or_clock(loader, node):
    if ':' in node.value:
        return loader.construct_scalar(node)
    return yaml.SafeLoader.construct_yaml_int(loader, node)


ContentLoader.add_constructor('tag:yaml.org,2002:int', integer_or_clock)


def read_yaml(path):
    return yaml.load(path.read_text(), Loader=ContentLoader)


def read_record(path):
    text = path.read_text()
    if not text.startswith('---\n'):
        raise ValueError('Entry needs YAML front matter')
    parts = text.split('---', 2)
    return yaml.load(parts[1], Loader=ContentLoader) or {}, parts[2].strip()


def day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def local_datetime(d, clock):
    if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', str(clock)):
        raise ValueError('Times must use 24-hour HH:mm, for example 19:00')
    naive = datetime.combine(day(d), time.fromisoformat(clock))
    aware = naive.replace(tzinfo=TZ)
    # Reject nonexistent and ambiguous local clock times at DST changes.
    if aware.astimezone(timezone.utc).astimezone(TZ).replace(tzinfo=None) != naive:
        raise ValueError('This local time does not exist due to daylight saving time')
    if naive.replace(tzinfo=TZ, fold=0).utcoffset() != naive.replace(tzinfo=TZ, fold=1).utcoffset():
        raise ValueError('This local time is ambiguous at the daylight saving change; choose a different time')
    return aware


def public_url(value, email=False):
    if not value:
        return
    parsed = urlparse(str(value))
    if email:
        if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', str(value)):
            raise ValueError('Use a valid approved email address')
    elif parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Public links must use a full https:// URL')
    elif parsed.hostname in {'localhost', '127.0.0.1'} or re.match(r'^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)', parsed.hostname):
        raise ValueError('A public link cannot use a local network address')


def image(root, value, alt, required=False):
    if not value:
        if required:
            raise ValueError('Please select an image')
        return
    if not alt or not str(alt).strip():
        raise ValueError(f'Please describe image {value} in its alt text field')
    if not str(value).startswith('/uploads/') or '..' in Path(value).parts:
        raise ValueError('Select images from the CMS Media library (/uploads/)')
    if Path(value).suffix.lower() not in EXTENSIONS:
        raise ValueError('Use JPEG, PNG, TIFF or WebP images')
    file = root / 'static' / value.lstrip('/')
    if not file.is_file():
        raise ValueError(f'Image file is missing: {value}; upload it or select another image')


def normalize(record, section, slug, now=None):
    now = now or datetime.now(TZ)
    d = day(record['start_date'])
    end_day = day(record.get('end_date') or d)
    all_day = bool(record.get('all_day', section == 'astronomy'))
    if end_day < d:
        raise ValueError('End date must be on or after the start date')
    if all_day:
        start, end = d, end_day + timedelta(days=1)  # CMS end date is inclusive.
        sort_start = datetime.combine(d, time.min, TZ)
        sort_end = datetime.combine(end, time.min, TZ)
        clock_label = 'All day'
    else:
        start = local_datetime(d, record.get('start_time', ''))
        if record.get('end_date') and not record.get('end_time'):
            raise ValueError('Supply an end time when using an end date for a timed event')
        end = local_datetime(end_day, record['end_time']) if record.get('end_time') else start + timedelta(hours=1)
        if end <= start:
            raise ValueError('End time must be after the start time; set end date for overnight events')
        sort_start, sort_end = start, end
        clock_label = start.strftime('%I:%M %p').lstrip('0')
        if record.get('end_time'):
            clock_label += ' – ' + end.strftime('%I:%M %p').lstrip('0')
    ctype = 'astronomy' if section == 'astronomy' else record.get('calendar_type', 'pac')
    status = record.get('status', 'scheduled')
    if ctype not in TYPES:
        raise ValueError('Select PAC or Joint as the calendar category')
    if status not in {'scheduled', 'tentative', 'cancelled', 'postponed'}:
        raise ValueError('Select a valid event status')
    return {
        'id': f'{section}/{slug}', 'slug': slug, 'title': record['title'],
        'summary': record['summary'], 'start': start.isoformat(), 'end': end.isoformat(),
        'allDay': all_day, 'url': f'/{section}/{slug}/', 'calendarType': ctype,
        'categoryLabel': TYPES[ctype], 'status': status,
        'category': record.get('category', record.get('kind', 'other')),
        'origin': 'curated', 'icon': icon_for(record) if ctype=='astronomy' else '',
        'planet': record.get('planet',''), 'replacesAutoEvent':record.get('replaces_auto_event',''),
        'location': record.get('location', ''), 'address': record.get('address', ''),
        'mapUrl': record.get('map_url', ''), 'registrationUrl': record.get('registration_url', ''),
        'coverImage': record.get('cover_image', ''), 'coverAlt': record.get('cover_alt', ''),
        'relatedAlbum': record.get('related_album_slug', ''),
        'sourceUrl': record.get('source_url', ''), 'lastVerified': str(record.get('last_verified') or ''),
        'dateLabel': d.strftime('%A, %B %-d, %Y') + ((' – ' + end_day.strftime('%B %-d, %Y')) if end_day != d else ''),
        'timeLabel': clock_label, 'day': d.strftime('%d'), 'month': d.strftime('%b'),
        'year': d.year, 'startDate': d.isoformat(), 'endDate': end_day.isoformat(),
        'upcoming': sort_end > now and status == 'scheduled' and ctype != 'astronomy',
        'past': sort_end <= now,
    }


def collect(root=ROOT, now=None):
    events, errors = [], []
    for path in sorted((root / 'content').glob('*/*.md')):
        if path.name.startswith('_'):
            continue
        try:
            r, body = read_record(path)
            if not isinstance(r.get('draft'), bool):
                raise ValueError('Set Keep as draft to on or off explicitly before saving this entry')
            if r['draft']:
                continue
            if not r.get('title'):
                raise ValueError('A title is required')
            if 'slug' in r or 'url' in r:
                raise ValueError('Keep the saved filename as the permanent URL; use aliases when moving an entry')
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', path.stem):
                raise ValueError('Use a lowercase filename with letters, numbers and hyphens')
            section = path.parent.name
            if section in {'events', 'astronomy'}:
                if not r.get('summary'):
                    raise ValueError('Please add a short summary')
                if section == 'events':
                    if r.get('category') not in {'observing', 'workshop', 'talk', 'outreach', 'social', 'other'}:
                        raise ValueError('Select an activity type')
                    image(root, r.get('cover_image'), r.get('cover_alt'))
                    for field in ['registration_url', 'map_url']:
                        public_url(r.get(field))
                else:
                    if r.get('kind') not in {'new_moon', 'full_moon', 'first_quarter', 'last_quarter', 'meteor_shower', 'planetary', 'opposition', 'season', 'eclipse', 'other'}:
                        raise ValueError('Select an astronomy type')
                    if r.get('planet') and r['planet'] not in PLANETS:
                        raise ValueError('Select a supported planet')
                    if not r.get('source_url') or not r.get('last_verified'):
                        raise ValueError('Verify astronomy dates: add a source URL and verification date before publication')
                    public_url(r['source_url'])
                    day(r['last_verified'])
                for field, target in [('related_album_slug', 'albums')]:
                    if r.get(field) and not (root / 'content' / target / (r[field] + '.md')).is_file():
                        raise ValueError(f'Related {target} entry does not exist')
                events.append(normalize(r, section, path.stem, now))
            elif section == 'albums':
                day(r['event_date'])
                image(root, r.get('cover_image'), r.get('cover_alt'))
                if not r.get('permission_to_publish'):
                    raise ValueError('Confirm photo publication permission')
                if not r.get('photos'):
                    raise ValueError('Add at least one photograph')
                for photo in r['photos']:
                    image(root, photo.get('image'), photo.get('alt'), True)
                    if not photo.get('credit'):
                        raise ValueError('Each album photo needs a photographer credit')
                if r.get('related_event_slug') and not (root/'content/events'/f"{r['related_event_slug']}.md").is_file():
                    raise ValueError('Related event filename does not exist')
            elif section == 'astrophotography':
                image(root, r.get('image'), r.get('alt'), True)
                if not r.get('photographer') or not r.get('permission_to_publish'):
                    raise ValueError('Add photographer credit and confirm publication permission')
                if r.get('capture_date'):
                    day(r['capture_date'])
            elif section == 'announcements':
                day(r['publish_date'])
                if not r.get('summary'):
                    raise ValueError('Add an announcement summary')
                image(root, r.get('image'), r.get('image_alt'))
            elif section == 'officers':
                if not r.get('role'):
                    raise ValueError('Add the officer role')
                image(root, r.get('image'), r.get('image_alt'))
                public_url(r.get('public_contact'), email=True)
            elif section == 'sponsors':
                image(root, r.get('logo'), r.get('logo_alt'))
                public_url(r.get('website'))
            # Rich-text images must also exist and have alt text.
            for alt, value in re.findall(r'!\[([^\]]*)\]\(([^\s)]+)(?:\s+[^)]*)?\)', body):
                image(root, value, alt, True)
            for url in re.findall(r'(?<!!)\[[^\]]*\]\(([^\s)]+)', body):
                if not url.startswith(('/', '#', 'mailto:')):
                    public_url(url)
                if url.startswith('//'):
                    raise ValueError('Use root-relative internal links or full HTTPS links')
        except (ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    months = read_yaml(root/'data/calendar/banners.yml') or []
    seen = set()
    for m in months:
        try:
            month = m['month']
            if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month) or month in seen:
                raise ValueError('Use a unique YYYY-MM month')
            seen.add(month)
            if m.get('banner_image') and m.get('permission_to_publish'):
                image(root, m['banner_image'], m.get('banner_alt'), True)
                if not m.get('photographer'):
                    raise ValueError('Monthly photos need a photographer credit')
            if (m.get('night_sky_notes') or m.get('visible_planets_notes')):
                if not m.get('source_url') or not m.get('last_verified'):
                    raise ValueError('Monthly sky notes need a source URL and verification date')
                public_url(m['source_url'])
                day(m['last_verified'])
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'Calendar Months: {exc}')
    try:
        home = read_yaml(root/'data/home.yml')
        image(root, home.get('hero_image'), home.get('hero_image_alt'))
        site = read_yaml(root/'data/site.yml')
        public_url(site.get('public_email'), email=True)
        for key in ['instagram', 'discord', 'github']:
            public_url(site.get(key))
    except (ValueError, TypeError) as exc:
        errors.append(f'Website settings: {exc}')
    if errors:
        raise ValueError('\n'.join(errors))
    return sorted(events, key=lambda e: e['start']), months
