from loguru import logger
from attrs import asdict

import app.services.repository as repository
from app.models.emails import AttachmentTransformed
from app.schemas.llm import LLMResponse
from app.schemas.db import BLRecordCreate, BLRecordEmail, BLRecordAttachment

async def get_unique_bl_attachment(bills: list[AttachmentTransformed]) -> tuple[list[AttachmentTransformed], list[AttachmentTransformed]]:
    assert bills, "the list must have attachments"
    logger.debug("removing duplicate attachments in db")
    
    unchecked_bl: list[AttachmentTransformed] = []
    unique_bills: list[AttachmentTransformed] = []
    for b in bills:
        # print("\ndocument in question", b.original_content_sha256, "bl_number", b.bl_number, "issuer_name", b.issuer_name, end="\n\n")
        if (
            await repository.is_bl_attachment_exist(b.original_content_sha256, b.page_range, b.doc_type)
        ): continue
        
        # print("\ndocument don't exist:", b.original_content_sha256, end="\n\n")
        
        if not b.bl_number or not b.issuer_name:
            unchecked_bl.append(b)
            continue
        
        if (
            await repository.is_bl_record_exist(b.bl_number, b.issuer_name, b.doc_type)
        ): continue
        
        # print("\ndocument don't exist:", "bl_number", b.bl_number, "issuer_name", b.issuer_name, end="\n\n")
        # exit()
        unique_bills.append(b)
    
    diff_count = len(bills) - len(unique_bills)
    if diff_count:
        logger.debug(f"{diff_count} duplicates found before processing")
    
    return unique_bills, unchecked_bl


# hashed_bl: request_id (LLMResponse) -> AttachmentTransformed
async def get_unique_bl_records(bl_data: list[LLMResponse], hashed_bl: dict[str, AttachmentTransformed]) -> list[LLMResponse]:
    assert bl_data, "the list must have bills records"
    
    unique_bl_data: list[LLMResponse] = []
    for b in bl_data:
        if (
            await repository.is_bl_record_exist(b.bl_number, b.issuer_name, b.doc_type)
        ): continue
        
        unique_bl_data.append(b)
    return unique_bl_data