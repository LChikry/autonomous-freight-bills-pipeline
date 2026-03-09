from pydantic import BaseModel, SecretStr, field_validator, field_serializer, SerializationInfo

from datetime import datetime
from enum import StrEnum
from typing import Any

from app.models.bill_of_lading import DocType

class EmailStatus(StrEnum):
    PRE_ALERT = "pre_alert"
    DRAFT = "draft"

class AttachmentBase(BaseModel):
    attachment_id: str
    email_id: str
    filename: str

class Attachment(AttachmentBase):
    content: bytes
    original_content_sha256: str

class EmailBody(BaseModel):
    full_body: str
    recent_body: str
    
    @property
    def has_body(self) -> bool:
        return bool(self.full_body.strip() and self.recent_body.strip())

class EmailHeader(BaseModel):
    subject: str
    sender: SecretStr
    
    @field_serializer("sender", when_used="json")
    def reveal_sender(self, sender: SecretStr, info: SerializationInfo):
        if info.context and info.context.get("reveal_secret_types") is True:
            return sender.get_secret_value()
        return sender

class EmailBase(EmailBody, EmailHeader):
    email_id: str
    received_at: datetime

    @field_validator("received_at", mode="before")
    @classmethod
    def parse_received_at(cls, v: Any) -> Any:
        if not isinstance(v, str): return v
        
        try:
            return datetime.strptime(v, "%d-%b-%Y %H:%M")
        except:
            return v

class Email(EmailBase):
    unique_attachments: list[Attachment]

class AttachmentTransformed(Attachment):
    bl_number: str | None
    page_range: tuple[int, int]
    email: EmailBase
    doc_type: DocType | None = None
    generated_at: datetime | None = None
    issuer_name: str | None

    @field_validator("doc_type", mode="before")
    @classmethod
    def parse_doc_type(cls, v: Any) -> Any:
        if v and isinstance(v, str):
            return DocType(v.lower())
        return v

    @field_validator("generated_at", mode="before")
    @classmethod
    def parse_generated_at(cls, v: Any) -> Any:
        if v and isinstance(v, str):
            return datetime.strptime(v, "%d-%b-%Y %H:%M")
        return v