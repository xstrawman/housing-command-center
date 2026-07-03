from __future__ import annotations

import logging
from datetime import date
from typing import TypedDict

from agents.db import briefing_exists, get_client, log_agent_run
from agents.outreach import draft_outreach_batch
from agents.strategist import select_daily_priorities, write_briefing

log = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    client_slug: str
    client_id: int
    client: dict
    briefing_date: str
    briefing_id: int
    analysis: dict
    outreach_ids: list[int]
    errors: list[str]
    status: str


def run_strategist(state: PipelineState) -> PipelineState:
    errors = list(state.get("errors", []))
    try:
        analysis = select_daily_priorities(state["client_id"])
        briefing_id = write_briefing(
            state["client_id"],
            analysis,
            state.get("briefing_date"),
        )
        log_agent_run(
            "strategist",
            "success",
            f"Briefing {briefing_id}: {len(analysis['tasks'])} tasks",
            {"briefing_id": briefing_id},
        )
        return {
            **state,
            "analysis": analysis,
            "briefing_id": briefing_id,
            "errors": errors,
        }
    except Exception as exc:
        log.exception("strategist failed")
        errors.append(f"strategist: {exc}")
        log_agent_run("strategist", "failed", str(exc))
        return {**state, "errors": errors, "status": "failed"}


def run_outreach(state: PipelineState) -> PipelineState:
    if state.get("status") == "failed":
        return state
    errors = list(state.get("errors", []))
    try:
        queue_ids = draft_outreach_batch(state["client_id"], state["client"])
        log_agent_run(
            "outreach_drafter",
            "success",
            f"Drafted {len(queue_ids)} outreach emails",
            {"queue_ids": queue_ids},
        )
        return {**state, "outreach_ids": queue_ids, "errors": errors}
    except Exception as exc:
        log.exception("outreach failed")
        errors.append(f"outreach: {exc}")
        log_agent_run("outreach_drafter", "failed", str(exc))
        return {**state, "errors": errors}


def run_daily_pipeline(
    client_slug: str = "chad-brizendine",
    *,
    force: bool = False,
    briefing_date: str | None = None,
) -> PipelineState:
    briefing_date = briefing_date or date.today().isoformat()
    client_row = get_client(client_slug)
    if not client_row:
        raise SystemExit(f"Client not found: {client_slug}")

    client_id = client_row["id"]
    if not force and briefing_exists(client_id, briefing_date):
        log.info("Briefing already exists for %s — use --force to regenerate", briefing_date)

    state: PipelineState = {
        "client_slug": client_slug,
        "client_id": client_id,
        "client": dict(client_row),
        "briefing_date": briefing_date,
        "errors": [],
        "outreach_ids": [],
    }

    state = run_strategist(state)
    state = run_outreach(state)
    state["status"] = "failed" if state.get("errors") else "success"
    return state