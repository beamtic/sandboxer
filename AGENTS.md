# Sandboxer repository guidelines

Sandboxer is a Docker Compose workshop for local web development, not a
production deployment. Keep it generic, small, reproducible, and easy to
extend. Prefer straightforward Compose services and Alpine-based images; use
extra dependencies or services only when they provide clear recurring value.

## Current architecture

[`docker-compose.yml`](/home/captain/Work/sandboxer/docker-compose.yml) runs:

- Apache and PHP-FPM for the shared `www/` tree.
- MariaDB with separate Sandboxer, WordPress, and HedgeDoc databases/accounts.
- One-shot setup services that create missing application directories and
  database accounts without replacing existing application checkouts.
- The pinned Turbulentarius HedgeDoc 1.x fork, built by
  [`hedgedoc.dockerfile`](/home/captain/Work/sandboxer/hedgedoc.dockerfile).
- Profundarium, WordPress, Laravel, and phpMyAdmin under the local virtual hosts.
- An optional `frontend` profile running Node against `www/${APP_PATH}`.

Published ports bind to `127.0.0.1`. Application files under `www/` and runtime
data under `dbdata/`, `iedata/`, and `log/` are local or nested-repository
content, not Sandboxer source. Do not inspect or modify them unless the task
requires it. The HedgeDoc fork has its own instructions in
[`www/hedgedoc/AGENTS.md`](/home/captain/Work/sandboxer/www/hedgedoc/AGENTS.md).

HedgeDoc uses the shared MariaDB service and the named `hedgedoc_public` volume
for uploads and built public assets. Keep the stable `CMD_SESSION_SECRET`
wiring intact: it preserves sessions across restarts, while changing it
intentionally logs users out. Keep the image pinned to an explicit fork ref.

## Changes and dependencies

Before changing behavior, inspect the relevant Compose service, Dockerfile,
configuration, setup script, and README section. Prefer a focused change over
new abstraction or infrastructure. Keep build-only packages out of runtime
images and preserve Alpine/musl compatibility.

Keep [`README.md`](/home/captain/Work/sandboxer/README.md) aligned with URLs,
commands, prerequisites, configuration, and user-visible behavior. Do not
commit real credentials, generated data, logs, or application dependencies.
Development credentials in `.env.example` are acceptable when clearly local.

## Branch and repository workflow

Use `develop` for Sandboxer changes. Preserve unrelated working-tree changes;
never reset, force-push, or create a routine feature branch. Commit, push,
merge, and release only when explicitly requested. Push Sandboxer changes only
to `origin develop` unless another target is requested.

`www/` contains independent application repositories. Follow their local
instructions and branches; do not commit their changes from the Sandboxer
repository. In particular, HedgeDoc changes belong in its nested repository,
while Compose integration belongs here.

## Validation and safety

Run the smallest relevant checks. For Compose or environment changes, normally
use:

```sh
docker compose config
docker compose ps -a
docker compose logs --tail=50 <service>
```

Build or start services only when the change requires it. Do not use
`docker compose down -v`, delete volumes, remove images, or otherwise destroy
local application or database data without explicit instruction. Check exposed
ports, mounts, capabilities, credentials, and Docker socket access when
reviewing security-sensitive changes.
