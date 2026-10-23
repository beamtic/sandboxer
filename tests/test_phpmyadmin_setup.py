"""Test phpMyAdmin's installer without Docker or downloads.

Checks fresh installation, preservation of existing files, rejection of symlink
destinations, and cleanup after failures.
All files are temporary fixtures; your installed phpMyAdmin is never touched.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/install-scripts/phpmyadmin.sh'


class SetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / 'sandbox'
        self.destination.mkdir()
        self.config = self.root / 'config.inc.php'
        self.config.write_text('<?php // fixture\n')
        self.template = self.root / 'template'
        self.template.mkdir()
        (self.template / 'index.php').write_text('<?php // prepared app\n')
        binaries = self.root / 'bin'
        binaries.mkdir()
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.destination),
                        PHPMYADMIN_CONFIG=str(self.config),
                        PHPMYADMIN_TEMPLATE=str(self.template),
                        PATH=str(binaries) + os.pathsep + os.environ['PATH'])

    def run_setup(self):
        result = subprocess.run(['sh', str(SCRIPT)], env=self.env,
                                capture_output=True, text=True)
        self.assertFalse(list(self.destination.glob('.phpmyadmin-setup.*')))
        return result

    def assert_failed(self):
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    # Normal startup: install once, then preserve developer edits on later starts.
    # Even a missing source configuration must not trigger a reinstall.
    def test_success_and_repeat_preserves_changes(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        app = self.destination / 'phpmyadmin'
        self.assertEqual((app / 'config.inc.php').read_bytes(), self.config.read_bytes())
        (app / 'index.php').write_text('developer edit')
        self.config.unlink()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((app / 'index.php').read_text(), 'developer edit')

    # Defensive check for an incomplete setup image: fail without publishing an app,
    # then allow installation once the missing template file is restored.
    def test_missing_template_then_retry(self):
        index = self.template / 'index.php'
        index.unlink()
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())
        index.write_text('<?php\n')
        self.assertEqual(self.run_setup().returncode, 0)

    # Defensive check for a missing bundled config: do not leave an apparently
    # installed phpMyAdmin that has never received its database configuration.
    def test_missing_configuration(self):
        self.config.unlink()
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())

    # Simulate a failed file copy, such as a disk or permission error.
    # The destination must remain absent so the next startup can retry.
    def test_template_copy_failure(self):
        cp = self.root / 'bin/cp'
        # Shadow cp through PATH to simulate a failed application-file copy.
        cp.write_text('#!/bin/sh\nexit 1\n')
        cp.chmod(0o755)
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())
        self.assertTrue(self.config.exists())

    # Simulate failure after application files copied but before configuration did.
    # Setup must discard that incomplete installation rather than publish it.
    def test_configuration_copy_failure(self):
        cp = self.root / 'bin/cp'
        # Let application copying succeed, then fail only the configuration copy.
        cp.write_text('#!/bin/sh\n[ "$1" != "$PHPMYADMIN_CONFIG" ] || exit 1\nexec /bin/cp "$@"\n')
        cp.chmod(0o755)
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())

    # An existing directory belongs to the developer.
    # Setup must leave its files alone and report success.
    def test_existing_installation_is_preserved(self):
        installed = self.destination / 'phpmyadmin'
        installed.mkdir()
        existing = installed / 'keep.txt'
        existing.write_text('existing data')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(existing.read_text(), 'existing data')

    # Reject a symlink at www/phpmyadmin, whether valid or broken, with a clear error.
    # Leave both the link and its target untouched for the developer to resolve.
    def test_destination_symlink_is_rejected(self):
        self.destination.mkdir(exist_ok=True)
        target = self.destination / 'phpmyadmin'
        for name in ('missing', 'existing'):
            with self.subTest(destination=name):
                destination = self.root / name
                if name == 'existing':
                    destination.mkdir()
                    (destination / 'keep.txt').write_text('developer files')
                target.symlink_to(destination)
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('www/phpmyadmin is a symlink', result.stderr)
                self.assertTrue(target.is_symlink())
                if name == 'existing':
                    self.assertEqual(list(destination.iterdir()), [destination / 'keep.txt'])
                    self.assertEqual((destination / 'keep.txt').read_text(), 'developer files')
                else:
                    self.assertFalse(destination.exists())
                target.unlink()


if __name__ == '__main__':
    unittest.main()
