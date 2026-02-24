// Mermaid theme sync: match diagram theme to light/dark mode toggle.
// The Material theme exposes a `__md_get` helper for palette state.
document.addEventListener("DOMContentLoaded", function () {
  var defined = typeof mermaid !== "undefined";
  if (!defined) return;

  var palette = __md_get("__palette");
  var dark = palette && palette.color && palette.color.scheme === "slate";

  mermaid.initialize({
    startOnLoad: true,
    theme: dark ? "dark" : "default",
  });
});
