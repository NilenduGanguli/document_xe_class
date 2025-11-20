import asyncio
import base64
from pathlib import Path
from typing import Optional, List
from google.genai import types
import aiofiles
import logging

from ..config.llm_config import get_llm

from .schema_converter import convert_db_schema_to_pydantic
from ..config import EXTRACTION_RETRY_ATTEMPTS
from ..db.models import DocumentSchema

# Configure logging
logger = logging.getLogger(__name__)


def detect_document_format(document_path: Path, content_type: str) -> str:
    if content_type == "application/pdf":
        return "pdf"
    
    extension = document_path.suffix.lower()
    format_map = {
        '.jpg': 'jpeg',
        '.jpeg': 'jpeg',
        '.png': 'png',
        '.pdf': 'pdf'
    }
    return format_map.get(extension, 'jpeg')


async def extract_with_db_schema(
    document_paths: List[Path],
    document_types: List[str],
    document_schema: DocumentSchema,
    attempt: int = 0
) -> Optional[str]:
    try:
        contents = []
        
        for doc_path, content_type in zip(document_paths, document_types):
            if not doc_path.exists():
                logger.warning(f"Document path does not exist: {doc_path}")
                continue
                
            try:
                async with aiofiles.open(doc_path, "rb") as doc_file:
                    document_data = await doc_file.read()

                contents.append(types.Part.from_bytes(data=document_data, mime_type=content_type))
            except IOError as e:
                logger.error(f"Failed to read document {doc_path}: {e}")
                continue

        if not contents:
            logger.error("No content could be read from documents")
            return None

    except Exception as e:
        logger.error(f"Error preparing document content: {e}")
        return None

    # Add a text prompt to contents to ensure the model receives a user instruction
    contents.append(types.Part.from_text(text="Please extract the information from the provided documents according to the schema."))

    try:
        pydantic_model = convert_db_schema_to_pydantic(
            document_schema.document_schema,
            document_schema.document_type
        )
    except Exception as e:
        logger.error(f"Failed to convert schema to Pydantic model: {e}")
        raise

    schema_fields = list(document_schema.document_schema.keys())

    extraction_prompt = f"""
    CRITICAL: Extract information from this {document_schema.document_type} document(s) (images and/or PDFs).
    
    STRICT EXTRACTION REQUIREMENTS:
    1. Examine the document(s) carefully (images and/or PDFs) and extract ALL visible information
    2. For each field, provide the EXACT text/value as it appears in the document
    3. If any information is unreadable or unclear, mark 'information_unreadable' as true
    4. If the document doesn't match the expected type, mark 'is_document_correct' as false
    5. For dates, use DD/MM/YYYY format unless a different format is clearly specified
    6. For names, include full names as they appear
    7. For numbers, include all digits and formatting as shown
    8. If a field is not visible or not present, leave it as null/empty

    ACCURACY REQUIREMENTS:
    - Double-check all extracted text for accuracy
    - Preserve original formatting and spacing where relevant
    - Do not guess or hallucinate information not clearly visible
    - If text is partially obscured, extract what is clearly readable
    - Process all provided documents (images and PDFs) to extract complete information
    
    Document Type: {document_schema.document_type}
    Country: {document_schema.country}
    Expected Fields: {schema_fields}
    
    FIELD DESCRIPTIONS:
    """

    for field_name, field_def in document_schema.document_schema.items():
        extraction_prompt += f"- {field_name}: {field_def.get('description', 'No description')}\n"

    if attempt > 0:
        retry_guidance = f"""
        
    RETRY ATTEMPT {attempt + 1}:
    Previous extraction had errors. Please ensure:
    - All field values match their expected types
    - Date formats are consistent (DD/MM/YYYY)
    - Required fields are not left empty unless truly unreadable
    - Text extraction is precise and matches what's visible in the documents
        """
        final_prompt = extraction_prompt + retry_guidance
    else:
        final_prompt = extraction_prompt

    client = get_llm()

    for retry_attempt in range(EXTRACTION_RETRY_ATTEMPTS + 1):
        try:
            logger.info(f"Sending extraction request to LLM (Attempt {retry_attempt + 1})")
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=final_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=pydantic_model
                )
            )

            validated_data = response.parsed
            if validated_data is None:
                logger.error("LLM returned None for parsed data")
                raise ValueError("LLM returned None for parsed data")
                
            return validated_data.model_dump_json(indent=2)
        except Exception as e:
            logger.error(f"Extraction attempt {retry_attempt + 1} failed: {e}")
            if retry_attempt == EXTRACTION_RETRY_ATTEMPTS:
                raise

            wait_time = 2 ** retry_attempt
            await asyncio.sleep(wait_time)


async def extract_with_schema(
    front_image_path: Path,
    back_image_path: Optional[Path],
    document_schema,
    pydantic_model,
    attempt: int = 0
) -> Optional[str]:
    return await extract_with_db_schema(
        front_image_path, back_image_path, document_schema, attempt
    )
