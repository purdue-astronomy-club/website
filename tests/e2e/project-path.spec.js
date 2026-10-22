const {test, expect} = require('@playwright/test');
const {cpSync, existsSync, mkdtempSync, readFileSync, rmSync, statSync} = require('node:fs');
const {tmpdir} = require('node:os');
const {join, relative, sep} = require('node:path');
const {execFileSync} = require('node:child_process');
const {createServer} = require('node:http');

test('a GitHub Pages project path loads styles, photos, calendar data and internal links', async ({page, browserName}) => {
  test.setTimeout(120000);
  const source = process.cwd();
  const checkout = mkdtempSync(join(tmpdir(), 'pac-project-test-'));
  const ignored = new Set(['media', 'drive-gallery', 'events', 'astronomy', 'events.json', 'months.json', 'calendar.ics']);
  let server;
  try {
    for (const folder of ['assets', 'content', 'data', 'layouts', 'static', 'scripts', 'hugo.yaml']) {
      cpSync(join(source, folder), join(checkout, folder), {recursive: true, filter: path => {
        const parts = relative(source, path).split(sep);
        return !(parts[0] === 'static' && ignored.has(parts[1])) && !(parts[0] === 'data' && parts[1] === 'generated');
      }});
    }
    execFileSync(process.env.PYTHON_BIN || 'python3', ['scripts/build.py'], {
      cwd: checkout,
      env: {...process.env, PAC_OFFLINE: '1', HUGO_BASEURL: 'https://example.github.io/website/'},
      stdio: 'pipe', timeout: 90000
    });
    // Serve only /website/. A mistakenly requested /css, /media or /events.json
    // must return 404, matching GitHub project hosting instead of the root preview.
    const types = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.ics': 'text/calendar'};
    server = createServer((req, res) => {
      const path = new URL(req.url, 'http://localhost').pathname;
      if (!path.startsWith('/website/')) { res.writeHead(404).end(); return; }
      let file = join(checkout, 'public', decodeURIComponent(path.slice('/website/'.length)));
      if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
      if (!existsSync(file)) { res.writeHead(404).end(); return; }
      res.setHeader('Content-Type', types[file.slice(file.lastIndexOf('.'))] || 'application/octet-stream');
      res.end(readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}/website/`;
    const failures = [];
    page.on('response', response => { if (response.status() >= 400) failures.push(response.url()); });
    page.on('pageerror', error => failures.push(error.message));
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(base);
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(8, 12, 16)');
    await expect(page.locator('.brand-mark').first()).toHaveCSS('width', '43px');
    await page.locator('.hero-image').evaluate(img => img.decode());
    if (browserName === 'chromium') await page.screenshot({path: 'docs/screenshots/project-home-desktop.jpg', type: 'jpeg', quality: 90});
    await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('link', {name: 'Events', exact: true}).click();
    await expect(page).toHaveURL(/\/website\/events\/(?:\?month=\d{4}-\d{2})?$/);
    await page.waitForFunction(() => window.calendarReady === true);
    await expect(page.locator('#enhanced-calendar')).toBeVisible();
    await expect(page.getByRole('link', {name: 'Subscribe / download calendar'})).toHaveAttribute('href', '/website/calendar.ics');
    const event = page.locator('#calendar a[href^="/website/astronomy/"]').first();
    await expect(event).toBeVisible();
    await expect(event.locator('use')).toHaveAttribute('href', /^\/website\/icons\/sky\.svg#/);
    await event.click();
    await expect(page.getByRole('link', {name: 'Add to Calendar ↓'})).toHaveAttribute('href', /^\/website\/astronomy\/.+\/event\.ics$/);
    await page.goto(base + 'gallery/');
    await page.locator('#astrophotography .gallery-card > a').first().click();
    await expect(page).toHaveURL(/\/website\/astrophotography\//);
    await page.locator('.astro-showcase img').evaluate(img => img.decode());
    await page.locator('[data-lightbox]').click();
    await page.getByRole('dialog', {name: 'Photo viewer'}).locator('img').evaluate(img => img.decode());
    await page.keyboard.press('Escape');
    await page.goto(base + 'officers/');
    await expect(page.locator('.officer-card')).toHaveCount(8);
    await page.locator('.officer-card h2 a').first().click();
    await expect(page.locator('.officer-profile')).toBeVisible();
    await page.locator('.officer-profile img').evaluate(img => img.decode());
    await page.getByRole('link', {name: 'Meet all officers', exact: false}).click();
    await expect(page).toHaveURL(base + 'officers/');
    await page.goto(base + 'calendar/?month=2026-10');
    await expect(page).toHaveURL(base + 'events/?month=2026-10');
    await page.waitForFunction(() => window.calendarReady === true);
    await page.setViewportSize({width: 390, height: 844});
    await expect(page.locator('.fc-listMonth-view')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    expect(failures).toEqual([]);
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    rmSync(checkout, {recursive: true, force: true});
  }
});
