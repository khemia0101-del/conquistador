"""Public routes — homepage, services, areas, about, contact."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

SERVICE_AREAS = {
    "lancaster": {
        "city": "Lancaster",
        "state": "PA",
        "description": "Serving Lancaster County with heating oil delivery and HVAC services.",
        "zips": ["17601", "17602", "17603", "17604", "17605", "17606",
                 "17543", "17545", "17554", "17557", "17560", "17572", "17576", "17584"],
    },
    "york": {
        "city": "York",
        "state": "PA",
        "description": "Professional heating oil and HVAC services in York County.",
        "zips": ["17401", "17402", "17403", "17404", "17405", "17406", "17407"],
    },
    "harrisburg": {
        "city": "Harrisburg",
        "state": "PA",
        "description": "Reliable heating oil delivery and HVAC repair in the Harrisburg area.",
        "zips": ["17101", "17102", "17103", "17104", "17105", "17106",
                 "17107", "17108", "17109", "17110", "17111", "17112"],
    },
    "lebanon": {
        "city": "Lebanon",
        "state": "PA",
        "description": "Heating oil and HVAC services for Lebanon County residents.",
        "zips": ["17042", "17046"],
    },
    "reading": {
        "city": "Reading",
        "state": "PA",
        "description": "Serving Berks County with professional heating and cooling services.",
        "zips": ["19601", "19602", "19603", "19604", "19605", "19606",
                 "19607", "19608", "19609", "19610", "19611"],
    },
}


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    return templates.TemplateResponse("services.html", {"request": request})


@router.get("/areas", response_class=HTMLResponse)
async def areas(request: Request):
    return templates.TemplateResponse("areas.html", {"request": request, "areas": SERVICE_AREAS})


@router.get("/areas/{city}", response_class=HTMLResponse)
async def area_city(request: Request, city: str):
    area = SERVICE_AREAS.get(city.lower())
    if not area:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("areas/city.html", {"request": request, "area": area})


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})
