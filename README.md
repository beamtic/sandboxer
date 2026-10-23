# sandboxer

Basic sandboxing environment for all kinds of experiments. The idea is to mainly use existing images to keep it as simple as possible for new Docker users.


Currently insecure for production and only intended for educational purposes and quick testing + learning Docker, and I wanted it to be very simple to spin up without having to think about file permissions on the host. Etc. Etc.

Run the containers:
```
docker compose up
```

Stop the containers:
```
docker compose stop
```
Or hit `CTRL` + `C` inside your console window.

View your running containers after starting them:
```
docker ps
```

Compose generates container names from the project and service names. Use
`docker compose exec <service> ...` to run commands without depending on a
container name. Run `docker compose up -d` to recreate existing containers with
the generated names; their bind-mounted application and database data remain.
Separate projects can use `docker compose -p <name> ...`, but concurrent stacks
still require different host ports.

If you need CLI access to the database:

```
docker compose exec db bash
mariadb -uroot -p
```

The `root` password is `superduperroot`.

- To open phpMyAdmin, open `http://database.localhost` in a browser.
- To open the default website (`www/default`), open `http://localhost`.
- To open the generated Laravel example (`www/laravel`), open `http://laravel.localhost`.
- To open HedgeDoc, open `http://hedgedoc.localhost`.
- To develop Profundarium (`www/profundarium`), open `http://hedgedoc.localhost/profundarium/`.

Published ports bind to `127.0.0.1` (IPv4 loopback) for access from the Docker host.
For a database client on the host, connect to `127.0.0.1:3306`; containers continue
to use `db:3306`. Access from another device requires an intentional change to
the port bindings and a review of the development credentials.

After changing port bindings, run `docker compose up -d` to recreate affected
containers. `docker compose restart` does not apply Compose configuration changes.
Use `docker compose ps` to confirm published ports show `127.0.0.1`.

> [!WARNING]  
> **Do NOT use this for deployment on production!**
>
> Local-only port bindings do not make the development credentials or configuration suitable for production.

## Startup readiness

Apache starts after setup exits successfully and MariaDB, PHP-FPM, and HedgeDoc
report healthy. MariaDB checks connectivity and InnoDB initialization; PHP checks an
FPM worker's built-in ping response using Alpine's small `fcgi` client.

Use `docker compose ps -a` to see health and setup exit status. If startup is
blocked, inspect `docker compose logs setup db php`. Existing data directories
need MariaDB's health-check account/configuration from image initialization.
These startup gates do not automatically restart services or stop Apache when a
dependency becomes unhealthy later; applications still need connection retries.

## Alpine and PHP

The custom images use Alpine 3.24.2. PHP runs from Alpine's `php85` packages
(PHP 8.5; the patch version follows the Alpine 3.24 package repository).
PHP configuration lives in `config/php85/` and the image definition is
`php8.5-fpm.dockerfile`. OPcache is built into PHP 8.5.

After changing these files, rebuild and check the services:

```bash
docker compose build --pull setup php apache2
docker compose run --rm --no-deps php php -v
docker compose run --rm --no-deps php php-fpm85 -t
docker compose run --rm --no-deps apache2 httpd -t
docker compose up -d php apache2
```

Test your PHP application and phpMyAdmin in the browser after upgrading.
Package availability does not guarantee application compatibility with PHP 8.5.

PHP applications can read `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`,
`MYSQL_USER`, and `MYSQL_PASSWORD` with `getenv()`. These are explicitly passed
through to FPM workers in `config/php85/php-fpm.d/www.conf`; other inherited
variables remain cleared. PHP receives the application account, not the database
root password. Rebuild PHP after changing the FPM configuration.

## Composer

The PHP image installs Composer 2.10.3 directly from its versioned PHAR download
and verifies a pinned SHA-256 checksum before making it executable. Download or
checksum errors fail the build. No additional packages are needed.

To update Composer, change both the version in the download URL and the checksum
in `php8.5-fpm.dockerfile` using the [official downloads](https://getcomposer.org/download/).
Rebuild and check the installed version without mounting application files:

```bash
docker compose build php
docker run --rm --network none --entrypoint composer sandboxer-php --version
```

Run `docker compose up -d --no-deps php` to apply the rebuilt image to the service.

## Optional Node / React / Vite development

The `frontend` profile provides Node 24.21.0 on Alpine 3.24 without adding packages
to PHP or Apache. Source files and Git stay on the host. Copy `.env.example` to
`.env` at the repository root and set `APP_PATH` to a project directory relative
to `www/` (default: `laravel`). Run setup first to create the example. This Compose settings file is
separate from Laravel's application `.env`. The selected directory must exist
and contain a `package.json` with a Vite `dev` script.

```bash
docker compose run --rm node npm install
# Use npm ci instead when the project already has a package-lock.json.
docker compose --profile frontend up -d node
docker compose logs --tail=30 node
docker compose run --rm node npm run build
docker compose stop node
```

Normal `docker compose up` does not start Node. Explicit `run node` commands do
not require the profile flag. The Vite port is fixed at `127.0.0.1:5173`; startup
fails if it is occupied. Open `http://localhost:5173` for a standalone React/Vite
app. For the example, open `http://laravel.localhost`; Vite serves its frontend assets.

Dependencies live in the Compose `node_modules` volume, separate from host
`node_modules`. Stop Node before changing `APP_PATH`, then reinstall dependencies
(prefer `npm ci`) and recreate Node. Use separate Compose project names for
separate dependency volumes; running multiple stacks also requires distinct host
ports. Avoid alternating host and container npm installations into the same
`node_modules` directory.

The generated example already configures Vite for Docker. For other Laravel
projects, merge these settings into `vite.config.js`, keeping their plugins and inputs:

```js
server: {
    hmr: { host: 'localhost' },
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
},
```

If mounted-file changes are not detected, stop Node and try polling:

```bash
docker compose run --rm --service-ports -e VITE_USE_POLLING=true node
```

Polling uses more CPU. File watching and ownership need validation on each host
platform; container commands currently run as root and may create root-owned
source/build files on native Linux. Alpine uses musl, so native npm packages need
compatible binaries or project-specific build dependencies. Add those only when
needed. Host editors may need a container-aware setup for dependency completion
because the dependency volume is not visible on the host.

Apache can serve a standalone React app's built `dist/` directory, with an
`index.html` fallback if client-side routing is used. This does not provide Vite
hot reload or a server-side React runtime. Laravel's Vite build goes into its
application's `public/build/`. Stop Vite when testing built Laravel assets; if an
abrupt shutdown leaves `public/hot`, remove that stale file after confirming the
dev server has stopped.

## Setup file ownership

The setup container starts as root, reads the numeric UID/GID of `/srv/sandboxer`
(the `www/` bind mount), and uses Alpine's small `su-exec` utility to run its setup
command as that identity. No host UID/GID variables, host scripts, or additional
bootstrap command are needed. A temporary directory checks write access before
any installer runs. Missing directories, failed identity changes, or unwritable
mounts stop setup with an error. No users/groups are added to the container.

On native Linux without user remapping, new setup files belong to the owner of
`www/`, so that owner can edit the normally owner-writable generated files. On
Docker Desktop, setup uses the IDs exposed by its file-sharing layer; macOS and
Windows host access remains governed by that layer and host permissions. This
uses the same container code on every platform; Desktop validation is still
required on those hosts.

UID 0 is accepted: rootless Docker or user namespaces may map it to an
unprivileged host user. Unmapped IDs, filesystem ACLs, or restrictive sharing can
still prevent writes. Ownership of the directory is the source of truth, not the
identity of whoever ran Compose. In particular, a missing `www/` may be created
by Docker as root-owned on native Linux; setup cannot infer a different intended
owner from that directory. Existing root-owned files are not repaired or changed.
Node and explicit CLI commands retain their existing identities. PHP-FPM worker
ownership is described below.

After updating the setup image, normal `docker compose up --build` applies this
behavior. Existing applications retain their normal installer preservation rules.

## PHP-FPM worker ownership

The FPM master starts as root and starts workers with the numeric UID/GID exposed
by the `www/` mount. No host variables or container user accounts are required.
Alpine's small `su-exec` package checks write access as the selected worker before
FPM starts. The application mount remains writable; startup does not recursively
change ownership or permissions. Apply changes with `docker compose up -d --build php`.

When the mount reports UID 0, startup tries the existing `nobody` account instead.
This can work with Docker Desktop's translated file permissions. If that identity
cannot write, startup fails explicitly rather than allowing root workers. Under
rootless Docker/user namespaces, UID 0 may map to an unprivileged host owner;
such a mount can still be inaccessible to other container IDs. Strict non-root
workers and writable mounts therefore are not guaranteed on every mapping.
Docker Desktop and real rootless Docker must be validated on those platforms.
Run `python3 tests/check_fpm_ownership.py` after building PHP to test real FPM
requests and file ownership in disposable containers, including failure cases.

The check covers the mount root, not every existing application file. Older
root-owned caches, sessions, logs, or uploads can still need targeted ownership
repair. Different owners for individual applications require separate pools or
appropriate shared permissions. The worker cannot modify root-owned container
configuration, but it can modify application files accessible to the mount owner.
`docker compose exec php ...` still runs CLI commands as root by default.

## Sandboxer landing page setup

On every setup run, `sandboxer-site.sh` copies `index.php` and
`beamtic-sandboxer.png` from
`config/host/default/` are copied to `www/default/` only if missing. Existing files,
including edited pages, are preserved. Existing symlinks are left alone. This
step runs independently of the phpMyAdmin completion marker.

After editing the templates, rebuild with `docker compose build setup` and run
`docker compose run --rm setup`. Template changes do not replace existing files;
move an individual destination file aside first if you want its new template.

## Laravel example setup

The setup container installs an independent example in `www/laravel`, served at
`http://laravel.localhost`. The default `http://localhost` site stays in
`www/default`; phpMyAdmin stays at `http://database.localhost`. All applications
under `www/` remain ignored by Sandboxer's Git repo; the installer and dependency
lockfile are the reproducible source of the example.

The setup image downloads the official `laravel/laravel` v13.10.1 skeleton,
verifies its pinned SHA-256, and installs dependencies from
`config/laravel/composer.lock` (Laravel framework 13.33.0). PHP development
packages are included so Artisan tests work. Composer and download tools stay
in the build stage; no Node packages are added to the setup or PHP image.

On first run, setup stages the app, sets `APP_URL=http://laravel.localhost`,
generates a unique application key, and initializes its own SQLite database.
Only successful initialization publishes `www/laravel`. Failed attempts clean
up staging files and can be retried. Laravel's built-in welcome page works
without npm or Vite; use the optional Node service when developing frontend assets.

If `www/laravel` already exists (including a symlink), setup leaves it entirely
unchanged: no reinstall, migrations, key rotation, or upgrades. It never resets
an existing database. The phpMyAdmin `www/setup-completed` marker controls only
phpMyAdmin; it does not prevent installing the Laravel example on an existing
Sandboxer checkout. A fresh example can be installed after you deliberately move
an existing `www/laravel` aside; preserve any work and database first.

For an existing checkout after these setup changes:

```bash
docker compose build setup apache2
docker compose run --rm setup
docker compose up -d apache2
```

New checkouts install both examples through the normal `docker compose up` flow.
No Compose override is needed. If your system does not resolve
`laravel.localhost`, map it to `127.0.0.1` in your host's hosts file.

Useful commands (change the working directory for your own projects):

```bash
docker compose exec -w /srv/sandboxer/laravel php composer check-platform-reqs
docker compose exec -w /srv/sandboxer/laravel php php artisan about
docker compose exec -w /srv/sandboxer/laravel -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: php php artisan test
```

Run Composer and Artisan inside PHP; run npm through the Node service. Laravel's
`composer run dev` / `composer run setup` scripts may expect Node in the same
environment, so use the separate commands documented here. Queue workers and
scheduling remain application-specific. The example is a plain Laravel skeleton,
not a React starter kit; the Node service also supports separate React projects.

Laravel uses `DB_*` settings, not Sandboxer's `MYSQL_*` names. To deliberately
switch an application to the included MariaDB, set its own `.env` to:

```dotenv
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=sandbox
DB_USERNAME=sandboxer
DB_PASSWORD=localuserpassword
```

Run migrations only after choosing the intended database. Keep `storage/` and
`bootstrap/cache/` writable. For other Laravel sites, add an Apache virtual host
modeled on `config/apache2/conf.d/laravel.conf`, serving only `public/`.

When upgrading the generated template, update the skeleton version and checksum
in `setup.dockerfile`, regenerate its Composer lockfile with PHP 8.5, and review
`config/laravel/vite.config.js` against the new skeleton. Rebuild and test a fresh
installation; existing applications remain the developer's responsibility.

## HedgeDoc and Profundarium

The standard stack includes one HedgeDoc instance, built from
[Turbulentarius's HedgeDoc fork](https://github.com/Turbulentarius/hedgedoc), and
a separate Profundarium source checkout at `www/profundarium`. The clean Laravel
example remains independent at `www/laravel`.

- `http://hedgedoc.localhost`: create and edit Markdown notes.
- `http://hedgedoc.localhost/profundarium/<note-id>`: follow the fork's public-view link.
- `http://hedgedoc.localhost/profundarium/`: develop and view Profundarium.
- `http://laravel.localhost`: develop unrelated Laravel applications.

Apache serves Profundarium through Sandboxer's shared PHP-FPM container. There
is no separate packaged Profundarium service, second HedgeDoc, or PostgreSQL
service in the default stack.

The HedgeDoc image builds commit `90212dc04003741393d19b2c90a4cba2f81b8a7b`
from the fork on Alpine Node.js 24. Native modules and frontend assets are built
in a separate stage; Git, compilers, and development dependencies stay out of
the runtime image. To select another tested fork commit, set HEDGEDOC_REF under
the service's build args or pass `--build-arg HEDGEDOC_REF=<commit>` when building.

The existing `hedgedoc_public` volume preserves the SQLite database and uploads.
HedgeDoc mounts it at `/data`, so it does not hide the image's compiled public
assets. Apache and PHP mount the same volume read-only at `/hedgedoc/public`.
Apache serves `/uploads/` directly. No database or upload volume is deleted when
services are recreated.

First-run setup installs a pinned Profundarium `main` checkout with Composer
dependencies, a local application key, and a connection to the shared HedgeDoc
SQLite database. Existing `www/profundarium` directories are left unchanged.
The pinned source commit is configured as PROFUNDARIUM_REF in `setup.dockerfile`;
the checkout tracks `origin/main`, so users can run `git pull` to update it.
Setup leaves existing checkouts and their selected branches unchanged.
To develop Profundarium, explicitly switch branches:

```sh
cd www/profundarium
git fetch origin
git switch development
```

Run application commands from Sandboxer's root with:

```sh
docker compose exec -w /srv/sandboxer/profundarium php composer test
docker compose exec -w /srv/sandboxer/profundarium php php artisan media:unused
```

The data volume is read-only in PHP: listing media works, while deleting uploads
requires an intentional writable mount in a local override.

The local HedgeDoc account is `sandboxer@sandboxer.localhost`, with password
`localuserpassword`. The one-shot `hedgedoc-setup` service creates it only if
missing; it never resets an existing password.

```sh
docker compose logs hedgedoc-setup
docker compose run --rm --no-deps hedgedoc-setup
```

To run the isolated account-setup tests:

```sh
docker compose run --rm --no-deps --entrypoint node -v ./tests:/tests:ro hedgedoc-setup --test /tests/test_hedgedoc_user.cjs
```


## MariaDB version

The database uses the official `mariadb:11.4.13` image from the
[11.4 LTS series](https://mariadb.org/about/#maintenance-policy).
Database files persist in `dbdata/`; recreating a container does not reset them.

On first initialization, MariaDB creates the `sandbox` database and grants
`sandboxer` access using the development password `localuserpassword`. These
initialization settings do not change an existing database directory.

When moving from 11.2, test with a fresh data directory if the old data is
unneeded. Stop `db` before moving its data directory aside. If retaining data,
back it up and follow the upstream upgrade instructions before starting the new
version. Do not run an older image against files already upgraded by a newer one.

After preparing the data directory, run:

```bash
docker compose pull db
docker compose up -d --no-deps db
docker compose logs --tail=50 db
docker compose exec db mariadb -uroot -p -e "SELECT VERSION();"
```

Expect version `11.4.13` (possibly with a packaging suffix), then verify database
access through phpMyAdmin at `http://database.localhost`.

## phpMyAdmin setup

phpMyAdmin connects automatically as `sandboxer`, with access to the `sandbox`
database. Use the root CLI login above for server-wide administration.

The setup service installs phpMyAdmin 5.2.3 only when `www/setup-completed` is absent.
The setup image downloads and verifies the pinned ZIP in its `phpmyadmin-template`
build stage. Starting containers needs no phpMyAdmin download. At startup, setup
copies the prepared files and local configuration into place. Copy or configuration
errors stop setup without writing the marker; temporary files are cleaned up.
After fixing the cause, retry with `docker compose run --rm setup`.
Rebuild script changes first with `docker compose build setup`.

An existing `www/phpmyadmin` directory without a completion marker is preserved
and setup stops for inspection. Move that directory aside before retrying if
you want a fresh installation. Existing completion markers are still honored;
this change does not repair or upgrade previous installations automatically.

For isolated script checks, SANDBOXER_ROOT, PHPMYADMIN_TEMPLATE, and
PHPMYADMIN_CONFIG override the destination, prepared application, and configuration.
Their defaults are `/srv/sandboxer`, `/opt/phpmyadmin`, and `/config.inc.php`.

## Testing the setup installers

Run the tests after changing a setup script or its tests, before committing.
They require Python 3 and a POSIX shell on your host. From the
repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The tests check the setup scripts' failure handling, retries, cleanup,
and preservation of existing files, symlinks, application keys, and databases.

The tests use temporary directories, prepared application fixtures, and simulated
Laravel initialization commands. They are safe to run
with phpMyAdmin installed and do not touch your application or database data.
They are not needed during normal use and do not replace testing the real
installation in Docker.

For the setup entrypoint's numeric ownership and failure-path checks, use Docker:

```bash
docker compose build setup
python3 tests/check_setup_ownership.py
```

These seven checks use temporary container filesystems without networking. They
cover arbitrary numeric IDs, UID 0, matching non-root execution, missing paths,
read-only mounts, insufficient permissions, and identity mismatches. They do not
exercise Docker Desktop file sharing or a real rootless daemon.

### Profundarium asset URLs

Profundarium stores its CSS and fonts under `public/profundarium/assets/`.
The Profundarium virtual host serves these directly at `/profundarium/assets/`;
no asset alias is required.
