# backend/Services/HelpdeskService/tests/test_neon_storage.py
import uuid
import pytest
import httpx
from httpx import AsyncClient

from resources.storageService import storage_service


@pytest.mark.asyncio
async def test_neon_storage_service_direct():
    """Verify Neon Object Storage put_object, get_object, and presigned URLs end-to-end."""
    assert storage_service.is_neon_enabled, "Neon Object Storage should be enabled via AWS env vars"

    doc_id = uuid.uuid4()
    test_key = storage_service.generate_storage_key(doc_id, version_number=1)
    test_payload = b"%PDF-1.4\n%Mock Document Bytes for Neon Storage Test\n%%EOF"

    # 1. Put document bytes to Neon
    stored_uri = storage_service.put_document_bytes(
        key=test_key,
        content=test_payload,
        content_type="application/pdf",
    )
    assert stored_uri.startswith("neon://")
    assert test_key in stored_uri

    # 2. Get document bytes from Neon
    retrieved_bytes = storage_service.get_document_bytes(stored_uri)
    assert retrieved_bytes == test_payload

    # 3. Presigned download URL
    presigned_url = storage_service.generate_presigned_download_url(
        stored_uri,
        expires_in=300,
        download_filename="test_neon_download.pdf",
    )
    assert presigned_url is not None
    assert "https://" in presigned_url

    # 4. Verify HTTP GET from presigned URL directly against Neon S3 endpoint
    async with httpx.AsyncClient() as client:
        resp = await client.get(presigned_url)
        assert resp.status_code == 200
        assert resp.content == test_payload
        assert resp.headers.get("content-type") == "application/pdf"
