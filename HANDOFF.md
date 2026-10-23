# Sandboxer handoff

## Working rules

Read `AGENTS.md` and inspect only files relevant to the task. Use Sandboxer's `develop` branch for future code changes and pushes, following
the branch policy in AGENTS.md. Keep changes small and explain them plainly: the maintainer wants to understand the implementation.
Keep documentation focused on normal use rather than hypothetical migrations or
completed-work history. Commit, push, merge, and release only when requested;
never assume that both main and a development branch should be pushed.

Sandboxer and the applications under `www/` are separate Git repositories.
Check the applicable repository's branch and instructions before editing or
publishing. Profundarium has its own development-only push policy in its AGENTS.md.

## Remaining review candidates

These are not authorization to make additional changes:

- Docker Desktop and a real rootless Docker daemon have not been validated.
  Preserve writable host editing and avoid recursively chowning source trees.
- Measure image sizes before optimizing. Retain ImageMagick, Imagick, and existing
  image-format support unless the maintainer requests otherwise.
- Configurable host ports may be useful if parallel Sandboxer instances are needed.
