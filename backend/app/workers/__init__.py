"""Asynchronous workers.

Workers run background tasks: entity extraction, relationship proposal, and graph
indexing. They are *producers of proposals*, never of confirmed conclusions —
everything a worker proposes is routed through the review queue. See
``docs/analyst_workflow.md``.

The skeleton ships one illustrative worker (``relationship_proposer``) and a task
registry. No scheduler is wired up; tasks are plain callables that can be invoked
directly or, later, from a queue.
"""
