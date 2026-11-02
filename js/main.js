// Pickleball Buddies: scroll-driven crossfade between the hall renders, plus navigation, waitlist and legal dialogs.
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- stage: one render per scene section (neighbours may share one); the next one fades in over the middle
  // two fifths of the scroll between them. The hero scrim lifts as you leave the hero. Wherever content bands run
  // (a group of consecutive .sheet sections) the whole stage dims evenly into graphite and lifts again after them,
  // so there is never a gradient edge scrolling over a picture; renders swap while the stage is dimmed.
  const scenes = [...document.querySelectorAll('main [data-shot]')];
  const layers = new Map([...document.querySelectorAll('.stage .shot')].map(p => [p.dataset.shot, p]));
  const bands = [];
  [...document.querySelector('main').children].forEach((el, i, all) => {
    if (!el.classList.contains('sheet')) return;
    if (all[i - 1] && all[i - 1].classList.contains('sheet')) bands[bands.length - 1].last = el;
    else bands.push({ first: el, last: el });
  });
  const stage = $('.stage');
  const scrim = $('#scrim');
  const veil = $('#veil');
  const note = $('#vizNote');
  const nav = $('#nav');
  const roll = $('#roll'), rollBall = roll.querySelector('.roll-ball'), rollFill = roll.querySelector('.roll-fill'), rollHoles = $('#rollHoles');

  function load(picture) {
    if (!picture || picture.dataset.loaded) return;
    picture.dataset.loaded = '1';
    picture.querySelectorAll('[data-srcset]').forEach(el => { el.srcset = el.dataset.srcset; el.removeAttribute('data-srcset'); });
    const img = picture.querySelector('img');
    if (img.dataset.src) { img.src = img.dataset.src; img.removeAttribute('data-src'); }
  }
  load(layers.get('hero'));

  const smooth = t => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
  function progress() {
    // fractional scene index of the viewport centre (0 = hero centred, 1 = next scene centred, ...)
    const c = innerHeight / 2;
    const mids = scenes.map(s => { const r = s.getBoundingClientRect(); return r.top + r.height / 2; });
    if (c <= mids[0]) return 0;
    for (let i = 0; i < mids.length - 1; i++) if (c <= mids[i + 1]) return i + (c - mids[i]) / (mids[i + 1] - mids[i]);
    return mids.length - 1;
  }

  let ticking = false;
  function update() {
    ticking = false;
    const s = progress();
    const max = document.documentElement.scrollHeight - innerHeight, d = roll.clientWidth, rail = roll.clientHeight;
    const i = Math.floor(s), f = s - i;
    const t = reduceMotion ? (f > 0.5 ? 1 : 0) : smooth((f - 0.3) / 0.4);
    const cur = scenes[i].dataset.shot, next = scenes[i + 1] ? scenes[i + 1].dataset.shot : cur;
    // only the current render and the incoming one are visible; the incoming one lies on top and fades in
    layers.forEach((layer, name) => {
      const fading = name === next && next !== cur;
      layer.style.opacity = fading ? t : name === cur ? 1 : 0;
      layer.style.zIndex = fading ? 2 : 1;
    });
    scenes.slice(i, i + 3).forEach(sec => load(layers.get(sec.dataset.shot)));
    scrim.style.opacity = 1 - smooth(s / 0.6);
    const h = innerHeight;
    // dims in while a band's top rises from the bottom edge to 30 % of the screen, lifts while its end leaves the top 70 %
    // (the last band runs into the footer, so it never lifts)
    const dim = Math.max(0, ...bands.map((b, k) => {
      const into = smooth((h - b.first.getBoundingClientRect().top) / (h * 0.7));
      const out = k === bands.length - 1 ? 1 : smooth(b.last.getBoundingClientRect().bottom / (h * 0.7));
      return into * out;
    }));
    veil.style.opacity = dim;
    stage.style.visibility = dim >= 1 ? 'hidden' : '';
    note.classList.toggle('off', dim > 0.4);
    nav.classList.toggle('solid', scrollY > 60);
    // progress ball: its place on the rail follows the page, its holes turn by the distance rolled (arc / radius);
    // it rolls against the right-hand wall, so it turns anticlockwise on the way down
    const y = (max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 0) * (rail - d);
    rollBall.style.transform = `translate3d(0, ${y}px, 0)`;
    rollFill.style.transform = `scaleY(${rail ? (y + d / 2) / rail : 0})`;
    if (!reduceMotion) rollHoles.setAttribute('transform', `rotate(${(-y / (d / 2) * 180 / Math.PI).toFixed(1)})`);
    roll.classList.toggle('on', scrollY > 40 || grab !== null);
  }
  const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
  addEventListener('scroll', request, { passive: true });
  addEventListener('resize', request);

  // the ball is also a handle: drag it and the page follows 1:1 (no smooth scrolling while dragging), click the rail
  // and the page glides there; grab is where on the ball it was taken, so it does not jump under the pointer
  let grab = null;
  function railTo(clientY, behavior) {
    const r = roll.getBoundingClientRect(), d = roll.clientWidth, max = document.documentElement.scrollHeight - innerHeight;
    const p = Math.min(1, Math.max(0, (clientY - (grab ?? d / 2) - r.top) / (r.height - d)));
    scrollTo({ top: p * max, behavior });
  }
  roll.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const b = rollBall.getBoundingClientRect();
    if (e.clientY < b.top - 10 || e.clientY > b.bottom + 10) { railTo(e.clientY, 'smooth'); return; }
    e.preventDefault();
    grab = Math.min(b.height, Math.max(0, e.clientY - b.top));
    roll.setPointerCapture(e.pointerId);
    roll.classList.add('drag');
    document.documentElement.style.scrollBehavior = 'auto';
  });
  roll.addEventListener('pointermove', e => { if (grab !== null) railTo(e.clientY, 'auto'); });
  const release = () => {
    if (grab === null) return;
    grab = null; roll.classList.remove('drag');
    document.documentElement.style.scrollBehavior = '';
    request();
  };
  roll.addEventListener('pointerup', release);
  roll.addEventListener('pointercancel', release);
  update();

  // ---- gentle reveal of text blocks (content is visible without it)
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  // ---- rally clip: autoplays muted and looping, pauses while off screen; with reduced motion it waits for the viewer
  const clip = $('#clip');
  if (reduceMotion) { clip.pause(); clip.controls = true; }
  else new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) clip.play().catch(() => { clip.controls = true; });
    else clip.pause();
  }), { threshold: 0.25 }).observe(clip);

  // ---- waitlist (not connected to a backend yet; kept in this browser only)
  $('#waitForm').addEventListener('submit', e => {
    e.preventDefault();
    const n = $('#wName').value.trim(), m = $('#wMail').value.trim(), ok = $('#wOk').checked, out = $('#wNote');
    out.className = 'note';
    if (!n || !/^\S+@\S+\.\S+$/.test(m)) { out.textContent = 'Bitte Name und eine gültige E-Mail-Adresse eintragen.'; return; }
    if (!ok) { out.textContent = 'Bitte stimme der Benachrichtigung zu.'; return; }
    try {
      const list = JSON.parse(localStorage.getItem('pbb-wait') || '[]');
      list.push({ n, m, role: $('#wRole').value, t: Date.now() });
      localStorage.setItem('pbb-wait', JSON.stringify(list));
    } catch (err) { /* private mode: nothing to keep */ }
    out.className = 'note ok';
    out.textContent = 'Danke, ' + n.split(' ')[0] + '. Hinweis: Die Warteliste ist noch nicht angebunden, der Eintrag bleibt vorerst in deinem Browser.';
    e.target.reset();
  });

  // ---- Impressum / Datenschutz (placeholders until go-live)
  function legal(title, text) {
    const d = document.createElement('div');
    d.className = 'legal';
    d.setAttribute('role', 'dialog');
    d.setAttribute('aria-label', title);
    d.innerHTML = `<div><h3>${title}</h3><p>${text}</p><button class="btn btn-ghost" type="button">Schließen</button></div>`;
    d.addEventListener('click', ev => { if (ev.target === d || ev.target.tagName === 'BUTTON') d.remove(); });
    document.addEventListener('keydown', function esc(ev) { if (ev.key === 'Escape') { d.remove(); document.removeEventListener('keydown', esc); } });
    document.body.appendChild(d);
    d.querySelector('button').focus();
  }
  $('#impLink').addEventListener('click', e => { e.preventDefault(); legal('Impressum', 'Platzhalter. Hier stehen vor dem Livegang Firmenname, Anschrift, Vertretungsberechtigte, Kontakt, Registereintrag und Umsatzsteuer-ID nach § 5 DDG.'); });
  $('#datLink').addEventListener('click', e => { e.preventDefault(); legal('Datenschutz', 'Platzhalter. Hier steht vor dem Livegang die Datenschutzerklärung, inklusive Angaben zur Warteliste und zu den eingebundenen Schriftarten.'); });
})();
