import asyncio
import base64
from pathlib import Path
from typing import Optional, List
from langchain_core.messages import HumanMessage
import aiofiles

from ..config.llm_config import get_llm

from .schema_converter import convert_db_schema_to_pydantic
from ..config import EXTRACTION_RETRY_ATTEMPTS
from ..db.models import DocumentSchema


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
        document_parts = []
        
        for doc_path, content_type in zip(document_paths, document_types):
            if not doc_path.exists():
                continue
                
            try:
                async with aiofiles.open(doc_path, "rb") as doc_file:
                    document_data = base64.b64encode(await doc_file.read()).decode("utf-8")

                if content_type == "application/pdf":
                    document_parts.append({
                        "type": "media",
                        "mime_type": "application/pdf",
                        "data": document_data
                    })
                else:
                    doc_format = detect_document_format(doc_path, content_type)
                    document_parts.append({
                        "type": "image_url",
                        "image_url": f"data:{content_type};base64,{document_data}",
                    })
            except IOError as e:
                continue

        if not document_parts:
            return None

    except Exception as e:
        return None

    pydantic_model = convert_db_schema_to_pydantic(
        document_schema.document_schema,
        document_schema.document_type
    )

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

    llm = await get_llm(
        model_name="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.0,
        structured_schema=pydantic_model
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": final_prompt},
            *document_parts,
        ]
    )

    for retry_attempt in range(EXTRACTION_RETRY_ATTEMPTS + 1):
        try:
            validated_data = await llm.ainvoke([message])

            return validated_data.model_dump_json(indent=2)
        except Exception as e:
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
