from fastapi import APIRouter
import logging

from core.attachments_handler import split_grouped_bills
from services.gmail import fetch_latest_emails
from services.ai import process_shipping_documents
from core.bl_process import check_duplicates, create_bls_for_db
from shared_types.app_types import BLDocument
from services.ai import process_shipping_documents
from core.bl_process import check_duplicates, create_bls_for_db
from shared_types.api_types import PostProcessResponse
import services.db as db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ops", tags=["Operations"])


@router.post("/process", response_model=PostProcessResponse)
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
    if not bls: return PostProcessResponse(
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
    await db.save_bls(db_bls)

    return PostProcessResponse(
            emails_processed_count=len(emails),
            attachments_processed_count=original_att_count,
            bl_processed_count=original_docs_count,
            docs_created_count=len(bls),
            skipped_duplicated_docs_count=original_docs_count-len(bls),
        )

