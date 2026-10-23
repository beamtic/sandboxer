#!/bin/sh
set -eu

destination=${SANDBOXER_ROOT:-/srv/sandboxer}
configuration=${PHPMYADMIN_CONFIG:-/config.inc.php}
template=${PHPMYADMIN_TEMPLATE:-/opt/phpmyadmin}

if [ -f "$destination/setup-completed" ]; then
    echo "Setup not requested... Exiting setup..."
    exit 0
fi

echo "Running setup..."

# Preserve existing installations instead of merging a retry into their files.
if [ -e "$destination/phpmyadmin" ] || [ -L "$destination/phpmyadmin" ]; then
    echo "phpmyadmin exists without a completion marker; inspect it before retrying." >&2
    exit 1
fi

test -f "$configuration"
test -f "$template/index.php"
mkdir -p "$destination"
staging=$(mktemp -d "$destination/.phpmyadmin-setup.XXXXXX")
# Remove temporary files when the shell exits, whether setup succeeds or fails.
trap 'rm -rf "$staging"' EXIT
# On hangup (HUP), Ctrl+C (INT), or a termination request (TERM), exit with
# failure status 1. This also triggers the EXIT cleanup above.
# Forced termination (SIGKILL) or power loss cannot be caught for cleanup.
trap 'exit 1' HUP INT TERM

# The image already contains the verified application. Stage a complete install
# beside its destination so a failed copy never publishes partial files.
mkdir "$staging/app"
cp -R "$template/." "$staging/app/"
cp "$configuration" "$staging/app/config.inc.php"
if [ -e "$destination/phpmyadmin" ] || [ -L "$destination/phpmyadmin" ]; then
    echo "phpmyadmin appeared during setup; refusing to replace it." >&2
    exit 1
fi
mv -T "$staging/app" "$destination/phpmyadmin"
touch "$destination/setup-completed"
echo "Setup complete."
