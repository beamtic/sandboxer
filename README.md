# Sandboxer

Sandboxer is a Docker Compose workshop for local web development with Apache,
PHP-FPM, MariaDB, and phpMyAdmin. It includes a clean Laravel application and
Profundarium alongside [our HedgeDoc fork](https://github.com/Turbulentarius/hedgedoc)
for editing and publishing Markdown notes.

This environment is for local development, not production. Published ports bind
to `127.0.0.1`, and the included passwords are development credentials.

## Getting started

Install Docker with Compose v2 and Git. From your Sandboxer checkout:

```sh
mkdir -p www
docker compose up -d --build
docker compose ps -a
```

Create `www/` as your normal host user before the first start; see
[file permissions](#file-permissions) below. The first build downloads dependencies
and prepares the applications, so it can take a while.

| Application | URL | Source directory |
| --- | --- | --- |
| Sandboxer start page | http://localhost | `www/default` |
| Laravel | http://laravel.localhost | `www/laravel` |
| HedgeDoc | http://hedgedoc.localhost | Built into its image |
| Profundarium | http://hedgedoc.localhost/profundarium/ | `www/profundarium` |
| phpMyAdmin | http://database.localhost | `www/phpmyadmin` |

If your system does not resolve these `.localhost` names, add the names you use
to your hosts file with address `127.0.0.1`.

The local HedgeDoc account is `sandboxer@sandboxer.localhost`, with password
`localuserpassword`. Setup creates it if missing and preserves existing passwords.

The `setup` and `hedgedoc-setup` services finish and exit successfully; this is
normal. If startup fails, check:

```sh
docker compose logs --tail=50 setup hedgedoc-setup db php apache2 hedgedoc
```

Stop the environment with `docker compose stop`. Start it again with
`docker compose up -d`.

## Developing Profundarium

Edit `www/profundarium` on your host; the containers use those files directly.
Profundarium shares HedgeDoc's notes and uploads, and a note's public view is at
`http://hedgedoc.localhost/profundarium/<note-id>`.

New installations start from a pinned `main` checkout. To work on Profundarium,
switch its separate Git repository to `development`:

```sh
cd www/profundarium
git fetch origin
git switch development
```

From **Sandboxer's root**, run Composer and application commands through PHP:

```sh
docker compose exec -w /srv/sandboxer/profundarium php composer install
docker compose exec -w /srv/sandboxer/profundarium php composer test
```

HedgeDoc data is read-only in PHP. Commands that delete uploads need an
intentional writable mount in your local Compose override.

## Developing a Laravel application

`www/laravel` is an independent Laravel skeleton, ready at
http://laravel.localhost. Setup installs Composer dependencies, generates its
application key, and initializes a SQLite database. Edit it directly to start
your own application; it is separate from Profundarium.

From Sandboxer's root:

```sh
docker compose exec -w /srv/sandboxer/laravel php composer install
docker compose exec -w /srv/sandboxer/laravel php php artisan about
docker compose exec -w /srv/sandboxer/laravel php php artisan test
```

To use MariaDB instead, change `www/laravel/.env`:

```dotenv
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=sandbox
DB_USERNAME=sandboxer
DB_PASSWORD=localuserpassword
```

Then run your application's migrations. Other Laravel projects can use an Apache
virtual host modeled on `config/apache2/conf.d/laravel.conf`, serving their
`public/` directory.

Application directories under `www/` are ignored by Sandboxer's Git repository;
manage your applications in their own repositories. Setup leaves existing Laravel
and Profundarium directories unchanged, including their dependencies and branches.

## Optional frontend development

Node runs separately from PHP. The default project is `www/laravel`; to select
another project, copy the root `.env.example` to `.env` and set `APP_PATH` to its
path relative to `www/`. This file is separate from your application's `.env`.

```sh
docker compose run --rm node npm install
# Use npm ci instead if the project already has a package-lock.json.
docker compose --profile frontend up -d node
```

Open your application's usual URL. A standalone Vite app is available at
http://localhost:5173. The generated Laravel app already has Docker-compatible
Vite settings; other projects may need their own configuration.

```sh
docker compose run --rm node npm run build
docker compose stop node
```

Node is optional and does not start with the normal stack. Dependencies live in
a named `node_modules` volume. Stop Node before changing `APP_PATH`, reinstall the
selected project's dependencies, and recreate the service with `up -d node`.
Run Composer/Artisan through PHP and npm through Node, rather than using Laravel
scripts that expect both tools in one container.

## Database and saved data

phpMyAdmin connects as `sandboxer` to the `sandbox` database with password
`localuserpassword`. Host database clients connect to `127.0.0.1:3306`;
applications inside the stack use `db:3306`. For database administration:

```sh
docker compose exec db mariadb -uroot -p
```

The development root password is `superduperroot`. Initial database credentials
apply when MariaDB creates a new database directory, not to existing databases.

- Application files live in `www/`.
- MariaDB data lives in `dbdata/`; `iedata/` is available for import/export files.
- HedgeDoc's SQLite database and uploads live in the `hedgedoc_public` named volume.
- Apache and PHP logs live under `log/`; other service logs use `docker compose logs`.

Stopping or recreating containers preserves this data. Back it up before removing
data directories or volumes; `docker compose down -v` deletes named volumes.

## File permissions

On native Linux without user remapping, setup creates application files as the
owner of `www/`, and PHP-FPM workers use that directory's numeric UID/GID. Creating
`www/` yourself avoids Docker creating it as root. Setup and PHP startup check
write access but do not repair existing file ownership or permissions.

`docker compose exec` and Node commands run as root by default and can create
root-owned files on native Linux. For PHP CLI commands, you can use your host
identity, for example:

```sh
docker compose exec --user "$(id -u):$(id -g)" -w /srv/sandboxer/laravel php php artisan about
```

Docker Desktop and rootless Docker use different ownership mappings and have not
been validated here. If the mount reports UID 0, PHP tries non-root `nobody`
workers and fails startup if they cannot write. There is no universal guarantee
that host permissions need no attention.

For Sandboxer maintenance and validation, see [CONTRIBUTING.md](CONTRIBUTING.md).
