import hashlib
import tempfile
import unittest
from pathlib import Path

from privacy_guard.service.model_environment import ModelEnvironment
from privacy_guard.service.model_files import ModelFiles, ModelFilesError

FILES = {"config.json": b"{}", "model.onnx": b"weights", "tokenizer.json": b"vocab"}
MANIFEST = {name: hashlib.sha256(content).hexdigest() for name, content in FILES.items()}


class ModelFilesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.source = root / "published"
        self.source.mkdir()
        for name, content in FILES.items():
            (self.source / name).write_bytes(content)
        self.files = ModelFiles(root / "models" / "person-ner", manifest=MANIFEST)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetch_from_a_directory_installs_verified_files(self):
        self.assertFalse(self.files.is_ready())

        self.files.fetch(str(self.source))

        self.assertTrue(self.files.is_ready())

    def test_rejects_a_tampered_file_and_keeps_the_installed_model(self):
        self.files.fetch(str(self.source))
        (self.source / "model.onnx").write_bytes(b"malicious weights")

        with self.assertRaises(ModelFilesError):
            self.files.fetch(str(self.source))

        self.assertTrue(self.files.is_ready())

    def test_detects_a_file_changed_after_installation(self):
        self.files.fetch(str(self.source))
        installed = Path(self._tmp.name) / "models" / "person-ner" / "model.onnx"

        installed.write_bytes(b"changed")

        self.assertFalse(self.files.is_ready())

    def test_refuses_unencrypted_downloads(self):
        with self.assertRaises(ModelFilesError):
            self.files.fetch("http://example.com/model")


class ModelEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # No requirements: tests the environment's life cycle without network access.
        self.environment = ModelEnvironment(Path(self._tmp.name) / "model-env", requirements=())

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_then_remove(self):
        self.assertFalse(self.environment.is_ready())

        self.environment.create()
        self.assertTrue(self.environment.is_ready())
        self.assertTrue(self.environment.python.exists())

        self.environment.remove()
        self.assertFalse(self.environment.is_ready())

    def test_requirement_change_makes_it_stale(self):
        self.environment.create()
        updated = ModelEnvironment(Path(self._tmp.name) / "model-env", requirements=("numpy==9.9.9",))

        self.assertFalse(updated.is_ready())


if __name__ == "__main__":
    unittest.main()
