"""Test the Laravel installer without running Laravel or connecting to a database.

Checks fresh setup, preservation of existing source, keys and databases, rejection
of symlink destinations, and cleanup after failures. Fake PHP commands record
Artisan calls and simulate key generation and migrations so failures can be tested
safely. Only temporary fixtures are changed, never your applications.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/install-scripts/laravel.sh'


class LaravelSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / 'www'
        self.destination.mkdir()
        self.template = self.root / 'template'
        (self.template / 'vendor').mkdir(parents=True)
        (self.template / 'database').mkdir()
        (self.template / 'artisan').write_text('fixture')
        (self.template / 'vendor/autoload.php').write_text('fixture')
        (self.template / '.env.example').write_text('APP_URL=http://localhost\nAPP_KEY=\n')
        binaries = self.root / 'bin'
        binaries.mkdir()
        php = binaries / 'php85'
        # Record calls and fake their output so reruns and failed migrations are observable.
        php.write_text("#!/bin/sh\n"
                       'echo "$2" >> "$CALL_LOG"\n'
                       '[ "$2" != "${FAIL_COMMAND:-}" ] || exit 1\n'
                       'case "$2" in\n'
                       '  key:generate) echo "fixture-key" >> .env ;;\n'
                       '  migrate) echo "fixture-db" > database/database.sqlite ;;\n'
                       'esac\n')
        php.chmod(0o755)
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.destination),
                        LARAVEL_TEMPLATE=str(self.template), CALL_LOG=str(self.calls),
                        FAIL_COMMAND='', PATH=str(binaries) + os.pathsep + os.environ['PATH'])

    def run_setup(self):
        result = subprocess.run(['sh', str(SCRIPT)], env=self.env,
                                capture_output=True, text=True)
        self.assertFalse(list(self.destination.glob('.laravel-setup.*')))
        return result

    # Normal startup: install the app once. Later starts must not rotate its key,
    # rerun migrations, replace its database, or overwrite source edits.
    def test_success_and_repeat_preserves_key_database_and_edits(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        app = self.destination / 'laravel'
        self.assertIn('APP_URL=http://laravel.localhost', (app / '.env').read_text())
        (app / '.env').write_text('developer-key')
        (app / 'database/database.sqlite').write_text('developer-data')
        (app / 'artisan').write_text('developer-edit')
        before = self.calls.read_text()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(self.calls.read_text(), before)
        self.assertEqual((app / '.env').read_text(), 'developer-key')
        self.assertEqual((app / 'database/database.sqlite').read_text(), 'developer-data')
        self.assertEqual((app / 'artisan').read_text(), 'developer-edit')

    # Simulate failures in package discovery, key generation, and migration.
    # Each failure must leave no published app, allowing setup to retry later.
    def test_initialization_failure_leaves_no_app_and_allows_retry(self):
        for command in ['package:discover', 'key:generate', 'migrate']:
            with self.subTest(command=command):
                self.env['FAIL_COMMAND'] = command
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.destination / 'laravel').exists())
        self.env['FAIL_COMMAND'] = ''
        self.assertEqual(self.run_setup().returncode, 0)

    # Defensive check for an incomplete setup image: refuse to publish Laravel
    # when its Composer dependencies are missing.
    def test_missing_template_does_not_publish(self):
        (self.template / 'vendor/autoload.php').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        self.assertFalse((self.destination / 'laravel').exists())

    # A developer may supply their own Laravel directory before running Sandboxer.
    # Setup must preserve it and run no Artisan initialization commands.
    def test_existing_app_is_preserved_without_marker(self):
        app = self.destination / 'laravel'
        app.mkdir()
        (app / 'keep.txt').write_text('existing app')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((app / 'keep.txt').read_text(), 'existing app')
        self.assertFalse(self.calls.exists())

    # Reject a symlink at www/laravel, whether valid or broken, with a clear error.
    # Leave both the link and its target untouched for the developer to resolve.
    def test_destination_symlink_is_rejected(self):
        self.destination.mkdir(exist_ok=True)
        target = self.destination / 'laravel'
        for name in ('missing', 'existing'):
            with self.subTest(destination=name):
                destination = self.root / name
                if name == 'existing':
                    destination.mkdir()
                    (destination / 'keep.txt').write_text('developer files')
                target.symlink_to(destination)
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('www/laravel is a symlink', result.stderr)
                self.assertTrue(target.is_symlink())
                if name == 'existing':
                    self.assertEqual(list(destination.iterdir()), [destination / 'keep.txt'])
                    self.assertEqual((destination / 'keep.txt').read_text(), 'developer files')
                else:
                    self.assertFalse(destination.exists())
                target.unlink()
        self.assertFalse(self.calls.exists())

    # Legacy compatibility: the former phpMyAdmin completion marker must not
    # prevent an independent Laravel installation.
    def test_phpmyadmin_marker_does_not_skip_laravel(self):
        (self.destination / 'setup-completed').touch()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertTrue((self.destination / 'laravel/artisan').is_file())


if __name__ == '__main__':
    unittest.main()
