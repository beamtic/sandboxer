"""Check setup's file ownership and startup failures using real Docker containers.

Verifies that newly installed application files belong to the mount owner,
including numeric IDs without user accounts. Also checks that unwritable or
missing mounts and mismatched non-root identities fail before installation.
Uses disposable container filesystems with networking disabled, not host data.
Build first: docker compose build setup
Run: python3 tests/check_setup_ownership.py
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

    # Verify real installers create editable files as the mounted directory owner,
    # without needing a matching user account inside the image.
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
for path in default/index.php phpmyadmin/index.php phpmyadmin/config.inc.php wordpress/wp-config.php wordpress/wp-settings.php laravel/.env laravel/database/database.sqlite profundarium/.env profundarium/.git/HEAD; do
    test "$(stat -c %u:%g /srv/sandboxer/$path)" = 12345:23456
    test -w /srv/sandboxer/$path
done
'
"""])
        self.assert_success(result)
        self.assertIn('mount owner 12345:23456', result.stdout)

    # Check the entrypoint accepts container UID 0 when it owns the mount.
    # User namespaces can map that ID to an unprivileged host user.
    def test_uid_zero_is_accepted(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer'],
            ['/bin/sh', '-c', 'test "$(id -u)" = 0 && touch /srv/sandboxer/created'])
        self.assert_success(result)

    # If setup already runs as the mount owner, it should work without attempting
    # a privilege change that would require root.
    def test_already_matching_nonroot_identity_is_accepted(self):
        result = self.run_container(
            ['--user', '12345:23456', '--tmpfs', '/srv/sandboxer:uid=12345,gid=23456'],
            ['/bin/sh', '-c', 'touch /srv/sandboxer/created'])
        self.assert_success(result)

    # Defensive configuration check: an invalid application path must stop setup
    # before any installation command runs.
    def test_missing_or_non_directory_fails_before_command(self):
        for root in ['/missing-directory', '/etc/alpine-release']:
            with self.subTest(root=root):
                result = self.run_container(
                    ['-e', 'SANDBOXER_ROOT=' + root], ['echo', 'COMMAND_RAN'])
                self.assert_failure_before_command(result, 'missing or not a directory')

    # A read-only bind mount cannot accept installed files, even from root.
    # Report that problem before running installers.
    def test_readonly_mount_fails_even_for_root(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer:ro'], ['echo', 'COMMAND_RAN'])
        self.assert_failure_before_command(result, 'cannot write')

    # Directory ownership alone does not guarantee write permission.
    # Detect an unwritable directory before running installers.
    def test_owner_without_write_permission_fails(self):
        result = self.run_container(
            ['--tmpfs', '/srv/sandboxer', '--entrypoint', '/bin/sh'],
            ['-c', 'chown 12345:23456 /srv/sandboxer && chmod 500 /srv/sandboxer && '
             'exec /bin/sh /setup-entrypoint.sh echo COMMAND_RAN'])
        self.assert_failure_before_command(result, 'cannot write')

    # Defensive configuration check: a non-root process cannot switch to another
    # mount owner; fail rather than create files with unexpected ownership.
    def test_nonroot_identity_mismatch_fails(self):
        result = self.run_container(
            ['--user', '12345:23456', '--tmpfs', '/srv/sandboxer'],
            ['echo', 'COMMAND_RAN'])
        self.assert_failure_before_command(result, 'start setup as root')


if __name__ == '__main__':
    unittest.main(verbosity=2)
