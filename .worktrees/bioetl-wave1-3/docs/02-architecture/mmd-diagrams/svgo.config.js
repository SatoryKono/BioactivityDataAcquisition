/** @type {import('svgo').Config} */
module.exports = {
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          // Preserve foreignObject elements — Mermaid renders edge labels
          // and node labels as HTML inside <foreignObject>. Removing or
          // inlining styles breaks label rendering in PNG conversion.
          removeHiddenElems: false,
          inlineStyles: false,
          // Prevent merging/stripping of !important overrides for edge
          // label opacity and background (custom.css vs Mermaid defaults).
          minifyStyles: false,
        },
      },
    },
    // Never strip foreignObject (edge labels, node labels).
    {
      name: "removeUnknownsAndDefaults",
      params: {
        keepDataAttrs: true,
        keepAriaAttrs: true,
      },
    },
  ],
};
