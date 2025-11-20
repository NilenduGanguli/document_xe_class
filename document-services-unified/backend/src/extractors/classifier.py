import base64
from pathlib import Path
from typing import Optional, List
from langchain_core.messages import HumanMessage
import aiofiles
from difflib import SequenceMatcher
from sqlalchemy import select
from ..db.models import DocumentTypeClassification, DocumentSchema
from ..config.llm_config import get_llm
from ..db.connection import db


def calculate_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def get_existing_document_types(country: str) -> List[str]:
    try:
        async with db.async_session_factory() as session:
            stmt = select(DocumentSchema).where(DocumentSchema.country == country)
            result = await session.execute(stmt)
            existing_schemas = result.scalars().all()
            
            document_types = list(set(schema.document_type for schema in existing_schemas))
            return document_types
    except Exception as e:
        return []


def find_best_matching_document_type(classified_type: str, existing_types: List[str], threshold: float = 0.8) -> Optional[str]:
    if not existing_types:
        return None
    
    best_match = None
    best_score = 0.0
    
    classified_lower = classified_type.lower().strip()
    
    for existing_type in existing_types:
        existing_lower = existing_type.lower().strip()
        
        if classified_lower == existing_lower:
            return existing_type
        
        similarity = calculate_similarity(classified_lower, existing_lower)
        
        if (classified_lower in existing_lower or existing_lower in classified_lower):
            similarity = max(similarity, 0.85)
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = existing_type
    
    return best_match


async def classify_document_type(
    document_paths: List[Path],
    content_types: List[str],
    max_retries: int = 3
) -> Optional[DocumentTypeClassification]:
    if not document_paths or len(document_paths) == 0:
        return None

    try:
        document_parts = []
        
        for doc_path, content_type in zip(document_paths, content_types):
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

        if not document_parts:
            return None

    except IOError as e:
        return None

    classification_prompt = """
    You MUST analyze these document(s) (images and/or PDFs) and classify the document type AND identify the issuing country.
    
    CLASSIFICATION REQUIREMENTS:
    1. Identify the specific document type from the image
    2. Identify the country that issued this document
    3. Provide confidence score between 0.0 and 1.0
    4. Examples of document type names (lowercase with underscores):
       - aadhar_card (Indian Aadhar/Aadhaar card)
       - pan_card (Indian PAN card)
       - passport (Any country passport)
       - driver_license (Driving license/permit)
       - voter_id (Voter ID card)
       - bank_statement (Bank account statement)
       - utility_bill (Electricity/gas/water bill)
       - income_certificate (Income certificate)
       - birth_certificate (Birth certificate)
       - marriage_certificate (Marriage certificate)
       - property_deed (Property documents)
       - insurance_policy (Insurance documents)
       - medical_report (Medical reports/prescriptions)
       - academic_certificate (Educational certificates)
       - employment_letter (Employment/salary documents)
    
    5. CRITICAL: Only use the above specific document types. DO NOT use generic categories like "other_government_id", "other_financial", or "other_personal"
    6. If the document doesn't match any of the above types, use the exact document name you see (e.g., if you see "Domicile Certificate", use "domicile_certificate")
    7. Always prefer specific document names over generic categories
    8. If you're unsure between multiple types, choose the most likely one
    9. Provide alternative document types if confidence is below 0.8
    
    COUNTRY IDENTIFICATION:
    - MUST use ISO 3166-1 alpha-2 codes ONLY (e.g., "IN" for India, "US" for United States, "GB" for United Kingdom)
    - Country codes must be UPPERCASE and exactly 2 letters
    - Look for country-specific text, logos, government seals, language, and formatting
    - Common country indicators and their ISO codes:
      * India (IN): Hindi/English text, Government of India seals, specific formats for Aadhar/PAN
      * United States (US): English text, state seals, US government formatting
      * United Kingdom (GB): English text, UK government symbols, specific formatting
      * Canada (CA): English/French text, Canadian government symbols
      * Australia (AU): English text, Australian government formatting
      * Germany (DE): German text, EU symbols, German government formatting
      * France (FR): French text, EU symbols, French government formatting
    - If country cannot be determined with certainty, use "XX" (unknown country code)
    
    ACCURACY REQUIREMENTS:
    - Examine text, layout, logos, and official formatting
    - Consider language and regional specifics
    - Look for specific identifying elements (document numbers, government seals, etc.)
    - Be conservative with confidence scores - only use 0.9+ for very clear documents
    - READ the document title/header carefully and use that as the document type name
    """

    llm = await get_llm(
        model_name="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.0,
        structured_schema=DocumentTypeClassification
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": classification_prompt},
            *document_parts,
        ]
    )

    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke([message])

            if not response.document_type:
                continue

            existing_types = await get_existing_document_types(response.country)
            
            matched_type = find_best_matching_document_type(
                response.document_type, 
                existing_types,
                threshold=0.8
            )
            
            final_document_type = matched_type if matched_type else response.document_type
            
            final_response = DocumentTypeClassification(
                document_type=final_document_type,
                confidence=response.confidence,
                country=response.country,
                alternative_types=response.alternative_types
            )
            
            return final_response

        except Exception as e:
            if attempt < max_retries - 1:
                continue

    return None
