"""Test installation of the Sandboxer landing page and its image.

Checks that missing files are copied, edited pages and file symlinks are preserved,
and a missing template can be restored before retrying. The installer must not
accept a symlink as the site directory or write through it into another directory.
Everything runs against temporary fixtures, not your actual www/default site.
"""
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

    # Normal startup: copy the landing page and image; a second run must succeed
    # and leave the same file contents.
    def test_fresh_install_and_repeat(self):
        for _ in range(2):
            result = self.run_setup()
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ['index.php', 'beamtic-sandboxer.png']:
                self.assertEqual((self.destination / 'default' / name).read_bytes(),
                                 (self.template / name).read_bytes())

    # Keep a developer-edited landing page while adding its missing image.
    def test_existing_page_preserved_and_missing_image_added(self):
        site = self.destination / 'default'
        site.mkdir(parents=True)
        (site / 'index.php').write_text('developer page')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((site / 'index.php').read_text(), 'developer page')
        self.assertTrue((site / 'beamtic-sandboxer.png').is_file())

    # Defensive edge case: preserve a landing-page file symlink, including one
    # whose target is absent, rather than writing through or replacing it.
    def test_existing_file_symlink_preserved(self):
        site = self.destination / 'default'
        site.mkdir(parents=True)
        missing = self.root / 'missing'
        (site / 'index.php').symlink_to(missing)
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertTrue((site / 'index.php').is_symlink())
        self.assertFalse(missing.exists())

    # Reject a symlink at www/default, whether valid or broken, with a clear error.
    # Leave both the link and its target untouched for the developer to resolve.
    def test_destination_symlink_is_rejected(self):
        self.destination.mkdir(exist_ok=True)
        target = self.destination / 'default'
        for name in ('missing', 'existing'):
            with self.subTest(destination=name):
                destination = self.root / name
                if name == 'existing':
                    destination.mkdir()
                    (destination / 'keep.txt').write_text('developer files')
                target.symlink_to(destination)
                result = self.run_setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('www/default is a symlink', result.stderr)
                self.assertTrue(target.is_symlink())
                if name == 'existing':
                    self.assertEqual(list(destination.iterdir()), [destination / 'keep.txt'])
                    self.assertEqual((destination / 'keep.txt').read_text(), 'developer files')
                else:
                    self.assertFalse(destination.exists())
                target.unlink()

    # Defensive check for an incomplete template: report the missing image,
    # then allow a retry to add it after the source file is restored.
    def test_missing_source_fails_and_can_retry(self):
        (self.template / 'beamtic-sandboxer.png').unlink()
        self.assertNotEqual(self.run_setup().returncode, 0)
        (self.template / 'beamtic-sandboxer.png').write_bytes(b'restored')
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual((self.destination / 'default/beamtic-sandboxer.png').read_bytes(),
                         b'restored')


if __name__ == '__main__':
    unittest.main()
