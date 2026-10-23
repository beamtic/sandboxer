"""Docker integration checks: build setup, then python3 tests/check_setup_ownership.py.

Uses only disposable container filesystems, with networking disabled.
"""
import os
import subprocess
import unittest

IMAGE = os.environ.get('SANDBOXER_SETUP_IMAGE', 'sandboxer-setup')


class SetupOwnershipTests(unittest.TestCase):
    def run_container(self, options=(), command=()):
        result = subprocess.run(
            ['docker', 'run', '--rm', '--network', 'none', *options, IMAGE, *command],
            capture_output=True, text=True, timeout=60)
        return result

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_failure_before_command(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn('COMMAND_RAN', result.stdout)

    def test_numeric_owner_without_passwd_entry_creates_real_apps(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer', '--entrypoint', '/bin/sh'],
            ['-c', """
set -eu
chown 12345:23456 /srv/sandboxer
exec /bin/sh /setup-entrypoint.sh /bin/sh -c '
set -eu
test "$(id -u):$(id -g)" = 12345:23456
/bin/sh /setup.sh
for path in default/index.php phpmyadmin/index.php phpmyadmin/config.inc.php setup-completed laravel/.env laravel/database/database.sqlite profundarium/.env profundarium/.git/HEAD; do
    test "$(stat -c %u:%g /srv/sandboxer/$path)" = 12345:23456
    test -w /srv/sandboxer/$path
done
'
"""])
        self.assert_success(result)
        self.assertIn('mount owner 12345:23456', result.stdout)

    def test_uid_zero_is_accepted(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer'],
            ['/bin/sh', '-c', 'test "$(id -u)" = 0 && touch /srv/sandboxer/created'])
        self.assert_success(result)

    def test_already_matching_nonroot_identity_is_accepted(self):
        result = self.run_container(
            ['--user', '12345:23456', '--tmpfs', '/srv/sandboxer:uid=12345,gid=23456'],
            ['/bin/sh', '-c', 'touch /srv/sandboxer/created'])
        self.assert_success(result)

    def test_missing_or_non_directory_fails_before_command(self):
        for root in ['/missing-directory', '/etc/alpine-release']:
            with self.subTest(root=root):
                result = self.run_container(
                    ['-e', 'SANDBOXER_ROOT=' + root], ['echo', 'COMMAND_RAN'])
                self.assert_failure_before_command(result, 'missing or not a directory')

    def test_readonly_mount_fails_even_for_root(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer:ro'], ['echo', 'COMMAND_RAN'])
        self.assert_failure_before_command(result, 'cannot write')

    def test_owner_without_write_permission_fails(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer', '--entrypoint', '/bin/sh'],
            ['-c', 'chown 12345:23456 /srv/sandboxer && chmod 500 /srv/sandboxer && '
             'exec /bin/sh /setup-entrypoint.sh echo COMMAND_RAN'])
        self.assert_failure_before_command(result, 'cannot write')

    def test_nonroot_identity_mismatch_fails(self):
        result = self.run_container(
            ['--user', '12345:23456', '--tmpfs', '/srv/sandboxer'],
            ['echo', 'COMMAND_RAN'])
        self.assert_failure_before_command(result, 'start setup as root')


if __name__ == '__main__':
    unittest.main(verbosity=2)
