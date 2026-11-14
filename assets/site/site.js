/* Page helpers for the exported site: fit the home desk collage to the screen. */
(function () {
  function fitDesk() {
    const desk = document.querySelector('[style*="width: 725px"][style*="height: 616px"]');
    if (!desk || !desk.parentElement) return;
    const w = desk.parentElement.getBoundingClientRect().width;
    const s = Math.min(1, w / 725);
    document.documentElement.style.setProperty('--desk-s', s.toFixed(4));
  }
  document.addEventListener('dc:mounted', fitDesk);
  window.addEventListener('resize', fitDesk);
  window.addEventListener('load', fitDesk);
})();
