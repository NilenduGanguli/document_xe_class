# Document Services Unified - API Documentation

## Overview

The Document Services Unified platform provides two main API services for document processing:
- **Classification API** (Port 8000): Document type classification using AI
- **Extraction API** (Port 8001): Schema-based data extraction from documents

Both APIs are containerized and run on separate ports with comprehensive logging and error handling.

---

## 🚀 Quick Start

### Base URLs
- **Classification API**: `http://your-server:8000`
- **Extraction API**: `http://your-server:8001`

### Interactive Documentation
- **Classification API Docs**: `http://your-server:8000/docs`
- **Extraction API Docs**: `http://your-server:8001/docs`

### Health Checks
```bash
# Check Classification API
curl http://your-server:8000/

# Check Extraction API  
curl http://your-server:8001/
```

---

## 📋 Classification API (Port 8000)

### Overview
Classifies PDF documents page-by-page using Gemini AI to identify document types with confidence scores.

### Authentication
- Requires Google API key for Gemini LLM
- Set via environment variable: `GOOGLE_API_KEY`

### Endpoints

#### 1. Health Check
```http
GET /
```

**Response:**
```json
{
  "message": "Document Classification API is running"
}
```

#### 2. Classify Document
```http
POST /classify
```

**Description:** Classifies a PDF document and returns page-by-page analysis.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:** `file` (PDF file)

**Example:**
```bash
curl -X POST \
  "http://your-server:8000/classify" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "filename": "document.pdf",
  "total_pages": 2,
  "overall_classification": "us_passport",
  "confidence": 0.95,
  "reasoning": "Document contains passport-specific fields and layout",
  "pages": [
    {
      "page_number": 1,
      "classification": "us_passport",
      "confidence": 0.98,
      "reasoning": "Contains passport photo, personal details, and passport number"
    },
    {
      "page_number": 2,
      "classification": "us_passport",
      "confidence": 0.92,
      "reasoning": "Contains visa pages and travel stamps"
    }
  ]
}
```

**Error Responses:**
```json
// Invalid file type
{
  "detail": "Only PDF files are supported"
}

// Processing error
{
  "detail": "Classification failed: [error message]"
}
```

---

## 🔍 Extraction API (Port 8001)

### Overview
Extracts structured data from documents using predefined or custom schemas. Supports schema management, document processing, and data export.

### Authentication
- Requires Google API key for LLM operations
- Set via environment variable: `GOOGLE_API_KEY`

### Database
- **Type:** SQLite (embedded)
- **Location:** `/app/data/document_services.db`
- **Pre-loaded schemas:** 4 approved schemas (US Passport, Driver's License, etc.)

---

## 📄 Document Processing Endpoints

### 1. Health Check
```http
GET /
```

**Response:**
```json
{
  "status": "healthy"
}
```

### 2. Extract Data from Document
```http
POST /extract
```

**Description:** Extracts structured data using a specific schema.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:** 
  - `file` (PDF file)
  - `schema_id` (UUID string)

**Example:**
```bash
curl -X POST \
  "http://your-server:8001/extract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@passport.pdf" \
  -F "schema_id=550e8400-e29b-41d4-a716-446655440001"
```

**Response:**
```json
{
  "extraction_id": "550e8400-e29b-41d4-a716-446655440002",
  "filename": "passport.pdf",
  "schema_id": "550e8400-e29b-41d4-a716-446655440001",
  "document_type": "us_passport",
  "extracted_data": {
    "full_name": "John Michael Smith",
    "passport_number": "123456789",
    "date_of_birth": "1985-03-15",
    "place_of_birth": "New York, USA",
    "issue_date": "2020-01-10",
    "expiration_date": "2030-01-10"
  },
  "confidence_score": 0.92,
  "processing_time": 3.45,
  "created_at": "2025-11-19T10:30:00Z"
}
```

### 3. Auto-Extract with Classification
```http
POST /auto-extract
```

**Description:** Automatically classifies document and extracts data using the best matching schema.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:** `file` (PDF file)

**Example:**
```bash
curl -X POST \
  "http://your-server:8001/auto-extract" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "extraction_id": "550e8400-e29b-41d4-a716-446655440003",
  "filename": "document.pdf",
  "classification_result": {
    "document_type": "us_drivers_license",
    "confidence": 0.89
  },
  "schema_used": {
    "schema_id": "550e8400-e29b-41d4-a716-446655440004",
    "document_type": "us_drivers_license",
    "version": 1
  },
  "extracted_data": {
    "full_name": "Jane Doe",
    "license_number": "D123456789",
    "date_of_birth": "1990-05-20",
    "address": "123 Main St, Anytown, ST 12345"
  },
  "confidence_score": 0.87,
  "processing_time": 4.12,
  "created_at": "2025-11-19T10:35:00Z"
}
```

---

## 📋 Schema Management Endpoints

### 1. Get All Schemas
```http
GET /schemas
```

**Query Parameters:**
- `document_type` (optional): Filter by document type
- `country` (optional): Filter by country
- `status` (optional): Filter by approval status

**Example:**
```bash
curl "http://your-server:8001/schemas?document_type=us_passport&status=approved"
```

**Response:**
```json
{
  "schemas": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "document_type": "us_passport",
      "country": "US",
      "version": 1,
      "status": "approved",
      "document_schema": {
        "full_name": {
          "type": "string",
          "description": "Full name as appears on passport",
          "required": true,
          "example": "John Michael Smith"
        },
        "passport_number": {
          "type": "string",
          "description": "9-digit passport number",
          "required": true,
          "example": "123456789"
        }
      },
      "created_at": "2025-11-19T10:00:00Z",
      "updated_at": "2025-11-19T10:00:00Z"
    }
  ],
  "total_count": 1,
  "filtered_count": 1
}
```

### 2. Get Schema by ID
```http
GET /schemas/{schema_id}
```

**Example:**
```bash
curl "http://your-server:8001/schemas/550e8400-e29b-41d4-a716-446655440001"
```

### 3. Create New Schema
```http
POST /create-schema
```

**Description:** Generates a schema definition from sample documents.

**Request:**
```json
{
  "documents": [
    {
      "document_type": "custom_document",
      "file_content": "base64_encoded_pdf_content",
      "filename": "sample1.pdf"
    }
  ],
  "country": "US",
  "description": "Custom document type schema"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Schema generated successfully",
  "schema_definition": {
    "document_type": "custom_document",
    "country": "US", 
    "version": 1,
    "document_schema": {
      "field1": {
        "type": "string",
        "description": "Generated field description",
        "required": true,
        "example": "Sample value"
      }
    }
  },
  "usage_instructions": {
    "description": "Save this schema_definition as a JSON file in schemas/ directory",
    "filename_suggestion": "custom_document.json",
    "reload_instructions": "Restart application to load the new schema"
  }
}
```

---

## 📥 Schema Export Endpoints

### 1. Download All Schemas (JSON)
```http
GET /download-schemas
```

**Description:** Returns all schemas in JSON format for programmatic access.

**Example:**
```bash
curl "http://your-server:8001/download-schemas" > all_schemas.json
```

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 4 schema definitions",
  "schema_definitions": [
    {
      "document_type": "us_passport",
      "country": "US",
      "version": 1,
      "document_schema": { ... }
    }
  ],
  "usage_instructions": {
    "description": "Save each schema definition as a separate JSON file",
    "filename_format": "{document_type}.json",
    "example_save": "Save each object as schemas/{document_type}.json"
  }
}
```

### 2. Download Single Schema
```http
GET /download-schema/{schema_id}
```

**Example:**
```bash
curl "http://your-server:8001/download-schema/550e8400-e29b-41d4-a716-446655440001" > schema.json
```

### 3. Download Schemas as ZIP
```http
GET /download-schemas/zip
```

**Description:** Downloads all schemas as a ZIP file containing individual JSON files.

**Example:**
```bash
curl "http://your-server:8001/download-schemas/zip" -o schemas.zip
```

**ZIP Contents:**
```
schemas.zip
├── us_passport_us.json
├── us_drivers_license_us.json  
├── indian_pan_card_in.json
└── us_utility_bill_us.json
```

---

## 🔍 Data Retrieval Endpoints

### 1. Get Extraction History
```http
GET /extractions
```

**Query Parameters:**
- `document_type` (optional): Filter by document type
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```bash
curl "http://your-server:8001/extractions?document_type=us_passport&limit=10"
```

**Response:**
```json
{
  "extractions": [
    {
      "extraction_id": "550e8400-e29b-41d4-a716-446655440002",
      "filename": "passport.pdf",
      "document_type": "us_passport",
      "confidence_score": 0.92,
      "created_at": "2025-11-19T10:30:00Z",
      "extracted_data": { ... }
    }
  ],
  "total_count": 25,
  "returned_count": 10
}
```

### 2. Get Specific Extraction
```http
GET /extractions/{extraction_id}
```

**Example:**
```bash
curl "http://your-server:8001/extractions/550e8400-e29b-41d4-a716-446655440002"
```

---

## 📊 Schema Administration Endpoints

### 1. Approve Schema
```http
POST /schemas/{schema_id}/approve
```

**Request:**
```json
{
  "approved_by": "admin_user_id",
  "notes": "Schema reviewed and approved for production use"
}
```

### 2. Modify Schema
```http
PUT /schemas/{schema_id}
```

**Request:**
```json
{
  "document_schema": {
    "updated_field": {
      "type": "string",
      "description": "Updated field description",
      "required": true
    }
  },
  "version_notes": "Added new required field"
}
```

### 3. Delete Schema
```http
DELETE /schemas/{schema_id}
```

**Response:**
```json
{
  "status": "success",
  "message": "Schema deleted successfully"
}
```

---

## 🚨 Error Handling

### Standard Error Response Format
```json
{
  "detail": "Error description",
  "error_code": "ERROR_TYPE",
  "timestamp": "2025-11-19T10:30:00Z"
}
```

### Common HTTP Status Codes

| Status | Description | Common Causes |
|--------|-------------|---------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid file type, missing parameters |
| 404 | Not Found | Schema or extraction not found |
| 422 | Validation Error | Invalid request format |
| 500 | Server Error | Processing failure, database error |

### Error Examples

```bash
# File type error
{
  "detail": "Only PDF files are supported",
  "error_code": "INVALID_FILE_TYPE"
}

# Schema not found
{
  "detail": "Schema not found",
  "error_code": "SCHEMA_NOT_FOUND"
}

# Processing error
{
  "detail": "Failed to extract data: Document format not supported",
  "error_code": "EXTRACTION_FAILED"
}
```

---

## 🔧 Integration Examples

### Python Client Example
```python
import requests
import json

# Classification
def classify_document(file_path, api_base="http://localhost:8000"):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{api_base}/classify",
            files={"file": f}
        )
    return response.json()

# Extraction with specific schema
def extract_with_schema(file_path, schema_id, api_base="http://localhost:8001"):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{api_base}/extract",
            files={"file": f},
            data={"schema_id": schema_id}
        )
    return response.json()

# Auto-extraction
def auto_extract(file_path, api_base="http://localhost:8001"):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{api_base}/auto-extract",
            files={"file": f}
        )
    return response.json()

# Get all schemas
def get_schemas(api_base="http://localhost:8001"):
    response = requests.get(f"{api_base}/schemas")
    return response.json()

# Example usage
result = classify_document("document.pdf")
print(f"Document type: {result['overall_classification']}")

extraction = auto_extract("document.pdf")
print(f"Extracted data: {extraction['extracted_data']}")
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Classification
async function classifyDocument(filePath, apiBase = 'http://localhost:8000') {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    
    const response = await axios.post(`${apiBase}/classify`, form, {
        headers: form.getHeaders()
    });
    return response.data;
}

// Auto-extraction
async function autoExtract(filePath, apiBase = 'http://localhost:8001') {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    
    const response = await axios.post(`${apiBase}/auto-extract`, form, {
        headers: form.getHeaders()
    });
    return response.data;
}

// Get schemas
async function getSchemas(apiBase = 'http://localhost:8001') {
    const response = await axios.get(`${apiBase}/schemas`);
    return response.data;
}

// Example usage
(async () => {
    try {
        const classification = await classifyDocument('document.pdf');
        console.log('Classification:', classification);
        
        const extraction = await autoExtract('document.pdf');
        console.log('Extraction:', extraction);
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
})();
```

### cURL Examples
```bash
# Classify document
curl -X POST \
  "http://localhost:8000/classify" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# Extract with specific schema
curl -X POST \
  "http://localhost:8001/extract" \
  -F "file=@document.pdf" \
  -F "schema_id=550e8400-e29b-41d4-a716-446655440001"

# Auto-extract
curl -X POST \
  "http://localhost:8001/auto-extract" \
  -F "file=@document.pdf"

# Get all schemas
curl "http://localhost:8001/schemas"

# Download schemas as ZIP
curl "http://localhost:8001/download-schemas/zip" -o schemas.zip
```

---

## 🏗️ Deployment Configuration

### Environment Variables
```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
DATABASE_PATH=/app/data/document_services.db
LOG_LEVEL=info
```

### Docker Deployment
```yaml
version: '3.8'
services:
  document-services:
    image: document-services-unified
    ports:
      - "8000:8000"  # Classification API
      - "8001:8001"  # Extraction API
      - "8080:8080"  # Landing page
      - "8501:8501"  # Extraction UI
      - "8502:8502"  # Classification UI
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - document_data:/app/data
volumes:
  document_data:
```

### Health Monitoring
```bash
# Check service health
curl http://localhost:8000/ && echo "Classification API: OK"
curl http://localhost:8001/ && echo "Extraction API: OK"

# Monitor logs
docker logs document-services-unified --tail=100 -f
```

---

## 📝 Rate Limits & Performance

### Processing Limits
- **File size**: Maximum 50MB per file
- **File type**: PDF only
- **Concurrent requests**: 10 per service
- **Timeout**: 300 seconds per request

### Performance Metrics
- **Classification**: ~2-5 seconds per document
- **Extraction**: ~3-8 seconds per document  
- **Schema operations**: ~100ms per request
- **Database queries**: ~50ms per query

### Best Practices
1. **Batch processing**: Send multiple files in separate requests
2. **Error handling**: Implement retry logic with exponential backoff
3. **Caching**: Cache schema data to reduce API calls
4. **Monitoring**: Track response times and error rates

---

## 🤝 Support & Contact

### Issue Reporting
- **API Issues**: Include request/response examples
- **Integration Questions**: Provide code samples
- **Performance**: Include timing measurements

### Development Environment
- **Base URLs**: Use `http://localhost` for local development
- **API Documentation**: Available at `/docs` endpoints
- **Container logs**: `docker logs document-services-unified`

---

## 📋 Changelog

### Version 1.0.0 (Current)
- Initial release with classification and extraction APIs
- SQLite database integration
- Pre-loaded schema support
- ZIP export functionality
- Comprehensive logging

### Future Enhancements
- Batch processing endpoints
- Webhook notifications
- API key authentication
- Custom field validation
- Performance analytics

---

*This documentation covers Document Services Unified v1.0.0*  
*For the latest updates, check the interactive API documentation at `/docs` endpoints*