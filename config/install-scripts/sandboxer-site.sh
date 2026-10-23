#!/bin/sh
set -eu

# Install the Sandboxer landing page linking to the other local services.

root=${SANDBOXER_ROOT:-/srv/sandboxer}
template=${DEFAULT_TEMPLATE:-/opt/default}
destination="$root/default"

# Do not follow a developer-provided link or replace a conflicting file.
if [ -L "$destination" ] || { [ -e "$destination" ] && [ ! -d "$destination" ]; }; then
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
