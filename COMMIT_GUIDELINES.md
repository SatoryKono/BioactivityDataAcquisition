# Commit Message Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/) format for all commit messages.

## Format

All commit messages must follow this format:

```
<type>: <subject>

[optional body]

[optional footer]
```

## Types

The commit type must be one of the following:

- `feat`: A new feature
- `fix`: A bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `chore`: Changes to build process or auxiliary tools
- `perf`: Performance improvements
- `ci`: Changes to CI configuration files and scripts
- `build`: Changes that affect the build system or external dependencies
- `style`: Code style changes (formatting, missing semi colons, etc)
- `revert`: Reverts a previous commit

## Examples

```
feat: add new data source for ChEMBL
fix: correct query parameter validation
docs: update README with installation instructions
test: add unit tests for data transformer
chore: update dependencies
refactor: simplify error handling logic
```

## Validation

Commit messages are automatically validated using [commitlint](https://commitlint.js.org/) in CI/CD pipeline.

Configuration is defined in `commitlint.config.js`.

## Rules

- Subject line must not be empty
- Type must not be empty
- Type must be one of the allowed types listed above
- Header (type + subject) must not exceed 100 characters
- Scope should be in lower-case (if provided)

## CI Check

The commit-lint workflow runs on all pull requests to ensure commit messages follow these guidelines.
See `.github/workflows/commit-lint.yml` for the workflow configuration.
