from dataclasses import dataclass, asdict
from typing import Literal


ClaimType = Literal[
    "empirical_technical",
    "empirical_historical",
    "empirical_scientific",
    "interpretive",
    "normative",
    "anecdotal",
    "predictive",
]

VerificationStrategy = Literal[
    "literature_review",
    "source_context_review",
    "no_external_verification",
    "future_tracking",
]


@dataclass(frozen=True)
class AnchorClip:
    start: float
    end: float


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    verbatim_quote: str
    anchor_chunk: str
    char_offset_start: int
    char_offset_end: int
    anchor_clip: AnchorClip
    claim_type: ClaimType
    verification_strategy: VerificationStrategy
    embed_url: str


def map_claim_type_to_strategy(claim_type: ClaimType) -> VerificationStrategy:
    empirical_types = {
        "empirical_technical",
        "empirical_historical",
        "empirical_scientific",
    }

    if claim_type in empirical_types:
        return "literature_review"

    if claim_type == "predictive":
        return "future_tracking"

    if claim_type in {"interpretive", "anecdotal"}:
        return "source_context_review"

    if claim_type == "normative":
        return "no_external_verification"

    raise ValueError(f"Unsupported claim type: {claim_type}")


def verify_verbatim_quote(
    source_text: str,
    verbatim_quote: str,
    char_start: int,
    char_end: int,
) -> bool:
    if char_start < 0 or char_end < 0:
        return False

    if char_end <= char_start:
        return False

    if char_end > len(source_text):
        return False

    return source_text[char_start:char_end] == verbatim_quote


def build_claim_embed_url(
    embed_base_url: str,
    clip: AnchorClip,
) -> str:
    if clip.start < 0:
        raise ValueError("Clip start cannot be negative.")

    if clip.end <= clip.start:
        raise ValueError("Clip end must be greater than clip start.")

    start = int(clip.start)
    end = int(clip.end)

    separator = "&" if "?" in embed_base_url else "?"

    return f"{embed_base_url}{separator}start={start}&end={end}&rel=0"


def create_claim_record(
    claim_id: str,
    source_text: str,
    verbatim_quote: str,
    anchor_chunk: str,
    char_offset_start: int,
    char_offset_end: int,
    anchor_clip: AnchorClip,
    claim_type: ClaimType,
    embed_base_url: str,
) -> ClaimRecord | None:
    is_verbatim = verify_verbatim_quote(
        source_text=source_text,
        verbatim_quote=verbatim_quote,
        char_start=char_offset_start,
        char_end=char_offset_end,
    )

    if not is_verbatim:
        return None

    verification_strategy = map_claim_type_to_strategy(claim_type)
    embed_url = build_claim_embed_url(embed_base_url, anchor_clip)

    return ClaimRecord(
        claim_id=claim_id,
        verbatim_quote=verbatim_quote,
        anchor_chunk=anchor_chunk,
        char_offset_start=char_offset_start,
        char_offset_end=char_offset_end,
        anchor_clip=anchor_clip,
        claim_type=claim_type,
        verification_strategy=verification_strategy,
        embed_url=embed_url,
    )


def claim_record_to_dict(record: ClaimRecord) -> dict:
    return asdict(record)

def build_claim_inventory(
    candidate_claims: list[dict],
    source_text_by_chunk_id: dict[str, str],
    embed_base_url: str,
) -> list[ClaimRecord]:
    inventory: list[ClaimRecord] = []

    for candidate in candidate_claims:
        if not validate_candidate_claim(candidate):
            continue

        anchor_chunk = candidate["anchor_chunk"]

        if anchor_chunk not in source_text_by_chunk_id:
            continue

        source_text = source_text_by_chunk_id[anchor_chunk]

        anchor_clip = AnchorClip(
            start=float(candidate["anchor_clip"]["start"]),
            end=float(candidate["anchor_clip"]["end"]),
        )

        record = create_claim_record(
            claim_id=candidate["claim_id"],
            source_text=source_text,
            verbatim_quote=candidate["verbatim_quote"],
            anchor_chunk=anchor_chunk,
            char_offset_start=int(candidate["char_offset_start"]),
            char_offset_end=int(candidate["char_offset_end"]),
            anchor_clip=anchor_clip,
            claim_type=candidate["claim_type"],
            embed_base_url=embed_base_url,
        )

        if record is not None:
            inventory.append(record)

    return inventory

REQUIRED_CANDIDATE_CLAIM_FIELDS = {
    "claim_id",
    "verbatim_quote",
    "anchor_chunk",
    "char_offset_start",
    "char_offset_end",
    "anchor_clip",
    "claim_type",
}


def validate_candidate_claim(candidate: dict) -> bool:
    if not isinstance(candidate, dict):
        return False

    missing_fields = REQUIRED_CANDIDATE_CLAIM_FIELDS - set(candidate.keys())

    if missing_fields:
        return False

    if not isinstance(candidate["claim_id"], str) or not candidate["claim_id"].strip():
        return False

    if not isinstance(candidate["verbatim_quote"], str) or not candidate["verbatim_quote"].strip():
        return False

    if not isinstance(candidate["anchor_chunk"], str) or not candidate["anchor_chunk"].strip():
        return False

    if not isinstance(candidate["char_offset_start"], int):
        return False

    if not isinstance(candidate["char_offset_end"], int):
        return False

    if not isinstance(candidate["anchor_clip"], dict):
        return False

    if "start" not in candidate["anchor_clip"] or "end" not in candidate["anchor_clip"]:
        return False

    if candidate["claim_type"] not in {
        "empirical_technical",
        "empirical_historical",
        "empirical_scientific",
        "interpretive",
        "normative",
        "anecdotal",
        "predictive",
    }:
        return False

    return True