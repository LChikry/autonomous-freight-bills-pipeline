from pydantic import BaseModel, Field
from enum import StrEnum
from typing import Literal

from shared_types.bl_schema import DbRetrievedBL

class PostProcessResponse(BaseModel):
    emails_processed_count: int
    attachments_processed_count: int
    bl_processed_count: int
    docs_created_count: int
    skipped_duplicated_docs_count: int


# List
class GetBlListRequestBase(BaseModel):
    limit: int = Field(20, ge=1, le=100)
    cursor: str | None = Field(default=None)

class GetHblListRequest(GetBlListRequestBase):
    pass

class GetMblListRequest(GetBlListRequestBase):
    pass


class GetBlListResponseBase(BaseModel):
    documents: list[DbRetrievedBL]
    next_cursor: str | None

class GetHblListResponse(GetBlListResponseBase):
    pass

class GetMblListResponse(GetBlListResponseBase):
    pass


# By Id
# class GetBlRequestBase(BaseModel):
#     pass

# class GetHblRequest(GetBlRequestBase):
#     pass

# class GetMblRequest(GetBlRequestBase):
#     pass


# class GetBlResponseBase(BaseModel):
#     pass

# class GetHblResponse(GetBlResponseBase):
#     pass

# class GetMblResponse(GetBlResponseBase):
#     pass

