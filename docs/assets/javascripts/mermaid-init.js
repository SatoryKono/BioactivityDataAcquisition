document$.subscribe(function () {
  if (typeof mermaid === "undefined") {
    return;
  }
  mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
  mermaid.run({ querySelector: ".mermaid" });
});
