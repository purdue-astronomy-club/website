/* FullCalendar Standard 6.1.20, self-hosted. All records come from the build normalizer. */
(async () => {
  const root = document.querySelector('[data-calendar-page]');
  if (!root || !window.FullCalendar) return;
  const status = document.querySelector('#calendar-status');
  const base = document.documentElement.dataset.siteRoot || '/';
  try {
    const [eventResponse, monthResponse] = await Promise.all([fetch(base + 'events.json'), fetch(base + 'months.json')]);
    if (!eventResponse.ok || !monthResponse.ok) throw new Error('Calendar data unavailable');
    const [records, months] = await Promise.all([eventResponse.json(), monthResponse.json()]);
    const today = () => new Intl.DateTimeFormat('en-CA', {timeZone:'America/Indiana/Indianapolis',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    const validMonth = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value || '') && Number(value.slice(0,4)) >= 1900 && Number(value.slice(0,4)) <= 2200;
    const chosen = new URLSearchParams(location.search).get('month');
    const firstMonth = validMonth(chosen) ? chosen : today().slice(0,7);
    const isPoster = document.body.classList.contains('poster');
    const fallbackImage = document.querySelector('#month-banner').getAttribute('src');
    const fallbackAlt = document.querySelector('#month-banner').alt;
    const enabled = new Set(['pac','joint','astronomy']);
    const icons = new Set(['new-moon','first-quarter','full-moon','last-quarter','meteor','mars','jupiter','saturn','uranus','neptune','planet','sun','eclipse','star']);
    const iconNode = r => {
      if (!r.icon) return null;
      const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
      svg.setAttribute('class','celestial-icon'); svg.setAttribute('aria-hidden','true'); svg.setAttribute('focusable','false');
      const use=document.createElementNS('http://www.w3.org/2000/svg','use');
      use.setAttribute('href',base+'icons/sky.svg#'+(icons.has(r.icon)?r.icon:'star')); svg.append(use); return svg;
    };

    const fmt = new Intl.DateTimeFormat('en-US', {month:'long',year:'numeric',timeZone:'UTC'});
    // Floating wall-clock dates keep Indiana times independent of the visitor's time zone.
    // Offsets remain explicit in the public feed and ICS. Only the display copy is floating.
    const display = r => {
      const astronomy = r.calendarType === 'astronomy';
      const nextDay = new Date(r.endDate + 'T00:00:00Z');
      nextDay.setUTCDate(nextDay.getUTCDate() + 1);
      return {...r, allDay:astronomy || r.allDay,
        start:astronomy ? r.startDate : r.start.slice(0,19),
        end:astronomy ? nextDay.toISOString().slice(0,10) : r.end.slice(0,19),
        classNames:['fc-type-'+r.calendarType,'fc-status-'+r.status], extendedProps:r};
    };
    const list = (target, items, empty) => {
      target.replaceChildren();
      if (!items.length) { const p = document.createElement('p'); p.textContent = empty; target.append(p); return; }
      const ul = document.createElement('ul');
      items.forEach(r => { const li = document.createElement('li'); li.className='type-'+r.calendarType; const tag=document.createElement('span'); tag.className='tag'; tag.textContent=r.categoryLabel; const link=document.createElement('a'); link.href=r.url; link.textContent=(r.status==='scheduled'?'':r.status.charAt(0).toUpperCase()+r.status.slice(1)+': ')+r.title; const when=document.createElement('small'); when.textContent=r.dateLabel || r.startDate; const icon=iconNode(r); if(icon) link.prepend(icon); li.append(tag,link,when); ul.append(li); }); target.append(ul);
    };
    const calendar = new FullCalendar.Calendar(document.querySelector('#calendar'), {
      initialView:'dayGridMonth',
      initialDate:firstMonth+'-01', now:today(), timeZone:'local', firstDay:0, headerToolbar:false,
      height:isPoster?620:'auto', fixedWeekCount:false, dayMaxEvents:isPoster?false:3, eventDisplay:'block', displayEventTime:false,
      moreLinkClick:'popover', noEventsContent:'No events announced for this month.',
      events:records.map(display),
      eventClassNames:arg => ['fc-type-'+arg.event.extendedProps.calendarType],
      eventContent:arg => {
        const r=arg.event.extendedProps, box=document.createElement('span');
        box.textContent=r.categoryLabel+' · '+(r.status==='scheduled'?'':r.status.charAt(0).toUpperCase()+r.status.slice(1)+': ')+arg.event.title;
        const icon=iconNode(r); if(icon) box.prepend(icon);
        return {domNodes:[box]};
      },
      eventDidMount:arg => { const r=arg.event.extendedProps; arg.el.setAttribute('aria-label',r.categoryLabel+': '+r.title+'. '+r.status+'. '+r.startDate+'. '+(r.status==='postponed'?'New date to be announced':r.calendarType==='astronomy'?'':r.timeLabel)+(r.location?'. '+r.location:'')); },
      datesSet:info => {
        const start=info.view.currentStart;
        const key=start.getFullYear()+'-'+String(start.getMonth()+1).padStart(2,'0');
        const title=fmt.format(new Date(key+'-01T12:00:00Z'));
        document.querySelector('#month-title').textContent=title;
        document.querySelector('#banner-month').textContent=title;
        const url=new URL(location.href); url.searchParams.set('month',key); history.replaceState(null,'',url);
        const next=new Date(start.getFullYear(),start.getMonth()+1,1);
        const nextKey=next.getFullYear()+'-'+String(next.getMonth()+1).padStart(2,'0')+'-01';
        const visible=records.filter(r => enabled.has(r.calendarType) && r.startDate<nextKey && r.endDate>=key+'-01');
        const sky=document.querySelector('#sky-notes');
        list(sky,visible.filter(r=>r.calendarType==='astronomy'),'Astronomy highlights will appear here when added.');
        const month=months.find(m=>m.month===key);
        const banner=document.querySelector('#month-banner');
        banner.src=month?.banner_image || fallbackImage;
        banner.alt=month?.banner_alt || fallbackAlt;
        const credit=document.querySelector('#banner-credit');
        credit.textContent=month?.photographer ? 'Photo: '+month.photographer : '';
        credit.hidden=!credit.textContent;
        if (month) { ['night_sky_notes','visible_planets_notes'].forEach(field=>{if(month[field]){const p=document.createElement('p');p.className='sky-editorial';p.textContent=month[field];sky.append(p);}}); if(month.source_url){const a=document.createElement('a');a.href=month.source_url;a.textContent='Sky notes source ↗';sky.append(a);} }
        status.textContent=visible.length ? visible.length+' calendar '+(visible.length===1?'entry':'entries')+' shown for '+title+'.' : 'No events announced for '+title+'.';
        const coverage=document.querySelector('#sky-coverage');
        if(coverage){const out=start.getFullYear()<Number(coverage.dataset.firstYear)||start.getFullYear()>Number(coverage.dataset.lastYear);coverage.hidden=!out;}
        window.calendarReady = true;
      }
    });
    document.querySelector('#enhanced-calendar').hidden=false;
    calendar.render();
    document.querySelector('#calendar-fallback').hidden=true;
    document.querySelector('#calendar-controls').hidden=false;
    document.querySelector('#calendar-filters').hidden=false;
    document.querySelector('#previous-month').addEventListener('click',()=>calendar.prev());
    document.querySelector('#next-month').addEventListener('click',()=>calendar.next());
    document.querySelector('#today-month').addEventListener('click',()=>calendar.gotoDate(today()));
    document.querySelectorAll('#calendar-filters input').forEach(input=>input.addEventListener('change',()=>{ input.checked?enabled.add(input.value):enabled.delete(input.value); calendar.getEventSources().forEach(source=>source.remove()); calendar.addEventSource(records.filter(r=>enabled.has(r.calendarType)).map(display)); calendar.getOption('datesSet')({view:calendar.view}); }));
    window.pacCalendar = calendar;
  } catch (error) {
    status.textContent='The interactive calendar could not load. Use the calendar download above.';
    document.querySelector('#enhanced-calendar').hidden=true;
    document.querySelector('#calendar-fallback').hidden=false;
    console.error(error);
  }
})();
