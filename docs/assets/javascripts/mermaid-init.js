// Mermaid adaptive init: responsive diagrams + theme sync.
// Material theme exposes `__md_get` for palette state.
document.addEventListener("DOMContentLoaded", function () {
  if (typeof mermaid === "undefined") return;

  var palette = __md_get("__palette");
  var dark = palette && palette.color && palette.color.scheme === "slate";

  mermaid.initialize({
    startOnLoad: true,
    theme: dark ? "dark" : "default",
    // Adaptive: SVG scales to container width
    flowchart: { useMaxWidth: true },
    sequence: { useMaxWidth: true },
    class: { useMaxWidth: true },
    state: { useMaxWidth: true },
    er: { useMaxWidth: true },
    pie: { useMaxWidth: true },
    mindmap: { useMaxWidth: true },
    gantt: { useMaxWidth: true },
  });
});

// Re-init on palette toggle (light / dark)
document.addEventListener("change", function (ev) {
  if (
    ev.target &&
    ev.target.closest &&
    ev.target.closest("[data-md-color-scheme]")
  ) {
    location.reload();
  }
});
