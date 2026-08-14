from uuid import UUID

from pydantic import BaseModel, SecretStr


class RegisterRequest(BaseModel):
    username: str
    password: SecretStr


class LoginRequest(BaseModel):
    username: str
    password: SecretStr


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
