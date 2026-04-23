from __future__ import annotations

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
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

AREA_TAXONOMY = [
    "Administracion", "Agroindustria", "Analitica", "Arquitectura", "Atencion al cliente", "Auditoria",
    "Automatizacion", "Backend", "Banca", "Biotecnologia", "Business Intelligence", "Calidad",
    "Capacitacion", "Ciberseguridad", "Ciencia de datos", "Comercial", "Compras", "Comunicaciones",
    "Compliance", "Construccion", "Contabilidad", "Control de gestion", "DevOps", "Derecho",
    "Diseno UX", "Diseno UI", "Ecommerce", "Educacion", "Electricidad", "Energia",
    "Farmacia", "Finanzas", "Frontend", "Gestion de proyectos", "Gobierno TI", "Help Desk",
    "Hoteleria", "IA", "Infraestructura", "Ingenieria civil", "Ingenieria industrial", "Integraciones",
    "Investigacion", "IoT", "Legal", "Logistica", "Manufactura", "Marketing",
    "Mecanica", "Medicina", "Mineria", "Mobile", "Negocios", "Networking",
    "Operaciones", "Planeamiento", "Postventa", "Power BI", "Preventa", "Procurement",
    "Producto", "Produccion", "QA", "Recursos humanos", "Redes", "RPA",
    "SAP", "Salesforce", "Salud", "Seguridad", "Seguridad ocupacional", "Soporte TI",
    "SQL", "SRE", "Telecomunicaciones", "Testing", "Transformacion digital", "Transporte",
    "Turismo", "Ventas", "Vision por computadora", "Web", "WordPress", "Otros"
]

DISABILITY_TREE = {
    "auditiva": ["leve", "moderada", "severa", "profunda", "cofosis"],
    "fisica": ["hemiplejia", "paraplejia", "tetraplejia", "amputacion", "movilidad_reducida"],
    "habla": ["disartria", "afasia", "tartamudez", "apraxia_habla"],
    "mental": ["intelectual_leve", "intelectual_moderada", "intelectual_severa"],
    "psicosocial": ["ansiedad", "depresion", "bipolaridad", "esquizofrenia"],
    "rehabilitado": ["accidente_laboral", "enfermedad_profesional", "post_quirurgico"],
    "visual": ["baja_vision", "ceguera_parcial", "ceguera_total", "daltonismo_severo"],
}

I18N = {
    "es": {
        "title": "IAnGogh MVP",
        "profiles": "Perfiles",
        "jobs": "Vacantes",
        "applications": "Postulaciones Pendientes",
        "manual": "Revision Manual",
    },
    "en": {
        "title": "IAnGogh MVP",
        "profiles": "Profiles",
        "jobs": "Jobs",
        "applications": "Pending Applications",
        "manual": "Manual Review",
    },
}


def _csv_to_list(raw: str) -> list[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


@app.get("/")
def dashboard(
    request: Request,
    lang: str = Query(default=CONFIG.app_locale, pattern="^(es|en)$"),
    theme: str = Query(default=CONFIG.app_theme, pattern="^(light|dark)$"),
):
    t = I18N.get(lang, I18N["es"])
    active = profile_service.get_active_profile()
    jobs = job_service.list_by_profile(active["profileId"]) if active else []

    personal = {}
    disability = {}
    professional = {}
    experiences = []
    education = []
    courses = []
    languages = []
    skills = []
    documents = []

    if active:
        profile_id = active["profileId"]
        personal = profile_service.get_personal_info(profile_id)
        disability = profile_service.get_disability_info(profile_id)
        professional = profile_service.get_professional_header(profile_id)
        experiences = profile_service.list_experiences(profile_id)
        education = profile_service.list_education(profile_id)
        courses = profile_service.list_courses(profile_id)
        languages = profile_service.list_languages(profile_id)
        skills = profile_service.list_skills(profile_id)
        documents = document_service.list_documents(profile_id)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "t": t,
            "theme": theme,
            "active": active,
            "profiles": profile_service.list_profiles(),
            "jobs": jobs,
            "personal": personal,
            "disability": disability,
            "professional": professional,
            "experiences": experiences,
            "education": education,
            "courses": courses,
            "languages": languages,
            "skills": skills,
            "documents": documents,
            "applications": application_service.pending(),
            "manual": application_service.list_manual_review(),
            "area_taxonomy": AREA_TAXONOMY,
            "disability_tree": DISABILITY_TREE,
        },
    )


@app.post("/ui/profiles/create")
def ui_create_profile(
    display_name: str = Form(...),
    professional_title: str = Form(default=""),
):
    profile_service.create_profile(display_name=display_name, professional_title=professional_title)
    return RedirectResponse(url="/", status_code=303)


@app.post("/ui/profiles/{profile_id}/activate")
def ui_activate_profile(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if profile:
        profile_service.set_active_profile(profile_id)
    return RedirectResponse(url="/", status_code=303)


@app.post("/ui/profiles/{profile_id}/personal")
def ui_save_personal(
    profile_id: str,
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    display_name: str = Form(default=""),
    birth_date: str = Form(default=""),
    document_type: str = Form(default=""),
    document_type_other: str = Form(default=""),
    document_number: str = Form(default=""),
    email_personal: str = Form(default=""),
    email_university: str = Form(default=""),
    email_corporate: str = Form(default=""),
    email_others_csv: str = Form(default=""),
    phone_prefix: str = Form(default="+51"),
    phone_main: str = Form(default=""),
    phone_optional: str = Form(default=""),
    country_of_residence: str = Form(default=""),
    country_of_birth: str = Form(default=""),
    postal_code: str = Form(default=""),
    address: str = Form(default=""),
    gender: str = Form(default=""),
    has_children: str = Form(default="no"),
    marital_status: str = Form(default=""),
):
    selected_doc_type = document_type_other if document_type == "Otro" else document_type
    emails = [email_personal, email_university, email_corporate] + _csv_to_list(email_others_csv)
    phones = []
    if phone_main:
        phones.append(f"{phone_prefix} {phone_main}".strip())
    if phone_optional:
        phones.append(f"{phone_prefix} {phone_optional}".strip())

    payload = {
        "profileId": profile_id,
        "firstName": first_name,
        "lastName": last_name,
        "displayName": display_name,
        "birthDate": birth_date,
        "countryOfResidence": country_of_residence,
        "countryOfBirth": country_of_birth,
        "postalCode": postal_code,
        "address": address,
        "gender": gender,
        "maritalStatus": marital_status,
        "hasChildren": has_children == "si",
        "emails": [e for e in emails if e],
        "phones": phones,
        "documentType": selected_doc_type,
        "documentNumber": document_number,
    }
    profile_service.upsert_personal_info(payload)
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/disability")
def ui_save_disability(
    profile_id: str,
    has_disability: str = Form(default="no"),
    disability_types_csv: str = Form(default=""),
    disability_sublevels_csv: str = Form(default=""),
    disability_percentage: str = Form(default=""),
    accessibility_resources: str = Form(default=""),
    report_document_id: str = Form(default=""),
    consent_accepted: str = Form(default="no"),
):
    payload = {
        "hasDisability": has_disability == "si",
        "disabilityTypes": _csv_to_list(disability_types_csv),
        "disabilitySublevels": _csv_to_list(disability_sublevels_csv),
        "disabilityPercentage": disability_percentage,
        "accessibilityResources": accessibility_resources,
        "reportDocumentId": report_document_id,
        "consentAccepted": consent_accepted == "si",
    }
    profile_service.upsert_disability_info(profile_id, payload)
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/professional")
def ui_save_professional(
    profile_id: str,
    professional_title: str = Form(default=""),
    summary: str = Form(default=""),
    desired_roles_csv: str = Form(default=""),
):
    payload = {
        "professionalTitle": professional_title,
        "summary": summary,
        "desiredRoles": _csv_to_list(desired_roles_csv),
    }
    profile_service.upsert_professional_header(profile_id, payload)
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/experiences/add")
def ui_add_experience(
    profile_id: str,
    position: str = Form(default=""),
    company: str = Form(default=""),
    area: str = Form(default=""),
    start_date: str = Form(default=""),
    end_date: str = Form(default=""),
    is_current: str = Form(default="no"),
    description: str = Form(default=""),
    technologies_csv: str = Form(default=""),
    references: str = Form(default=""),
):
    profile_service.add_experience(
        profile_id,
        {
            "position": position,
            "company": company,
            "area": area,
            "startDate": start_date,
            "endDate": end_date,
            "isCurrent": is_current == "si",
            "description": description,
            "technologies": _csv_to_list(technologies_csv),
            "references": references,
        },
    )
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/education/add")
def ui_add_education(
    profile_id: str,
    level: str = Form(default=""),
    institution: str = Form(default=""),
    status: str = Form(default=""),
    grade_or_cycle: str = Form(default=""),
    condition: str = Form(default=""),
    start_date: str = Form(default=""),
    end_date: str = Form(default=""),
):
    profile_service.add_education(
        profile_id,
        {
            "level": level,
            "institution": institution,
            "status": status,
            "gradeOrCycle": grade_or_cycle,
            "condition": condition,
            "startDate": start_date,
            "endDate": end_date,
        },
    )
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/courses/add")
def ui_add_course(
    profile_id: str,
    name: str = Form(default=""),
    institution: str = Form(default=""),
    duration_hours: str = Form(default=""),
    duration_minutes: str = Form(default=""),
    start_date: str = Form(default=""),
    end_date: str = Form(default=""),
    is_certified: str = Form(default="no"),
    certification_url: str = Form(default=""),
):
    profile_service.add_course(
        profile_id,
        {
            "name": name,
            "institution": institution,
            "durationHours": duration_hours,
            "durationMinutes": duration_minutes,
            "startDate": start_date,
            "endDate": end_date,
            "isCertified": is_certified == "si",
            "certificationUrl": certification_url,
        },
    )
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/languages/add")
def ui_add_language(
    profile_id: str,
    name: str = Form(default=""),
    speaking_level: str = Form(default=""),
    listening_level: str = Form(default=""),
    writing_level: str = Form(default=""),
    is_self_taught: str = Form(default="no"),
):
    profile_service.add_language(
        profile_id,
        {
            "name": name,
            "speakingLevel": speaking_level,
            "listeningLevel": listening_level,
            "writingLevel": writing_level,
            "isSelfTaught": is_self_taught == "si",
        },
    )
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/profiles/{profile_id}/skills/add")
def ui_add_skill(
    profile_id: str,
    name: str = Form(default=""),
    category: str = Form(default=""),
    speaking_level: str = Form(default=""),
    listening_level: str = Form(default=""),
    writing_level: str = Form(default=""),
    self_assessment: str = Form(default=""),
    notes: str = Form(default=""),
):
    profile_service.add_skill(
        profile_id,
        {
            "name": name,
            "category": category,
            "speakingLevel": speaking_level,
            "listeningLevel": listening_level,
            "writingLevel": writing_level,
            "selfAssessment": self_assessment,
            "notes": notes,
        },
    )
    return RedirectResponse(url="/?tab=granular", status_code=303)


@app.post("/ui/documents/ingest")
def ui_ingest_document(
    profile_id: str = Form(...),
    source_path: str = Form(...),
    category: str = Form(default="cv"),
):
    try:
        document_service.ingest_document(profile_id=profile_id, source_path=source_path, category=category, is_favorite=True)
    except FileNotFoundError:
        pass
    return RedirectResponse(url="/", status_code=303)


@app.post("/ui/jobs/mock")
def ui_mock_job():
    active = profile_service.get_active_profile()
    if active:
        job_service.add_extracted_jobs(
            [
                {
                    "profileId": active["profileId"],
                    "sourcePortal": "LinkedIn",
                    "jobTitle": "Automation Engineer",
                    "company": "Demo Corp",
                    "location": "Lima",
                    "country": "Peru",
                    "workMode": "remote",
                    "salaryText": "S/ 7,000 - S/ 9,000",
                    "description": "Role created from dashboard for MVP flow testing",
                    "requirements": "Python, APIs, UiPath",
                    "technologiesRaw": "python,uipath,fastapi",
                    "technologiesNormalized": ["python", "uipath", "fastapi"],
                    "jobUrl": "https://example.com/mock-job",
                    "score": 85,
                    "priority": 1,
                    "matchedSkills": ["python", "uipath"],
                    "missingSkills": ["azure"],
                    "recommendation": "apply",
                    "duplicateKey": f"mock|demo|automation engineer|{active['profileId']}",
                }
            ]
        )
    return RedirectResponse(url="/", status_code=303)


@app.post("/ui/applications/mock")
def ui_mock_application():
    active = profile_service.get_active_profile()
    if active:
        jobs = job_service.list_by_profile(active["profileId"])
        if jobs:
            application_service.create_pending(
                profile_id=active["profileId"],
                job_id=jobs[0]["jobId"],
                portal=jobs[0]["sourcePortal"],
            )
    return RedirectResponse(url="/", status_code=303)


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
