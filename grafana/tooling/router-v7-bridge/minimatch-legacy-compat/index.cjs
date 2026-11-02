'use strict';

// Existing ESLint/webpack consumers require a callable CommonJS entry point.
// Matching and pattern preprocessing are implemented by the fixed upstream.
const fixed = require('minimatch-fixed');
module.exports = fixed.minimatch;
// Explicit assignments preserve statically discoverable named ESM exports too.
module.exports.minimatch = fixed.minimatch;
module.exports.Minimatch = fixed.Minimatch;
module.exports.GLOBSTAR = fixed.GLOBSTAR;
module.exports.sep = fixed.sep;
module.exports.filter = fixed.filter;
module.exports.defaults = fixed.defaults;
module.exports.braceExpand = fixed.braceExpand;
module.exports.match = fixed.match;
module.exports.escape = fixed.escape;
module.exports.unescape = fixed.unescape;
