"""Terms of Service and Privacy Policy: JSON for the app, HTML for app stores and browsers."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api.deps import ContainerDep, RulesDep
from app.legal import LegalDoc, build
from app.schemas.misc import LegalDocOut

router = APIRouter(prefix="/legal", tags=["legal"])
# Public pages outside /v1 so the URLs stay stable across API versions (they go in the store listings).
pages = APIRouter(prefix="/legal", include_in_schema=False)
_templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[2] / "templates"),
    autoescape=select_autoescape(["html"]),
)


@router.get("/{doc}", response_model=LegalDocOut)
async def legal_json(doc: LegalDoc, rules: RulesDep, c: ContainerDep) -> dict:
    return build(doc, c.settings, rules).as_json()


@pages.get("/{doc}", response_class=HTMLResponse)
async def legal_page(doc: LegalDoc, rules: RulesDep, c: ContainerDep) -> HTMLResponse:
    document = build(doc, c.settings, rules).as_json()
    other = LegalDoc.PRIVACY if doc is LegalDoc.TERMS else LegalDoc.TERMS
    html = _templates.get_template("legal.html").render(
        doc=document,
        app_name=c.settings.app_name,
        other_doc=other.value,
        other_title=build(other, c.settings, rules).title,
    )
    return HTMLResponse(html)
