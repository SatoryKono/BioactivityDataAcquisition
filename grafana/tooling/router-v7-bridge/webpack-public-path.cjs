/** Preserve the scaffold's public-path injection on Windows and POSIX paths. */
exports.portablePublicPathRules = (rules) => {
  return rules?.map((rule) =>
    rule && typeof rule === 'object' && 'test' in rule && rule.test instanceof RegExp &&
    rule.test.source === String.raw`src\/(?:.*\/)?module\.tsx?$`
      ? { ...rule, test: /src[\\/](?:.*[\\/])?module\.tsx?$/ }
      : rule);
};
