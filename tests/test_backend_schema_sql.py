import sqlite3
from pathlib import Path


SCHEMA_PATH = Path("src/backend/schema.sql")


def _connect_with_schema() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    return conn


def test_schema_file_exists():
    assert SCHEMA_PATH.exists()


def test_schema_creates_required_tables():
    conn = _connect_with_schema()

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name;
        """
    ).fetchall()

    table_names = {row[0] for row in rows}

    assert "speakers" in table_names
    assert "videos" in table_names
    assert "claims" in table_names
    assert "evidence_records" in table_names
    assert "papers" in table_names
    assert "runs" in table_names
    assert "audit_events" in table_names


def test_can_insert_video_with_speaker():
    conn = _connect_with_schema()

    conn.execute(
        """
        INSERT INTO speakers (
            id,
            name,
            credentials,
            stated_motivations
        )
        VALUES (?, ?, ?, ?);
        """,
        (
            "speaker_001",
            "Dr. Jane Smith",
            "Professor of Computer Science",
            "Clarifying misconceptions in AI discourse",
        ),
    )

    conn.execute(
        """
        INSERT INTO videos (
            id,
            url,
            title,
            embed_base_url,
            duration_seconds,
            speaker_id
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            "video_001",
            "https://www.youtube.com/watch?v=ABC123",
            "Example Video",
            "https://www.youtube-nocookie.com/embed/ABC123",
            120.0,
            "speaker_001",
        ),
    )

    row = conn.execute(
        """
        SELECT videos.title, speakers.name
        FROM videos
        JOIN speakers ON videos.speaker_id = speakers.id
        WHERE videos.id = ?;
        """,
        ("video_001",),
    ).fetchone()

    assert row == ("Example Video", "Dr. Jane Smith")


def test_video_rejects_non_privacy_embed_domain():
    conn = _connect_with_schema()

    try:
        conn.execute(
            """
            INSERT INTO videos (
                id,
                url,
                title,
                embed_base_url,
                duration_seconds
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                "video_bad",
                "https://www.youtube.com/watch?v=BAD123",
                "Bad Embed",
                "https://www.youtube.com/embed/BAD123",
                100.0,
            ),
        )
    except sqlite3.IntegrityError:
        return

    raise AssertionError("Expected schema to reject non youtube-nocookie embed URL")


def test_can_insert_claim_and_evidence_record():
    conn = _connect_with_schema()

    conn.execute(
        """
        INSERT INTO videos (
            id,
            url,
            title,
            embed_base_url,
            duration_seconds
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            "video_001",
            "https://www.youtube.com/watch?v=ABC123",
            "Example Video",
            "https://www.youtube-nocookie.com/embed/ABC123",
            120.0,
        ),
    )

    conn.execute(
        """
        INSERT INTO claims (
            id,
            video_id,
            verbatim_quote,
            claim_type,
            verification_strategy,
            char_offset_start,
            char_offset_end,
            anchor_clip_start,
            anchor_clip_end,
            embed_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "claim_001",
            "video_001",
            "Multi-agent systems are non-stationary.",
            "empirical_technical",
            "literature_review",
            10,
            48,
            25.0,
            32.0,
            "https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
        ),
    )

    conn.execute(
        """
        INSERT INTO evidence_records (
            id,
            claim_id,
            tier,
            stance,
            source_title,
            source_url,
            identifier,
            key_finding
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "evidence_001",
            "claim_001",
            1,
            "supports",
            "A Survey of Multi-Agent Reinforcement Learning",
            "https://example.com/paper",
            "doi:10.0000/example",
            "The paper discusses non-stationarity as a MARL challenge.",
        ),
    )

    row = conn.execute(
        """
        SELECT evidence_records.source_title, evidence_records.stance
        FROM evidence_records
        JOIN claims ON evidence_records.claim_id = claims.id
        WHERE claims.id = ?;
        """,
        ("claim_001",),
    ).fetchone()

    assert row == ("A Survey of Multi-Agent Reinforcement Learning", "supports")


def test_claim_rejects_invalid_offsets():
    conn = _connect_with_schema()

    conn.execute(
        """
        INSERT INTO videos (
            id,
            url,
            title,
            embed_base_url
        )
        VALUES (?, ?, ?, ?);
        """,
        (
            "video_001",
            "https://www.youtube.com/watch?v=ABC123",
            "Example Video",
            "https://www.youtube-nocookie.com/embed/ABC123",
        ),
    )

    try:
        conn.execute(
            """
            INSERT INTO claims (
                id,
                video_id,
                verbatim_quote,
                claim_type,
                verification_strategy,
                char_offset_start,
                char_offset_end,
                anchor_clip_start,
                anchor_clip_end,
                embed_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "claim_bad",
                "video_001",
                "Bad offset claim.",
                "empirical_technical",
                "literature_review",
                50,
                20,
                25.0,
                32.0,
                "https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
            ),
        )
    except sqlite3.IntegrityError:
        return

    raise AssertionError("Expected schema to reject invalid claim offsets")


def test_can_insert_run_and_audit_event():
    conn = _connect_with_schema()

    conn.execute(
        """
        INSERT INTO videos (
            id,
            url,
            title,
            embed_base_url
        )
        VALUES (?, ?, ?, ?);
        """,
        (
            "video_001",
            "https://www.youtube.com/watch?v=ABC123",
            "Example Video",
            "https://www.youtube-nocookie.com/embed/ABC123",
        ),
    )

    conn.execute(
        """
        INSERT INTO runs (
            id,
            video_id,
            pipeline_name,
            status,
            pipeline_config_json,
            input_artifacts_json,
            output_artifacts_json,
            started_at,
            finished_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """,
        (
            "run_001",
            "video_001",
            "week6_video_registration",
            "completed",
            '{"source":"fastapi"}',
            '{"video_url":"https://www.youtube.com/watch?v=ABC123"}',
            '{}',
        ),
    )

    conn.execute(
        """
        INSERT INTO audit_events (
            id,
            run_id,
            video_id,
            event_type,
            message,
            metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            "audit_001",
            "run_001",
            "video_001",
            "video_registered",
            "Video registered through FastAPI backend.",
            '{"title":"Example Video"}',
        ),
    )

    row = conn.execute(
        """
        SELECT audit_events.event_type, runs.pipeline_name
        FROM audit_events
        JOIN runs ON audit_events.run_id = runs.id
        WHERE audit_events.id = ?;
        """,
        ("audit_001",),
    ).fetchone()

    assert row == ("video_registered", "week6_video_registration")
