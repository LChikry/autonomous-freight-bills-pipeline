from fastapi import FastAPI, Request
import time
import logging
from collections import defaultdict

from fetch_emails import fetch_latest_emails
from attachments_handler import split_grouped_bills
from types.app_types import BLDocument, BaseEmail
from db import save_bls
from types.bl_schema import DbBL
from doc_extraction import process_shipping_documents
from bl_process import check_duplicates, create_bls_for_db

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


@app.post("/process")
async def process():
    emails = fetch_latest_emails(limit=1)
    bls: list[BLDocument] = []
    
    for e in emails:
        for att in e.attachments:
            bls.extend(split_grouped_bills(att))
        del e.attachments

    bls = check_duplicates(bls)
    if not bls: return
    
    emails = {e.id: e for e in emails}
    to_process_bls = [{"bytes": b.content, "bl_number": b.bl_number, "latest_body_text": emails[b.email_id].latest_body_text} for b in bls]
    pbls = process_shipping_documents(to_process_bls)
    
    logger.info(f"We have Extracted {len(pbls)} BLs")
    db_bls = create_bls_for_db(pbls, bls, emails)
    save_bls(db_bls)


@app.get("/hbl")
async def fetch_hbl():
    pass