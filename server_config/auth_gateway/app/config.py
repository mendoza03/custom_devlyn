from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "odoo-biometric-auth-gateway"
    app_env: str = "dev"
    app_debug: bool = False
    app_secret_key: str = "change-me"

    aws_region: str = "us-east-1"

    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""

    rekognition_liveness_threshold: float = 80.0
    rekognition_face_match_threshold: float = 80.0
    rekognition_max_attempts: int = 3
    liveness_mock_mode: bool = False

    s3_bucket_name: str = "biometric"
    s3_public_base_url: str = ""

    odoo_base_url: str = "https://erp.odootest.mvpstart.click"
    odoo_db_name: str = "devlyn_com"
    odoo_oauth_provider_id: int = 1
    odoo_event_ingest_url: str = "https://erp.odootest.mvpstart.click/biometric/api/v1/event"
    odoo_user_context_url: str = "https://erp.odootest.mvpstart.click/biometric/api/v1/user-context"
    odoo_api_key: str = "change-me"

    auth_base_url: str = "https://auth.odootest.mvpstart.click"
    biometric_mode: str = "admin_demo_only"
    biometric_admin_demo_login: str = "admin"

    mysql_fallback_enabled: bool = True
    mysql_fallback_connection_file: str = "./connection_values.json"

    gps_required: bool = True

    webauthn_enabled: bool = False
    webauthn_rp_id: str = "auth.odootest.mvpstart.click"
    webauthn_rp_name: str = "Odoo Biometric Auth"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
