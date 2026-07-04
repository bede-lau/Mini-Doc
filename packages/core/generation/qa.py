"""Grounded Q&A with abstention.

Three layers, all returning the same Answer schema:
  * qa()              — orchestration: retrieve -> (LLM | offline) -> validate
  * build_api_answer  — validate/ground an LLM JSON answer against retrieved hits
  * extractive_answer — deterministic offline grounding (the default; no API key)

Grounding is enforced structurally: a supported answer can only be built from
citations that exist in the retrieved chunks. Anything else becomes abstention.
"""
from __future__ import annotations

import json
import re

from packages.core.config import Settings, get_settings
from packages.core.generation.llm_adapter import ABSTAIN_TEXT, GROUNDING_SYSTEM_PROMPT, LLMClient
from packages.core.schemas.evidence import Answer, Citation, Claim, RetrievalHit
from packages.core.utils.logging import get_logger

log = get_logger(__name__)

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "be", "as",
    "by", "with", "what", "which", "who", "whom", "whose", "how", "why", "when", "where",
    "does", "do", "did", "can", "could", "should", "would", "will", "shall", "may", "must",
    "this", "that", "these", "those", "it", "its", "their", "there", "then", "than", "from",
    "into", "about", "under", "over", "any", "all", "per", "list", "give", "tell", "show",
}
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]{1,}")
_SECTION_PREFIX = re.compile(r"^\s*(?:\d+(?:\.\d+)*[\).\-\s]+|[A-Za-z][\).\-]\s*)")
_ACTION_START = {
    "approving",
    "apprising",
    "assessing",
    "establishing",
    "ensuring",
    "giving",
    "maintaining",
    "managing",
    "monitoring",
    "reviewing",
    "setting",
    "undertaking",
}


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def _sentences(text: str) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in _SENT_SPLIT.split(text) if p and p.strip()]


def _terms(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD.finditer(text or "") if m.group(0).lower() not in _STOP}


def _score_sentence(sentence: str, qterms: set[str]) -> int:
    if not qterms:
        return 0
    st = _terms(sentence)
    return len(qterms & st)


def _word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


def _is_heading_like(sentence: str) -> bool:
    """Reject section labels/TOC fragments that are not usable answer text."""
    cleaned = re.sub(r"\s+", " ", sentence or "").strip()
    if not cleaned:
        return True
    words = _WORD.findall(cleaned)
    if len(words) <= 4:
        return True
    starts_numbered = bool(re.match(r"^\s*\d+(?:\.\d+)*\s+", cleaned))
    lacks_terminal_punctuation = cleaned[-1:] not in ".;:?!"
    starts_action = words[0].lower() in _ACTION_START if words else False
    if starts_numbered and lacks_terminal_punctuation and len(words) <= 10:
        return True
    if lacks_terminal_punctuation and len(words) <= 8 and not starts_action:
        return True
    return False


def _clean_answer_line(sentence: str) -> str:
    cleaned = re.sub(r"\s+", " ", sentence or "").strip()
    cleaned = _SECTION_PREFIX.sub("", cleaned).strip()
    if not cleaned:
        return sentence.strip()
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1:] in ";,":
        cleaned = cleaned[:-1].rstrip() + "."
    if cleaned[-1:] not in ".;:?!":
        cleaned += "."
    return cleaned


def _format_extractive_answer(chosen: list[tuple[RetrievalHit, str]]) -> str:
    if not chosen:
        return ABSTAIN_TEXT
    if len(chosen) == 1:
        return _clean_answer_line(chosen[0][1])
    lines = ["Based on the cited evidence:"]
    lines.extend(f"- {_clean_answer_line(sent)}" for _, sent in chosen)
    return "\n".join(lines)


def _norm(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.lower()).strip()


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple] = set()
    out: list[Citation] = []
    for c in citations:
        key = (c.filename, c.page, c.chunk_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _abstain(question: str, hits: list[RetrievalHit]) -> Answer:
    return Answer(
        question=question,
        answer_type="insufficient_evidence",
        answer=ABSTAIN_TEXT,
        retrieved_chunks=hits,
    )


# --------------------------------------------------------------------------- #
# Offline (deterministic) grounded answer
# --------------------------------------------------------------------------- #
def extractive_answer(
    question: str, hits: list[RetrievalHit], settings: Settings | None = None
) -> Answer:
    """Build a grounded answer purely from retrieved chunks.

    Picks the highest term-overlap sentences from the top hits and cites the
    exact chunk each came from. Abstains when retrieval is too weak or when no
    sentence shares terminology with the question.
    """
    s = settings or get_settings()
    if not hits:
        return _abstain(question, hits)
    if hits[0].score < s.abstention_threshold:
        return _abstain(question, hits)

    qterms = _terms(question)
    scored: list[tuple[int, RetrievalHit, str]] = []
    for hit in hits[:6]:
        for sent in _sentences(hit.chunk_text):
            if len(sent) < 15:
                continue
            if _is_heading_like(sent):
                continue
            sc = _score_sentence(sent, qterms)
            if sc > 0:
                scored.append((sc, hit, sent))

    if not scored:
        return _abstain(question, hits)

    scored.sort(
        key=lambda t: (
            -t[0],
            -min(_word_count(t[2]), 60),
            -t[1].score,
        )
    )
    chosen: list[tuple[RetrievalHit, str]] = []
    seen: set[str] = set()
    for sc, hit, sent in scored:
        key = _norm(sent)
        if key in seen:
            continue
        seen.add(key)
        chosen.append((hit, sent))
        if len(chosen) >= 3:
            break

    claims: list[Claim] = []
    citations: list[Citation] = []
    for i, (hit, sent) in enumerate(chosen, start=1):
        cit = Citation(filename=hit.filename, page=hit.page_start, chunk_id=hit.chunk_id, section=hit.section)
        claims.append(Claim(claim_id=f"claim_{i:03d}", claim_text=sent, citations=[cit]))
        citations.append(cit)

    return Answer(
        question=question,
        answer_type="supported",
        answer=_format_extractive_answer(chosen),
        claims=claims,
        citations=_dedupe_citations(citations),
        retrieved_chunks=hits,
    )


# --------------------------------------------------------------------------- #
# LLM answer grounding / validation
# --------------------------------------------------------------------------- #
def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Balanced-brace fallback.
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def build_api_answer(
    question: str, raw: str, hits: list[RetrievalHit], settings: Settings | None = None
) -> Answer:
    """Ground and validate an LLM-produced JSON answer.

    Claims referencing chunks that were NOT retrieved are dropped. If nothing
    survives grounding, we fall back to the deterministic extractive answer so
    the response is never an unsupported hallucination.
    """
    s = settings or get_settings()
    data = _extract_json(raw)
    if data is None:
        log.warning("LLM output was not valid JSON; degrading to extractive.")
        return extractive_answer(question, hits, s)

    answer_type = data.get("answer_type", "supported")
    answer_text = (data.get("answer") or "").strip()

    if answer_type == "insufficient_evidence":
        return _abstain(question, hits)

    by_id = {h.chunk_id: h for h in hits}
    claims: list[Claim] = []
    citations: list[Citation] = []
    for i, c in enumerate(data.get("claims", []) or [], start=1):
        cids = c.get("chunk_ids") or []
        valid = [by_id[cid] for cid in cids if cid in by_id]
        if not valid:
            continue  # ungrounded claim — discarded
        cs = [
            Citation(filename=h.filename, page=h.page_start, chunk_id=h.chunk_id, section=h.section)
            for h in valid
        ]
        claims.append(
            Claim(
                claim_id=c.get("claim_id") or f"claim_{i:03d}",
                claim_text=(c.get("claim_text") or "").strip(),
                citations=cs,
            )
        )
        citations.extend(cs)

    if not claims or not citations:
        return extractive_answer(question, hits, s)

    atype = "conflicting_evidence" if answer_type == "conflicting_evidence" else "supported"
    return Answer(
        question=question,
        answer_type=atype,  # type: ignore[arg-type]
        answer=answer_text or " ".join(cl.claim_text for cl in claims),
        claims=claims,
        citations=_dedupe_citations(citations),
        retrieved_chunks=hits,
    )


def _build_user_prompt(question: str, hits: list[RetrievalHit]) -> str:
    lines = [
        "Answer the question using ONLY the evidence below.",
        "Return a JSON object with this exact shape:",
        '{"answer_type":"supported|insufficient_evidence|conflicting_evidence",'
        '"answer":"...","claims":[{"claim_text":"...","chunk_ids":["..."]}]}',
        "Every claim MUST list at least one chunk_id from the evidence. If the "
        "evidence does not support an answer, use answer_type "
        '"insufficient_evidence".',
        "",
        f"QUESTION: {question}",
        "",
        "EVIDENCE:",
    ]
    for h in hits:
        snippet = (h.chunk_text or "").strip().replace("\n", " ")
        if len(snippet) > 900:
            snippet = snippet[:900] + "…"
        lines.append(
            f"[EVIDENCE id={h.chunk_id} file={h.filename} page={h.page_start}] {snippet}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def qa(
    question: str,
    retriever,
    *,
    top_k: int | None = None,
    filters: dict | None = None,
    settings: Settings | None = None,
) -> Answer:
    """End-to-end Q&A: retrieve, then ground (LLM if configured, else offline)."""
    s = settings or get_settings()
    hits = retriever.retrieve(question, top_k=top_k or s.top_k, filters=filters)

    if s.effective_llm_provider == "offline":
        return extractive_answer(question, hits, s)

    try:
        client = LLMClient(s)
        raw = client.complete(GROUNDING_SYSTEM_PROMPT, _build_user_prompt(question, hits))
        return build_api_answer(question, raw, hits, s)
    except Exception as exc:  # never crash the API/benchmark on a model hiccup
        log.warning("LLM path failed (%s); degrading to deterministic extractive.", exc)
        return extractive_answer(question, hits, s)
