import base64
import binascii
import re
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


class S3Service:
    def __init__(self, region: str, bucket: str, public_base_url: str = ""):
        self.client = boto3.client("s3", region_name=region)
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")

    def upload_public_base64_video(self, object_key: str, video_base64: str) -> str:
        raw = self._decode_base64_payload(video_base64)
        if len(raw) < 256:
            raise ValueError(f"Video payload too short ({len(raw)} bytes)")
        if not raw.startswith(b"\x1A\x45\xDF\xA3"):
            raise ValueError("Video payload is not a valid WebM file")
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=raw,
                ACL="public-read",
                ContentType="video/webm",
            )
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc
        return self.public_url(object_key)

    def upload_public_json(self, object_key: str, payload: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=payload.encode("utf-8"),
                ACL="public-read",
                ContentType="application/json",
            )
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc
        return self.public_url(object_key)

    @staticmethod
    def _decode_base64_payload(payload: str) -> bytes:
        if not payload:
            raise ValueError("Empty base64 payload")

        cleaned = payload.strip()
        lower = cleaned.lower()
        base64_marker = ";base64,"
        marker_index = lower.find(base64_marker)
        if marker_index >= 0:
            cleaned = cleaned[marker_index + len(base64_marker) :]
        elif lower.startswith("data:") and "," in cleaned:
            cleaned = cleaned.rsplit(",", 1)[-1]
        cleaned = "".join(cleaned.split())
        if not cleaned:
            raise ValueError("Empty base64 payload after cleanup")

        normalized = cleaned.replace("-", "+").replace("_", "/")
        missing = (-len(normalized)) % 4
        if missing:
            normalized += "=" * missing

        if not re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", normalized):
            raise ValueError("Invalid base64 characters")

        try:
            return base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 payload") from exc

    def public_url(self, object_key: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{object_key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{object_key}"

    @staticmethod
    def extension_for_mime(mime: str) -> str:
        mapping = {
            "video/webm": ".webm",
            "video/mp4": ".mp4",
            "application/json": ".json",
        }
        return mapping.get(mime, Path(mime).suffix or "")
