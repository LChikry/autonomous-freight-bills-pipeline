from fastapi import FastAPI, Request, Depends
import time
import logging

from fetch_emails import fetch_latest_emails
from attachments_handler import split_grouped_bills
from shared_types.app_types import BLDocument, BaseEmail
import db
from doc_extraction import process_shipping_documents
from bl_process import check_duplicates, create_bls_for_db
from shared_types.api_types import PostProcessResponse, GetHblListRequest, GetMblListRequest, GetHblListResponse, GetMblListResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s, %(name)-33s, %(levelname)-5s, %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI()
logger = logging.getLogger(__name__)
logger.info("\n\nNEW INSTANCE--------------------------------------------")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    
    logger.info(
        f"Path: {request.url.path} "
        f"Method: {request.method} "
        f"Status: {response.status_code} "
        f"Duration: {formatted_process_time}ms"
    )
    
    return response

@app.get("/")
def status_check():
    return {"status": "ok"}


@app.post("/process", response_model=PostProcessResponse)
async def process():
    emails = fetch_latest_emails(limit=1)
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



@app.get("/hbl", response_model=GetHblListResponse)
async def fetch_hbl(params: GetHblListRequest = Depends()):
    limit, cursor = params.limit, params.cursor or None
    docs, cursor = await db.get_paginated_documents("hbl", limit, cursor)
    
    return GetHblListResponse(
        documents=docs,
        next_cursor=cursor
    )


@app.get("/mbl", response_model=GetMblListResponse)
async def fetch_mbl(params: GetMblListRequest = Depends()):
    limit, cursor = params.limit, params.cursor or None
    docs, cursor = await db.get_paginated_documents("mbl", limit, cursor)
    
    return GetMblListResponse(
        documents=docs,
        next_cursor=cursor
    )