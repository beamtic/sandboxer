#!/bin/sh
set -eu
root=${SANDBOXER_ROOT:-/srv/sandboxer}
template=${PROFUNDARIUM_TEMPLATE:-/opt/profundarium}
target="$root/profundarium"

# Existing source checkouts belong to the developer; never reinstall or upgrade.
if [ -e "$target" ] || [ -L "$target" ]; then
    echo 'Profundarium already exists; leaving it unchanged.'
    exit 0
fi
test -f "$template/artisan"
test -f "$template/vendor/autoload.php"
staging=$(mktemp -d "$root/.profundarium-setup.XXXXXX")
trap 'rm -rf "$staging"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$staging/app"
cp -R "$template/." "$staging/app/"
cd "$staging/app"
cp .env.example .env
sed -i \
    -e 's|^APP_URL=.*|APP_URL=http://hedgedoc.localhost|' \
    -e 's|^HEDGEDOC_URL=.*|HEDGEDOC_URL=http://hedgedoc:3000|' \
    -e 's|^HEDGEDOC_PUBLIC_URL=.*|HEDGEDOC_PUBLIC_URL=http://hedgedoc.localhost|' \
    -e 's|^HEDGEDOC_UPLOADS_PATH=.*|HEDGEDOC_UPLOADS_PATH=/hedgedoc/public/uploads|' \
    -e 's|^HEDGEDOC_DB_CONNECTION=.*|HEDGEDOC_DB_CONNECTION=sqlite|' \
    -e 's|^HEDGEDOC_DB_DATABASE=.*|HEDGEDOC_DB_DATABASE=/hedgedoc/public/hedgedoc.sqlite|' .env
php85 artisan package:discover --no-interaction
php85 artisan key:generate --force --no-interaction
if [ -e "$target" ] || [ -L "$target" ]; then
    echo 'Profundarium destination appeared during setup; refusing to replace it.' >&2
    exit 1
fi
mv -T "$staging/app" "$target"
echo 'Profundarium installed at http://hedgedoc.localhost/profundarium/.'
