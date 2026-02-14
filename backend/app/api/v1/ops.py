from fastapi import APIRouter
from pydantic import BaseModel

import logging

from services.attachments_handler import split_grouped_bills
from services.gmail import fetch_latest_emails
from services.ai import process_shipping_documents
from services.bl_process import check_duplicates, create_bls_for_db
from shared_types.app_types import BLDocument
from services.ai import process_shipping_documents
from services.bl_process import check_duplicates, create_bls_for_db
import services.repository as repository


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ops", tags=["Operations"])


class TriggerProcessResponse(BaseModel):
    emails_processed_count: int
    attachments_processed_count: int
    bl_processed_count: int
    docs_created_count: int
    skipped_duplicated_docs_count: int


@router.post("/process", response_model=TriggerProcessResponse)
async def trigger_processing():
    emails = fetch_latest_emails()
    bls: list[BLDocument] = []
    original_att_count = 0
    
    for e in emails:
        for att in e.attachments:
            original_att_count += 1
            bls.extend(split_grouped_bills(att))
        del e.attachments

    logger.info("checking for duplicates")
    original_docs_count = len(bls)
    bls = await check_duplicates(bls)
    logger.info(f"Number of unique BL documents found are {len(bls)}")
    if not bls: return TriggerProcessResponse(
            emails_processed_count=len(emails),
            attachments_processed_count=original_att_count,
            bl_processed_count=original_docs_count,
            docs_created_count=len(bls),
            skipped_duplicated_docs_count=original_docs_count-len(bls),
        )
    
    emails = {e.id: e for e in emails}
    to_process_bls = [{"bytes": b.content, "bl_number": b.bl_number, "latest_body_text": emails[b.email_id].latest_body_text} for b in bls]
    
    pbls = process_shipping_documents(to_process_bls)
    
    logger.info(f"We have Extracted {len(pbls)} BLs")
    db_bls = create_bls_for_db(pbls, bls, emails)
    await repository.save_bls(db_bls)

    return TriggerProcessResponse(
            emails_processed_count=len(emails),
            attachments_processed_count=original_att_count,
            bl_processed_count=original_docs_count,
            docs_created_count=len(bls),
            skipped_duplicated_docs_count=original_docs_count-len(bls),
        )

