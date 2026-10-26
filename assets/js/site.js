(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#main-nav');
  if (toggle && nav) {
    const small = matchMedia('(max-width: 767px)');
    const update = () => { toggle.hidden = !small.matches; nav.hidden = small.matches && toggle.getAttribute('aria-expanded') !== 'true'; };
    toggle.addEventListener('click', () => { toggle.setAttribute('aria-expanded', String(toggle.getAttribute('aria-expanded') !== 'true')); update(); });
    nav.addEventListener('keydown', e => { if (e.key === 'Escape' && small.matches) { toggle.setAttribute('aria-expanded', 'false'); update(); toggle.focus(); } });
    small.addEventListener('change', update); update();
  }
  const links = document.querySelectorAll('[data-lightbox]');
  if (!links.length) return;
  const dialog = document.createElement('dialog'); dialog.className = 'lightbox'; dialog.setAttribute('aria-label', 'Photo viewer');
  const toolbar = document.createElement('div'); toolbar.className = 'lightbox-toolbar';
  const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Close photo ×';
  const zoom = document.createElement('button'); zoom.type = 'button'; zoom.textContent = 'Zoom to 100%'; zoom.setAttribute('aria-pressed', 'false');
  const full = document.createElement('a'); full.textContent = 'Open full-resolution image'; full.target = '_blank'; full.rel = 'noopener';
  const viewport = document.createElement('div'); viewport.className = 'lightbox-viewport'; viewport.tabIndex = 0; viewport.setAttribute('role', 'region'); viewport.setAttribute('aria-label', 'Photo; scroll to pan when zoomed');
  const img = document.createElement('img'); const caption = document.createElement('p');
  const status = document.createElement('p'); status.setAttribute('role', 'status');
  const details = document.createElement('div'); details.append(status, caption);
  toolbar.append(close, zoom, full); viewport.append(img);
  dialog.append(toolbar, viewport, details); document.body.append(dialog);
  const resetZoom = () => {
    dialog.classList.remove('is-zoomed'); img.style.width = ''; img.style.height = '';
    zoom.textContent = 'Zoom to 100%'; zoom.setAttribute('aria-pressed', 'false');
    viewport.scrollTo(0, 0);
  };
  zoom.addEventListener('click', () => {
    if (dialog.classList.contains('is-zoomed')) { resetZoom(); return; }
    dialog.classList.add('is-zoomed'); img.style.width = `${img.naturalWidth}px`; img.style.height = `${img.naturalHeight}px`;
    zoom.textContent = 'Fit to screen'; zoom.setAttribute('aria-pressed', 'true');
    viewport.focus();
  });
  img.addEventListener('load', () => {
    zoom.disabled = false; viewport.setAttribute('aria-busy', 'false');
    status.textContent = `${img.naturalWidth.toLocaleString()} × ${img.naturalHeight.toLocaleString()} pixels`;
  });
  img.addEventListener('error', () => {
    if (!dialog.open) return;
    zoom.disabled = true; viewport.setAttribute('aria-busy', 'false');
    status.textContent = 'Photo could not load. Try opening the full-resolution image.';
  });
  dialog.addEventListener('close', () => { resetZoom(); img.removeAttribute('src'); });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  links.forEach(link => link.addEventListener('click', e => {
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || typeof dialog.showModal !== 'function') return;
    e.preventDefault(); resetZoom(); zoom.disabled = true; status.textContent = 'Loading full-resolution photo…'; viewport.setAttribute('aria-busy', 'true');
    full.href = link.href; img.alt = link.querySelector('img').alt;
    caption.textContent = [link.dataset.caption, link.dataset.credit ? 'Photo: ' + link.dataset.credit : ''].filter(Boolean).join(' · ');
    dialog.showModal(); img.src = link.href;
  }));
})();
