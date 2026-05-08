from src.frontend.state import (
    LAST_ACTION_SESSION_KEY,
    LastAction,
    clear_last_action,
    get_last_action,
    initialize_studio_state,
    normalize_query_params,
    persist_studio_state_to_query_params,
    record_last_action,
    set_last_action,
)


def test_initialize_studio_state_prefers_query_params_for_empty_session():
    session_state = {}
    query_params = {
        "library_query": "reinforcement",
        "library_status": "completed",
        "audit_path": "data/outputs/audit.json",
        "backend_base_url": "http://localhost:9000",
    }

    state = initialize_studio_state(
        session_state,
        query_params,
        defaults={
            "backend_base_url": "http://127.0.0.1:8000",
        },
    )

    assert state.library_query == "reinforcement"
    assert state.library_status == "completed"
    assert state.audit_report_path == "data/outputs/audit.json"
    assert state.backend_base_url == "http://localhost:9000"
    assert session_state["studio_library_query"] == "reinforcement"


def test_initialize_studio_state_preserves_existing_session_values():
    session_state = {
        "studio_library_query": "session value",
    }
    query_params = {
        "library_query": "query value",
    }

    state = initialize_studio_state(session_state, query_params)

    assert state.library_query == "session value"
    assert session_state["studio_library_query"] == "session value"


def test_initialize_studio_state_rejects_invalid_choice_query_param():
    session_state = {}
    query_params = {
        "library_status": "archived",
    }

    state = initialize_studio_state(session_state, query_params)

    assert state.library_status == "all"
    assert session_state["studio_library_status"] == "all"


def test_persist_studio_state_writes_non_default_values_and_removes_defaults():
    session_state = {
        "studio_library_query": "multi agent",
        "studio_library_status": "all",
        "studio_backend_base_url": "http://localhost:9000",
    }
    query_params = {
        "library_status": "completed",
        "stale": "kept",
    }

    persist_studio_state_to_query_params(
        session_state,
        query_params,
        defaults={
            "backend_base_url": "http://127.0.0.1:8000",
        },
    )

    assert query_params["library_query"] == "multi agent"
    assert query_params["backend_base_url"] == "http://localhost:9000"
    assert "library_status" not in query_params
    assert query_params["stale"] == "kept"


def test_normalize_query_params_flattens_streamlit_style_values():
    query_params = {
        "single": "value",
        "list": ["first", "second"],
        "empty": [],
        "none": None,
    }

    normalized = normalize_query_params(query_params)

    assert normalized == {
        "single": "value",
        "list": "first",
        "empty": "",
        "none": "",
    }


def test_last_action_round_trips_through_session_state():
    session_state = {}
    action = LastAction(
        title="Run launched",
        message="Local run started.",
        status="success",
        details={"run_id": "run_001"},
        artifact_path="logs/runs/run_001/progress.json",
        created_at="2026-05-08T12:00:00Z",
    )

    set_last_action(session_state, action)
    loaded = get_last_action(session_state)

    assert session_state[LAST_ACTION_SESSION_KEY]["title"] == "Run launched"
    assert loaded == action


def test_record_last_action_creates_timestamped_action():
    session_state = {}

    action = record_last_action(
        session_state,
        title="Audit opened",
        message="Loaded audit report.",
        status="success",
        details={"path": "audit.json"},
    )

    assert action.created_at is not None
    assert action.status == "success"
    assert get_last_action(session_state) == action


def test_clear_last_action_removes_session_entry():
    session_state = {
        LAST_ACTION_SESSION_KEY: {
            "title": "Existing action",
            "message": "Existing message",
        }
    }

    clear_last_action(session_state)

    assert get_last_action(session_state) is None
