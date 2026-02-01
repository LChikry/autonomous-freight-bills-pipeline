import instructor
import base64
from anthropic import Anthropic
from dotenv import load_dotenv
import os

from types.bl_schema import BatchExtractionResult, BillOfLading
from auth import get_credentials_filepath

load_dotenv(dotenv_path=get_credentials_filepath("../.env"))

def process_shipping_documents(file_data_list: list[dict]) -> list[BillOfLading]:
    client = instructor.from_anthropic(Anthropic(
        api_key= os.getenv("ANTHROPIC_API_KEY")
    ))

    # Prepare the message content for the batch
    content_blocks = []
    
    for file_info in file_data_list:
        raw_bytes = file_info['bytes']
        bl_number = file_info['bl_number']
        latest_body_text = file_info['latest_body_text']
        
        # KEY STEP: Convert raw bytes to standard Base64 string for API
        b64_string = base64.b64encode(raw_bytes).decode("utf-8")
        
        content_blocks.append({
            "type": "text",
            "text": f"""--- EMAIL CONTENT STARTS: ---
                    latest_body_text={latest_body_text}"""
        })
        
        content_blocks.append({
            "type": "text",
            "text": f"--- DOCUMENT START: ID {bl_number} ---"
        })
        
        # Add the document
        content_blocks.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64_string
            }
        })

    # Add the final instruction prompt
    content_blocks.append({
        "type": "text", 
        "text": (
            "Extract the shipping data from the attached Bill of Lading documents. Also, use the email content in latest_body_text section to classify email_status to be either pre_alert or draft."
            "For each document, set the 'source_file_id' field to the ID specified before the document. "
            "Return a list containing one result per document."
        )
    })

    print(f"Sending {len(file_data_list)} documents to Claude...")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929", 
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": content_blocks
                }
            ],
            response_model=BatchExtractionResult,
        )
        return response.documents

    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return []