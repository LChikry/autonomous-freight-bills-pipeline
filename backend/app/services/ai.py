import asyncio
from loguru import logger
from app.core import settings
from pydantic_ai import Agent
from returns.result import Result, Success, Failure
from returns.pipeline import is_successful

from app.schemas.llm import LLMRequest, LLMResponse
from app.core import log_call


async def extract_bl_documents_data(bl_documents: list[LLMRequest]) -> list[LLMResponse]:
    logger.info(f"Sending {len(bl_documents)} BL documents for extraction using {settings.llm_model_name}")
    
    agent = Agent(
        model=f"{settings.llm_provider_name}:{settings.llm_model_name}",
        system_prompt="You are an excellent PDF information extractor. You help users extract information from their Bill of Lading. Always return the expected structured output and be precise and accurate. DO NOT MADE UP VALUES; IF YOU DON NOT HAVE THE VALUE OF THE FIELD RETURN `null` IN THE JSON; DON'T WRITE SOMETHING LIKE 'ANONYMOUS' OR 'SOME PLACE' ETC.",
        output_type=LLMResponse,
        retries=3,
    )
    
    MAX_CONCURRENT_CALLS = 10
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
    
    extraction_requests = [
        _extract_bill_text_content(bl, agent, semaphore)
        for bl in bl_documents
    ]
    
    results = await asyncio.gather(*extraction_requests, return_exceptions=True)
    return [
        r.unwrap()
        for r in results
        if isinstance(r, Success)
    ]


async def _extract_bill_text_content(bill: LLMRequest, agent: Agent[None, LLMResponse], semaphore: asyncio.Semaphore) -> Result[LLMResponse, str]:
    prompt = (
        "<RequestId>\n"
        f"{bill.request_id}"
        "</RequestId>\n"
        "<DocumentBytes>\n"
        f"{bill.content}\n"
        "</DocumentBytes>\n"
        "<EmailBody>\n"
        f"{bill.email_body}\n"
        "</EmailBody>\n"
        "<UserPrompt>\n"
        "Extract the bill of lading data from the DocumentBytes section. Also, use the email content in EmailBody section to classify email_status to be strictly either 'pre_alert' or 'draft'\n"
        "</UserPrompt>\n"
        )
        
    async with semaphore:
        try:
            with log_call(settings.llm_provider_name, model_type=settings.llm_model_name):
                res = await agent.run(user_prompt=prompt)
                return Success(res.output)
        except Exception:
            return Failure("API_FAILED")