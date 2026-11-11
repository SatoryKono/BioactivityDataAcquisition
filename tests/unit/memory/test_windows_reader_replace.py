import concurrent.futures
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import storage


class ReplaceReaderTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics")
    def test_open_reader_releases_before_same_write_completes(self):
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("MCP_REPLACE_TEST_ROOT")
        ) as raw:
            target = Path(raw) / "graph.json"
            target.write_text('{"old": true}')
            original_replace = storage.os.replace
            denied = threading.Event()
            attempts = []

            def replace(source, destination):
                attempts.append(source)
                try:
                    return original_replace(source, destination)
                except PermissionError:
                    self.assertTrue(target.with_name(".graph.json.lock").exists())
                    denied.set()
                    raise

            with (
                target.open("rb") as reader,
                patch.object(storage.os, "replace", side_effect=replace),
                concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool,
            ):
                result = pool.submit(storage.atomic_write_json, target, {"new": True})
                self.assertTrue(
                    denied.wait(0.5), "Expected a real Windows sharing violation"
                )
                reader.close()
                result.result(timeout=3)
            self.assertGreater(len(attempts), 1)
            self.assertEqual(len(set(attempts)), 1)
            self.assertEqual(json.loads(target.read_text()), {"new": True})

    def test_permanent_permission_denial_is_bounded_and_preserves_graph(self):
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("MCP_REPLACE_TEST_ROOT")
        ) as raw:
            target = Path(raw) / "graph.json"
            target.write_text("original")
            with (
                patch.object(
                    storage.os, "replace", side_effect=PermissionError("denied")
                ),
                patch.object(storage.time, "monotonic", side_effect=[0, 0, 2, 2]),
                self.assertRaises(PermissionError),
            ):
                storage.atomic_write_json(target, {"new": True})
            self.assertEqual(target.read_text(), "original")
            self.assertEqual([p.name for p in Path(raw).iterdir()], ["graph.json"])

    def test_other_replace_errors_are_not_retried(self):
        with patch.object(
            storage.os, "replace", side_effect=OSError("unrelated")
        ) as replace:
            with self.assertRaises(OSError):
                storage._replace_with_reader_wait(Path("source"), Path("target"))
            replace.assert_called_once()


if __name__ == "__main__":
    unittest.main()
