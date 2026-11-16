/* Page helpers for the exported site (loaded before runtime.js). */
(function () {
  // Home: fit the fixed 725 x 616 desk collage to narrow screens.
  function fitDesk() {
    const desk = document.querySelector('[style*="width: 725px"][style*="height: 616px"]');
    if (!desk || !desk.parentElement) return;
    const w = desk.parentElement.getBoundingClientRect().width;
    document.documentElement.style.setProperty('--desk-s', Math.min(1, w / 725).toFixed(4));
  }
  document.addEventListener('dc:mounted', fitDesk);
  window.addEventListener('resize', fitDesk);
  window.addEventListener('load', fitDesk);

  // Video loops: download and play only while on screen (saves data on slow connections).
  const seen = new WeakSet();
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
    for (const e of entries) {
      const v = e.target;
      if (e.isIntersecting) { v.muted = true; const p = v.play(); if (p && p.catch) p.catch(() => {}); }
      else if (!v.paused) v.pause();
    }
  }, { rootMargin: '200px 0px' }) : null;
  window.__lazyPlay = function (v) {
    if (!io) return v.play();
    if (!seen.has(v)) { seen.add(v); io.observe(v); }
    return Promise.resolve();
  };
})();
