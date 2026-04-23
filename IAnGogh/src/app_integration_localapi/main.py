from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn

from app_core.services import (
    application_service,
    backup_service,
    document_service,
    job_service,
    profile_service,
)
from app_infrastructure.config import CONFIG
from app_infrastructure.mongo import mongo

app = FastAPI(title="IAnGogh Local API", version="0.1.0")
templates = Jinja2Templates(directory=str((CONFIG.base_dir / "src" / "app_desktop" / "templates")))

I18N = {
    "es": {
        "title": "IAnGogh MVP",
        "profiles": "Perfiles",
        "jobs": "Vacantes",
        "applications": "Postulaciones Pendientes",
        "manual": "Revisión Manual",
    },
    "en": {
        "title": "IAnGogh MVP",
        "profiles": "Profiles",
        "jobs": "Jobs",
        "applications": "Pending Applications",
        "manual": "Manual Review",
    },
}


@app.get("/")
def dashboard(
    request: Request,
    lang: str = Query(default=CONFIG.app_locale, pattern="^(es|en)$"),
    theme: str = Query(default=CONFIG.app_theme, pattern="^(light|dark)$"),
):
    t = I18N.get(lang, I18N["es"])
    active = profile_service.get_active_profile()
    jobs = job_service.list_by_profile(active["profileId"]) if active else []

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "t": t,
            "theme": theme,
            "active": active,
            "profiles": profile_service.list_profiles(),
            "jobs": jobs,
            "applications": application_service.pending(),
            "manual": application_service.list_manual_review(),
        },
    )


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "IAnGogh",
        "version": "0.1.0",
        "dbBackend": mongo.backend,
    }


@app.get("/api/profiles")
def list_profiles():
    return profile_service.list_profiles()


@app.post("/api/profiles")
def create_profile(payload: dict):
    display_name = payload.get("displayName")
    if not display_name:
        raise HTTPException(status_code=400, detail="displayName is required")
    return profile_service.create_profile(display_name, payload.get("professionalTitle", ""))


@app.post("/api/profiles/{profile_id}/activate")
def activate_profile(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    profile_service.set_active_profile(profile_id)
    return {"ok": True, "activeProfileId": profile_id}


@app.get("/api/profiles/active")
def get_active_profile():
    profile = profile_service.get_active_profile()
    if not profile:
        return JSONResponse(status_code=404, content={"detail": "No active profile"})
    return profile


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@app.post("/api/profiles/{profile_id}/personal-info")
def upsert_personal(profile_id: str, payload: dict):
    payload["profileId"] = profile_id
    profile_service.upsert_personal_info(payload)
    return {"ok": True}


@app.get("/api/jobs/pending-search")
def jobs_pending_search():
    return job_service.pending_search()


@app.post("/api/jobs/extracted")
def jobs_extracted(payload: dict):
    jobs = payload.get("jobs", [])
    count = job_service.add_extracted_jobs(jobs)
    return {"ok": True, "upserts": count}


@app.post("/api/jobs/scored")
def jobs_scored(payload: dict):
    jobs = payload.get("jobs", [])
    count = job_service.add_extracted_jobs(jobs)
    return {"ok": True, "updated": count}


@app.get("/api/applications/pending")
def applications_pending():
    return application_service.pending()


@app.post("/api/applications/result")
def application_result(payload: dict):
    application_service.upsert_result(payload)
    return {"ok": True}


@app.post("/api/applications/manual-review")
def application_manual_review(payload: dict):
    application_service.manual_review(payload)
    return {"ok": True}


@app.get("/api/documents/profile/{profile_id}")
def documents_by_profile(profile_id: str):
    return document_service.list_documents(profile_id)


@app.post("/api/documents/ingest")
def ingest_document(payload: dict):
    required = ["profileId", "sourcePath"]
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"{field} is required")
    doc = document_service.ingest_document(
        profile_id=payload["profileId"],
        source_path=payload["sourcePath"],
        category=payload.get("category", "cv"),
        tags=payload.get("tags", []),
        is_favorite=payload.get("isFavorite", False),
    )
    return doc


@app.get("/api/resumes/best-for-profile/{profile_id}")
def best_resume(profile_id: str):
    docs = document_service.list_documents(profile_id)
    preferred = [d for d in docs if d.get("category") in {"cv", "resume"}]
    if not preferred:
        return JSONResponse(status_code=404, content={"detail": "No resume found"})
    return preferred[0]


@app.post("/api/logs/rpa")
def rpa_logs(payload: dict):
    return {"ok": True, "received": payload.get("message", "")[:120]}


@app.post("/api/captcha/waiting")
def captcha_waiting(payload: dict):
    application_service.manual_review({
        "type": "captcha_waiting",
        "payload": payload,
    })
    return {"ok": True}


@app.post("/api/captcha/resolved")
def captcha_resolved(payload: dict):
    return {"ok": True, "applicationId": payload.get("applicationId")}


@app.post("/api/backup/export")
def backup_export(payload: dict | None = None):
    bundle = backup_service.export_bundle(password_hint=(payload or {}).get("passwordHint", ""))
    return {"ok": True, "bundlePath": bundle}


@app.post("/api/backup/import")
def backup_import(_payload: dict):
    # MVP intentionally guarded: import validation path to be completed next iteration.
    return {"ok": False, "message": "Import pipeline pending validation implementation."}


@app.get("/api/contracts/active-profile")
def active_profile_contract():
    payload = profile_service.get_exportable_active_profile()
    if not payload:
        return JSONResponse(status_code=404, content={"detail": "No active profile"})
    return payload


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8787)


if __name__ == "__main__":
    run()
