#!/bin/sh
set -eu

# Install the Sandboxer landing page linking to the other local services.

root=${SANDBOXER_ROOT:-/srv/sandboxer}
template=${DEFAULT_TEMPLATE:-/opt/default}
destination="$root/default"

# Symlinks are not supported as installation destinations; leave removal to the user.
if [ -L "$destination" ]; then
    echo 'www/default is a symlink. Remove it or configure a bind mount before installing.' >&2
    exit 1
fi

# Do not replace a conflicting file.
if [ -e "$destination" ] && [ ! -d "$destination" ]; then
    echo "Default site destination is not a regular directory; leaving it unchanged."
    exit 0
fi

mkdir -p "$destination"
for name in index.php beamtic-sandboxer.png; do
    if [ -e "$destination/$name" ] || [ -L "$destination/$name" ]; then
        continue
    fi
    # BusyBox cp -n also prevents replacing a file created after the check.
    cp -n "$template/$name" "$destination/$name"
done
echo "Sandboxer landing page copied where missing."
