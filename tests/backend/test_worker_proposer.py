"""The relationship-proposer worker proposes, and only proposes."""

from __future__ import annotations

from app.models.enums import Origin, ReviewStatus
from app.workers.relationship_proposer import propose_shared_phone_relationships
from app.workers.tasks import get_task, registered_tasks


def test_task_is_registered():
    assert "propose_shared_phone" in registered_tasks()
    assert get_task("propose_shared_phone") is propose_shared_phone_relationships


def test_proposer_only_proposes():
    # The seed already has a shared_phone relationship between the two ads, so the
    # proposer should not duplicate it.
    proposed = propose_shared_phone_relationships()
    for rel in proposed:
        assert rel.origin is Origin.SYSTEM_PROPOSED
        assert rel.status is ReviewStatus.PROPOSED  # never confirmed by a worker
