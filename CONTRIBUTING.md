# Maintaining Sandboxer

Use `develop` for Sandboxer changes and pushes, then open a pull request to
`main`. Applications under `www/` have their own repositories and branch rules.
Read [AGENTS.md](AGENTS.md) for repository guidelines.

## Configuration and templates

`docker-compose.yml` defines the local environment. Root-level `*.dockerfile`
files define custom images; service configuration and installers live in `config/`.
Custom images use Alpine. Native dependencies must support musl or be built for it;
keep compilers and other build-only tools out of runtime images where practical.

`setup.dockerfile` prepares phpMyAdmin, WordPress, Laravel, and Profundarium in build stages.
Runtime installers copy missing applications into the host-mounted `www/`.
Existing Laravel, Profundarium, WordPress, and phpMyAdmin directories are preserved. Each
installer stages a complete application before moving it into place; no separate
completion marker is needed. The landing-page installer copies only
missing files from `config/host/default/`.

When updating pinned downloads, update the version and checksum together. Laravel's
skeleton and `config/laravel/composer.lock` must remain compatible. Profundarium
and HedgeDoc source revisions are selected by `PROFUNDARIUM_REF` in
`setup.dockerfile` and `HEDGEDOC_REF` in `hedgedoc.dockerfile`.
Test new installations: rebuilding setup does not upgrade existing applications.

Apache routes `/profundarium/` on `hedgedoc.localhost` to the shared PHP-FPM
service and serves its assets using an alias in `config/apache2/conf.d/hedgedoc.conf`.
The HedgeDoc data volume is writable in HedgeDoc and read-only in Apache and PHP.

## Validation

Validate Compose changes:

```sh
docker compose config --quiet
```

After installer changes, run the isolated tests (Python 3 and a POSIX shell):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

These use temporary fixtures rather than your installed applications. For changes
to setup or FPM ownership handling, build the relevant image and run its Docker checks:

```sh
docker compose build setup php
python3 tests/check_setup_ownership.py
python3 tests/check_fpm_ownership.py
```

These checks do not validate Docker Desktop sharing or a real rootless daemon.
Setup follows the mount's numeric owner; FPM uses non-root workers, falling back
to `nobody` if the mount reports UID 0. Neither recursively changes source ownership.

For the HedgeDoc account initializer:

```sh
docker compose run --rm --no-deps --entrypoint node -v ./tests:/tests:ro hedgedoc-setup --test /tests/test_hedgedoc_user.cjs
```

Rebuild affected services and verify their actual behavior after configuration or
image changes. Use `docker compose up -d --build <service>` to apply changes;
`restart` alone does not apply Compose changes. Check `docker compose ps -a` and
relevant service logs. Apache's startup dependencies gate initial readiness;
they do not automatically restart it when a dependency later becomes unhealthy.

`wordpress-db-setup` reuses the PHP image to provision WordPress's database and
account after MariaDB becomes healthy, then exits. It also works with existing
MariaDB data. Reruns preserve passwords and tables; changed passwords require an
explicit account update. PHP receives the WordPress account, never the root password.
