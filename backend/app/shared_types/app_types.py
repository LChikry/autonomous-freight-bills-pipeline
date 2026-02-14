from pydantic import BaseModel, Field
from enum import StrEnum
from typing import Literal

class BaseEmail(BaseModel):
    id: str = Field(..., min_length=1, description="Email Id provided by Gmail API")
    subject: str
    received_at: str = Field(..., min_length=1)
    raw_text_excerpt: str = Field(..., min_length=1)
    latest_body_text: str = Field(..., min_length=1)
    source_from: str
    email_status: Literal["pre_alert", "draft"] | None = Field(default=None, description="An email is status is classified either as pre_alert or draft. To know which one it is, we use the newest body (latest_body_text) since it will contain wording indicating pre-alert or draft.")


class BaseAttachment(BaseModel):
    attachment_id: str = Field(..., min_length=1, description="Attachment Id provided by Gmail API")
    email_id: str = Field(..., min_length=1, description="Email Id this attachment belongs to. It is provided by Gmail API")
    filename: str
    content: bytes

class FetchedAttachment(BaseAttachment):
    pass

class Email(BaseEmail):
    attachments: list[FetchedAttachment]

class AttachmentPages(BaseModel):
    content: bytes
    page_range: tuple[int, int]
    bl_number: str = Field(..., description="Bill of Lading (BL) number is unique reference number. Examples: MBL-2677407 or HBL-5437923")
    generated_at: str | None

class BLDocument(BaseAttachment, AttachmentPages):
    doc_type: Literal["hbl", "mbl"] = Field(..., description="Bill of Lading type: either mbl (master) or hbl (House)")
    pass

