from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from group_interview_arena_api.identity.credentials import PASSWORD_MAX_LENGTH


class RegisterRequest(BaseModel):
    username: str
    password: SecretStr = Field(max_length=PASSWORD_MAX_LENGTH)
    invite_code: SecretStr = Field(min_length=1, max_length=256)


class LoginRequest(BaseModel):
    username: str
    password: SecretStr = Field(max_length=PASSWORD_MAX_LENGTH)


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
