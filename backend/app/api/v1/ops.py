from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger
from returns.pipeline import is_successful
import ulid
import asyncio

import app.services.repository as repository
from app.services.gmail import fetch_latest_emails, FetchLatestUnrecordedEmailsError
from app.services.attachments import process_emails_to_bills
from app.services.ai import extract_bl_documents_data
from app.services.bl_process import get_unique_bl_attachment, get_unique_bl_records
from app.schemas.llm import LLMRequest, LLMResponse
from app.schemas.db import BLRecordCreate, BLRecordEmail, BLRecordAttachment


router = APIRouter(prefix="/api/v1/ops", tags=["Operations"])


class TriggerProcessResponse(BaseModel):
    emails_count: int
    attachments_count: int
    bls_count: int
    bl_records_count: int
    duplicate_bls_count: int

class TriggerProcessingRequest(BaseModel):
    recent_emails_limit: int = Field(10, ge=1, le=50)


@router.post("/process", response_model=TriggerProcessResponse)
async def trigger_processing(params: TriggerProcessingRequest):
    emails = await fetch_latest_emails(
        limit=params.recent_emails_limit
    )
    if not is_successful(emails):
        match emails.failure():
            case FetchLatestUnrecordedEmailsError.NO_EMAILS:
                raise HTTPException(
                    status_code=404,
                    detail="There is no emails that need to be processed"
                )
            case FetchLatestUnrecordedEmailsError.API_FAILED:
                raise HTTPException(
                    status_code=503,
                    detail="This service is temporary unavailable"
                )
            case FetchLatestUnrecordedEmailsError.BAD_API_RESPONSE:
                raise HTTPException(
                    status_code=502,
                    detail="This service is temporary unavailable"
                )
            case _:
                assert False, "A returned error was unhandled"

    emails = emails.unwrap()
    emails_count = len(emails)
    
    bills = process_emails_to_bills(emails)
    if not is_successful(bills):
        raise HTTPException(
            status_code=400,
            detail="The documents found in the emails are not eligible or recognizable by our application"
        )
    
    att_count, bills = bills.unwrap()
    checked_bl, unchecked_bl = (
        await get_unique_bl_attachment(bills)
    )
    if not checked_bl and not unchecked_bl: return TriggerProcessResponse(
            emails_count=len(emails),
            attachments_count=att_count,
            bls_count=len(bills),
            bl_records_count=len(checked_bl),
            duplicate_bls_count=len(bills)-len(checked_bl),
        )
    
    async def get_llm_extracted_data(hashed_bl) -> list[LLMResponse]:
        bls = [
                LLMRequest(
                    request_id=id,
                    content=bl.content,
                    email_body=bl.email.recent_body,
                )
                for id, bl in hashed_bl.items()
            ]
        return await extract_bl_documents_data(bls)
    
    hashed_checked_bl = {str(ulid.ULID()): bl for bl in checked_bl}
    hashed_unchecked_bl = {str(ulid.ULID()): bl for bl in unchecked_bl}
    
    checked_bl_data, unchecked_bl_data = await asyncio.gather(
            get_llm_extracted_data(hashed_checked_bl),
            get_llm_extracted_data(hashed_unchecked_bl),
        )
    
    unique_bl_data: list[LLMResponse] = []
    if unchecked_bl_data:
        unique_bl_data = (
            await get_unique_bl_records(unchecked_bl_data, hashed_unchecked_bl)
        )
    unique_bl_data.extend(checked_bl_data)
    hashed_checked_bl.update(hashed_unchecked_bl)
    
    bl_records = [
        BLRecordCreate(
            **bl.model_dump(),
            email=BLRecordEmail(
                **hashed_checked_bl[bl.request_id].email.model_dump(),
                email_status=bl.email_status,
            ),
            attachment=BLRecordAttachment(
                **hashed_checked_bl[bl.request_id].model_dump(),
            )
        )
        for bl in unique_bl_data
    ]
    
    await repository.save_bl_documents(bl_records)

    return TriggerProcessResponse(
            emails_count=emails_count,
            attachments_count=att_count,
            bls_count=len(bills),
            bl_records_count=len(bl_records),
            duplicate_bls_count=len(bills)-len(bl_records),
        )