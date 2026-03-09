from loguru import logger
import re, io, pdfplumber, pikepdf
from attrs import define, field
from datetime import datetime
from returns.result import Result, Success, Failure
from returns.pipeline import is_successful
from enum import StrEnum, auto

from app.models.emails import Email, AttachmentTransformed, Attachment
from app.models.bill_of_lading import DocType

__all__ = ["process_emails_to_bills"]

@define
class _BillMetadata():
    page_range: tuple[int, int]
    bl_number: str | None
    issuer_name: str | None
    doc_type: DocType | None = field(
        converter=lambda t: DocType(t) if t.lower() in DocType else None
    )
    generated_at: datetime | None = field(
        converter=lambda s: datetime.strptime(s, "%d-%b-%Y %H:%M") if s and isinstance(s, str) else None if not s else s
    )

@define
class _BillData(_BillMetadata):
    content: bytes

class _GetBillMetadataError(StrEnum):
    HAS_ZERO_PAGES = auto()
    PAGES_NOT_IDENTIFIED = auto()

class ProcessEmailsToBillsError(StrEnum):
    DOCUMENT_CONTENT_DO_NOT_EXIST_OR_INVALID = auto()
    

def process_emails_to_bills(emails: list[Email]) -> Result[tuple[int, list[AttachmentTransformed]], str]:
    result: list[AttachmentTransformed] = []
    attachments_count = 0
    skipped_att_count = 0
    
    for email in emails:
        attachments_count += len(email.unique_attachments)
        for att in email.unique_attachments:
            
            with logger.contextualize(email_id=email.email_id, attachment_id=att.attachment_id):
                metadata = _get_bill_metadata(att.content)

                if not is_successful(metadata):
                    logger.debug("Attachment has no content", result_msg=metadata.failure())
                    skipped_att_count += 1
                    continue
                
                pages_count, pages_metadata = metadata.unwrap()
                transformed_att = _transform_attachment(att, pages_count, pages_metadata)
                
                for trans_att in transformed_att:
                    result.append(AttachmentTransformed(
                        attachment_id=att.attachment_id,
                        email_id=att.email_id,
                        filename=att.filename,
                        email=email,
                        content=trans_att.content,
                        original_content_sha256=att.original_content_sha256,
                        bl_number=trans_att.bl_number,
                        page_range=trans_att.page_range,
                        doc_type=trans_att.doc_type,
                        generated_at=trans_att.generated_at,
                        issuer_name=trans_att.issuer_name,
                    ))
    
    if len(result) == 0:
        return Failure(ProcessEmailsToBillsError.DOCUMENT_CONTENT_DO_NOT_EXIST_OR_INVALID)
    return Success((attachments_count, result))


def _get_bill_metadata(file_content: bytes) -> Result[tuple[int, list[_BillMetadata]], _GetBillMetadataError]: 
    issuer_pattern = re.compile(r"issued\s*by\s*:\s*(.+)", re.IGNORECASE)
    page_range_pattern = re.compile(r"Page\s+(\d+)\s*(?:of|/)\s*(\d+)", re.IGNORECASE)
    bl_number_pattern = re.compile(r"Reference:\s*((?:MBL|HBL)-\d+)", re.IGNORECASE)
    date_pattern = re.compile(r"Generated:\s*(\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2})", re.IGNORECASE)
    

    bills: list[_BillMetadata] = []
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        if len(pdf.pages) <= 0:
            return Failure(_GetBillMetadataError.HAS_ZERO_PAGES)
        
        is_bill_exist = False
        
        cur_start_page = 0
        active_bln = None
        active_date = None
        active_doc_type = None
        active_issuer = None
        
        for page_num, page in enumerate(pdf.pages):
            header = page.crop((0, 0, page.width, page.height * 0.15))
            footer = page.crop((0, page.height * 0.9, page.width, page.height))
            header_text = header.extract_text() or ""
            footer_text = footer.extract_text() or ""
            
            issuer_match = issuer_pattern.search(header_text)
            page_match = page_range_pattern.search(footer_text)
            bln_match = bl_number_pattern.search(footer_text)
            date_match = date_pattern.search(footer_text)
            
            if page_match and int(page_match.group(1)) == 1: # New Bill
                is_bill_exist = True
                if page_num > 0: # Not first page
                    bills.append(_BillMetadata(
                        page_range=(cur_start_page, page_num),
                        bl_number=active_bln,
                        generated_at=active_date,
                        doc_type=active_doc_type,
                        issuer_name=active_issuer,
                    ))
                    cur_start_page = page_num
                
                new_bln = new_doc_type = None
                if bln_match:
                    new_bln = str(bln_match.group(1)).upper()
                    new_doc_type = new_bln.split("-")[0].lower()
                active_bln, active_doc_type = new_bln, new_doc_type
                
                new_date = None
                if date_match: new_date = str(date_match.group(1))
                active_date = new_date
                
                new_issuer = None
                if issuer_match:
                    new_issuer = str(issuer_match.group(1)).strip()
                active_issuer = new_issuer
                
                continue
            
            # Fallback
            if bln_match and not active_bln:
                active_bln = str(bln_match.group(1)).upper()
                active_doc_type = active_bln.split("-")[0].lower()
            
            if date_match and not active_date:
                active_date = str(date_match.group(1))
            
            if issuer_match and not active_issuer:
                active_issuer = str(issuer_match.group(1)).strip()

        if not is_bill_exist:
            return Failure(_GetBillMetadataError.PAGES_NOT_IDENTIFIED)

        total_pages = len(pdf.pages)
        bills.append(_BillMetadata(
            page_range=(cur_start_page, total_pages),
            bl_number=active_bln,
            generated_at=active_date,
            doc_type=active_doc_type,
            issuer_name=active_issuer,
        ))
        return Success((total_pages, bills))


def _transform_attachment(attachment: Attachment, total_pages: int, pages_metadata: list[_BillMetadata]) -> list[_BillData]:
    assert total_pages != 0, "the file must have at least 1 page"

    if len(pages_metadata) == 1:
        start, end = pages_metadata[0].page_range
        if start == 0 and end == total_pages: # for mixed files
            logger.debug("Attachment has exactly one bill")
            return [
                _BillData(
                    bl_number=pages_metadata[0].bl_number,
                    page_range=pages_metadata[0].page_range,
                    doc_type=pages_metadata[0].doc_type,
                    generated_at=pages_metadata[0].generated_at,
                    content=attachment.content,
                    issuer_name=pages_metadata[0].issuer_name,
                )
            ]

    logger.debug("Attachment has multiple bills")
    splitted_bills: list[_BillData] = []
    with pikepdf.open(io.BytesIO(attachment.content)) as pdf:
        for page in pages_metadata:
            new_pdf = pikepdf.new()
            for page_num in range(page.page_range[0], page.page_range[1]):
                new_pdf.pages.append(pdf.pages[page_num])
            
            output_buffer = io.BytesIO()
            new_pdf.save(output_buffer)
            
            splitted_bills.append(_BillData(
                bl_number=page.bl_number,
                page_range=page.page_range,
                doc_type=page.doc_type,
                generated_at=page.generated_at,
                content=output_buffer.getvalue(),
                issuer_name=page.issuer_name,
            ))
    
    return splitted_bills