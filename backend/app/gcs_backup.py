"""
GCS-backed SQLite persistence for Cloud Run.

On startup: download DB from GCS if it exists (restores previous state).
After every write: upload DB file back to GCS.

Gracefully no-ops when GCS_BUCKET is not set (local dev / missing credentials).
"""
import logging
import os

logger = logging.getLogger(__name__)

_BUCKET = os.environ.get("GCS_BUCKET", "")
_GCS_KEY = os.environ.get("GCS_DB_KEY", "agentmaster.db")
_DB_PATH = os.environ.get("DATABASE_URL", "").replace("sqlite:////", "/")


def _client_and_bucket():
    if not _BUCKET:
        return None, None
    try:
        from google.cloud import storage  # type: ignore
        client = storage.Client()
        return client, client.bucket(_BUCKET)
    except Exception as e:
        logger.warning("GCS client init failed (persistence disabled): %s", e)
        return None, None


def restore_from_gcs():
    """Download DB from GCS on startup. Safe to call even if GCS is unavailable."""
    if not _BUCKET or not _DB_PATH:
        return
    client, bucket = _client_and_bucket()
    if not bucket:
        return
    blob = bucket.blob(_GCS_KEY)
    try:
        if blob.exists():
            os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
            blob.download_to_filename(_DB_PATH)
            size = os.path.getsize(_DB_PATH)
            logger.info("✅ Restored DB from GCS gs://%s/%s (%d bytes)", _BUCKET, _GCS_KEY, size)
        else:
            logger.info("No existing DB found in GCS — starting fresh")
    except Exception as e:
        logger.warning("GCS restore failed (starting fresh): %s", e)


def backup_to_gcs():
    """Upload current DB to GCS. Call after any write operation."""
    if not _BUCKET or not _DB_PATH:
        return
    if not os.path.exists(_DB_PATH):
        return
    client, bucket = _client_and_bucket()
    if not bucket:
        return
    blob = bucket.blob(_GCS_KEY)
    try:
        blob.upload_from_filename(_DB_PATH)
        logger.debug("📦 DB backed up to GCS gs://%s/%s", _BUCKET, _GCS_KEY)
    except Exception as e:
        logger.warning("GCS backup failed: %s", e)
