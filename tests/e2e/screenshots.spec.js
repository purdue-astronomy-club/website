const { test } = require('@playwright/test');
test('record final desktop and phone screenshots', async({page,browserName})=>{
 test.skip(browserName!=='chromium','One set of reference screenshots is sufficient');
 await page.setViewportSize({width:1440,height:1000});await page.goto('/');
 await page.locator('.hero-image').evaluate(img=>img.decode());
 await page.screenshot({path:'docs/screenshots/preview.jpg',fullPage:false,type:'jpeg',quality:90});
 await page.screenshot({path:'docs/screenshots/home-desktop.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.locator('.gallery-feature').hover();
 await page.locator('.gallery-feature').screenshot({path:'docs/screenshots/home-carousel-desktop.jpg',type:'jpeg',quality:90});
 await page.goto('/gallery/');
 await page.locator('#astrophotography img').evaluateAll(async images=>{
  for(const img of images)img.loading='eager';
  await Promise.all(images.map(img=>img.decode()));
 });
 await page.screenshot({path:'docs/screenshots/gallery-desktop.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.screenshot({path:'docs/screenshots/gallery-preview.jpg',fullPage:false,type:'jpeg',quality:90});
 await page.goto('/officers/');
 await page.locator('.officer-card img').evaluateAll(async images=>{
  for(const img of images)img.loading='eager';
  await Promise.all(images.map(img=>img.decode()));
 });
 await page.screenshot({path:'docs/screenshots/officers-desktop.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.screenshot({path:'docs/screenshots/officers-preview.jpg',fullPage:false,type:'jpeg',quality:90});
 await page.goto('/events/?month=2026-10');await page.waitForFunction(()=>window.calendarReady);
 await page.screenshot({path:'docs/screenshots/calendar-desktop.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.locator('.calendar-page').screenshot({path:'docs/screenshots/calendar-preview.jpg',type:'jpeg',quality:90});
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await page.screenshot({path:'docs/screenshots/home-mobile.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.locator('.gallery-feature').hover();
 await page.locator('.gallery-feature').screenshot({path:'docs/screenshots/home-carousel-mobile.jpg',type:'jpeg',quality:90});
 await page.goto('/gallery/');
 await page.locator('#astrophotography img').evaluateAll(async images=>{
  for(const img of images)img.loading='eager';
  await Promise.all(images.map(img=>img.decode()));
 });
 await page.screenshot({path:'docs/screenshots/gallery-mobile.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.goto('/officers/');
 await page.locator('.officer-card img').evaluateAll(async images=>{
  for(const img of images)img.loading='eager';
  await Promise.all(images.map(img=>img.decode()));
 });
 await page.screenshot({path:'docs/screenshots/officers-mobile.jpg',fullPage:true,type:'jpeg',quality:90});
 await page.goto('/events/?month=2026-10');await page.waitForFunction(()=>window.calendarReady);
 await page.screenshot({path:'docs/screenshots/calendar-mobile.jpg',fullPage:true,type:'jpeg',quality:90});
});
