const {test, expect} = require('@playwright/test');

async function openCarousel(page, {width = 1440, reducedMotion = 'no-preference'} = {}) {
  await page.setViewportSize({width, height: 1000});
  await page.emulateMedia({reducedMotion});
  await page.goto('/');
  const carousel = page.getByRole('region', {name: 'Member Gallery'});
  await carousel.scrollIntoViewIfNeeded();
  await page.mouse.move(0, 0);
  await expect(carousel.locator('[data-carousel-controls]')).toBeVisible();
  return carousel;
}

test('homepage carousel includes the gallery, wraps, and supports keyboard and phone layouts', async ({page}) => {
  await page.goto('/gallery/');
  const gallery = await page.locator('#astrophotography .gallery-card > a').evaluateAll(links => links.map(link => link.getAttribute('href')));
  const carousel = await openCarousel(page);
  const links = await carousel.locator('.carousel-slide > a').evaluateAll(links => links.map(link => link.getAttribute('href')));
  for (const href of gallery) expect(links).toContain(href);
  expect(links.length).toBeGreaterThan(3);
  const count = links.length;
  const position = carousel.locator('[data-carousel-position]');
  await expect(position).toHaveText(`1–3 of ${count}`);
  await carousel.getByRole('button', {name: 'Previous photo', exact: true}).click();
  await expect(position).toHaveText(`${count - 2}–${count} of ${count}`);
  await carousel.getByRole('button', {name: 'Next photo', exact: true}).click();
  await expect(position).toHaveText(`1–3 of ${count}`);
  const track = carousel.locator('.carousel-track');
  await expect(track).toHaveCSS('scrollbar-width', 'none');
  await expect.poll(() => track.evaluate(element => element.scrollLeft)).toBeLessThan(2);
  await track.press('End');
  await expect(position).toHaveText(`${count - 2}–${count} of ${count}`);
  await track.press('Home');
  await track.press('ArrowRight');
  await expect(position).toHaveText(`2–4 of ${count}`);
  await page.setViewportSize({width: 768, height: 1000});
  await track.press('Home');
  await expect(position).toHaveText(`1–2 of ${count}`);
  await page.setViewportSize({width: 390, height: 844});
  await track.press('Home');
  await expect(position).toHaveText(`1 of ${count}`);
  await track.press('End');
  await expect(position).toHaveText(`${count} of ${count}`);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test('rotation continues without a pause button and resumes after keyboard navigation', async ({page}) => {
  await page.clock.install();
  const carousel = await openCarousel(page);
  const position = carousel.locator('[data-carousel-position]');
  const initial = await position.innerText();
  await expect(carousel).toHaveAttribute('data-rotating', 'true');
  await page.clock.fastForward(5500);
  await expect(position).not.toHaveText(initial);
  await expect.poll(() => carousel.locator('.carousel-track').evaluate(track => track.scrollLeft)).toBeGreaterThan(0);
  await expect(carousel.getByRole('button', {name: /slideshow/i})).toHaveCount(0);
  await carousel.getByRole('button', {name: 'Next photo', exact: true}).click();
  const afterClick = await position.innerText();
  await expect(carousel).toHaveAttribute('data-rotating', 'true');
  await page.clock.fastForward(5500);
  await expect(position).not.toHaveText(afterClick);
  await carousel.hover();
  const hovered = await position.innerText();
  await page.clock.fastForward(5500);
  await expect(position).not.toHaveText(hovered);
  await page.mouse.wheel(0, 100);
  await expect(carousel).toHaveAttribute('data-rotating', 'true');
  const afterWheel = await position.innerText();
  await page.clock.fastForward(5500);
  await expect(position).not.toHaveText(afterWheel);
  await page.keyboard.press('Tab');
  await carousel.locator('.carousel-track').focus();
  await expect(carousel).toHaveAttribute('data-rotating', 'false');
  const focused = await position.innerText();
  await page.clock.fastForward(15000);
  await expect(position).toHaveText(focused);
  await page.getByRole('link', {name: 'Explore the gallery', exact: false}).focus();
  await expect(carousel).toHaveAttribute('data-rotating', 'true');
  await page.clock.fastForward(5500);
  await expect(position).not.toHaveText(focused);
});

test('reduced motion starts paused and manual controls still reach every photo', async ({page}) => {
  await page.clock.install();
  const carousel = await openCarousel(page, {width: 390, reducedMotion: 'reduce'});
  await expect(carousel.getByRole('button', {name: /slideshow/i})).toHaveCount(0);
  await expect(carousel).toHaveAttribute('data-rotating', 'false');
  const count = await carousel.locator('.carousel-slide').count();
  const position = carousel.locator('[data-carousel-position]');
  await page.clock.fastForward(20000);
  await expect(position).toHaveText(`1 of ${count}`);
  for (let index = 2; index <= count; index++) {
    await carousel.getByRole('button', {name: 'Next photo', exact: true}).click();
    await expect(position).toHaveText(`${index} of ${count}`);
  }
  await carousel.getByRole('button', {name: 'Next photo', exact: true}).click();
  await expect(position).toHaveText(`1 of ${count}`);
});

test('gallery photographs remain browsable without JavaScript', async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
  const page = await context.newPage();
  await page.goto('/');
  const carousel = page.getByRole('region', {name: 'Member Gallery'});
  await expect(carousel.locator('[data-carousel-controls]')).toBeHidden();
  const slides = carousel.locator('.carousel-slide');
  expect(await slides.count()).toBeGreaterThan(3);
  await slides.last().locator('a').focus();
  await expect.poll(() => carousel.locator('.carousel-track').evaluate(track => track.scrollLeft)).toBeGreaterThan(0);
  await expect(slides.last().locator('a')).toBeFocused();
  await context.close();
});
