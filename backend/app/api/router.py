"""Aggregate router mounted under the configured API prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    cases,
    clusters,
    dashboard,
    entities,
    evidence,
    graph,
    health,
    observations,
    relationships,
    reports,
    review,
    sources,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(cases.router)
api_router.include_router(observations.router)
api_router.include_router(entities.router)
api_router.include_router(relationships.router)
api_router.include_router(clusters.router)
api_router.include_router(review.router)
api_router.include_router(evidence.router)
api_router.include_router(reports.router)
api_router.include_router(graph.router)
api_router.include_router(sources.router)
