"""Offline checks for installing the prepared phpMyAdmin template safely."""
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
        self.assertFalse((self.destination / 'setup-completed').exists())
        return result

    def test_success_and_repeat_preserves_changes(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.destination / 'setup-completed').exists())
        app = self.destination / 'phpmyadmin'
        self.assertEqual((app / 'config.inc.php').read_bytes(), self.config.read_bytes())
        (app / 'index.php').write_text('developer edit')
        self.config.unlink()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((app / 'index.php').read_text(), 'developer edit')

    def test_obsolete_marker_does_not_skip_missing_installation(self):
        marker = self.destination / 'setup-completed'
        marker.write_text('legacy marker')
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.destination / 'phpmyadmin/index.php').is_file())
        self.assertEqual(marker.read_text(), 'legacy marker')

    def test_missing_template_then_retry(self):
        index = self.template / 'index.php'
        index.unlink()
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())
        index.write_text('<?php\n')
        self.assertEqual(self.run_setup().returncode, 0)

    def test_missing_configuration(self):
        self.config.unlink()
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())

    def test_template_copy_failure(self):
        cp = self.root / 'bin/cp'
        cp.write_text('#!/bin/sh\nexit 1\n')
        cp.chmod(0o755)
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())
        self.assertTrue(self.config.exists())

    def test_configuration_copy_failure(self):
        cp = self.root / 'bin/cp'
        cp.write_text('#!/bin/sh\n[ "$1" != "$PHPMYADMIN_CONFIG" ] || exit 1\nexec /bin/cp "$@"\n')
        cp.chmod(0o755)
        self.assert_failed()
        self.assertFalse((self.destination / 'phpmyadmin').exists())

    def test_existing_installation_without_marker_is_preserved(self):
        installed = self.destination / 'phpmyadmin'
        installed.mkdir()
        existing = installed / 'keep.txt'
        existing.write_text('existing data')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(existing.read_text(), 'existing data')

    def test_existing_symlink_is_preserved(self):
        installed = self.destination / 'phpmyadmin'
        installed.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertTrue(installed.is_symlink())


if __name__ == '__main__':
    unittest.main()
