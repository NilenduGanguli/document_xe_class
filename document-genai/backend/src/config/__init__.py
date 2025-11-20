MIN_CLASSIFICATION_CONFIDENCE = 0.8
MAX_RETRY_ATTEMPTS = 3
EXTRACTION_RETRY_ATTEMPTS = 2
SCHEMA_GENERATION_RETRY_ATTEMPTS = 3

SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]
SUPPORTED_PDF_TYPES = ["application/pdf"]
SUPPORTED_DOCUMENT_TYPES = SUPPORTED_IMAGE_TYPES + SUPPORTED_PDF_TYPES

DOCUMENT_FORMAT_MAPPING = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "application/pdf": "pdf"
}
