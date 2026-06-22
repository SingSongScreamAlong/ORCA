"""Hunting Grounds — continuous (scheduled) discovery.

The autonomous *cadence*: rather than waiting for an operator to press a button, ORCA can seek
across its AOR watchlist on a fixed interval, on its own. This is the strongest expression of
"let the machine do the trawling" — and it inherits every guardrail of the discovery engine:

* it runs a **sweep**, which only ever **proposes** (an administrator still authorizes each
  source before anything is monitored);
* it reaches out only through the **configured lawful source** (no scraping, no dark-web);
* it is **CSAM-safe** (text/metadata candidates only);
* it is **disabled by default** and gated twice — a config switch
  (``ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED``) to start the loop at all, plus a runtime
  **kill-switch** (``pause``) an administrator can flip without a redeploy.

Each automatic run is attributed to a clear ``system`` actor and recorded in the central audit
log (via the sweep), so an unattended cadence is still fully accountable.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.rbac import Role
from app.core.security import Principal
from app.repositories.uow import build_unit_of_work
from app.schemas.hunting import HuntingDiscoveryScheduleStatus, HuntingDiscoverySweepResult
from app.services.hunting_discovery import DiscoveryError, HuntingDiscoveryService

_DEFAULT_INTERVAL_MINUTES = 60
_MIN_INTERVAL_SECONDS = 60  # floor, so a misconfiguration can't busy-loop the source

# The unattended cadence acts as a clearly-labelled system identity (not a real person), so its
# proposals and audit entries are attributable without impersonating an operator.
SYSTEM_PRINCIPAL = Principal(
    id="system", username="system", display_name="Discovery Scheduler", role=Role.ANALYST
)


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DiscoveryScheduleConfig:
    """Cadence configuration, read from ``ORCA_HUNTING_DISCOVERY_SCHEDULE_*``. Off by default."""

    enabled: bool = False
    interval_minutes: int = _DEFAULT_INTERVAL_MINUTES
    limit_per_aor: int = 10

    @classmethod
    def from_env(cls, env: dict | None = None) -> DiscoveryScheduleConfig:
        env = os.environ if env is None else env
        interval = _as_int(
            env.get("ORCA_HUNTING_DISCOVERY_SCHEDULE_INTERVAL_MINUTES"), _DEFAULT_INTERVAL_MINUTES
        )
        return cls(
            enabled=_as_bool(env.get("ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED")),
            interval_minutes=max(1, interval),
            limit_per_aor=max(1, _as_int(env.get("ORCA_HUNTING_DISCOVERY_SCHEDULE_LIMIT"), 10)),
        )

    def interval_seconds(self) -> float:
        return max(_MIN_INTERVAL_SECONDS, self.interval_minutes * 60)


class DiscoveryScheduler:
    """Process-wide controller for the continuous discovery loop.

    Holds the runtime kill-switch (``paused``) and the rolling record of the last run. The loop
    itself is thin: it sleeps the interval and calls :meth:`run_once`. The same run path backs the
    admin "run now" endpoint, so the cadence and a manual trigger behave identically.
    """

    def __init__(self, config: DiscoveryScheduleConfig | None = None) -> None:
        self._config = config
        self.paused = False
        self.runs = 0
        self.last_run_at: datetime | None = None
        self.last_error: str | None = None
        self.last_summary: dict | None = None
        self._task: asyncio.Task | None = None

    def config(self) -> DiscoveryScheduleConfig:
        return self._config or DiscoveryScheduleConfig.from_env()

    def reset(self) -> None:
        """Clear runtime state (used by tests; does not touch the persistent registry)."""
        self.paused = False
        self.runs = 0
        self.last_run_at = None
        self.last_error = None
        self.last_summary = None

    # --- run recording -----------------------------------------------------------

    def record_run(self, sweep: HuntingDiscoverySweepResult) -> None:
        self.runs += 1
        self.last_run_at = datetime.now(UTC)
        self.last_error = None
        self.last_summary = {
            "aors": sweep.aors,
            "total_proposed": sweep.total_proposed,
            "total_skipped": sweep.total_skipped,
            "provider": sweep.provider,
        }

    def record_error(self, message: str) -> None:
        self.last_run_at = datetime.now(UTC)
        self.last_error = message

    # --- the run path (shared by the loop and "run now") -------------------------

    def run_once(self, principal: Principal = SYSTEM_PRINCIPAL) -> HuntingDiscoverySweepResult | None:
        """Run one sweep over the configured watchlist, recording the outcome.

        Builds its own unit of work and never raises for an expected discovery failure (disabled,
        no watchlist, upstream error) — those are recorded in ``last_error`` so the loop survives.
        Returns the sweep, or ``None`` if it failed.
        """
        cfg = self.config()
        uow = build_unit_of_work()
        try:
            sweep = HuntingDiscoveryService(uow).sweep(principal, limit_per_aor=cfg.limit_per_aor)
            uow.commit()
            self.record_run(sweep)
            return sweep
        except DiscoveryError as exc:  # disabled / no watchlist / upstream — message is secret-free
            uow.rollback()
            self.record_error(str(exc))
            return None
        except Exception:
            uow.rollback()
            raise
        finally:
            uow.close()

    # --- async loop lifecycle ----------------------------------------------------

    async def _loop(self) -> None:
        interval = self.config().interval_seconds()
        while True:
            await asyncio.sleep(interval)
            if self.paused:
                continue
            try:
                # Run the blocking sweep off the event loop so the API stays responsive.
                await asyncio.to_thread(self.run_once)
            except Exception as exc:  # noqa: BLE001 — the cadence must never die on one bad run
                self.record_error(f"Unexpected scheduler error: {exc!r}")

    def start(self) -> None:
        """Start the loop if the cadence is enabled (no-op otherwise, or if already running)."""
        if self._task is not None or not self.config().enabled:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    # --- status ------------------------------------------------------------------

    def status(self) -> HuntingDiscoveryScheduleStatus:
        cfg = self.config()
        summary = self.last_summary or {}
        return HuntingDiscoveryScheduleStatus(
            enabled=cfg.enabled,
            interval_minutes=cfg.interval_minutes,
            limit_per_aor=cfg.limit_per_aor,
            paused=self.paused,
            running=self.is_running(),
            runs=self.runs,
            last_run_at=self.last_run_at,
            last_error=self.last_error,
            last_total_proposed=summary.get("total_proposed"),
            last_total_skipped=summary.get("total_skipped"),
            last_aors=list(summary.get("aors", [])),
        )


# Process-wide singleton (the loop and the API share this state).
scheduler = DiscoveryScheduler()
