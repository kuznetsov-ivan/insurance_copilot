from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from insurance_copilot.dependencies import data_service

templates = Jinja2Templates(directory="src/insurance_copilot/templates")
router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"scenarios": data_service.scenarios()},
    )


@router.get("/notifications", response_class=HTMLResponse)
def notifications_app(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context={},
    )
