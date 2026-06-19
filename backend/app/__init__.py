"""ORCA backend application package.

ORCA preserves observations, discovers relationships, and maintains institutional
intelligence memory. This package is organized in layers — api, services,
repositories, models, schemas, workers, collection — with dependencies pointing
strictly downward (api -> services -> repositories -> stores).
"""

__version__ = "0.1.0"
