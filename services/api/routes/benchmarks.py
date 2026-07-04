"""Benchmark run + results routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.core.evaluation.benchmark import delete_run, list_runs, load_run_result, run_benchmark
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


@router.get("/benchmarks/results/{run_id}")
def result(run_id: str) -> dict:
    try:
        return load_run_result(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/benchmarks/results/{run_id}")
def delete(run_id: str) -> dict:
    try:
        return delete_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
