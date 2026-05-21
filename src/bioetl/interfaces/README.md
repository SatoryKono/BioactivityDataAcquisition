# Interfaces Layer — Navigation Map

The interfaces layer exposes the system to operators and external callers. It
may call into `composition/`, but it should stay thin and avoid embedding
business logic.

## Package Structure

| Package          | Responsibility                                                        |
| ---------------- | --------------------------------------------------------------------- |
| `cli/`           | Click-based commands, command groups, output formatting, exit codes   |
| `http/`          | HTTP health/metrics server seams and lightweight server state helpers |

## Reading Order

1. Start with `cli/main.py` for the command entrypoint.
1. Follow `cli/commands/` for command-specific behavior.
1. Inspect `http/` when debugging health or metrics serving.
1. Inspect `http/control_plane_identity/` when debugging control-plane identity
   payload shaping for HTTP surfaces.

## Placement Rules

- Keep argument parsing, response formatting, and protocol adapters here.
- Push business flow into `application/`.
- Push assembly and dependency creation into `composition/`.
