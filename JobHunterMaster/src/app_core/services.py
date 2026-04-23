from __future__ import annotations

import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from app_domain.models import ApplicationAttempt, JobOpportunity, Profile
from app_infrastructure.config import CONFIG
from app_infrastructure.fs_utils import copy_file, ensure_profile_dirs, sha256_file
from app_infrastructure.mongo import mongo
from app_infrastructure.security import CryptoService


def _to_dict(model) -> dict:
    return model.model_dump(by_alias=True)


def write_placeholder_pdf(path: Path, title: str, details: list[str]) -> None:
    # Minimal PDF generator for MVP, dependency-free.
    text = [title, ""] + details
    lines = "\\n".join(text).replace("(", "[").replace(")", "]")
    stream = f"BT /F1 12 Tf 50 780 Td ({lines}) Tj ET"
    content = stream.encode("latin-1", errors="ignore")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(f"5 0 obj << /Length {len(content)} >> stream\n".encode() + content + b"\nendstream endobj\n")

    xref_offsets = []
    pdf = b"%PDF-1.4\n"
    for obj in objects:
        xref_offsets.append(len(pdf))
        pdf += obj

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for off in xref_offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf)


class ProfileService:
    def __init__(self) -> None:
        self.collection = mongo.db.profiles
        self.personal_collection = mongo.db.personal_info
        self.settings_collection = mongo.db.settings
        self.crypto = CryptoService()

    def create_profile(self, display_name: str, professional_title: str = "") -> dict:
        profile = Profile(
            profileId=str(uuid.uuid4()),
            displayName=display_name,
            professionalTitle=professional_title,
            targetTitles=[professional_title] if professional_title else [],
        )
        self.collection.insert_one(_to_dict(profile))
        return _to_dict(profile)

    def list_profiles(self) -> list[dict]:
        return list(self.collection.find({}, {"_id": 0}).sort("updatedAt", -1))

    def get_profile(self, profile_id: str) -> dict | None:
        return self.collection.find_one({"profileId": profile_id}, {"_id": 0})

    def set_active_profile(self, profile_id: str) -> None:
        self.collection.update_many({}, {"$set": {"isActive": False}})
        self.collection.update_one(
            {"profileId": profile_id},
            {"$set": {"isActive": True, "updatedAt": datetime.utcnow()}},
        )

    def get_active_profile(self) -> dict | None:
        return self.collection.find_one({"isActive": True}, {"_id": 0})

    def upsert_personal_info(self, payload: dict) -> None:
        profile_id = payload["profileId"]
        for field in ["address", "documentNumber"]:
            if payload.get(field):
                payload[f"{field}Encrypted"] = self.crypto.encrypt(payload[field])
                del payload[field]
        if payload.get("phones"):
            payload["phonesEncrypted"] = [self.crypto.encrypt(p) for p in payload["phones"]]
            del payload["phones"]
        self.personal_collection.update_one(
            {"profileId": profile_id}, {"$set": payload}, upsert=True
        )

    def get_exportable_active_profile(self) -> dict | None:
        profile = self.get_active_profile()
        if not profile:
            return None

        personal = self.personal_collection.find_one({"profileId": profile["profileId"]}, {"_id": 0}) or {}
        docs = list(
            mongo.db.documents.find(
                {"profileId": profile["profileId"], "isFavorite": True}, {"_id": 0}
            )
        )

        return {
            "identity": {
                "firstName": personal.get("firstName", ""),
                "lastName": personal.get("lastName", ""),
                "displayName": profile.get("displayName", ""),
            },
            "contact": {
                "emails": personal.get("emails", []),
                "phones": [],
            },
            "location": {
                "countryOfResidence": personal.get("countryOfResidence", ""),
                "preferredLocations": profile.get("preferredLocations", []),
            },
            "legalSensitiveAllowedFields": {
                "allowOptionalPhone": False,
                "allowDocumentNumber": False,
            },
            "profileSummary": {
                "professionalTitle": profile.get("professionalTitle", ""),
                "summary": profile.get("summary", ""),
            },
            "desiredRoles": profile.get("desiredRoles", []),
            "skills": [],
            "languages": [{"name": profile.get("primaryLanguage", "es")}],
            "workExperiences": [],
            "education": [],
            "preferredDocuments": [
                {
                    "documentId": d.get("documentId"),
                    "category": d.get("category"),
                    "pdfPath": d.get("pdfPath"),
                    "originalPath": d.get("originalPath"),
                }
                for d in docs
            ],
            "applicationPreferences": {
                "preferredWorkModes": profile.get("preferredWorkModes", []),
                "preferredCountries": profile.get("preferredCountries", []),
            },
            "fieldAliases": {
                "phone": ["phone", "telefono", "mobile", "celular"],
                "email": ["email", "correo", "mail"],
                "resume": ["resume", "cv", "curriculum"],
            },
        }


class DocumentService:
    def __init__(self) -> None:
        self.collection = mongo.db.documents
        self.base_docs = CONFIG.data_dir / "documents"

    def ingest_document(self, profile_id: str, source_path: str, category: str = "cv", tags: list[str] | None = None, is_favorite: bool = False) -> dict:
        src = Path(source_path).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"Document not found: {src}")

        dirs = ensure_profile_dirs(self.base_docs, profile_id)
        file_hash = sha256_file(src)

        duplicate = self.collection.find_one({"profileId": profile_id, "fileHash": file_hash}, {"_id": 0})
        if duplicate:
            return duplicate

        document_id = str(uuid.uuid4())
        original_name = f"{document_id}{src.suffix.lower()}"
        original_path = dirs["originals"] / original_name
        copy_file(src, original_path)

        pdf_path = dirs["pdf"] / f"{document_id}.pdf"
        if src.suffix.lower() == ".pdf":
            copy_file(src, pdf_path)
        else:
            write_placeholder_pdf(
                pdf_path,
                "JobHunterMaster - PDF Derivado",
                [
                    f"source: {src.name}",
                    f"profileId: {profile_id}",
                    "Nota: conversion visual completa pendiente para formatos complejos.",
                ],
            )

        doc = {
            "documentId": document_id,
            "profileId": profile_id,
            "category": category,
            "originalPath": str(original_path),
            "pdfPath": str(pdf_path),
            "originalExtension": src.suffix.lower(),
            "fileHash": file_hash,
            "fileSize": src.stat().st_size,
            "uploadedAt": datetime.utcnow(),
            "language": "es",
            "tags": tags or [],
            "isFavorite": is_favorite,
            "source": "manual",
        }
        self.collection.insert_one(doc)
        return doc

    def list_documents(self, profile_id: str) -> list[dict]:
        return list(self.collection.find({"profileId": profile_id}, {"_id": 0}).sort("uploadedAt", -1))


class JobService:
    def __init__(self) -> None:
        self.collection = mongo.db.job_opportunities

    def add_extracted_jobs(self, jobs: list[dict]) -> int:
        upserts = 0
        for row in jobs:
            row.setdefault("jobId", str(uuid.uuid4()))
            row.setdefault("updatedAt", datetime.utcnow())
            row.setdefault("extractedAt", datetime.utcnow())
            row.setdefault("reviewStatus", "new")
            row.setdefault("appliedStatus", "pending")
            self.collection.update_one(
                {"profileId": row["profileId"], "duplicateKey": row["duplicateKey"]},
                {"$set": row},
                upsert=True,
            )
            upserts += 1
        return upserts

    def pending_search(self) -> list[dict]:
        return list(self.collection.find({"reviewStatus": "new"}, {"_id": 0}).limit(50))

    def list_by_profile(self, profile_id: str) -> list[dict]:
        return list(self.collection.find({"profileId": profile_id}, {"_id": 0}).sort("updatedAt", -1).limit(200))


class ApplicationService:
    def __init__(self) -> None:
        self.collection = mongo.db.application_attempts
        self.alerts = mongo.db.manual_review_alerts

    def pending(self) -> list[dict]:
        return list(self.collection.find({"status": "pending"}, {"_id": 0}).limit(100))

    def upsert_result(self, payload: dict) -> None:
        payload.setdefault("finishedAt", datetime.utcnow())
        self.collection.update_one(
            {"applicationId": payload["applicationId"]}, {"$set": payload}, upsert=True
        )

    def manual_review(self, payload: dict) -> None:
        payload["createdAt"] = datetime.utcnow()
        self.alerts.insert_one(payload)

    def list_manual_review(self) -> list[dict]:
        return list(self.alerts.find({}, {"_id": 0}).sort("createdAt", -1).limit(200))


class BackupService:
    def __init__(self) -> None:
        self.backup_dir = CONFIG.data_dir / "backups"
        self.export_dir = CONFIG.data_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def export_bundle(self, password_hint: str = "") -> str:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out = self.export_dir / f"jobhuntermaster_export_{stamp}.zip"

        dump = {
            "profiles": list(mongo.db.profiles.find({}, {"_id": 0})),
            "personal_info": list(mongo.db.personal_info.find({}, {"_id": 0})),
            "documents": list(mongo.db.documents.find({}, {"_id": 0})),
            "job_opportunities": list(mongo.db.job_opportunities.find({}, {"_id": 0})),
            "application_attempts": list(mongo.db.application_attempts.find({}, {"_id": 0})),
            "meta": {
                "version": "0.1.0",
                "exportedAt": datetime.utcnow().isoformat(),
                "passwordHint": password_hint,
            },
        }

        json_dump = self.backup_dir / f"dump_{stamp}.json"
        json_dump.write_text(json.dumps(dump, default=str, indent=2), encoding="utf-8")

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_dump, arcname="metadata/dump.json")
            docs_root = CONFIG.data_dir / "documents"
            if docs_root.exists():
                for p in docs_root.rglob("*"):
                    if p.is_file():
                        zf.write(p, arcname=str(Path("documents") / p.relative_to(docs_root)))

        return str(out)


profile_service = ProfileService()
document_service = DocumentService()
job_service = JobService()
application_service = ApplicationService()
backup_service = BackupService()
