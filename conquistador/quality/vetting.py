"""Contractor vetting checks."""

import logging

logger = logging.getLogger(__name__)

VETTING_REQUIREMENTS = [
    "Valid PA contractor license (HVAC) or fuel dealer permit (oil delivery)",
    "General liability insurance ($1M minimum) and workers' compensation",
    "Minimum 2 years in business",
    "Minimum 3.5 star average on Google, Yelp, or Angi",
    "No unresolved BBB complaints",
    "Agree to Conquistador service standards and response time commitments",
    "Provide technician photo/ID for customer verification",
]


def check_vetting_completeness(contractor_data: dict) -> list[str]:
    """Check which vetting requirements are missing. Returns list of missing items."""
    missing = []

    if not contractor_data.get("license_number"):
        missing.append("PA contractor license or fuel dealer permit number")

    if not contractor_data.get("insurance_verified"):
        missing.append("Insurance verification (liability + workers' comp)")

    if not contractor_data.get("service_types"):
        missing.append("Service types offered")

    if not contractor_data.get("service_zips"):
        missing.append("Service area zip codes")

    if not contractor_data.get("phone"):
        missing.append("Contact phone number")

    return missing
