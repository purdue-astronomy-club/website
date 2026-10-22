// Local/CI export only. No public endpoint can dispatch a workflow.
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
const payload = JSON.parse(process.env.CMS_PAYLOAD || '{}');
const month = process.argv[2] || payload.inputs?.month;
if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month || '') || Number(month.slice(0,4))<1900 || Number(month.slice(0,4))>2200) throw new Error('Enter Month as YYYY-MM (1900–2200).');
mkdirSync('calendar-exports', {recursive:true});
const browser = await chromium.launch();
try {
 const page = await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 await page.goto('http://127.0.0.1:1313/calendar-poster/?month='+month);
 await page.waitForFunction(()=>window.calendarReady===true);
 await page.evaluate(()=>document.fonts.ready);
 await page.locator('#month-banner').evaluate(img=>img.decode());
 if (await page.locator('body').evaluate(el=>el.scrollHeight>1080 || [...el.querySelectorAll('#calendar .fc-scroller')].some(box=>box.scrollHeight>box.clientHeight+1))) throw new Error('This month has too much content for a readable 1920×1080 poster. Shorten monthly notes or use the website calendar.');
 const png = await page.screenshot({path:`calendar-exports/${month}.png`,fullPage:false});
 // Put the verified PNG on one landscape sheet so print pagination cannot split the grid.
 const sheet = await browser.newPage();
 await sheet.setContent('<!doctype html><html><head><style>@page{size:A3 landscape;margin:0}html,body{margin:0;width:100%;height:100%;background:#080c10}img{display:block;width:100%;height:100vh;object-fit:contain}</style></head><body><img alt="Purdue Astronomy Club monthly calendar" src="data:image/png;base64,'+png.toString('base64')+'"></body></html>');
 await sheet.locator('img').evaluate(img=>img.decode());
 await sheet.pdf({path:`calendar-exports/${month}.pdf`,format:'A3',landscape:true,printBackground:true,margin:{top:0,right:0,bottom:0,left:0}});
 for (const suffix of ['png','pdf']) if(readFileSync(`calendar-exports/${month}.${suffix}`).length<1000) throw new Error('Export appears empty');
} finally { await browser.close(); }
