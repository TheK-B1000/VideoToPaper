import json
import unittest
from pathlib import Path

import videotopaper
from videotopaper.chunking import chunk_transcript
from videotopaper.transcripts import clean_text, load_transcript, save_transcript, validate_segment


class ScaffoldTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(videotopaper.__version__, "0.1.0")

    def test_starter_functions_exist(self) -> None:
        self.assertTrue(callable(clean_text))
        self.assertTrue(callable(validate_segment))
        self.assertTrue(callable(load_transcript))
        self.assertTrue(callable(save_transcript))
        self.assertTrue(callable(chunk_transcript))

    def test_mock_transcript_uses_canonical_shape(self) -> None:
        path = Path("data/mock_transcript.json")
        segments = json.loads(path.read_text(encoding="utf-8"))

        self.assertGreater(len(segments), 0)
        for segment in segments:
            self.assertEqual(set(segment), {"text", "start_time", "end_time"})
            self.assertIsInstance(segment["text"], str)
            self.assertIsInstance(segment["start_time"], float)
            self.assertIsInstance(segment["end_time"], float)
            self.assertLessEqual(segment["start_time"], segment["end_time"])


if __name__ == "__main__":
    unittest.main()
