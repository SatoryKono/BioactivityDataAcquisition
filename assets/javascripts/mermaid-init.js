(function () {
    // Offline-compatible Mermaid initializer
    function getMaterialTheme() {
        var el = document.documentElement;
        var themeAttr = el.getAttribute('data-md-color-scheme') || el.getAttribute('data-theme');
        if (themeAttr === 'dark' || themeAttr === 'slate') return 'dark';
        return 'default';
    }

    function initMermaid() {
        try {
            if (typeof mermaid === 'undefined') return;
            mermaid.initialize({
                startOnLoad: false,
                securityLevel: 'loose',
                theme: getMaterialTheme(),
            });
        } catch (e) {
            console.warn('mermaid init error', e);
        }
    }

    function renderAll() {
        try {
            if (typeof mermaid === 'undefined') return;
            // render existing .mermaid containers and fenced code blocks converted by pymdownx
            document.querySelectorAll('div.mermaid, code.language-mermaid').forEach(function (el) {
                try {
                    if (el.tagName.toLowerCase() === 'code') {
                        var text = el.textContent || '';
                        var container = document.createElement('div');
                        container.className = 'mermaid';
                        container.textContent = text;
                        var parent = el.parentElement;
                        if (parent) parent.replaceWith(container);
                        mermaid.init(undefined, container);
                    } else {
                        mermaid.init(undefined, el);
                    }
                } catch (err) {
                    // silent per-render error
                }
            });
        } catch (e) {
            console.warn('mermaid render error', e);
        }
    }

    function renderAndInit() {
        initMermaid();
        renderAll();
    }

    document.addEventListener('DOMContentLoaded', function () {
        renderAndInit();
    });

    // Re-render when Material theme attribute changes (light/dark)
    try {
        var observer = new MutationObserver(function (mutations) {
            var shouldReinit = mutations.some(function (m) {
                return m.attributeName === 'data-md-color-scheme' || m.attributeName === 'data-theme';
            });
            if (shouldReinit) {
                try {
                    initMermaid();
                    renderAll();
                } catch (e) {
                    // ignore
                }
            }
        });
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-md-color-scheme', 'data-theme']
        });
    } catch (e) {
        // ignore if MutationObserver unsupported
    }

})();
