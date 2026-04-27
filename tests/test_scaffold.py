import json
import unittest
from pathlib import Path

import videotopaper
from videotopaper.arguments import extract_argument_map
from videotopaper.chunking import chunk_transcript
from videotopaper.sources import capture_speaker_context, register_video
from videotopaper.transcripts import clean_text, load_transcript, validate_segment


class ScaffoldTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(videotopaper.__version__, "0.2.0")

    def test_starter_functions_exist(self) -> None:
        self.assertTrue(callable(register_video))
        self.assertTrue(callable(capture_speaker_context))
        self.assertTrue(callable(clean_text))
        self.assertTrue(callable(validate_segment))
        self.assertTrue(callable(load_transcript))
        self.assertTrue(callable(chunk_transcript))
        self.assertTrue(callable(extract_argument_map))

    def test_mock_video_uses_source_registry_shape(self) -> None:
        path = Path("data/mock_video.json")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            set(payload),
            {
                "video_id",
                "title",
                "url",
                "duration_seconds",
                "speaker",
                "transcript_origin",
                "ingested_at",
            },
        )
        self.assertEqual(
            set(payload["speaker"]),
            {
                "name",
                "credentials",
                "stated_expertise",
                "stated_motivations",
            },
        )
        self.assertIsInstance(payload["speaker"]["stated_expertise"], list)
        self.assertGreater(payload["duration_seconds"], 0)

    def test_mock_transcript_preserves_offsets(self) -> None:
        path = Path("data/mock_transcript.json")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            set(payload),
            {"video_id", "transcript_origin", "source_text", "segments"},
        )

        source_text = payload["source_text"]
        self.assertIsInstance(source_text, str)
        self.assertGreater(len(payload["segments"]), 0)

        for segment in payload["segments"]:
            self.assertEqual(
                set(segment),
                {
                    "text",
                    "start_time",
                    "end_time",
                    "char_offset_start",
                    "char_offset_end",
                },
            )
            self.assertIsInstance(segment["text"], str)
            self.assertIsInstance(segment["start_time"], float)
            self.assertIsInstance(segment["end_time"], float)
            self.assertIsInstance(segment["char_offset_start"], int)
            self.assertIsInstance(segment["char_offset_end"], int)
            self.assertLessEqual(segment["start_time"], segment["end_time"])
            self.assertLess(segment["char_offset_start"], segment["char_offset_end"])
            self.assertGreaterEqual(segment["char_offset_start"], 0)
            self.assertLessEqual(segment["char_offset_end"], len(source_text))
            self.assertEqual(
                source_text[
                    segment["char_offset_start"] : segment["char_offset_end"]
                ],
                segment["text"],
            )


if __name__ == "__main__":
    unittest.main()
