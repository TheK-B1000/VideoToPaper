from __future__ import annotations

from typing import Any, Dict, List


def _status_icon(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _format_reasons(reasons: List[str]) -> str:
    if not reasons:
        return "- No reasons provided."

    return "\n".join(f"- {reason}" for reason in reasons)


def render_audit_summary(audit_payload: Dict[str, Any]) -> str:
    """
    Render a human-readable Markdown summary from an audit report payload.

    This is intentionally lightweight so it can be shown in the CLI,
    displayed inside an operator UI, or copied into a development log.
    """
    decision = audit_payload.get("publishability_decision", {})
    publishable = decision.get("publishable", False)
    reasons = decision.get("reasons", [])
    blocking_axes = decision.get("blocking_axes", [])

    steelman = audit_payload.get("steelman_accuracy", {})
    evidence = audit_payload.get("evidence_balance", {})
    citation = audit_payload.get("citation_integrity", {})
    clip = audit_payload.get("clip_anchor_accuracy", {})

    lines = [
        "# Inquiry Audit Summary",
        "",
        f"**Publishable:** {_status_icon(bool(publishable))}",
        "",
        "## Gate Decision",
        "",
        _format_reasons(reasons),
        "",
        "## Blocking Axes",
        "",
    ]

    if blocking_axes:
        lines.extend(f"- {axis}" for axis in blocking_axes)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Metric Snapshot",
            "",
            "| Axis | Result |",
            "| --- | --- |",
            f"| Steelman anchored assertions | {steelman.get('verbatim_anchored_assertions', 'unknown')} |",
            f"| Qualifications preserved | {steelman.get('qualifications_preserved', 'unknown')} |",
            f"| Hedge drift detected | {steelman.get('hedge_drift_detected', 'unknown')} |",
            f"| Balanced retrieval | {evidence.get('claims_with_balanced_retrieval', 'unknown')} |",
            f"| Cherry-picking score | {evidence.get('cherry_picking_score', 'unknown')} |",
            f"| False consensus count | {evidence.get('false_consensus_count', 'unknown')} |",
            f"| References resolved | {citation.get('references_resolved', 'unknown')} |",
            f"| Fabricated references | {citation.get('fabricated_references', 'unknown')} |",
            f"| Clips within tolerance | {clip.get('clips_within_tolerance', 'unknown')} |",
            f"| Clip tolerance seconds | {clip.get('tolerance_seconds', 'unknown')} |",
        ]
    )

    drift_detected = clip.get("drift_detected", [])
    unresolved_references = citation.get("unresolved_references", [])
    missing_anchors = steelman.get("missing_anchors", [])

    if missing_anchors:
        lines.extend(
            [
                "",
                "## Missing Anchors",
                "",
            ]
        )
        for item in missing_anchors:
            text = item.get("text", "")
            anchors = ", ".join(item.get("anchors", []))
            lines.append(f"- `{text}` attempted anchors: {anchors}")

    if unresolved_references:
        lines.extend(
            [
                "",
                "## Unresolved References",
                "",
            ]
        )
        for reference in unresolved_references:
            evidence_id = reference.get("evidence_record_id", "unknown")
            identifier = reference.get("identifier", "unknown")
            lines.append(f"- `{evidence_id}` / `{identifier}`")

    if drift_detected:
        lines.extend(
            [
                "",
                "## Clip Drift",
                "",
            ]
        )
        for drift in drift_detected:
            claim_id = drift.get("claim_id", "unknown_claim")
            start_drift = drift.get("start_drift", "unknown")
            end_drift = drift.get("end_drift", "unknown")
            lines.append(
                f"- `{claim_id}` start drift: {start_drift}, end drift: {end_drift}"
            )

    return "\n".join(lines).strip() + "\n"