import sys
import tempfile
import unittest
from pathlib import Path

from privacy_guard.setup.errors import SetupError, user_message

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from windows_payload import MAX_PATH, longest_install_directory  # noqa: E402


class UserMessageTest(unittest.TestCase):
    def test_setup_errors_keep_their_french_sentence(self):
        self.assertEqual(user_message(SetupError("Le modèle de noms est incomplet.")),
                         "Le modèle de noms est incomplet.")

    def test_unexpected_errors_show_a_category_never_their_text(self):
        message = user_message(PermissionError("C:/Users/Camille Lefebvre/AppData is locked"))
        self.assertIn("(permission)", message)
        self.assertNotIn("Camille", message)
        self.assertNotIn("AppData", message)


class InstallDirectoryLimitTest(unittest.TestCase):
    def test_limit_keeps_the_longest_payload_path_under_max_path(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = Path(temp)
            deep = payload / "runtime/Lib/site-packages/package/module.py"
            deep.parent.mkdir(parents=True)
            deep.write_text("")
            limit = longest_install_directory(payload, "0.1.0-preview.2")
            install_dir = "C:/" + "d" * (limit - 3)
            full = f"{install_dir}\\versions\\0.1.0-preview.2\\runtime/Lib/site-packages/package/module.py"
            self.assertEqual(len(full), MAX_PATH)


if __name__ == "__main__":
    unittest.main()
