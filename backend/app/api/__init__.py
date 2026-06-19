"""HTTP API layer.

Routing, request/response schemas, and validation only. The API never touches a
database driver directly; it calls services, which own the ontology rules.
"""
