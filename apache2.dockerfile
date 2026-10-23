FROM alpine:3.24.2
RUN apk add --no-cache \
        shadow \
        apache2 \
        apache2-proxy \
        apache2-webdav \
        apache-mod-fcgid \
		apache2-brotli \
        bash


# Load the generic localhost site first so it remains the fallback virtual host.
COPY ./config/apache2/conf.d/sandboxer.conf /etc/apache2/conf.d/000-sandboxer.conf
COPY ./config/apache2/conf.d/wordpress.conf /etc/apache2/conf.d/wordpress.conf
COPY ./config/apache2/conf.d/laravel.conf /etc/apache2/conf.d/laravel.conf
COPY ./config/apache2/conf.d/phpmyadmin.conf /etc/apache2/conf.d/phpmyadmin.conf
COPY ./config/apache2/conf.d/hedgedoc.conf /etc/apache2/conf.d/hedgedoc.conf
COPY ./config/apache2/conf.d/mpm.conf /etc/apache2/conf.d/mpm.conf
COPY ./config/apache2/httpd.conf /etc/apache2/httpd.conf

RUN mkdir -p /srv/sandboxer && \
    chmod -R 775 /srv/sandboxer
	
WORKDIR /srv/sandboxer

# Ensure Apache runs in the foreground
CMD ["httpd", "-D", "FOREGROUND"]