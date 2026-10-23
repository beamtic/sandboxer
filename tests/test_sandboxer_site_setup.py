"""Sandboxer landing-page setup preserves existing developer files."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/install-scripts/sandboxer-site.sh'


class DefaultSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / 'www'
        self.template = self.root / 'template'
        self.template.mkdir()
        (self.template / 'index.php').write_text('template page')
        (self.template / 'beamtic-sandboxer.png').write_bytes(b'fixture image')
        self.env = dict(os.environ, SANDBOXER_ROOT=str(self.destination),
                        DEFAULT_TEMPLATE=str(self.template))

    def run_setup(self):
        return subprocess.run(['sh', str(SCRIPT)], env=self.env,
                              capture_output=True, text=True)

    def test_fresh_install_and_repeat(self):
        for _ in range(2):
            result = self.run_setup()
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ['index.php', 'beamtic-sandboxer.png']:
                self.assertEqual((self.destination / 'default' / name).read_bytes(),
                                 (self.template / name).read_bytes())

    def test_existing_page_preserved_and_missing_image_added(self):
        site = self.destination / 'default'
        site.mkdir(parents=True)
        (site / 'index.php').write_text('developer page')
        (self.destination / 'setup-completed').touch()
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((site / 'index.php').read_text(), 'developer page')
        self.assertTrue((site / 'beamtic-sandboxer.png').is_file())

    def test_existing_file_symlink_preserved(self):
        site = self.destination / 'default'
        site.mkdir(parents=True)
        missing = self.root / 'missing'
        (site / 'index.php').symlink_to(missing)
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertTrue((site / 'index.php').is_symlink())
        self.assertFalse(missing.exists())

    def test_destination_symlink_not_followed(self):
        self.destination.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.destination / 'default').symlink_to(outside)
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_missing_source_fails_and_can_retry(self):
        (self.template / 'beamtic-sandboxer.png').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        (self.template / 'beamtic-sandboxer.png').write_bytes(b'restored')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((self.destination / 'default/beamtic-sandboxer.png').read_bytes(),
                         b'restored')


if __name__ == '__main__':
    unittest.main()
