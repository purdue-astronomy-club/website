const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
for (const width of [360,390,768,1024,1440,1920]) {
 test(`home and calendar fit ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:1000});
  for(const route of ['/','/events/?month=2026-10']) {
   await page.goto(route);
   if(route.includes('events'))await page.waitForFunction(()=>window.calendarReady);
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  }
  await expect(page.locator('.fc-dayGridMonth-view')).toBeVisible();
 });
}
for (const route of ['/','/events/?month=2026-10','/about/','/gallery/','/officers/','/contact/']) {
 test(`accessibility ${route}`, async({page})=>{
  await page.goto(route);
  if(route.includes('events'))await page.waitForFunction(()=>window.calendarReady);
  const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
 });
}
test('month navigation, leap years and invalid month',async({page})=>{
 await page.goto('/events/?month=2028-02');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('[data-date="2028-02-29"]')).toHaveCount(1);
 await page.getByRole('button',{name:'Next month',exact:true}).click();
 await expect(page).toHaveURL(/month=2028-03/);
 await page.goto('/events/?month=not-a-month');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('#month-title')).not.toHaveText('Invalid Date');
});
test('no JavaScript fallback and public routes',async({browser})=>{
 const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
 await page.goto('/events/');await expect(page.locator('#calendar-fallback')).toBeVisible();
 await expect(page.locator('#main-nav')).toBeVisible();await context.close();
});
test('keyboard menu',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 const menu=page.getByRole('button',{name:/Menu/});await menu.press('Enter');
 await expect(menu).toHaveAttribute('aria-expanded','true');
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'About',exact:true}).press('Escape');
 await expect(menu).toBeFocused();await expect(menu).toHaveAttribute('aria-expanded','false');
});
test('month calendar keeps category filters without an agenda',async({page})=>{
 const entries=Array.from({length:5},(_,i)=>({id:'events/test-'+i,title:'Test fixture '+i,summary:'Test only',start:'2026-10-22T19:00:00-04:00',end:'2026-10-22T20:00:00-04:00',startDate:'2026-10-22',endDate:'2026-10-22',allDay:false,url:'/events/test-'+i+'/',calendarType:i===0?'joint':'pac',categoryLabel:i===0?'Joint event':'PAC event',timeLabel:'7:00 PM · Indiana time',status:'scheduled',location:'Fixture location'}));
 await page.route('**/events.json',r=>r.fulfill({json:entries}));
 await page.goto('/events/?month=2026-10');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('.fc-daygrid-more-link')).toBeVisible();
 await page.getByLabel('Joint events',{exact:true}).uncheck();
 await page.locator('.fc-daygrid-more-link').click();
 await expect(page.locator('#calendar')).not.toContainText('Test fixture 0');
 await expect(page.locator('#calendar')).toContainText('Test fixture 1');
 await expect(page.getByRole('button',{name:'Agenda',exact:true})).toHaveCount(0);
 await expect(page.locator('#month-overview')).toHaveCount(0);
});
test('monthly banner credit and sourced notes follow selected month',async({page})=>{
 await page.route('**/months.json',r=>r.fulfill({json:[{month:'2026-10',banner_image:'/images/hero-lunar-eclipse.png',banner_alt:'Fixture monthly image',photographer:'Test photographer',permission_to_publish:true,night_sky_notes:'Fixture sky notes',source_url:'https://science.nasa.gov/',last_verified:'2026-10-22'}]}));
 await page.goto('/events/?month=2026-10');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('#banner-credit')).toHaveText('Photo: Test photographer');
 await expect(page.locator('#sky-notes')).toContainText('Fixture sky notes');
 await page.getByRole('button',{name:'Next month',exact:true}).click();
 await expect(page.locator('#banner-credit')).toBeHidden();
 await expect(page.locator('#sky-notes')).not.toContainText('Fixture sky notes');
});
test('local photo preparation produces a download without an upload',async({page})=>{
 await page.goto('/photo-prep/');
 await page.locator('#photos').setInputFiles({name:'test.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAIAAAAC64paAAAAHUlEQVR4nGNkYGhgIBcwka1zVPOo5lHNo5qpohkAxLIAqJyKsuMAAAAASUVORK5CYII=','base64')});
 await expect(page.locator('#prepared-photos a')).toHaveAttribute('download','test-web.webp');
});
test('photo viewer supports keyboard close and returns focus',async({page})=>{
 await page.route('**/gallery/',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace('</main>','<figure><a href="/images/hero-lunar-eclipse.png" data-lightbox data-caption="Fixture caption" data-credit="Test photographer"><img src="/images/hero-lunar-eclipse.png" alt="Fixture photo"></a></figure></main>')});});
 await page.goto('/gallery/');const link=page.locator('[data-lightbox]');await link.press('Enter');
 await expect(page.getByRole('dialog',{name:'Photo viewer'})).toBeVisible();
 await page.getByRole('button',{name:'Close photo ×'}).press('Escape');
 await expect(link).toBeFocused();
});
test('published gallery photo retains its title and credit through the larger view',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/gallery/');
 const cards=page.locator('#astrophotography .gallery-card');
 test.skip(await cards.count()===0,'No published astrophotography in this content revision');
 const card=cards.first();
 const title=(await card.locator('h3').innerText()).replace('↗','').trim();
 const credit=(await card.locator('p').innerText()).trim();
 await card.locator('a').click();
 await expect(page.getByRole('heading',{level:1})).toHaveText(title);
 await expect(page.locator('.page-heading .lead')).toHaveText(credit);
 const photo=page.locator('.astro-showcase img');
 await photo.evaluate(img=>img.decode());
 expect(await photo.evaluate(img=>img.naturalWidth)).toBeGreaterThan(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 const larger=page.locator('.astro-showcase [data-lightbox]');
 await larger.click();
 await expect(page.getByRole('dialog',{name:'Photo viewer'})).toContainText(credit.replace('Image by ','Photo: '));
 await page.keyboard.press('Escape');
 await expect(larger).toBeFocused();
});
test('calculated moon has an icon, source details and an invitation',async({page})=>{
 const records=await (await page.request.get('/events.json')).json();
 const moon=records.find(r=>r.origin==='calculated' && r.category==='new_moon');
 expect(moon).toBeTruthy();
 await page.goto('/events/?month='+moon.startDate.slice(0,7));await page.waitForFunction(()=>window.calendarReady);
 const link=page.locator('#calendar a[href="'+moon.url+'"]');
 await expect(link.locator('use')).toHaveAttribute('href','/icons/sky.svg#new-moon');
 await link.click();
 await expect(page.getByRole('heading',{level:1})).toHaveText('New Moon');
 await expect(page.locator('.detail-facts time')).toHaveText(moon.dateLabel);
 await expect(page.locator('.detail-facts time')).toHaveAttribute('datetime',moon.startDate);
 await expect(page.locator('.detail-facts')).not.toContainText(moon.timeLabel);
 await expect(page.locator('.detail-facts')).not.toContainText('Verified');
 await expect(page.getByRole('link',{name:'Astronomy source ↗'})).toHaveAttribute('href','https://pypi.org/project/astronomy-engine/');
 await expect(page.getByRole('link',{name:'Add to Calendar ↓'})).toHaveAttribute('href',moon.url+'event.ics');
});
test('calendar removes automatic sky disclosure and keeps out-of-range notice',async({page})=>{
 await page.goto('/events/?month=2026-10');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('.sky-data-note')).toHaveCount(0);
 await expect(page.locator('.calendar-help')).toHaveCount(0);
 await expect(page.locator('#sky-notes')).not.toContainText(/\d{1,2}:\d{2}\s*[AP]M|Verified/);
 await page.goto('/events/?month=2099-10');await page.waitForFunction(()=>window.calendarReady);
 await expect(page.locator('#sky-coverage')).toBeVisible();
});
