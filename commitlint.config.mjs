export default {
  extends: ['@commitlint/config-conventional'],
  ignores: [
    (message) => {
      const head = (message.trimStart().split(/\r?\n/, 1)[0] ?? '');
      // Automated conflict resolutions use this counted subject instead of "Merge".
      return /^merge\b/i.test(head) ||
        /^Resolve merge conflicts in [1-9]\d* file\(s\)$/.test(head);
    },
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
