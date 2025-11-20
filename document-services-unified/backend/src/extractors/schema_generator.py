import asyncio
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from langchain_core.messages import HumanMessage
import aiofiles
from pydantic import BaseModel, Field

from ..config.llm_config import get_llm
from ..config import SCHEMA_GENERATION_RETRY_ATTEMPTS
from ..utils.parsing import parse_llm_string_to_dict


class ExtractedFields(BaseModel):
    field_names: List[str] = Field(...,
                                   description="List of field names found in the document")


class FieldDefinition(BaseModel):
    type: str = Field(...,
                      description="Field data type (string, integer, date, boolean, etc.)")
    description: str = Field(...,
                             description="Description of what this field contains")
    required: bool = Field(
        default=True, description="Whether this field is required")
    example: Optional[str] = Field(
        default=None, description="Example value for this field")
    pattern: Optional[str] = Field(
        default=None, description="Regex pattern for validation")
    confidence: float = Field(..., ge=0, le=1,
                              description="Confidence in schema generation")


class GeneratedSchema(BaseModel):
    document_type: str = Field(..., description="Type of document analyzed")
    country: str = Field(...,
                         description="Country of document issuance (ISO 3166-1 alpha-2 code)")
    document_schema: Dict[str, Dict[str, Any]
                          ] = Field(..., description="Schema definition with field details")
    confidence: float = Field(..., ge=0, le=1,
                              description="Confidence in schema generation")


async def get_field_list_from_documents(
    document_paths: List[Path],
    document_types: List[str],
    document_type: str,
    country: str
) -> Optional[List[str]]:
    try:
        document_parts = []
        
        for doc_path, content_type in zip(document_paths, document_types):
            if not doc_path.exists():
                continue
                
            async with aiofiles.open(doc_path, "rb") as doc_file:
                document_data = base64.b64encode(await doc_file.read()).decode("utf-8")

            if content_type == "application/pdf":
                document_parts.append({
                    "type": "media",
                    "mime_type": "application/pdf",
                    "data": document_data
                })
            else:
                document_parts.append({
                    "type": "image_url", 
                    "image_url": f"data:{content_type};base64,{document_data}"
                })

        if not document_parts:
            return None

    except IOError as e:
        return None

    prompt = f"""
    Analyze the provided document(s) (images and/or PDFs) for a {document_type} from {country}.
    Identify every distinct field and label present in the document(s).
    Return the field names as a structured list.

    RULES FOR NAMING FIELDS:
    - Use snake_case for all field names
    - For visual elements, use these specific names:
      - signature_present for signatures
      - photo_present for photographs  
      - qr_code_present for QR codes
    - Do NOT use names like "signature" or "photo". Use the "_present" suffix
    - Include text fields like name, date_of_birth, id numbers, etc.
    - Include any headers or department names if visible
    - Process all provided documents (images and PDFs) to identify all fields

    IMPORTANT: Return the field names directly as a structured object, not as JSON text.
    """

    llm = await get_llm(
        model_name="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.0,
        structured_schema=ExtractedFields
    )

    message = HumanMessage(
        content=[{"type": "text", "text": prompt}, *document_parts])

    try:
        validated_data = await llm.ainvoke([message])
        return validated_data.field_names
    except Exception as e:
        return None


async def generate_schema_from_documents(
    document_paths: List[Path],
    document_types: List[str],
    document_type: str,
    country: str
) -> Optional[GeneratedSchema]:
    try:
        field_extraction_task = get_field_list_from_documents(
            document_paths, document_types, document_type, country
        )

        document_reading_tasks = []

        async def read_document_data():
            document_parts = []
            for doc_path, content_type in zip(document_paths, document_types):
                if not doc_path.exists():
                    continue
                    
                async with aiofiles.open(doc_path, "rb") as doc_file:
                    document_data = base64.b64encode(await doc_file.read()).decode("utf-8")

                if content_type == "application/pdf":
                    document_parts.append({
                        "type": "media",
                        "mime_type": "application/pdf",
                        "data": document_data
                    })
                else:
                    document_parts.append({
                        "type": "image_url",
                        "image_url": f"data:{content_type};base64,{document_data}",
                    })
            return document_parts

        document_reading_tasks.append(read_document_data())

        results = await asyncio.gather(field_extraction_task, *document_reading_tasks)
        field_names = results[0]
        document_parts = results[1]

        if not field_names or not document_parts:
            return None

    except IOError as e:
        return None

    generation_prompt = f"""
    CRITICAL INSTRUCTION: You MUST analyze this {document_type} document and generate a detailed schema for the following fields: {", ".join(field_names)}.
    Return a GeneratedSchema object with the EXACT format specified below.

    STRICT FORMAT REQUIREMENTS:
    - document_type: "{document_type}"
    - country: "{country}"
    - document_schema: A dictionary where each key is a field name and each value is a dictionary with:
      - type: "string" | "integer" | "date" | "boolean"
      - description: Clear description of the field
      - required: true | false
      - example: Example value (optional)
      - pattern: Regex pattern for validation (optional)
    - confidence: A float between 0.0 and 1.0

    EXAMPLE FORMAT FOR PAN CARD (follow this EXACTLY):
    {{
        "document_type": "pan_card",
        "country": "IN",
        "document_schema": {{
            "pan_number": {{
                "type": "string",
                "description": "The PAN card number",
                "required": false,
                "example": "ABCDE1234F",
                "pattern": "^[A-Z]{{5}}[0-9]{{4}}[A-Z]$"
            }},
            "name": {{
                "type": "string", 
                "description": "The full name of the cardholder",
                "required": false,
                "example": "JOHN DOE"
            }},
            "father_s_name": {{
                "type": "string",
                "description": "The father's name of the cardholder",
                "required": false,
                "example": "FATHER NAME"
            }},
            "date_of_birth": {{
                "type": "string",
                "description": "The date of birth as a string in DD/MM/YYYY format",
                "required": false,
                "example": "01/01/1990",
                "pattern": "^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\\\\d{{4}}$"
            }},
            "signature_present": {{
                "type": "boolean",
                "description": "Boolean indicating if a signature is visible",
                "required": false,
                "example": true
            }},
            "photo_present": {{
                "type": "boolean",
                "description": "Boolean indicating if a photograph is visible",
                "required": false,
                "example": true
            }},
            "qr_code_present": {{
                "type": "boolean",
                "description": "Boolean indicating if a QR code is visible",
                "required": false,
                "example": true
            }},
            "information_unreadable": {{
                "type": "boolean",
                "description": "Set to true if any required information is missing or unreadable",
                "required": true,
                "example": false
            }},
            "is_document_correct": {{
                "type": "boolean",
                "description": "Set to true if the document appears to be a PAN card",
                "required": true,
                "example": true
            }}
        }},
        "confidence": 0.95
    }}

    FIELD EXTRACTION RULES:
    1. Look at the document image carefully
    2. Identify ALL visible text fields and visual elements
    3. Create appropriate field names using snake_case
    4. Use only these data types: "string", "integer", "date", "boolean"
    5. Most fields should be optional (required: false) except for validation fields
    6. Include presence detection fields for visual elements (photos, signatures, QR codes)
    7. Always include information_unreadable and is_document_correct validation fields
    8. Add regex patterns for structured fields when appropriate
    9. Provide realistic examples based on what you see

    STRICT COMPLIANCE:
    - DO NOT add extra fields not in the format
    - DO NOT change the structure
    - Return valid JSON format
    - FOLLOW the example format exactly
    - Make most fields optional except validation fields
    - When including regex patterns, ensure backslashes are properly escaped
    - Return a proper JSON object

    Document to analyze: {document_type} from {country}
    Fields to process: {", ".join(field_names)}
    """

    llm = await get_llm(
        model_name="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.0,
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": generation_prompt},
            *document_parts,
        ]
    )

    for attempt in range(SCHEMA_GENERATION_RETRY_ATTEMPTS):
        try:
            response = await asyncio.wait_for(llm.ainvoke([message]), timeout=240.0)

            llm_output_str = response.content
            parsed_dict = parse_llm_string_to_dict(llm_output_str)
            generated_schema = GeneratedSchema(**parsed_dict)
            return generated_schema

        except asyncio.TimeoutError:
            if attempt == SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
                return None

        except Exception as e:
            if attempt == SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
                return None

        if attempt < SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
