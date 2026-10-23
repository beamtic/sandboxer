#!/bin/sh
set -eu
root=${SANDBOXER_ROOT:-/srv/sandboxer}
template=${WORDPRESS_TEMPLATE:-/opt/wordpress}
target="$root/wordpress"

# Preserve existing applications, including developer-managed symlinks.
if [ -e "$target" ] || [ -L "$target" ]; then
    echo 'WordPress already exists; leaving it unchanged.'
    exit 0
fi
test -f "$template/wp-settings.php"
test -f "$template/wp-config-sample.php"
mkdir -p "$root"
staging=$(mktemp -d "$root/.wordpress-setup.XXXXXX")
trap 'rm -rf "$staging"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$staging/app"
cp -R "$template/." "$staging/app/"
# Generate independent secrets locally; no network or database access is needed.
php85 -r '
$config = file_get_contents($argv[1] . "/wp-config-sample.php");
// Store environment lookups rather than embedding development credentials.
$settings = ["database_name_here" => "WORDPRESS_DB_NAME", "username_here" => "WORDPRESS_DB_USER",
             "password_here" => "WORDPRESS_DB_PASSWORD", "localhost" => "MYSQL_HOST"];
$config = str_replace(
    array_map(fn($key) => var_export($key, true), array_keys($settings)),
    array_map(fn($name) => "getenv(" . var_export($name, true) . ")", array_values($settings)),
    $config);
$config = preg_replace_callback("/put your unique phrase here/", fn() => bin2hex(random_bytes(32)), $config);
if (file_put_contents($argv[1] . "/wp-config.php", $config) === false) { exit(1); }
' "$staging/app"
if [ -e "$target" ] || [ -L "$target" ]; then
    echo 'WordPress destination appeared during setup; refusing to replace it.' >&2
    exit 1
fi
mv -T "$staging/app" "$target"
echo 'WordPress files ready. Finish installation at http://wordpress.localhost.'
