from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
import mongomock

from app_infrastructure.config import CONFIG


class Mongo:
    def __init__(self) -> None:
        self.backend = "mongodb"
        try:
            self.client = MongoClient(CONFIG.mongodb_uri, serverSelectionTimeoutMS=1500)
            self.db = self.client[CONFIG.mongodb_db]
            self._ensure_indexes()
        except (OperationFailure, ServerSelectionTimeoutError):
            # Fallback for local development where MongoDB auth/instance is unavailable.
            self.backend = "mongomock"
            self.client = mongomock.MongoClient()
            self.db = self.client[CONFIG.mongodb_db]
            self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.db.profiles.create_index("profileId", unique=True)
        self.db.documents.create_index([("profileId", 1), ("fileHash", 1)], unique=True)
        self.db.job_opportunities.create_index([("profileId", 1), ("duplicateKey", 1)], unique=True)
        self.db.application_attempts.create_index("applicationId", unique=True)


mongo = Mongo()
