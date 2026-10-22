(() => {
  const carousel = document.querySelector('[data-gallery-carousel]');
  if (!carousel) return;
  const track = carousel.querySelector('.carousel-track');
  const slides = [...track.querySelectorAll('.carousel-slide')];
  const controls = carousel.querySelector('[data-carousel-controls]');
  const previous = carousel.querySelector('[data-carousel-previous]');
  const next = carousel.querySelector('[data-carousel-next]');
  const position = carousel.querySelector('[data-carousel-position]');
  const announcement = carousel.querySelector('[data-carousel-announcement]');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0, visible = 1, step = 0, timer, settled;
  let focusHold = false, pointerHold = false;
  let inView = !('IntersectionObserver' in window), moving = false;
  const lastIndex = () => Math.max(0, slides.length - visible);

  const render = () => {
    const first = index + 1, last = Math.min(slides.length, index + visible);
    position.textContent = (first === last ? first : `${first}–${last}`) + ` of ${slides.length}`;
    controls.hidden = slides.length <= visible;
  };
  const schedule = () => {
    clearTimeout(timer);
    const rotating = !reducedMotion.matches && !focusHold && !pointerHold && inView && !document.hidden && lastIndex() > 0;
    carousel.dataset.rotating = String(rotating);
    if (!rotating) return;
    timer = setTimeout(() => move(index === lastIndex() ? 0 : index + 1, false), 5000);
  };
  const move = (target, manual = true) => {
    index = Math.max(0, Math.min(lastIndex(), target));
    moving = true;
    track.scrollTo({left: index * step, behavior: reducedMotion.matches ? 'instant' : 'smooth'});
    if (manual) {
      announcement.textContent = `Showing photo ${index + 1}${visible > 1 ? ` through ${Math.min(slides.length, index + visible)}` : ''} of ${slides.length}.`;
    }
    render();
    schedule();
  };
  const measure = () => {
    clearTimeout(settled);
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    step = slides[0].getBoundingClientRect().width + gap;
    if (!step) return;
    visible = Math.max(1, Math.min(slides.length, Math.round((track.clientWidth + gap) / step)));
    index = Math.min(index, lastIndex());
    moving = false;
    track.scrollTo({left: index * step, behavior: 'instant'});
    render();
    schedule();
  };

  previous.addEventListener('click', () => move(index === 0 ? lastIndex() : index - 1));
  next.addEventListener('click', () => move(index === lastIndex() ? 0 : index + 1));
  track.addEventListener('keydown', event => {
    if (event.target !== track) return;
    const target = {ArrowLeft: index === 0 ? lastIndex() : index - 1,
      ArrowRight: index === lastIndex() ? 0 : index + 1, Home: 0, End: lastIndex()}[event.key];
    if (target === undefined) return;
    event.preventDefault();
    move(target);
  });
  track.addEventListener('pointerdown', () => {
    pointerHold = true;
    moving = false;
    schedule();
  }, {passive: true});
  const releasePointer = () => { pointerHold = false; schedule(); };
  window.addEventListener('pointerup', releasePointer, {passive: true});
  window.addEventListener('pointercancel', releasePointer, {passive: true});
  track.addEventListener('scroll', () => {
    clearTimeout(settled);
    settled = setTimeout(() => {
      // Keep the requested destination through interrupted smooth scrolling,
      // including quickly alternating Previous and Next in Firefox.
      if (moving && Math.abs(track.scrollLeft - index * step) > 2) return;
      moving = false;
      index = Math.max(0, Math.min(lastIndex(), Math.round(track.scrollLeft / step)));
      render();
    }, 120);
    if (!moving) {
      index = Math.max(0, Math.min(lastIndex(), Math.round(track.scrollLeft / step)));
      render();
    }
  }, {passive: true});
  carousel.addEventListener('focusin', event => {
    // Hold the current photo during keyboard navigation, then resume on exit.
    focusHold = event.target.matches(':focus-visible');
    if (focusHold && event.target.closest('.carousel-slide')) moving = false;
    schedule();
  });
  carousel.addEventListener('focusout', event => {
    if (!carousel.contains(event.relatedTarget)) { focusHold = false; schedule(); }
  });
  carousel.addEventListener('keydown', () => { focusHold = true; schedule(); });
  document.addEventListener('visibilitychange', schedule);
  reducedMotion.addEventListener('change', schedule);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting && entries[0].intersectionRatio >= 0.2;
      schedule();
    }, {threshold: 0.2}).observe(carousel);
  }
  if ('ResizeObserver' in window) new ResizeObserver(measure).observe(track);
  else window.addEventListener('resize', measure);
  measure();
})();
