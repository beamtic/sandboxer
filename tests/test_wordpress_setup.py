"""Test WordPress file installation without Docker, WordPress, or MariaDB.

Checks fresh setup, preservation of existing files, rejection of symlink
destinations, and cleanup so failed installations can be retried. A fake PHP
command simulates configuration generation; it does not validate WordPress or its
database. Only temporary fixtures are changed, never your local installation.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/install-scripts/wordpress.sh'


class WordPressSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / 'www'
        self.destination.mkdir()
        self.template = self.root / 'template'
        self.template.mkdir()
        for name in ('wp-settings.php', 'wp-config-sample.php'):
            (self.template / name).write_text('<?php // fixture')
        self.binaries = self.root / 'bin'
        self.binaries.mkdir()
        self.php = self.binaries / 'php85'
        # Simulate configuration generation; the Docker ownership checks use real PHP.
        self.php.write_text('#!/bin/sh\nprintf config > "$3/wp-config.php"\n')
        self.php.chmod(0o755)
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.destination),
                        WORDPRESS_TEMPLATE=str(self.template),
                        PATH=str(self.binaries) + os.pathsep + os.environ['PATH'])

    def run_setup(self):
        result = subprocess.run(['sh', str(SCRIPT)], env=self.env,
                                capture_output=True, text=True)
        self.assertFalse(list(self.destination.glob('.wordpress-setup.*')))
        return result

    # Normal startup: prepare the WordPress files and configuration once.
    # Later starts must preserve the developer's existing configuration.
    def test_success_and_repeat_preserves_work(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.destination / 'wordpress/wp-config.php'
        config.write_text('custom configuration')
        self.php.unlink()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(config.read_text(), 'custom configuration')

    # Reject a symlink at www/wordpress, whether valid or broken, with a clear error.
    # Leave both the link and its target untouched for the developer to resolve.
    def test_destination_symlink_is_rejected(self):
        self.destination.mkdir(exist_ok=True)
        target = self.destination / 'wordpress'
        for name in ('missing', 'existing'):
            with self.subTest(destination=name):
                destination = self.root / name
                if name == 'existing':
                    destination.mkdir()
                    (destination / 'keep.txt').write_text('developer files')
                target.symlink_to(destination)
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('www/wordpress is a symlink', result.stderr)
                self.assertTrue(target.is_symlink())
                if name == 'existing':
                    self.assertEqual(list(destination.iterdir()), [destination / 'keep.txt'])
                    self.assertEqual((destination / 'keep.txt').read_text(), 'developer files')
                else:
                    self.assertFalse(destination.exists())
                target.unlink()

    # Defensive check for an incomplete setup image: missing WordPress files
    # must cause failure without publishing an application directory.
    def test_missing_template_is_not_published(self):
        (self.template / 'wp-settings.php').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        self.assertFalse((self.destination / 'wordpress').exists())

    # Simulate PHP failing to generate wp-config.php. The partial application
    # must be discarded so the next attempt can install it successfully.
    def test_configuration_failure_can_retry(self):
        command = self.php.read_text()
        self.php.write_text('#!/bin/sh\nexit 1\n')
        self.assertNotEqual(self.run_setup().returncode, 0)
        self.assertFalse((self.destination / 'wordpress').exists())
        self.php.write_text(command)
        self.assertEqual(self.run_setup().returncode, 0)


if __name__ == '__main__':
    unittest.main()
