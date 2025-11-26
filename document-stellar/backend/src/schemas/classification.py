"""
Classification schemas and configuration for document classification
"""
from pydantic import BaseModel, Field
from typing import List


class PageClassification(BaseModel):
    """Classification result for a single page"""
    page: int = Field(description="Page number")
    document_type: str = Field(
        description="Type of document identified on this page")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")


class ClassificationResponse(BaseModel):
    """Complete classification response for all pages in a document"""
    page_classifications: List[PageClassification] = Field(
        description="Brief page-by-page classifications with reasoning and confidence")


def create_classification_prompt() -> str:
    """
    Create the prompt for document classification
    
    Returns:
        str: The classification prompt with instructions
    """
    return """
    Analyze this entire PDF document and classify each page into different document types. 
    The PDF may contain multiple different documents which may or may not be mixed together.
    
    Common document types include:
    - Aadhaar Card
    - PAN Card  
    - Passport
    - Driver's License
    - Voter ID
    - Bank Statement
    - Salary Slip
    - Insurance Document
    - Educational Certificate
    - Other Government ID
    - Invoice/Receipt
    - Agreement/Contract
    - Medical Report
    - Utility Bill
    - Unknown/Unclear
    - Any other valid document type

    Do not restrict yourself to the above list. You can assign a new document type **only if** it is not a variation of an existing type and clearly represents a distinct, valid document.

    If a document could fall under a common type like "Educational Certificate", "Government ID", or "Utility Bill", **use that existing category** instead of introducing a new one.

    If you are not sure about the document type, classify it as **"Unknown/Unclear"**.

    IMPORTANT CONSOLIDATION RULES:
    - Group ALL related pages (front/back, instructions, info) under a single document type
    - Use the main category followed by Country (e.g., "Indian Driver's License", not "Indian DL" or "Western Australia DL")
    - Do NOT create subcategories or repeated similar entries under "Other"
    - If a page belongs to multiple types, choose the **most specific and relevant** category

    IMPORTANT INSTRUCTIONS:
    1. Analyze each page of the PDF carefully
    2. Identify the document type for each page
    3. Group consecutive pages that belong to the same document
    4. Handle interruptions—documents might be broken by pages of other documents
    5. Provide page-by-page classification with:
       - page number
       - document type
       - confidence score (0 to 1)
       - reasoning for classification

    Key Analysis Guidelines:
    - Look for document titles, logos, government stamps, watermarks
    - Consider layout, structure, and common field names
    - Use page order/context (e.g., front/back, sequence) to group pages
    - If a page is corrupted or unreadable, classify it as "Unknown/Unclear"

    Your response should include:
    1. page_classifications: List of detailed classifications for each page with page number, document type, confidence score, and reasoning
    """
