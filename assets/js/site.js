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
  const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Close photo ×';
  const img = document.createElement('img'); const caption = document.createElement('p');
  dialog.append(close, img, caption); document.body.append(dialog);
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  links.forEach(link => link.addEventListener('click', e => { e.preventDefault(); img.src = link.href; img.alt = link.querySelector('img').alt; caption.textContent = [link.dataset.caption, link.dataset.credit ? 'Photo: ' + link.dataset.credit : ''].filter(Boolean).join(' · '); dialog.showModal(); }));
})();
