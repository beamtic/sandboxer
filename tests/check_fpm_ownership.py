"""Check PHP-FPM worker permissions using real requests in disposable containers.

Verifies worker identities and ownership of files created by PHP, including the
fallback for root-owned mounts and failure when non-root workers cannot write.
Uses temporary container filesystems and no networking outside the container;
it does not touch your applications or validate Docker Desktop/rootless mappings.
Build first: docker compose build php
Run: python3 tests/check_fpm_ownership.py
"""
import os
import subprocess
import unittest

IMAGE = os.environ.get('SANDBOXER_PHP_IMAGE', 'sandboxer-php')


class FpmOwnershipTests(unittest.TestCase):
    def run_container(self, mount, script):
        return subprocess.run([
            'docker', 'run', '--rm', '--network', 'none',
            '--add-host', 'php:127.0.0.1', '--tmpfs', mount,
            '--entrypoint', '/bin/sh', IMAGE, '-c', script,
        ], capture_output=True, text=True, timeout=30)

    def check_worker(self, mount, identity):
        result = self.run_container(mount, r'''
set -eu
cat > /srv/sandboxer/probe.php <<'PHP'
<?php
file_put_contents('/srv/sandboxer/created', 'test');
echo 'WORKER=' . posix_geteuid() . ':' . posix_getegid() . "\n";
echo 'CONFIG_WRITABLE=' . (int) is_writable('/etc/php85/php.ini') . "\n";
PHP
/bin/sh /usr/local/bin/php-fpm-entrypoint php-fpm85 -F &
fpm=$!
trap 'kill "$fpm" 2>/dev/null || true; wait "$fpm" 2>/dev/null || true' EXIT
for i in $(seq 1 50); do
    if /bin/sh /usr/local/bin/php-fpm-healthcheck 2>/dev/null; then break; fi
    kill -0 "$fpm"
    sleep 0.1
done
env -i SCRIPT_FILENAME=/srv/sandboxer/probe.php REQUEST_METHOD=GET \
    cgi-fcgi -bind -connect php:9000
stat -c 'OWNER=%u:%g' /srv/sandboxer/created
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('WORKER=' + identity, result.stdout)
        self.assertIn('OWNER=' + identity, result.stdout)
        self.assertIn('CONFIG_WRITABLE=0', result.stdout)

    # Verify a real PHP request writes files as the mount owner, even when that
    # numeric identity has no named account; container config remains unwritable.
    def test_numeric_owner_without_user_account(self):
        self.check_worker('/srv/sandboxer:uid=12345,gid=23456,mode=0755', '12345:23456')

    # Exercise the UID-0 fallback with a deliberately writable temporary mount.
    # Workers must use nobody, not root; this does not emulate Docker Desktop.
    def test_root_owned_shared_mount_uses_nobody(self):
        self.check_worker('/srv/sandboxer:uid=0,gid=0,mode=0777', '65534:65534')

    # Check root-owned, permission-restricted, and read-only mounts fail startup
    # when the selected non-root worker cannot write application files.
    def test_unwritable_mounts_fail(self):
        for mount in ['/srv/sandboxer:uid=0,gid=0,mode=0755',
                      '/srv/sandboxer:uid=12345,gid=23456,mode=0555',
                      '/srv/sandboxer:uid=12345,gid=23456,ro']:
            with self.subTest(mount=mount):
                result = self.run_container(mount,
                    'exec /bin/sh /usr/local/bin/php-fpm-entrypoint php-fpm85 -tt')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('cannot write', result.stderr)

    # Defensive configuration check: fail clearly if the application directory
    # is absent rather than start PHP-FPM against an invalid path.
    def test_missing_mount_fails(self):
        result = self.run_container('/srv',
            'cd / && rmdir /srv/sandboxer && exec /bin/sh /usr/local/bin/php-fpm-entrypoint php-fpm85 -tt')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing or not a directory', result.stderr)

    # Composer, Artisan, and other CLI commands do not start FPM workers.
    # They must remain usable without the FPM application-mount checks.
    def test_cli_bypasses_fpm_setup(self):
        result = self.run_container('/srv',
            'exec /bin/sh /usr/local/bin/php-fpm-entrypoint php -r \'echo "CLI_OK";\'')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'CLI_OK')


if __name__ == '__main__':
    unittest.main()
