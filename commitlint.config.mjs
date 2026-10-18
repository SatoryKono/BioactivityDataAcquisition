export default {
  extends: ['@commitlint/config-conventional'],
  ignores: [
    (message) => {
      const head = (message.trimStart().split(/\r?\n/, 1)[0] ?? '');
      // Automated conflict resolutions use this counted subject instead of "Merge".
      return /^merge\b/i.test(head) ||
        /^Resolve merge conflicts in [1-9]\d* file\(s\)$/.test(head);
    },
    // CodeRabbit's generated conflict-resolution message includes these trailers.
    (message) =>
      /^Resolve merge conflicts in [1-9]\d* file\(s\)\r?\n/.test(message) &&
      /^Resolved conflicts in:\r?$/m.test(message) &&
      /^Co-authored-by: CodeRabbit <noreply@coderabbit\.ai>\r?$/m.test(message) &&
      /^CodeRabbit-Task-Id: [0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\r?$/m.test(message),
  ],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'ci', 'build', 'style', 'revert', 'merge']
    ],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [0],
    'footer-max-line-length': [0]
  }
};
