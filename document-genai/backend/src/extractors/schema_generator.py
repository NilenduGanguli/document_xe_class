import asyncio
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from google.genai import types
import aiofiles
from pydantic import BaseModel, Field
import logging

from ..config.llm_config import get_llm
from ..config import SCHEMA_GENERATION_RETRY_ATTEMPTS

# Configure logging
logger = logging.getLogger(__name__)


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


class SchemaFieldItem(BaseModel):
    name: str = Field(..., description="Name of the field (snake_case)")
    definition: FieldDefinition = Field(..., description="Definition of the field")


class GeneratedSchema(BaseModel):
    document_type: str = Field(..., description="Type of document analyzed")
    country: str = Field(...,
                         description="Country of document issuance (ISO 3166-1 alpha-2 code)")
    fields: List[SchemaFieldItem] = Field(..., description="List of fields in the schema")
    confidence: float = Field(..., ge=0, le=1,
                              description="Confidence in schema generation")


async def get_field_list_from_documents(
    document_paths: List[Path],
    document_types: List[str],
    document_type: str,
    country: str
) -> Optional[List[str]]:
    try:
        contents = []
        
        for doc_path, content_type in zip(document_paths, document_types):
            if not doc_path.exists():
                continue
                
            async with aiofiles.open(doc_path, "rb") as doc_file:
                document_data = await doc_file.read()

            contents.append(types.Part.from_bytes(data=document_data, mime_type=content_type))

        if not contents:
            return None

    except IOError as e:
        logger.error(f"Error reading documents for field extraction: {e}")
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

    client = get_llm()

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[types.Part.from_text(text=prompt)] + contents,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ExtractedFields
            )
        )
        return response.parsed.field_names
    except Exception as e:
        logger.error(f"Field extraction failed: {e}")
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
            parts = []
            for doc_path, content_type in zip(document_paths, document_types):
                if not doc_path.exists():
                    continue
                    
                async with aiofiles.open(doc_path, "rb") as doc_file:
                    document_data = await doc_file.read()

                parts.append(types.Part.from_bytes(data=document_data, mime_type=content_type))
            return parts

        document_reading_tasks.append(read_document_data())

        results = await asyncio.gather(field_extraction_task, *document_reading_tasks)
        field_names = results[0]
        document_parts = results[1]

        if not field_names or not document_parts:
            logger.error("Failed to get field names or document parts")
            return None

    except IOError as e:
        logger.error(f"Error preparing data for schema generation: {e}")
        return None

    generation_prompt = f"""
    CRITICAL INSTRUCTION: You MUST analyze this {document_type} document and generate a detailed schema for the following fields: {", ".join(field_names)}.
    Return a GeneratedSchema object with the EXACT format specified below.

    STRICT FORMAT REQUIREMENTS:
    - document_type: "{document_type}"
    - country: "{country}"
    - fields: A list of objects, where each object has:
      - name: The field name (snake_case)
      - definition: An object containing:
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
        "fields": [
            {{
                "name": "pan_number",
                "definition": {{
                    "type": "string",
                    "description": "The PAN card number",
                    "required": false,
                    "example": "ABCDE1234F",
                    "pattern": "^[A-Z]{{5}}[0-9]{{4}}[A-Z]$"
                }}
            }},
            {{
                "name": "name",
                "definition": {{
                    "type": "string", 
                    "description": "The full name of the cardholder",
                    "required": false,
                    "example": "JOHN DOE"
                }}
            }},
            {{
                "name": "is_document_correct",
                "definition": {{
                    "type": "boolean",
                    "description": "Set to true if the document appears to be a PAN card",
                    "required": true,
                    "example": true
                }}
            }}
        ],
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

    client = get_llm()

    for attempt in range(SCHEMA_GENERATION_RETRY_ATTEMPTS):
        try:
            logger.info(f"Sending schema generation request to LLM (Attempt {attempt + 1})")
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[types.Part.from_text(text=generation_prompt)] + document_parts,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=GeneratedSchema
                    )
                ),
                timeout=240.0
            )

            # Convert the list of fields back to the dictionary format expected by the application
            parsed_response = response.parsed
            
            # Create a new object with the expected structure for the rest of the app
            # We need to return an object that has a 'document_schema' attribute which is a dict
            
            class LegacyGeneratedSchema(BaseModel):
                document_type: str
                country: str
                document_schema: Dict[str, Any]
                confidence: float

            schema_dict = {}
            for field_item in parsed_response.fields:
                schema_dict[field_item.name] = field_item.definition.model_dump()
            
            return LegacyGeneratedSchema(
                document_type=parsed_response.document_type,
                country=parsed_response.country,
                document_schema=schema_dict,
                confidence=parsed_response.confidence
            )

        except asyncio.TimeoutError:
            logger.error(f"Schema generation timed out (Attempt {attempt + 1})")
            if attempt == SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
                return None

        except Exception as e:
            logger.error(f"Schema generation failed (Attempt {attempt + 1}): {e}")
            if attempt == SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
                return None

        if attempt < SCHEMA_GENERATION_RETRY_ATTEMPTS - 1:
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
