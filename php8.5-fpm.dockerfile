FROM alpine:3.24.2
RUN apk add --no-cache \
        bash \
        shadow \
        su-exec \
        curl \
        "php85>=8.5.12" \
        "php85-fpm>=8.5.12" \
        fcgi \
        sqlite \
        php85-pdo_sqlite \
        php85-pdo_pgsql \
        imagemagick \
        imagemagick-pdf \
        imagemagick-jpeg \
        imagemagick-raw \
        imagemagick-tiff \
        imagemagick-heic \
        imagemagick-webp \
        imagemagick-svg

# PHP extensions (OPcache is built into PHP 8.5).
RUN apk add --no-cache \
        php85-session \
        php85-posix \
        php85-ctype \
        php85-pecl-imagick \
        php85-fileinfo \
        php85-dom \
        php85-xml \
        php85-sodium \
        php85-simplexml \
        php85-curl \
        php85-xmlwriter \
        php85-xmlreader \
        php85-bcmath \
        php85-exif \
        php85-ftp \
        php85-gd \
        php85-gmp \
        php85-intl \
        php85-ldap \
        php85-pecl-redis \
        php85-pcntl \
        php85-mysqli \
        php85-pdo_mysql \
        php85-mbstring \
        php85-sysvsem \
        php85-zip \
        php85-phar \
        php85-openssl \
        php85-tokenizer

COPY ./config/php85/php-fpm.d/www.conf /etc/php85/php-fpm.d/www.conf
COPY ./config/php85/php.ini /etc/php85/php.ini
COPY ./config/php85/healthcheck.sh /usr/local/bin/php-fpm-healthcheck
COPY ./config/php85/entrypoint.sh /usr/local/bin/php-fpm-entrypoint

RUN mkdir -p /srv/sandboxer && \
    chmod -R 775 /srv/sandboxer

WORKDIR /srv/sandboxer

# Keep the version and SHA-256 from https://getcomposer.org/download/ in sync.
RUN curl -fsSLo /usr/local/bin/composer https://getcomposer.org/download/2.10.3/composer.phar && \
    echo '7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6  /usr/local/bin/composer' | sha256sum -c - && \
    chmod 755 /usr/local/bin/composer

# Ensure PHP-FPM runs in the foreground
ENTRYPOINT ["/bin/sh", "/usr/local/bin/php-fpm-entrypoint"]
CMD ["php-fpm85", "-F"]
