import base64
from typing import Any
import boto3
from botocore.exceptions import ClientError


class RekognitionService:
    def __init__(self, region: str):
        self.client = boto3.client("rekognition", region_name=region)

    def create_liveness_session(self, client_request_token: str, bucket: str, key_prefix: str) -> str:
        try:
            response = self.client.create_face_liveness_session(
                ClientRequestToken=client_request_token,
                Settings={
                    "AuditImagesLimit": 4,
                    "OutputConfig": {
                        "S3Bucket": bucket,
                        "S3KeyPrefix": key_prefix,
                    },
                },
            )
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc
        return response["SessionId"]

    def get_liveness_result(self, session_id: str) -> dict[str, Any]:
        try:
            response = self.client.get_face_liveness_session_results(SessionId=session_id)
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc

        return {
            "status": response.get("Status"),
            "confidence": float(response.get("Confidence") or 0.0),
            "reference_image": response.get("ReferenceImage"),
            "audit_images": response.get("AuditImages") or [],
        }

    def compare_faces(
        self,
        *,
        source_image_base64: str,
        target_image_base64: str,
        similarity_threshold: float,
    ) -> dict[str, Any]:
        try:
            source_bytes = base64.b64decode(source_image_base64)
            target_bytes = base64.b64decode(target_image_base64)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Invalid base64 payload for face comparison") from exc

        try:
            response = self.client.compare_faces(
                SourceImage={"Bytes": source_bytes},
                TargetImage={"Bytes": target_bytes},
                SimilarityThreshold=similarity_threshold,
            )
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc

        matches = response.get("FaceMatches") or []
        best_similarity = 0.0
        if matches:
            best_similarity = float(max((m.get("Similarity") or 0.0) for m in matches))

        return {
            "matched": best_similarity >= similarity_threshold,
            "similarity": best_similarity,
            "threshold": similarity_threshold,
            "matches": len(matches),
            "request_id": (response.get("ResponseMetadata") or {}).get("RequestId"),
        }
