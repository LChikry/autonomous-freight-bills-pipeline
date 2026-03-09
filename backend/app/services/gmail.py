import base64, hashlib
from loguru import logger
from pydantic import SecretStr
from returns.result import Result, Success, Failure
from enum import StrEnum, auto

from app.core import log_call
from app.services.auth_gmail import get_gmail_service
from app.models.emails import Email, Attachment, EmailBody, EmailHeader
from app.schemas.gmail_service import GmailMessageBlueprint, GmailMessageResponse, GmailHeader, GmailPart

__init__ = ["fetch_latest_emails", "FetchLatestEmailsError"]

class FetchLatestUnrecordedEmailsError(StrEnum):
    NO_EMAILS = auto()
    API_FAILED = auto()
    BAD_API_RESPONSE = auto()

async def fetch_latest_emails(limit: int = 10, user_id: str = 'me', label_id: str = "INBOX") -> Result[list[Email], FetchLatestUnrecordedEmailsError]:
    service = get_gmail_service()
    try:
        with log_call("Gmail/messages/list", max_email=limit, email_label=label_id, user_id=user_id):
            results = (
                service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=limit).execute()
            )
    except Exception:
        return Failure(FetchLatestUnrecordedEmailsError.API_FAILED)
    
    try:
        messages: list[GmailMessageBlueprint] = [
            GmailMessageBlueprint(**msg) for msg in results["messages"]
        ]
        if not messages:
            logger.debug("No emails found to fetch")
            return Failure(FetchLatestUnrecordedEmailsError.NO_EMAILS)
    except Exception:
        logger.exception("Gmail/messages/list response model is not as expected")
        return Failure(FetchLatestUnrecordedEmailsError.BAD_API_RESPONSE)
    
    logger.debug(f"{len(messages)} emails found")
    result: list[Email] = []
    
    seen_attachments = set()
    for msg in messages:
        with logger.contextualize(message_id=msg.id):
            email_data = _fetch_message_data(service, user_id, msg, seen_attachments)
            if not email_data: continue
            result.append(email_data)

    logger.debug(f"{len(result)} emails fetched for processing, {len(messages) - len(result)} emails skipped")
    return Success(result)


def _fetch_message_data(service, user_id: str, msg: GmailMessageBlueprint, unique_docs: set) -> Email | None:
    logger.debug(f"Fetching a new email")
    
    try:
        with log_call("Gmail/messages/get"):
            message_response = (
                service.users().messages().get(userId="me", id=msg.id, format="full").execute()
            )
    except Exception:
        return
    
    try:
        email = GmailMessageResponse(**message_response)
        if not email.has_attachments:
            logger.debug(f"Skipping the email because it has no attachments")
            return
    except Exception:
        logger.exception("Gmail/messages/get response model is not as expected")
        return
    
    attachments = _extract_exclusive_attachments(service, user_id, email, unique_docs)
    if not attachments:
        logger.debug(f"Skipping the email because it has no bills")
        return

    email_body: EmailBody = _extract_email_body(email)
    if not email_body.has_body:
        logger.debug(f"Skipping email because it has no body text")
        return

    email_header: EmailHeader= _parse_headers(email.payload.headers)
    
    return Email(
        email_id=email.id,
        subject=email_header.subject,
        sender=email_header.sender,
        full_body=email_body.full_body,
        recent_body=email_body.recent_body,
        received_at=email.internalDate,
        unique_attachments=attachments,
    )


def _parse_headers(headers: list[GmailHeader]) -> EmailHeader:
    logger.debug("parsing header")
    subject, sender = "", ""
    for h in headers:
        if h.is_subject: subject = h.value
        if h.is_sender: sender = h.value
        if subject and sender: break
    
    if 'Fwd: ' in subject: subject = subject[5:]
    return EmailHeader(
        subject=subject,
        sender=SecretStr(sender),
    )


def _extract_email_body(email: GmailMessageResponse) -> EmailBody:
    logger.debug(f"Parsing for full email text content and latest body")
    full_body = _get_email_full_body(email.payload) or ""
    recent_body = _extract_latest_body_text(full_body) or ""
    return EmailBody(
        full_body=full_body,
        recent_body=recent_body,
    )


def _get_email_full_body(part: GmailPart) -> str | None:
    if not part: return None
    
    def decode_data(data):
        """Helper to handle Base64 decoding"""
        if not data:
            return ""
        # Python requires padding for base64 decoding if length isn't divisible by 4
        padding = len(data) % 4
        if padding:
            data += '=' * (4 - padding)
        return base64.urlsafe_b64decode(data).decode('utf-8')
    
    if part.is_text:
        assert part.body, "body in part must exist, check is_text logic"
        return decode_data(part.body.data)
    
    for subpart in part.parts:
        text = _get_email_full_body(subpart)
        if text: return text
    return None


def _extract_latest_body_text(body_text: str | None) -> str | None:
    if not body_text: return None
    
    separator = "---------- Forwarded message ---------"
    if separator not in body_text:
        return body_text
    return body_text.split(separator)[0].strip()


def _extract_exclusive_attachments(service, user_id: str, email: GmailMessageResponse, seen_attachments: set) -> list[Attachment]:
    logger.debug("extracting attachments")
    bill_attachments = []
    
    parts: list[GmailPart] = [email.payload]
    while parts:
        part = parts.pop()
        parts.extend(part.parts)
        
        if not part.is_attachment: continue
        if not part.is_pdf:
            logger.debug(f"A non PDF attachment is skipped")
            continue

        assert part.body, "part.body must exist, check is_attachment logic!"
        assert part.body.attachmentId and part.filename, "attachment information must exist"
        att_id = part.body.attachmentId 
        filename = part.filename
        
        with logger.contextualize(attachment_id=att_id, filename=filename):
            logger.debug(f"A bill attachment found; start fetching")
            try:
                with log_call("Gmail/messages/attachments/get"):
                    attachment = service.users().messages().attachments().get(
                        userId=user_id,
                        messageId=email.id,
                        id=att_id
                    ).execute()
            except Exception:
                return []

            try:
                file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            except Exception:
                logger.exception("Gmail.users.messages.attachments model structure was not as expected")
                return []
        
        file_hash = hashlib.sha256(file_data).hexdigest()
        if file_hash in seen_attachments: continue
        seen_attachments.add(file_hash)
        
        bill_attachments.append(Attachment(
            attachment_id=att_id,
            email_id=email.id,
            filename=filename,
            content=file_data,
            original_content_sha256=file_hash
        ))

    return bill_attachments
