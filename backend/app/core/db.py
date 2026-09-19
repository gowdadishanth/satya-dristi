import os
import json
import shutil
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try importing real Google Cloud Firestore
_firestore_client = None
try:
    from google.cloud import firestore
    if settings.FIREBASE_CREDENTIALS_PATH or settings.GOOGLE_APPLICATION_CREDENTIALS or os.getenv("FIRESTORE_EMULATOR_HOST"):
        _firestore_client = firestore.Client(project=settings.FIREBASE_PROJECT_ID)
        logger.info("Connected to Google Cloud Firestore.")
except Exception as e:
    logger.info("Firestore client not connected, local document store will be active: %s", e)

class LocalDocumentStore:
    """Thread-safe, persistent local document store mirroring Firestore collections & documents."""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(str(self.db_path), timeout=10)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    collection TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, doc_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_col_doc ON documents (collection, doc_id)")
            conn.commit()

    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]):
        with self._get_conn() as conn:
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO documents (collection, doc_id, data_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(collection, doc_id) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
            """, (collection, doc_id, json.dumps(data, default=str), now))
            conn.commit()

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT data_json FROM documents WHERE collection = ? AND doc_id = ?", (collection, doc_id))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def delete_document(self, collection: str, doc_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM documents WHERE collection = ? AND doc_id = ?", (collection, doc_id))
            conn.commit()

    def query_collection(self, collection: str, filters: Dict[str, Any] = None, limit: int = 50, order_by_desc: str = "created_at") -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT data_json FROM documents WHERE collection = ?", (collection,))
            results = []
            for row in cursor.fetchall():
                doc = json.loads(row[0])
                match = True
                if filters:
                    for k, v in filters.items():
                        if v is not None and doc.get(k) != v:
                            match = False
                            break
                if match:
                    results.append(doc)

            if order_by_desc:
                results.sort(key=lambda x: str(x.get(order_by_desc, "")), reverse=True)
            return results[:limit]

# Persistent document store file
_local_store = LocalDocumentStore(settings.DATA_DIR / "satya_dristi_store.db")

class DatabaseService:
    """Unified service for Firestore & local persistent storage."""
    
    @staticmethod
    def save_user(user_data: Dict[str, Any]):
        uid = user_data["uid"]
        user_data["updated_at"] = datetime.utcnow().isoformat()
        _local_store.set_document("users", uid, user_data)
        if _firestore_client:
            try:
                _firestore_client.collection("users").document(uid).set(user_data, merge=True)
            except Exception as e:
                logger.error("Firestore save_user error: %s", e)

    @staticmethod
    def get_user(uid: str) -> Optional[Dict[str, Any]]:
        if _firestore_client:
            try:
                doc = _firestore_client.collection("users").document(uid).get()
                if doc.exists:
                    data = doc.to_dict()
                    _local_store.set_document("users", uid, data)
                    return data
            except Exception as e:
                logger.error("Firestore get_user error: %s", e)
        return _local_store.get_document("users", uid)

    @staticmethod
    def save_analysis(analysis_data: Dict[str, Any]):
        aid = analysis_data["analysis_id"]
        _local_store.set_document("analyses", aid, analysis_data)
        if _firestore_client:
            try:
                _firestore_client.collection("analyses").document(aid).set(analysis_data, merge=True)
            except Exception as e:
                logger.error("Firestore save_analysis error: %s", e)

    @staticmethod
    def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
        if _firestore_client:
            try:
                doc = _firestore_client.collection("analyses").document(analysis_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    _local_store.set_document("analyses", analysis_id, data)
                    return data
            except Exception as e:
                logger.error("Firestore get_analysis error: %s", e)
        return _local_store.get_document("analyses", analysis_id)

    @staticmethod
    def list_analyses(uid: str, task: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        filters = {"uid": uid}
        if task and task != "All":
            filters["task"] = task
            
        if _firestore_client:
            try:
                query = _firestore_client.collection("analyses").where("uid", "==", uid)
                if task and task != "All":
                    query = query.where("task", "==", task)
                query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
                docs = [d.to_dict() for d in query.stream()]
                for d in docs:
                    if "analysis_id" in d:
                        _local_store.set_document("analyses", d["analysis_id"], d)
                return docs
            except Exception as e:
                logger.error("Firestore list_analyses error: %s", e)
        return _local_store.query_collection("analyses", filters=filters, limit=limit, order_by_desc="created_at")

    @staticmethod
    def delete_analysis(analysis_id: str, uid: str) -> bool:
        doc = DatabaseService.get_analysis(analysis_id)
        if not doc or doc.get("uid") != uid:
            return False
        if _firestore_client:
            try:
                _firestore_client.collection("analyses").document(analysis_id).delete()
            except Exception as e:
                logger.error("Firestore delete_analysis error: %s", e)
                return False
        _local_store.delete_document("analyses", analysis_id)
        # Clean up scoped evidence directory and uploaded files
        try:
            evidence_dir = settings.EVIDENCE_DIR / analysis_id
            if evidence_dir.is_dir():
                shutil.rmtree(evidence_dir, ignore_errors=True)
            uploads_dir = settings.UPLOADS_DIR / analysis_id
            if uploads_dir.is_dir():
                shutil.rmtree(uploads_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("Artifact cleanup error during delete_analysis: %s", e)
        return True

    @staticmethod
    def save_report(report_data: Dict[str, Any]):
        rid = report_data["report_id"]
        _local_store.set_document("reports", rid, report_data)
        if _firestore_client:
            try:
                _firestore_client.collection("reports").document(rid).set(report_data, merge=True)
            except Exception as e:
                logger.error("Firestore save_report error: %s", e)

    @staticmethod
    def get_report(report_id: str) -> Optional[Dict[str, Any]]:
        if _firestore_client:
            try:
                doc = _firestore_client.collection("reports").document(report_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    _local_store.set_document("reports", report_id, data)
                    return data
            except Exception as e:
                logger.error("Firestore get_report error: %s", e)
        return _local_store.get_document("reports", report_id)

    @staticmethod
    def list_reports(uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        if _firestore_client:
            try:
                query = _firestore_client.collection("reports").where("uid", "==", uid).order_by("generated_at", direction=firestore.Query.DESCENDING).limit(limit)
                docs = [d.to_dict() for d in query.stream()]
                for d in docs:
                    if "report_id" in d:
                        _local_store.set_document("reports", d["report_id"], d)
                return docs
            except Exception as e:
                logger.error("Firestore list_reports error: %s", e)
        return _local_store.query_collection("reports", filters={"uid": uid}, limit=limit, order_by_desc="generated_at")

db = DatabaseService()
