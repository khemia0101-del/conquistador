"""Marketing Agent — SEO optimization, content generation, ad monitoring.

Runs as a Celery Beat scheduled task (daily).
"""

import logging
from conquistador.ai.engine import get_ai_engine

logger = logging.getLogger(__name__)

SEO_CITIES = [
    {"city": "Lancaster", "state": "PA", "slug": "lancaster"},
    {"city": "York", "state": "PA", "slug": "york"},
    {"city": "Harrisburg", "state": "PA", "slug": "harrisburg"},
    {"city": "Lebanon", "state": "PA", "slug": "lebanon"},
    {"city": "Reading", "state": "PA", "slug": "reading"},
]

CONTENT_PROMPT = """Generate a short, SEO-optimized paragraph (3-4 sentences) about {service} services
in {city}, {state}. Focus on local keywords and include a call to action mentioning Conquistador Oil,
Heating & Air Conditioning. Keep it natural and helpful."""


async def generate_city_content(city: str, state: str, service: str) -> str:
    """Generate SEO content for a city/service page."""
    engine = get_ai_engine()
    prompt = CONTENT_PROMPT.format(city=city, state=state, service=service)
    return await engine.chat(
        [{"role": "user", "content": prompt}],
        "You are an SEO copywriter for a heating oil and HVAC company in Central Pennsylvania.",
        max_tokens=200,
    )


async def run_daily_marketing_tasks():
    """Run daily marketing agent tasks."""
    logger.info("Marketing agent: running daily tasks")
    # Future: auto-generate social posts, monitor search rankings, etc.
    logger.info("Marketing agent: daily tasks complete")
