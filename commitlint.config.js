module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'ci', 'build', 'style', 'revert']
    ],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [0]
  }
};
