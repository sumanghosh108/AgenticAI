"""
Backblaze B2 Storage Client — secure file storage for generated reports.

Features:
  - Upload PDF/DOCX reports to B2 bucket
  - Generate time-limited authorized download URLs
  - File paths include username for per-user isolation
  - All files stored under: reports/{username}/{filename}
"""

import hashlib
import os
import time
from typing import Optional

import requests
from research_and_analyst.logger import GLOBAL_LOGGER as log


class B2StorageClient:
    """
    Backblaze B2 client using the B2 Native API (no SDK dependency).

    Authentication flow:
      1. b2_authorize_account → get API URL + auth token
      2. b2_get_upload_url → get upload endpoint
      3. Upload file with SHA1 checksum
      4. Generate authorized download URL with expiry
    """

    AUTH_URL = "https://api.backblazeb2.com/b2api/v2/b2_authorize_account"

    def __init__(self):
        self.key_id = os.getenv("B2_KEY_ID", "")
        self.app_key = os.getenv("B2_APP_KEY", "")
        self.bucket_name = os.getenv("B2_BUCKET_NAME", "agenticai-reports")

        # Populated after authorize()
        self._api_url = ""
        self._auth_token = ""
        self._download_url = ""
        self._bucket_id = ""
        self._upload_url = ""
        self._upload_token = ""
        self._authorized = False

    def authorize(self) -> bool:
        """Authorize with B2 and get API endpoints."""
        if self._authorized:
            return True

        if not self.key_id or not self.app_key:
            log.error("B2_KEY_ID and B2_APP_KEY must be set in environment")
            return False

        try:
            resp = requests.get(
                self.AUTH_URL,
                auth=(self.key_id, self.app_key),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            self._api_url = data["apiUrl"]
            self._auth_token = data["authorizationToken"]
            self._download_url = data["downloadUrl"]

            # Get bucket ID
            self._bucket_id = self._resolve_bucket_id()
            if not self._bucket_id:
                return False

            self._authorized = True
            log.info("B2 authorized", bucket=self.bucket_name)
            return True

        except Exception as e:
            log.error("B2 authorization failed", error=str(e))
            return False

    def _resolve_bucket_id(self) -> str:
        """Resolve bucket name to bucket ID."""
        try:
            resp = requests.post(
                f"{self._api_url}/b2api/v2/b2_list_buckets",
                headers={"Authorization": self._auth_token},
                json={"accountId": self._get_account_id(), "bucketName": self.bucket_name},
                timeout=15,
            )
            resp.raise_for_status()
            buckets = resp.json().get("buckets", [])

            for b in buckets:
                if b["bucketName"] == self.bucket_name:
                    return b["bucketId"]

            log.error("Bucket not found", bucket=self.bucket_name)
            return ""
        except Exception as e:
            log.error("Failed to resolve bucket", error=str(e))
            return ""

    def _get_account_id(self) -> str:
        """Extract account ID from auth response."""
        try:
            resp = requests.get(
                self.AUTH_URL,
                auth=(self.key_id, self.app_key),
                timeout=15,
            )
            return resp.json().get("accountId", "")
        except Exception:
            return ""

    def _get_upload_url(self) -> bool:
        """Get a fresh upload URL (required before each upload)."""
        try:
            resp = requests.post(
                f"{self._api_url}/b2api/v2/b2_get_upload_url",
                headers={"Authorization": self._auth_token},
                json={"bucketId": self._bucket_id},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            self._upload_url = data["uploadUrl"]
            self._upload_token = data["authorizationToken"]
            return True
        except Exception as e:
            log.error("Failed to get upload URL", error=str(e))
            return False

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        username: str,
        content_type: str = "application/octet-stream",
    ) -> Optional[dict]:
        """
        Upload a file to B2.

        Files are stored at: reports/{username}/{filename}
        This ensures per-user isolation.

        Returns:
            Dict with fileId, fileName, contentLength on success, None on failure.
        """
        if not self._authorized:
            if not self.authorize():
                return None

        if not self._get_upload_url():
            return None

        # Build storage path with username prefix
        storage_path = f"reports/{username}/{filename}"
        sha1 = hashlib.sha1(file_bytes).hexdigest()

        try:
            resp = requests.post(
                self._upload_url,
                headers={
                    "Authorization": self._upload_token,
                    "X-Bz-File-Name": storage_path,
                    "Content-Type": content_type,
                    "Content-Length": str(len(file_bytes)),
                    "X-Bz-Content-Sha1": sha1,
                },
                data=file_bytes,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            log.info("File uploaded to B2", file=storage_path, size=len(file_bytes))
            return {
                "file_id": data["fileId"],
                "file_name": data["fileName"],
                "content_length": data["contentLength"],
                "content_sha1": sha1,
            }

        except Exception as e:
            log.error("B2 upload failed", file=storage_path, error=str(e))
            # Reset auth state so next call re-authorizes
            self._authorized = False
            return None

    def get_download_url(self, file_id: str, valid_seconds: int = 3600) -> Optional[str]:
        """
        Generate a time-limited authorized download URL.

        Args:
            file_id: B2 file ID from upload.
            valid_seconds: How long the URL stays valid (default: 1 hour).

        Returns:
            Signed download URL or None.
        """
        if not self._authorized:
            if not self.authorize():
                return None

        try:
            resp = requests.post(
                f"{self._api_url}/b2api/v2/b2_get_download_authorization",
                headers={"Authorization": self._auth_token},
                json={
                    "bucketId": self._bucket_id,
                    "fileNamePrefix": "",
                    "validDurationInSeconds": valid_seconds,
                },
                timeout=15,
            )
            resp.raise_for_status()
            auth_token = resp.json()["authorizationToken"]

            # Get file info to get the file name
            file_info = self._get_file_info(file_id)
            if not file_info:
                return None

            file_name = file_info["fileName"]
            download_url = (
                f"{self._download_url}/file/{self.bucket_name}/{file_name}"
                f"?Authorization={auth_token}"
            )

            return download_url

        except Exception as e:
            log.error("Failed to generate download URL", error=str(e))
            return None

    def _get_file_info(self, file_id: str) -> Optional[dict]:
        """Get file info by ID."""
        try:
            resp = requests.post(
                f"{self._api_url}/b2api/v2/b2_get_file_info",
                headers={"Authorization": self._auth_token},
                json={"fileId": file_id},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.error("Failed to get file info", error=str(e))
            return None

    def delete_file(self, file_id: str, file_name: str) -> bool:
        """Delete a file from B2."""
        if not self._authorized:
            if not self.authorize():
                return False

        try:
            resp = requests.post(
                f"{self._api_url}/b2api/v2/b2_delete_file_version",
                headers={"Authorization": self._auth_token},
                json={"fileId": file_id, "fileName": file_name},
                timeout=15,
            )
            resp.raise_for_status()
            log.info("File deleted from B2", file=file_name)
            return True
        except Exception as e:
            log.error("Failed to delete file", error=str(e))
            return False
