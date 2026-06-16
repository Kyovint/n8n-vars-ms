from typing import Literal
from pydantic import BaseModel, field_validator
import re

IDENTIFIER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_RE.match(value):
        raise ValueError(
            "Must start with a letter and contain only letters, digits, or underscores"
        )
    return value


class CreateVariableRequest(BaseModel):
    project: str
    environment: Literal["dev", "test", "prod"]
    name: str
    value: str

    @field_validator("project", "name")
    @classmethod
    def validate_identifiers(cls, v: str) -> str:
        return validate_identifier(v)


class UpdateVariableRequest(BaseModel):
    value: str


class VariableResponse(BaseModel):
    project: str
    environment: str
    name: str
    value: str


class VariableItem(BaseModel):
    name: str
    value: str
