# Playwright Review Artifacts

This directory stores sanitized, long-lived review artifacts that are worth
tracking in git.

Rules:

- Keep local machine paths out of tracked files.
- Keep private network addresses out of tracked files.
- Prefer repo-relative paths for screenshots or outputs.
- Keep disposable browser output in `output/` and only promote curated review
  artifacts into this directory.
