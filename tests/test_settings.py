import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daily_brief.settings import load_env_file


class SettingsTests(unittest.TestCase):
    def test_loads_env_without_overwriting_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("NEW_VALUE='new'\nEXISTING_VALUE=file\n", encoding="utf-8")
            with patch.dict(os.environ, {"EXISTING_VALUE": "shell"}, clear=True):
                load_env_file(path)
                self.assertEqual(os.environ["NEW_VALUE"], "new")
                self.assertEqual(os.environ["EXISTING_VALUE"], "shell")


if __name__ == "__main__":
    unittest.main()
