"""Calculate dated sky events locally and merge dated meteor forecasts, without runtime APIs."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import shutil
import astronomy
import yaml
from content import ROOT, TZ, normalize, read_yaml
from refresh_meteors import AMS_URL, load_snapshot

ENGINE_SOURCE = 'https://pypi.org/project/astronomy-engine/'
PHASES = [('new_moon','New Moon'),('first_quarter','First Quarter Moon'),('full_moon','Full Moon'),('last_quarter','Last Quarter Moon')]
from sky_icons import PLANETS, ICONS


def settings(root=ROOT):
    path=root/'data/astronomy.yml'
    config=read_yaml(path) if path.exists() else {'enabled':False}
    config=config or {}
    for field in ['enabled','moon_phases','planetary_oppositions','meteor_showers','seasons']:
        if field in config and not isinstance(config[field],bool): raise ValueError(f'Automatic sky: {field} must be on or off')
    for field in ['years_past','years_ahead']:
        if not isinstance(config.get(field,1),int) or not 0<=config.get(field,1)<=2: raise ValueError(f'Automatic sky: {field} must be 0, 1, or 2')
    if not isinstance(config.get('hidden_events',[]),list): raise ValueError('Automatic sky: hidden events must be a list')
    return config


def instant_record(title, kind, moment, identity, summary, checked, planet=''):
    local = moment.Utc().replace(tzinfo=timezone.utc).astimezone(TZ)
    # Round only for display. JSON and ICS keep the actual calculated offset/instant.
    raw={'title':title,'summary':summary,'kind':kind,'start_date':local.date().isoformat(),
         'start_time':local.strftime('%H:%M'),'all_day':True,'source_url':ENGINE_SOURCE,'last_verified':checked}
    item=normalize(raw,'astronomy','auto-'+identity)
    # The UTC-derived instant is unambiguous even during the repeated DST hour.
    end=(local.astimezone(timezone.utc)+timedelta(minutes=1)).astimezone(TZ)
    item.update(allDay=False,start=local.isoformat(timespec='seconds'),end=end.isoformat(timespec='seconds'),
                timeLabel=local.strftime('%I:%M %p').lstrip('0')+' · Indiana time (calculated)',
                upcoming=False, origin='calculated',planet=planet,
                icon=planet.lower() if planet else ICONS[kind], instant=True)
    return item


def calculate(start_year, end_year, config, checked):
    start=datetime(start_year,1,1,tzinfo=TZ).astimezone(timezone.utc)
    end=datetime(end_year+1,1,1,tzinfo=TZ).astimezone(timezone.utc)
    begin=astronomy.Time.Parse(start.isoformat().replace('+00:00','Z'))
    limit=astronomy.Time.Parse(end.isoformat().replace('+00:00','Z'))
    records=[]
    if config.get('moon_phases',True):
        phase=astronomy.SearchMoonQuarter(begin)
        while phase.time.ut < limit.ut:
            kind,title=PHASES[phase.quarter]
            local=phase.time.Utc().replace(tzinfo=timezone.utc).astimezone(TZ)
            records.append(instant_record(title,kind,phase.time,f'{kind.replace("_","-")}-{local.date()}',
                'Calculated lunar phase instant. Observing conditions depend on the local sky and weather.',checked))
            phase=astronomy.NextMoonQuarter(phase)
    if config.get('planetary_oppositions',True):
        for planet in PLANETS:
            moment=astronomy.SearchRelativeLongitude(getattr(astronomy.Body,planet),0,begin)
            while moment.ut < limit.ut:
                local=moment.Utc().replace(tzinfo=timezone.utc).astimezone(TZ)
                records.append(instant_record(planet+' at Opposition','opposition',moment,
                    f'opposition-{planet.lower()}-{local.date()}',
                    'Calculated planetary alignment opposite the Sun. Local visibility and weather vary.',checked,planet))
                moment=astronomy.SearchRelativeLongitude(getattr(astronomy.Body,planet),0,moment.AddDays(1))
    if config.get('seasons',True):
        for year in range(start_year,end_year+1):
            seasons=astronomy.Seasons(year)
            for field,title in [('mar_equinox','March Equinox'),('jun_solstice','June Solstice'),('sep_equinox','September Equinox'),('dec_solstice','December Solstice')]:
                records.append(instant_record(title,'season',getattr(seasons,field),f'{field.replace("_","-")}-{year}',
                    'Calculated seasonal solar event, shown in Indiana local time.',checked))
    return records


def fingerprint(record):
    return record['category'],record.get('planet','').lower(),record['startDate']


def automatic_events(root=ROOT, manual=(), now=None):
    config=settings(root)
    generated=root/'.generated/content/astronomy'
    shutil.rmtree(generated,ignore_errors=True)
    generated.mkdir(parents=True,exist_ok=True)
    if not config.get('enabled'):
        return [],{'enabled':False}
    now=now or datetime.now(TZ)
    first,last=now.year-config.get('years_past',1),now.year+config.get('years_ahead',1)
    if not 1700<=first<=last<=2100: raise ValueError('Automatic sky calculations support years 1700–2100')
    checked=now.date().isoformat()
    records=calculate(first,last,config,checked)
    snapshot=load_snapshot(root)
    if config.get('meteor_showers',True):
        for meteor in snapshot['records']:
            if not first<=date.fromisoformat(meteor['start_date']).year<=last: continue
            raw={'title':meteor['name']+' Peak Night','summary':'Predicted meteor-shower peak observing window; conditions vary.',
                 'kind':'meteor_shower','start_date':meteor['start_date'],'end_date':meteor['end_date'],'all_day':True,
                 'source_url':AMS_URL+'#'+meteor['id'],'last_verified':snapshot['checked_on']}
            item=normalize(raw,'astronomy',f'auto-meteor-{meteor["id"]}-{meteor["start_date"][:4]}',now)
            item.update(origin='forecast',icon='meteor',instant=False,planet='',timeLabel='Predicted peak night · evening to following morning')
            records.append(item)
    hidden=set(str(x).removeprefix('astronomy/') for x in config.get('hidden_events',[]))
    replacements={r.get('replacesAutoEvent','') for r in manual}
    manual_keys={fingerprint(r) for r in manual if r['calendarType']=='astronomy'}
    records=[r for r in records if r['slug'] not in hidden and r['slug'] not in replacements and fingerprint(r) not in manual_keys]
    for item in records:
        front={'title':item['title'],'summary':item['summary'],'draft':False,'kind':item['category']}
        body='This entry updates automatically with the website’s daily build. '
        body+=('Meteor dates describe the source’s predicted peak night, not an exact peak time. ' if item['origin']=='forecast' else 'This is an approximate calculated instant, not a scheduled club activity. ')
        body+='A listed celestial event does not guarantee visibility from campus. Check local sky conditions before observing.'
        (generated/(item['slug']+'.md')).write_text('---\n'+yaml.safe_dump(front,sort_keys=False)+'---\n'+body+'\n')
    status={'enabled':True,'startYear':first,'endYear':last,'calculatedOn':checked,'engine':'Astronomy Engine 2.1.19',
            'meteorCheckedOn':snapshot['checked_on'],'meteorLatestDate':max((r['end_date'] for r in snapshot['records']),default=''),
            'meteorCount':len(snapshot['records']),'engineSource':ENGINE_SOURCE,'meteorSource':AMS_URL,
            'meteorStale': not snapshot['checked_on'] or (now.date()-date.fromisoformat(snapshot['checked_on'])).days>30}
    return sorted(records,key=lambda r:r['start']),status
