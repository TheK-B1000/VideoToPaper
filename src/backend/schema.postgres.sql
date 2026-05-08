-- Inquiry Engine Week 6 Postgres schema
-- Neon-compatible persistence layer for videos, speakers, claims, evidence, papers, runs, and audit events.

CREATE TABLE IF NOT EXISTS speakers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    credentials TEXT,
    stated_motivations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    embed_base_url TEXT NOT NULL,
    duration_seconds DOUBLE PRECISION,
    speaker_id TEXT REFERENCES speakers(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_videos_duration_nonnegative
        CHECK (duration_seconds IS NULL OR duration_seconds >= 0),

    CONSTRAINT chk_videos_embed_privacy_domain
        CHECK (embed_base_url LIKE '%youtube-nocookie.com/embed/%')
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    verbatim_quote TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    verification_strategy TEXT NOT NULL,
    char_offset_start INTEGER NOT NULL,
    char_offset_end INTEGER NOT NULL,
    anchor_clip_start DOUBLE PRECISION NOT NULL,
    anchor_clip_end DOUBLE PRECISION NOT NULL,
    embed_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_claim_offsets_valid
        CHECK (char_offset_start >= 0 AND char_offset_end > char_offset_start),

    CONSTRAINT chk_claim_clip_valid
        CHECK (anchor_clip_start >= 0 AND anchor_clip_end > anchor_clip_start),

    CONSTRAINT chk_claim_type_valid
        CHECK (
            claim_type IN (
                'empirical_technical',
                'empirical_scientific',
                'empirical_historical',
                'interpretive',
                'normative',
                'anecdotal',
                'predictive'
            )
        ),

    CONSTRAINT chk_verification_strategy_valid
        CHECK (
            verification_strategy IN (
                'literature_review',
                'source_context_review',
                'future_tracking',
                'not_externally_verified'
            )
        )
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    tier INTEGER NOT NULL,
    stance TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_url TEXT,
    identifier TEXT,
    abstract_or_summary TEXT,
    key_finding TEXT,
    retrieval_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_evidence_tier_valid
        CHECK (tier IN (1, 2, 3)),

    CONSTRAINT chk_evidence_stance_valid
        CHECK (
            stance IN (
                'supports',
                'contradicts',
                'complicates',
                'qualifies',
                'neutral'
            )
        )
);

CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    section_speaker_perspective TEXT NOT NULL DEFAULT '',
    section_evidence_review TEXT NOT NULL DEFAULT '',
    section_further_reading TEXT NOT NULL DEFAULT '',
    html_render_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,
    pipeline_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_artifacts JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_artifacts JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    error_message TEXT,

    CONSTRAINT chk_run_status_valid
        CHECK (status IN ('queued', 'running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
    video_id TEXT REFERENCES videos(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_audit_event_type_valid
        CHECK (
            event_type IN (
                'video_registered',
                'speaker_registered',
                'claim_created',
                'evidence_created',
                'paper_created',
                'pipeline_started',
                'pipeline_completed',
                'pipeline_failed',
                'audit_requested'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_videos_speaker_id
    ON videos(speaker_id);

CREATE INDEX IF NOT EXISTS idx_claims_video_id
    ON claims(video_id);

CREATE INDEX IF NOT EXISTS idx_evidence_records_claim_id
    ON evidence_records(claim_id);

CREATE INDEX IF NOT EXISTS idx_evidence_records_tier
    ON evidence_records(tier);

CREATE INDEX IF NOT EXISTS idx_evidence_records_stance
    ON evidence_records(stance);

CREATE INDEX IF NOT EXISTS idx_papers_video_id
    ON papers(video_id);

CREATE INDEX IF NOT EXISTS idx_runs_video_id
    ON runs(video_id);

CREATE INDEX IF NOT EXISTS idx_runs_status
    ON runs(status);

CREATE INDEX IF NOT EXISTS idx_runs_pipeline_name
    ON runs(pipeline_name);

CREATE INDEX IF NOT EXISTS idx_audit_events_video_id
    ON audit_events(video_id);

CREATE INDEX IF NOT EXISTS idx_audit_events_run_id
    ON audit_events(run_id);

CREATE INDEX IF NOT EXISTS idx_audit_events_event_type
    ON audit_events(event_type);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
    ON audit_events(created_at);

CREATE TABLE IF NOT EXISTS inquiry_engine_runs (
    run_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    youtube_url TEXT NOT NULL,
    request_json JSONB NOT NULL,
    progress_json JSONB NOT NULL,
    simulate_progress BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inquiry_engine_runs_request_id
    ON inquiry_engine_runs(request_id);
