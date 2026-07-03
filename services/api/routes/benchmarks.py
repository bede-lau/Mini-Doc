"""Benchmark run + results routes."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from packages.core.evaluation.benchmark import list_runs, run_benchmark
from services.api.state import get_retriever_or_503

router = APIRouter(tags=["benchmarks"])


class BenchmarkRunRequest(BaseModel):
    run_id: str = "run_001"


@router.post("/benchmarks/run")
def run(req: BenchmarkRunRequest) -> dict:
    retriever = get_retriever_or_503()
    return run_benchmark(run_id=req.run_id, retriever=retriever)


@router.get("/benchmarks/results")
def results() -> dict:
    return {"runs": list_runs()}
