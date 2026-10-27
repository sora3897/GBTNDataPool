"""The upstream sharing switch. Local pool writes are not gated here."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.sharing import confirm_upstream, load_settings, set_sharing, upstream_decision


class SharingTest(unittest.TestCase):
    def test_committed_default_is_off(self):
        data = json.loads((ROOT / "config" / "user_settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["share_data"], False)
        self.assertEqual(data["share_bugs"], False)
        self.assertEqual(data["upstream_confirmed"], False)

    def test_missing_file_is_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = load_settings(tmp)
            self.assertFalse(data["share_data"])
            self.assertEqual(upstream_decision(tmp, "data")["reason"], "off")
            self.assertEqual(upstream_decision(tmp, "bugs")["reason"], "off")

    def test_on_then_confirm_then_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_sharing(tmp, True)
            self.assertEqual(upstream_decision(tmp, "data")["reason"], "needs_confirmation")
            self.assertEqual(upstream_decision(tmp, "bugs")["reason"], "needs_confirmation")
            confirm_upstream(tmp)
            self.assertTrue(upstream_decision(tmp, "data")["allowed"])
            self.assertTrue(upstream_decision(tmp, "bugs")["allowed"])
            stored = json.loads((Path(tmp) / "config" / "user_settings.json").read_text(encoding="utf-8"))
            self.assertTrue(stored["share_data"])
            self.assertTrue(stored["share_bugs"])
            set_sharing(tmp, False)
            again = load_settings(tmp)
            self.assertFalse(again["share_data"])
            self.assertFalse(again["share_bugs"])
            self.assertFalse(again["upstream_confirmed"])
            self.assertEqual(upstream_decision(tmp, "bugs")["reason"], "off")

    def test_confirm_before_on_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                confirm_upstream(tmp)


if __name__ == "__main__":
    unittest.main()
