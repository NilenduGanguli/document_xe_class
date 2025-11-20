"""
Document Classification API
Classifies PDF documents page-by-page using Gemini AI
"""
import os
import base64
import uvicorn
from google import genai
from google.genai import types
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import SecretStr
from src.schemas.classification import ClassificationResponse, create_classification_prompt


app = FastAPI(
    title="PDF Document Classifier",
    description="Classify PDF documents into different document types",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PDFDocumentClassifier:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key is None:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)

    async def encode_pdf_to_base64(self, pdf_data: bytes) -> str | None:
        try:
            pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")
            return pdf_base64
        except Exception as e:
            print(f"Error encoding PDF: {e}")
            return None

    async def classify_entire_pdf(self, pdf_data: bytes) -> ClassificationResponse:
        pdf_base64 = await self.encode_pdf_to_base64(pdf_data)

        if pdf_base64 is None:
            return ClassificationResponse(
                page_classifications=[]
            )

        system_prompt = create_classification_prompt()
        
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Part.from_bytes(
                        data=base64.b64decode(pdf_base64), 
                        mime_type="application/pdf"
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=ClassificationResponse
                )
            )
            return response.parsed
        except Exception as e:
            print(f"Error classifying PDF: {e}")
            # Return empty response or raise
            return ClassificationResponse(page_classifications=[])


# Initialize classifier
classifier = PDFDocumentClassifier()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PDF Document Classification API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/classify-pdf")
async def classify_pdf(file: UploadFile = File(...)) -> ClassificationResponse:
    """
    Classify a PDF document page by page
    
    Args:
        file: PDF file to classify
        
    Returns:
        ClassificationResponse with page-by-page classifications
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        pdf_data = await file.read()
        result = await classifier.classify_entire_pdf(pdf_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Configure logging with app identifier
    logging.basicConfig(
        level=logging.INFO,
        format='[CLASSIFICATION-API] %(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    port = int(os.getenv("PORT", 8000))
    print(f"[CLASSIFICATION-API] Starting Classification API on port {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    )
