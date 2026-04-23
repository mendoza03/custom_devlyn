from typing import Any
import boto3
from botocore.exceptions import ClientError


class CognitoService:
    def __init__(self, region: str, user_pool_id: str, client_id: str):
        self.region = region
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client = boto3.client("cognito-idp", region_name=region)

    def custom_auth_with_password(self, username: str, password: str) -> dict[str, Any]:
        try:
            init = self.client.initiate_auth(
                AuthFlow="CUSTOM_AUTH",
                ClientId=self.client_id,
                AuthParameters={"USERNAME": username},
            )
            challenge = init.get("ChallengeName")
            session = init.get("Session")
            if challenge != "CUSTOM_CHALLENGE":
                raise RuntimeError(f"Unexpected challenge: {challenge}")

            response = self.client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName="CUSTOM_CHALLENGE",
                Session=session,
                ChallengeResponses={
                    "USERNAME": username,
                    "ANSWER": password,
                },
            )
            auth = response.get("AuthenticationResult")
            if not auth:
                raise RuntimeError("AuthenticationResult missing")
            return {
                "access_token": auth.get("AccessToken"),
                "id_token": auth.get("IdToken"),
                "refresh_token": auth.get("RefreshToken"),
                "expires_in": auth.get("ExpiresIn"),
                "token_type": auth.get("TokenType"),
            }
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc

    def get_user(self, access_token: str) -> dict[str, Any]:
        try:
            data = self.client.get_user(AccessToken=access_token)
        except ClientError as exc:
            raise RuntimeError(str(exc)) from exc

        attrs = {a["Name"]: a["Value"] for a in data.get("UserAttributes", [])}
        return {
            "username": data.get("Username"),
            "sub": attrs.get("sub"),
            "email": attrs.get("email") or data.get("Username"),
            "name": attrs.get("name") or attrs.get("preferred_username") or data.get("Username"),
            "attributes": attrs,
        }
