"""Check first-run setup without downloads or access to real application data."""
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
                'HEDGEDOC_UPLOADS_PATH', 'HEDGEDOC_DB_CONNECTION', 'HEDGEDOC_DB_DATABASE']
        (self.template / '.env.example').write_text(''.join(f'{key}=old\n' for key in keys))
        binaries = self.root / 'bin'
        binaries.mkdir()
        php = binaries / 'php85'
        php.write_text('#!/bin/sh\n[ "$2" != "${FAIL_COMMAND:-}" ]\n')
        php.chmod(0o755)
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.apps),
                        PROFUNDARIUM_TEMPLATE=str(self.template), FAIL_COMMAND='',
                        PATH=str(binaries) + os.pathsep + os.environ['PATH'])

    def run_setup(self):
        result = subprocess.run(['sh', str(SCRIPT)], env=self.env, capture_output=True, text=True)
        self.assertFalse(list(self.apps.glob('.profundarium-setup.*')))
        return result

    def test_fresh_setup_and_repeat_preserves_work(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        app = self.apps / 'profundarium'
        self.assertTrue((app / '.git').is_dir())
        environment = (app / '.env').read_text()
        self.assertIn('APP_URL=http://hedgedoc.localhost', environment)
        self.assertIn('HEDGEDOC_DB_CONNECTION=sqlite', environment)
        self.assertIn('HEDGEDOC_DB_DATABASE=/hedgedoc/public/hedgedoc.sqlite', environment)
        (app / '.env').write_text('developer settings')
        (app / 'artisan').write_text('developer changes')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((app / '.env').read_text(), 'developer settings')
        self.assertEqual((app / 'artisan').read_text(), 'developer changes')

    def test_failure_does_not_publish_and_retry_succeeds(self):
        for command in ('package:discover', 'key:generate'):
            self.env['FAIL_COMMAND'] = command
            self.assertNotEqual(self.run_setup().returncode, 0)
            self.assertFalse((self.apps / 'profundarium').exists())
        self.env['FAIL_COMMAND'] = ''
        self.assertEqual(self.run_setup().returncode, 0)

    def test_existing_symlink_is_preserved(self):
        target = self.apps / 'profundarium'
        target.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertTrue(target.is_symlink())

    def test_missing_template_is_not_published(self):
        (self.template / 'vendor/autoload.php').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        self.assertFalse((self.apps / 'profundarium').exists())


if __name__ == '__main__':
    unittest.main()
