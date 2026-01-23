// Sync Mermaid theme with MkDocs Material palette and (re)initialize on changes
(function () {
    function currentTheme() {
        const scheme = document.documentElement.getAttribute("data-md-color-scheme") || "default";
        // Map Material schemes to Mermaid themes
        return scheme === "slate" ? "dark" : "neutral";
    }

    function initMermaid() {
        if (!window.mermaid) return;
        try {
            window.mermaid.initialize({
                startOnLoad: true,
                securityLevel: "loose",
                theme: currentTheme(),
            });
            // Re-render existing diagrams
            window.mermaid.init(undefined, document.querySelectorAll(".mermaid"));
        } catch (e) {
            console.warn("Mermaid initialization failed:", e);
        }
    }

    // Initialize on page load
    document.addEventListener("DOMContentLoaded", initMermaid);

    // Re-initialize on palette changes (watch the data attribute)
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.attributeName === "data-md-color-scheme") {
                initMermaid();
                break;
            }
        }
    });
    observer.observe(document.documentElement, {attributes: true});
})();
