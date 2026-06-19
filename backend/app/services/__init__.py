"""Service layer — domain logic and the rules of the ontology.

Services depend only on repositories and the core modules. They are where the
ontology invariants live (an observation has a source; a relationship has supporting
observations; nothing reaches ``confirmed`` without an audited analyst action).
"""
