from pathlib import Path


POSTGRES_SCHEMA_PATH = Path("src/backend/schema.postgres.sql")


def test_postgres_schema_file_exists():
    assert POSTGRES_SCHEMA_PATH.exists()


def test_postgres_schema_contains_required_tables():
    schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS speakers" in schema
    assert "CREATE TABLE IF NOT EXISTS videos" in schema
    assert "CREATE TABLE IF NOT EXISTS claims" in schema
    assert "CREATE TABLE IF NOT EXISTS evidence_records" in schema
    assert "CREATE TABLE IF NOT EXISTS papers" in schema
    assert "CREATE TABLE IF NOT EXISTS runs" in schema
    assert "CREATE TABLE IF NOT EXISTS audit_events" in schema


def test_postgres_schema_uses_postgres_native_types():
    schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")

    assert "JSONB" in schema
    assert "TIMESTAMPTZ" in schema
    assert "NOW()" in schema
    assert "DOUBLE PRECISION" in schema


def test_postgres_schema_tracks_mlops_run_artifacts():
    schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")

    assert "pipeline_config JSONB" in schema
    assert "input_artifacts JSONB" in schema
    assert "output_artifacts JSONB" in schema
    assert "started_at TIMESTAMPTZ NOT NULL" in schema
    assert "finished_at TIMESTAMPTZ" in schema
    assert "error_message TEXT" in schema


def test_postgres_schema_tracks_audit_event_metadata():
    schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")

    assert "metadata JSONB" in schema
    assert "event_type TEXT NOT NULL" in schema
    assert "message TEXT NOT NULL" in schema
    assert "idx_audit_events_created_at" in schema


def test_postgres_schema_preserves_core_constraints():
    schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")

    assert "chk_videos_embed_privacy_domain" in schema
    assert "chk_claim_offsets_valid" in schema
    assert "chk_claim_clip_valid" in schema
    assert "chk_evidence_tier_valid" in schema
    assert "chk_evidence_stance_valid" in schema
    assert "chk_run_status_valid" in schema
    assert "chk_audit_event_type_valid" in schema
