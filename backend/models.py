from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field, model_validator

    _PYDANTIC_V2 = True
except Exception:
    from pydantic import BaseModel, Field, root_validator

    _PYDANTIC_V2 = False


class _BaseModel(BaseModel):
    if _PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")
    else:

        class Config:
            extra = "ignore"


class AuthRequest(_BaseModel):
    user_id: Optional[str] = None
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    client_version: str = "unknown"

    if _PYDANTIC_V2:

        @model_validator(mode="after")
        def _validate_one_of(self):
            user_id_ok = bool(self.user_id and str(self.user_id).strip())
            id_token_ok = bool(self.id_token and str(self.id_token).strip())
            access_token_ok = bool(self.access_token and str(self.access_token).strip())
            if not (user_id_ok or id_token_ok or access_token_ok):
                raise ValueError("user_id or id_token or access_token is required")
            return self

    else:

        @root_validator(pre=False)
        def _validate_one_of(cls, values):
            user_id = values.get("user_id")
            id_token = values.get("id_token")
            access_token = values.get("access_token")
            user_id_ok = bool(user_id and str(user_id).strip())
            id_token_ok = bool(id_token and str(id_token).strip())
            access_token_ok = bool(access_token and str(access_token).strip())
            if not (user_id_ok or id_token_ok or access_token_ok):
                raise ValueError("user_id or id_token or access_token is required")
            return values


class AuthResponse(_BaseModel):
    token: str
    expires_in_seconds: int


class ChatRequest(_BaseModel):
    request_id: Optional[str] = None
    user_id: str
    query: str
    client_version: str = "unknown"
    selection_id: Optional[str] = None
    exclude_ids: List[str] = Field(default_factory=list)

    if _PYDANTIC_V2:

        @model_validator(mode="after")
        def _validate_required(self):
            if not str(self.user_id or "").strip():
                raise ValueError("user_id is required")
            if not str(self.query or "").strip():
                raise ValueError("query is required")
            return self

    else:

        @root_validator(pre=False)
        def _validate_required(cls, values):
            if not str(values.get("user_id") or "").strip():
                raise ValueError("user_id is required")
            if not str(values.get("query") or "").strip():
                raise ValueError("query is required")
            return values


class ChatResponse(_BaseModel):
    request_id: str
    source: str
    candidates: List[Dict[str, Any]]
    answer: str
    guidance: str
    routing_department: str = ""
    hit_department: str = ""
    hit_row_id: str = ""


class FeedbackRequest(_BaseModel):
    request_id: str
    user_id: str
    user_feedback: str = ""
    solved: Optional[bool] = None
    selection_id: Optional[str] = None
    query: Optional[str] = None
    client_version: str = "unknown"
    candidates_ids: List[str] = Field(default_factory=list)
    searched_departments: List[str] = Field(default_factory=list)

    if _PYDANTIC_V2:

        @model_validator(mode="after")
        def _validate_required(self):
            if not str(self.request_id or "").strip():
                raise ValueError("request_id is required")
            if not str(self.user_id or "").strip():
                raise ValueError("user_id is required")
            return self

    else:

        @root_validator(pre=False)
        def _validate_required(cls, values):
            if not str(values.get("request_id") or "").strip():
                raise ValueError("request_id is required")
            if not str(values.get("user_id") or "").strip():
                raise ValueError("user_id is required")
            return values
