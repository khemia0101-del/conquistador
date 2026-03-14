"""Master Orchestrator Agent — coordinates all sub-agents, manages the full lifecycle.

This is the central brain that ties together intake, routing, contractor management,
customer service, revenue, and marketing agents into a unified autonomous pipeline.

Designed to run as a Celery Beat scheduler or be triggered on-demand via API.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from conquistador.agents.intake_agent import calculate_lead_score
from conquistador.agents.contractor_mgmt import (
    expire_stale_assignments,
    reset_daily_lead_counts,
)
from conquistador.agents.management_agent import run_hourly_audit, send_daily_summary
from conquistador.agents.customer_svc import send_pending_surveys
from conquistador.agents.revenue_agent import (
    generate_invoices_for_completed_leads,
    send_daily_revenue_report,
)
from conquistador.agents.marketing_agent import run_daily_marketing_tasks
from conquistador.comms.telegram_bot import send_admin_alert

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates all Conquistador agents into a unified pipeline.

    Lifecycle flow:
        1. INTAKE: Chatbot/form captures lead → scored by intake agent
        2. ROUTING: Lead matched to best contractors → cascade assignment
        3. CONTRACTOR MGMT: Accept/decline/expire handling
        4. SERVICE: Contractor performs the job
        5. CUSTOMER SVC: Post-service surveys, quality scoring
        6. REVENUE: Invoice generation, payment tracking
        7. MARKETING: SEO content, outreach (ongoing)
        8. MANAGEMENT: Hourly audits, daily KPI reports

    The orchestrator ensures each agent runs on schedule and handles
    cross-agent coordination (e.g. expired assignments trigger cascade,
    low quality scores trigger probation alerts).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._run_log: list[dict] = []

    def _log(self, agent: str, action: str, status: str = "ok", detail: str = ""):
        entry = {
            "agent": agent,
            "action": action,
            "status": status,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._run_log.append(entry)
        if status == "error":
            logger.error("%s.%s failed: %s", agent, action, detail)
        else:
            logger.info("%s.%s: %s", agent, action, status)

    async def _safe_run(self, agent: str, action: str, coro):
        """Run an agent task with error isolation — one failure doesn't stop others."""
        try:
            await coro
            self._log(agent, action)
        except Exception as e:
            self._log(agent, action, "error", str(e))

    # ── Scheduled Pipelines ──────────────────────────────────────────────

    async def run_minutely(self):
        """Run every minute: expire stale assignments."""
        await self._safe_run(
            "contractor_mgmt", "expire_stale_assignments",
            expire_stale_assignments(self.db),
        )

    async def run_hourly(self):
        """Run every hour: system audit, generate invoices."""
        await self._safe_run(
            "management", "hourly_audit",
            run_hourly_audit(self.db),
        )
        await self._safe_run(
            "revenue", "generate_invoices",
            generate_invoices_for_completed_leads(self.db),
        )

    async def run_daily(self):
        """Run daily at midnight: reset counts, surveys, revenue report, marketing."""
        await self._safe_run(
            "contractor_mgmt", "reset_daily_counts",
            reset_daily_lead_counts(self.db),
        )
        await self._safe_run(
            "customer_svc", "send_surveys",
            send_pending_surveys(self.db),
        )
        await self._safe_run(
            "revenue", "daily_report",
            send_daily_revenue_report(self.db),
        )
        await self._safe_run(
            "management", "daily_summary",
            send_daily_summary(self.db),
        )
        await self._safe_run(
            "marketing", "daily_tasks",
            run_daily_marketing_tasks(),
        )

    async def run_all(self):
        """Run every agent task — useful for testing or manual trigger."""
        await self.run_minutely()
        await self.run_hourly()
        await self.run_daily()
        return self._run_log

    # ── On-Demand Actions ────────────────────────────────────────────────

    async def process_new_lead(self, lead_data: dict) -> dict:
        """Full intake pipeline: score → create → route → webhook."""
        from conquistador.models.lead import Lead
        from conquistador.routing.matcher import route_lead
        from conquistador.web.routes.webhooks import fire_webhook

        score = calculate_lead_score(lead_data)
        lead = Lead(**lead_data, lead_score=score, source="orchestrator", status="new")
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)

        routed = await route_lead(lead, self.db)

        await fire_webhook("lead.created", {
            "id": lead.id,
            "service_type": lead.service_type,
            "zip_code": lead.zip_code,
            "urgency": lead.urgency,
            "lead_score": lead.lead_score,
            "status": lead.status,
        })

        self._log("orchestrator", "process_new_lead", detail=f"lead={lead.id} routed={routed}")
        return {"lead_id": lead.id, "score": score, "routed": routed, "status": lead.status}

    async def get_system_status(self) -> dict:
        """Get a snapshot of the entire system for dashboard display."""
        from sqlalchemy import select, func, and_
        from conquistador.models.lead import Lead
        from conquistador.models.contractor import Contractor
        from conquistador.models.assignment import LeadAssignment

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Leads today
        r = await self.db.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= today)
        )
        leads_today = r.scalar() or 0

        # Total active contractors
        r = await self.db.execute(
            select(func.count(Contractor.id)).where(Contractor.is_active.is_(True))
        )
        active_contractors = r.scalar() or 0

        # Pending contractors (registered but not yet activated)
        r = await self.db.execute(
            select(func.count(Contractor.id)).where(Contractor.is_active.is_(False))
        )
        pending_contractors = r.scalar() or 0

        # Pending assignments
        r = await self.db.execute(
            select(func.count(LeadAssignment.id)).where(LeadAssignment.status == "pending")
        )
        pending_assignments = r.scalar() or 0

        # Accepted today
        r = await self.db.execute(
            select(func.count(LeadAssignment.id)).where(
                and_(LeadAssignment.status == "accepted", LeadAssignment.responded_at >= today)
            )
        )
        accepted_today = r.scalar() or 0

        # Unmatched leads today
        r = await self.db.execute(
            select(func.count(Lead.id)).where(
                and_(Lead.status == "unmatched", Lead.created_at >= today)
            )
        )
        unmatched_today = r.scalar() or 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "leads_today": leads_today,
            "accepted_today": accepted_today,
            "unmatched_today": unmatched_today,
            "active_contractors": active_contractors,
            "pending_contractors": pending_contractors,
            "pending_assignments": pending_assignments,
        }
