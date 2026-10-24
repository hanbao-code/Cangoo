(() => {
  'use strict';
  document.documentElement.dataset.pdmMode = 'product';
  setLang('zh');
  window.pdmProduct = Object.freeze({ ready: true, bootstrapVersion: 1 });
  window.dispatchEvent(new CustomEvent('pdm-shared-canvas-ready'));
})();
