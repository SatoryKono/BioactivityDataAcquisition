(function () {
})();
  });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-md-color-scheme', 'data-theme'] });
    });
      }
        } catch (e) { /* ignore */ }
          renderAll();
          mermaid.initialize({ theme: getMaterialTheme() });
        try {
      if (shouldReinit) {
      });
        return m.attributeName === 'data-md-color-scheme' || m.attributeName === 'data-theme';
      var shouldReinit = mutations.some(function (m) {
    var observer = new MutationObserver(function (mutations) {
    renderAll();
    initMermaid();
  document.addEventListener('DOMContentLoaded', function () {

  }
    });
      }
        // silent
      } catch (err) {
        }
          mermaid.init(undefined, el);
        } else {
          mermaid.init(undefined, container);
          parent.replaceWith(container);
          container.textContent = text;
          container.className = 'mermaid';
          var container = document.createElement('div');
          var text = el.textContent;
          var parent = el.parentElement;
        if (el.tagName.toLowerCase() === 'code') {
      try {
    document.querySelectorAll('div.mermaid, code.language-mermaid').forEach(function (el) {
    // render existing .mermaid containers and fenced code blocks converted by pymdownx
    if (typeof mermaid === 'undefined') return;
  function renderAll() {

  }
    }
      console.warn('mermaid init error', e);
    } catch (e) {
      });
        securityLevel: 'loose'
        theme: getMaterialTheme(),
        startOnLoad: false,
      mermaid.initialize({
    try {
    if (typeof mermaid === 'undefined') return;
  function initMermaid() {

  }
    return 'default';
    if (themeAttr === 'dark' || themeAttr === 'slate') return 'dark';
    var themeAttr = el.getAttribute('data-md-color-scheme') || el.getAttribute('data-theme');
    var el = document.documentElement;
  function getMaterialTheme() {

