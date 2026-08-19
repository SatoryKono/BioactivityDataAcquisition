export default {
  extends: ['@commitlint/config-conventional'],
  ignores: [
    (message) => message.startsWith('Merge'),
  ],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'ci', 'build', 'style', 'revert']
    ],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [0],
    'footer-max-line-length': [0]
  }
};
