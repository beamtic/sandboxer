# Shared base: Alpine and the PHP packages needed by the build stages and setup.
# AS names a stage so later FROM and COPY instructions can refer to it.
FROM alpine:3.24.2 AS setup-base
RUN apk add --no-cache \
        shadow bash \
        "php85>=8.5.12" php85-ctype php85-curl php85-dom php85-fileinfo \
        php85-mbstring php85-openssl php85-pdo_sqlite php85-session \
        php85-tokenizer php85-xml php85-xmlwriter php85-phar php85-zip \
        php85-pcntl php85-posix

# Download and verify phpMyAdmin at build time. Only the extracted application
# is copied into the final image; download/extraction tools stay in this stage.
FROM alpine:3.24.2 AS phpmyadmin-template
RUN apk add --no-cache curl unzip
# Official all-languages ZIP checksum; update alongside the pinned version.
# https://files.phpmyadmin.net/phpMyAdmin/5.2.3/phpMyAdmin-5.2.3-all-languages.zip.sha256
RUN curl -fsSLo /tmp/phpmyadmin.zip https://files.phpmyadmin.net/phpMyAdmin/5.2.3/phpMyAdmin-5.2.3-all-languages.zip \
    && echo '2d2e13c735366d318425c78e4ee2cc8fc648d77faba3ddea2cd516e43885733f  /tmp/phpmyadmin.zip' | sha256sum -c - \
    && unzip -q /tmp/phpmyadmin.zip -d /opt \
    && mv /opt/phpMyAdmin-5.2.3-all-languages /opt/phpmyadmin \
    && test -f /opt/phpmyadmin/index.php \
    && rm /tmp/phpmyadmin.zip

# Pin the official WordPress archive and verify its locally recorded SHA-256.
# Downloads stay in this build stage; runtime setup only copies prepared files.
FROM alpine:3.24.2 AS wordpress-template
RUN apk add --no-cache curl
RUN curl -fsSLo /tmp/wordpress.tar.gz https://wordpress.org/wordpress-7.1.3.tar.gz \
    && echo 'd2a09acb6a15e3b9c471d72557753c266d6f41a79ed19bfe04cbfe49e283b2a5  /tmp/wordpress.tar.gz' | sha256sum -c - \
    && mkdir -p /opt \
    && tar -xzf /tmp/wordpress.tar.gz -C /opt \
    && test -f /opt/wordpress/wp-settings.php \
    && rm /tmp/wordpress.tar.gz

# Start from setup-base and prepare the clean Laravel example in /opt/laravel.
# Build it once so first-run setup needs no Composer or Laravel download.
FROM setup-base AS laravel-template
RUN apk add --no-cache curl unzip
RUN curl -fsSLo /usr/local/bin/composer https://getcomposer.org/download/2.10.3/composer.phar && \
    echo '7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6  /usr/local/bin/composer' | sha256sum -c -
# Official laravel/laravel skeleton v13.10.1; update hash and dependency lock together.
RUN curl -fsSLo /tmp/laravel.zip https://codeload.github.com/laravel/laravel/zip/refs/tags/v13.10.1 && \
    echo '0369aaebb8083eaa0a1763a6ae44248fa04d1fd15de9124f186cd962e0f84caa  /tmp/laravel.zip' | sha256sum -c - && \
    unzip -q /tmp/laravel.zip -d /opt && \
    mv /opt/laravel-13.10.1 /opt/laravel && rm /tmp/laravel.zip
WORKDIR /opt/laravel
COPY ./config/laravel/composer.lock ./composer.lock
RUN COMPOSER_ALLOW_SUPERUSER=1 php85 /usr/local/bin/composer install \
    --prefer-dist --no-interaction --no-progress --no-scripts --no-plugins && \
    php85 /usr/local/bin/composer check-platform-reqs
COPY ./config/laravel/vite.config.js ./vite.config.js

# Inherit laravel-template to reuse its PHP, Composer, and download tools.
# Inheritance makes the entire earlier filesystem available here, including
# /opt/laravel. That example is not copied into or used to create Profundarium.
# Instead, fetch Profundarium's own source from the remote repository below
# at a pinned commit, then install its dependencies in /opt/profundarium.
FROM laravel-template AS profundarium-template
RUN apk add --no-cache git
# Main-branch snapshot for new installs; existing local checkouts are untouched.
# Profundarium v0.3.0, including MySQL/MariaDB media support.
ARG PROFUNDARIUM_REF=8605fd8923a764f54f70b1af78573846348a0d4a
WORKDIR /opt/profundarium
RUN git init . && git remote add origin https://github.com/beamtic/Profundarium.git \
    && git fetch --depth=1 origin "${PROFUNDARIUM_REF}" \
    && git checkout -b main FETCH_HEAD \
    && git update-ref refs/remotes/origin/main HEAD \
    && git branch --set-upstream-to=origin/main main
RUN COMPOSER_ALLOW_SUPERUSER=1 php85 /usr/local/bin/composer install \
    --prefer-dist --no-interaction --no-progress --no-scripts --no-plugins

# Final setup image: start from the shared base, not a template stage.
# Copy only the prepared applications below; Composer, Git, curl, and unzip
# stay in the build stages. The setup scripts install missing apps into www/.
FROM setup-base
# Run bind-mount setup with its numeric owner; no passwd/group entries needed.
RUN apk add --no-cache su-exec
COPY ./config/install-scripts/setup-entrypoint.sh /setup-entrypoint.sh
COPY --from=wordpress-template /opt/wordpress /opt/wordpress
COPY --from=phpmyadmin-template /opt/phpmyadmin /opt/phpmyadmin
COPY --from=laravel-template /opt/laravel /opt/laravel
COPY --from=profundarium-template /opt/profundarium /opt/profundarium
COPY ./config/install-scripts/phpmyadmin.sh /phpmyadmin.sh
COPY ./config/install-scripts/wordpress.sh /wordpress.sh
COPY ./config/install-scripts/laravel.sh /laravel.sh
COPY ./config/install-scripts/profundarium.sh /profundarium.sh
COPY ./config/install-scripts/setup.sh /setup.sh
COPY ./config/install-scripts/sandboxer-site.sh /sandboxer-site.sh
COPY ./config/host/default/ /opt/default/
COPY ./config/host/phpMyAdmin/config.inc.php /
ENTRYPOINT ["/bin/sh", "/setup-entrypoint.sh"]
CMD ["/bin/sh", "/setup.sh"]
