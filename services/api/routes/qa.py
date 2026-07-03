"""Search and grounded Q&A routes."""
from __future__ import annotations

from fastapi import APIRouter

from packages.core.generation.qa import qa as run_qa
from packages.core.schemas.api import QARequest, SearchRequest, SearchResponse
from packages.core.schemas.evidence import Answer
from services.api.state import get_retriever_or_503

router = APIRouter(tags=["qa"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    retriever = get_retriever_or_503()
    hits = retriever.retrieve(req.query, top_k=req.top_k, filters=req.filters)
    return SearchResponse(query=req.query, hits=hits, total=len(hits))


@router.post("/qa", response_model=Answer)
def answer(req: QARequest) -> Answer:
    retriever = get_retriever_or_503()
    return run_qa(req.question, retriever, top_k=req.top_k, filters=req.filters)
