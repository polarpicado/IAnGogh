from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

WorkMode = Literal["remote", "hybrid", "onsite"]
ReviewStatus = Literal["new", "reviewed", "manual_required"]
AppliedStatus = Literal["pending", "applied", "failed", "skipped"]
ApplicationStatus = Literal["pending", "in_progress", "success", "failed", "manual_review"]


class Profile(BaseModel):
    profile_id: str = Field(alias="profileId")
    display_name: str = Field(alias="displayName")
    target_titles: list[str] = Field(default_factory=list, alias="targetTitles")
    professional_title: str = Field(default="", alias="professionalTitle")
    summary: str = ""
    desired_roles: list[str] = Field(default_factory=list, alias="desiredRoles")
    preferred_countries: list[str] = Field(default_factory=list, alias="preferredCountries")
    preferred_locations: list[str] = Field(default_factory=list, alias="preferredLocations")
    preferred_work_modes: list[WorkMode] = Field(default_factory=list, alias="preferredWorkModes")
    salary_expectation: str | None = Field(default=None, alias="salaryExpectation")
    primary_language: str = Field(default="es", alias="primaryLanguage")
    secondary_languages: list[str] = Field(default_factory=list, alias="secondaryLanguages")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    is_active: bool = Field(default=False, alias="isActive")


class PersonalInfo(BaseModel):
    profile_id: str = Field(alias="profileId")
    first_name: str = Field(default="", alias="firstName")
    last_name: str = Field(default="", alias="lastName")
    display_name: str = Field(default="", alias="displayName")
    country_of_residence: str = Field(default="", alias="countryOfResidence")
    postal_code: str = Field(default="", alias="postalCode")
    address_encrypted: str = Field(default="", alias="addressEncrypted")
    phones_encrypted: list[str] = Field(default_factory=list, alias="phonesEncrypted")
    emails: list[str] = Field(default_factory=list)
    document_type: str = Field(default="", alias="documentType")
    document_number_encrypted: str = Field(default="", alias="documentNumberEncrypted")


class DocumentMetadata(BaseModel):
    document_id: str = Field(alias="documentId")
    profile_id: str = Field(alias="profileId")
    category: str
    original_path: str = Field(alias="originalPath")
    pdf_path: str = Field(alias="pdfPath")
    original_extension: str = Field(alias="originalExtension")
    file_hash: str = Field(alias="fileHash")
    file_size: int = Field(alias="fileSize")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, alias="uploadedAt")
    language: str = "es"
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = Field(default=False, alias="isFavorite")
    source: str = "manual"


class JobOpportunity(BaseModel):
    job_id: str = Field(alias="jobId")
    profile_id: str = Field(alias="profileId")
    source_portal: str = Field(alias="sourcePortal")
    search_keyword: str = Field(default="", alias="searchKeyword")
    job_title: str = Field(alias="jobTitle")
    company: str
    location: str = ""
    country: str = ""
    work_mode: str = Field(default="", alias="workMode")
    salary_text: str = Field(default="", alias="salaryText")
    posted_date_text: str = Field(default="", alias="postedDateText")
    description: str = ""
    requirements: str = ""
    technologies_raw: str = Field(default="", alias="technologiesRaw")
    technologies_normalized: list[str] = Field(default_factory=list, alias="technologiesNormalized")
    job_url: str = Field(default="", alias="jobUrl")
    score: float = 0
    priority: int = 0
    matched_skills: list[str] = Field(default_factory=list, alias="matchedSkills")
    missing_skills: list[str] = Field(default_factory=list, alias="missingSkills")
    recommendation: str = ""
    review_status: ReviewStatus = Field(default="new", alias="reviewStatus")
    applied_status: AppliedStatus = Field(default="pending", alias="appliedStatus")
    notes: str = ""
    extracted_at: datetime = Field(default_factory=datetime.utcnow, alias="extractedAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    duplicate_key: str = Field(alias="duplicateKey")


class ApplicationAttempt(BaseModel):
    application_id: str = Field(alias="applicationId")
    profile_id: str = Field(alias="profileId")
    job_id: str = Field(alias="jobId")
    portal: str
    started_at: datetime = Field(default_factory=datetime.utcnow, alias="startedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    status: ApplicationStatus = "pending"
    captcha_encountered: bool = Field(default=False, alias="captchaEncountered")
    manual_intervention_required: bool = Field(default=False, alias="manualInterventionRequired")
    unknown_fields: list[str] = Field(default_factory=list, alias="unknownFields")
    uploaded_resume_id: str | None = Field(default=None, alias="uploadedResumeId")
    observations: str = ""


class ActiveProfilePayload(BaseModel):
    identity: dict
    contact: dict
    location: dict
    legal_sensitive_allowed_fields: dict = Field(alias="legalSensitiveAllowedFields")
    profile_summary: dict = Field(alias="profileSummary")
    desired_roles: list[str] = Field(alias="desiredRoles")
    skills: list[dict]
    languages: list[dict]
    work_experiences: list[dict] = Field(default_factory=list, alias="workExperiences")
    education: list[dict] = Field(default_factory=list)
    preferred_documents: list[dict] = Field(default_factory=list, alias="preferredDocuments")
    application_preferences: dict = Field(alias="applicationPreferences")
    field_aliases: dict = Field(alias="fieldAliases")
