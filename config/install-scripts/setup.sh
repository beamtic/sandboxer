#!/bin/sh
set -eu
/bin/sh /sandboxer-site.sh
/bin/sh /phpmyadmin.sh
/bin/sh /laravel.sh
/bin/sh /profundarium.sh
/bin/sh /wordpress.sh
