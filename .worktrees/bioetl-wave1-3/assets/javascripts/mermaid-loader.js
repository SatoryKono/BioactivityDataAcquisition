(function () {
    // Fallback loader: if local mermaid didn't load (e.g., not vendored), fetch version file and load from CDN.
    function loadScript(src, cb) {
        var s = document.createElement('script');
        s.src = src;
        s.async = false; // preserve execution order
        s.onload = function () {
            if (cb) cb(null);
        };
        s.onerror = function (e) {
            if (cb) cb(e || new Error('Failed to load ' + src));
        };
        document.head.appendChild(s);
    }

    function readVersionFile() {
        // Try to fetch MERMAID_VERSION under assets; fall back to embedded default.
        var defaultVersion = '10.4.0';
        try {
            return fetch('/assets/javascripts/MERMAID_VERSION', {cache: 'no-store'})
                .then(function (r) {
                    if (!r.ok) throw new Error('no version file');
                    return r.text();
                })
                .then(function (t) {
                    return (t || '').trim().split('\n')[0] || defaultVersion;
                })
                .catch(function () {
                    return defaultVersion;
                });
        } catch (e) {
            return Promise.resolve(defaultVersion);
        }
    }

    function tryLoadFromCDN() {
        readVersionFile().then(function (version) {
            var src = 'https://cdn.jsdelivr.net/npm/mermaid@' + encodeURIComponent(version) + '/dist/mermaid.min.js';
            loadScript(src, function (err) {
                if (err) {
                    console.warn('mermaid-loader: failed to load CDN mermaid', err);
                } else {
                    console.info('mermaid-loader: loaded mermaid from CDN (' + version + ')');
                }
            });
        });
    }

    // If mermaid is undefined after a short delay (allow local script to run), attempt CDN.
    if (typeof mermaid === 'undefined') {
        setTimeout(function () {
            if (typeof mermaid === 'undefined') {
                tryLoadFromCDN();
            }
        }, 1200);
    }
})();

