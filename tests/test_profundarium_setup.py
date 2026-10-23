"""Test Profundarium's first-run installer without a real application or database.

Checks the generated local URLs and MariaDB settings, preservation of existing
checkouts, rejection of symlink destinations, and cleanup/retry when initialization fails. A small fake PHP command
simulates Artisan success or failure; these tests do not test Laravel itself.
All files are created in temporary directories, outside your www/ checkout.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/install-scripts/profundarium.sh'


class ProfundariumSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.apps = self.root / 'www'
        self.apps.mkdir()
        self.template = self.root / 'template'
        (self.template / 'vendor').mkdir(parents=True)
        (self.template / '.git').mkdir()
        (self.template / 'artisan').write_text('fixture')
        (self.template / 'vendor/autoload.php').write_text('fixture')
        keys = ['APP_URL', 'HEDGEDOC_URL', 'HEDGEDOC_PUBLIC_URL',
                'HEDGEDOC_UPLOADS_PATH', 'HEDGEDOC_DB_CONNECTION', 'HEDGEDOC_DB_DATABASE',
                'HEDGEDOC_DB_HOST', 'HEDGEDOC_DB_PORT', 'HEDGEDOC_DB_USERNAME', 'HEDGEDOC_DB_PASSWORD']
        (self.template / '.env.example').write_text(''.join(f'{key}=old\n' for key in keys))
        binaries = self.root / 'bin'
        binaries.mkdir()
        php = binaries / 'php85'
        # FAIL_COMMAND selects which Artisan step the fake PHP command rejects.
        php.write_text('#!/bin/sh\n[ "$2" != "${FAIL_COMMAND:-}" ]\n')
        php.chmod(0o755)
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.apps),
                        PROFUNDARIUM_TEMPLATE=str(self.template), FAIL_COMMAND='',
                        PATH=str(binaries) + os.pathsep + os.environ['PATH'])

    def run_setup(self):
        result = subprocess.run(['sh', str(SCRIPT)], env=self.env, capture_output=True, text=True)
        self.assertFalse(list(self.apps.glob('.profundarium-setup.*')))
        return result

    # Normal startup: generate the Sandboxer URLs and MariaDB environment references,
    # then verify later starts preserve the developer's settings and source edits.
    def test_fresh_setup_and_repeat_preserves_work(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        app = self.apps / 'profundarium'
        self.assertTrue((app / '.git').is_dir())
        environment = (app / '.env').read_text()
        self.assertIn('APP_URL=http://hedgedoc.localhost', environment)
        self.assertIn('HEDGEDOC_DB_CONNECTION=mysql', environment)
        self.assertIn('HEDGEDOC_DB_DATABASE="${HEDGEDOC_DB_NAME}"', environment)
        self.assertIn('HEDGEDOC_DB_HOST=db', environment)
        self.assertIn('HEDGEDOC_DB_PORT=3306', environment)
        self.assertIn('HEDGEDOC_DB_USERNAME="${HEDGEDOC_DB_USER}"', environment)
        self.assertIn('HEDGEDOC_DB_PASSWORD="${HEDGEDOC_DB_PASSWORD}"', environment)
        (app / '.env').write_text('developer settings')
        (app / 'artisan').write_text('developer changes')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((app / '.env').read_text(), 'developer settings')
        self.assertEqual((app / 'artisan').read_text(), 'developer changes')

    # Simulate either Artisan initialization step failing. Setup must clean up the
    # incomplete app and permit a later successful retry.
    def test_failure_does_not_publish_and_retry_succeeds(self):
        for command in ('package:discover', 'key:generate'):
            self.env['FAIL_COMMAND'] = command
            self.assertNotEqual(self.run_setup().returncode, 0)
            self.assertFalse((self.apps / 'profundarium').exists())
        self.env['FAIL_COMMAND'] = ''
        self.assertEqual(self.run_setup().returncode, 0)

    # A symlink is an unsupported installation destination. Explain how to fix it
    # without removing the link or changing its target, whether valid or broken.
    def test_existing_symlink_is_rejected(self):
        target = self.apps / 'profundarium'
        for name in ('missing', 'existing'):
            with self.subTest(destination=name):
                destination = self.root / name
                if name == 'existing':
                    destination.mkdir()
                    (destination / 'keep.txt').write_text('developer files')
                target.symlink_to(destination)
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('www/profundarium is a symlink', result.stderr)
                self.assertTrue(target.is_symlink())
                if name == 'existing':
                    self.assertEqual(list(destination.iterdir()), [destination / 'keep.txt'])
                    self.assertEqual((destination / 'keep.txt').read_text(), 'developer files')
                else:
                    self.assertFalse(destination.exists())
                target.unlink()

    # Defensive check for an incomplete setup image: missing Composer dependencies
    # must fail setup before an application directory is published.
    def test_missing_template_is_not_published(self):
        (self.template / 'vendor/autoload.php').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        self.assertFalse((self.apps / 'profundarium').exists())


if __name__ == '__main__':
    unittest.main()
