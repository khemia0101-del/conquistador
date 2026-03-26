"""Partner/contractor application routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.contractor import Contractor
from conquistador.web.auth import hash_password
from conquistador.comms.telegram_bot import send_admin_alert
from conquistador.config import BASE_DIR

router = APIRouter(tags=["partners"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class PartnerApplication(BaseModel):
    company_name: str
    contact_name: str
    phone: str
    email: str
    address: str | None = None
    license_number: str | None = None
    service_types: list[str]
    service_zips: list[str]
    password: str


@router.get("/partners", response_class=HTMLResponse)
async def partners_page(request: Request):
    return templates.TemplateResponse("partners.html", {"request": request})


@router.post("/api/partners/apply")
async def apply(data: PartnerApplication, db: AsyncSession = Depends(get_db)):
    contractor = Contractor(
        company_name=data.company_name,
        contact_name=data.contact_name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        license_number=data.license_number,
        service_types=data.service_types,
        service_zips=data.service_zips,
        password_hash=hash_password(data.password),
        is_active=False,  # Must be activated after vetting
    )
    db.add(contractor)
    await db.commit()
    await db.refresh(contractor)

    # Alert admin of new application
    await send_admin_alert(
        f"<b>New Contractor Application</b>\n"
        f"Company: {data.company_name}\n"
        f"Contact: {data.contact_name}\n"
        f"Phone: {data.phone}\n"
        f"Services: {', '.join(data.service_types)}\n"
        f"Areas: {', '.join(data.service_zips[:5])}{'...' if len(data.service_zips) > 5 else ''}"
    )

    return {
        "status": "submitted",
        "message": "Thank you for applying! We'll review your application and contact you within 48 hours.",
    }
