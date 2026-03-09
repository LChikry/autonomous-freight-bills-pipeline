from typing import Any
from pydantic import Field, AwareDatetime, field_validator
from datetime import datetime, timezone

from app.models.bill_of_lading import BillOfLading
from app.models.emails import EmailBase, AttachmentBase, EmailStatus

class BLRecordEmail(EmailBase):
    email_status: EmailStatus
    
    @field_validator("email_status", mode="before")
    @classmethod
    def parse_doc_type(cls, v: Any) -> Any:
        if v and isinstance(v, str):
            return EmailStatus(v.lower())
        return v

class BLRecordAttachment(AttachmentBase):
    page_range: tuple[int, int]
    original_content_sha256: str


class _BLRecordBase(BillOfLading):
    email: BLRecordEmail
    attachment: BLRecordAttachment
    

class BLRecordCreate(_BLRecordBase):
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BLRecord(_BLRecordBase):
    doc_id: str
    created_at: AwareDatetime