# Document Services - Quick Integration Guide

## 🚀 Quick Start

### Service URLs
```
Classification API: http://your-server:8000
Extraction API:     http://your-server:8001
API Documentation:  http://your-server:8001/docs
```

### Prerequisites
- Google API key (set as `GOOGLE_API_KEY` environment variable)
- PDF files for processing
- HTTP client (curl, Python requests, etc.)

---

## 📋 Common Use Cases

### 1. Document Classification
**Identify document type with confidence scores**

```bash
curl -X POST "http://your-server:8000/classify" \
  -F "file=@document.pdf"
```

```python
# Python
response = requests.post(
    "http://your-server:8000/classify",
    files={"file": open("document.pdf", "rb")}
)
result = response.json()
print(f"Document type: {result['overall_classification']}")
```

### 2. Auto Data Extraction
**Automatically classify and extract data**

```bash
curl -X POST "http://your-server:8001/auto-extract" \
  -F "file=@document.pdf"
```

```python
# Python
response = requests.post(
    "http://your-server:8001/auto-extract", 
    files={"file": open("document.pdf", "rb")}
)
data = response.json()
print(f"Extracted: {data['extracted_data']}")
```

### 3. Schema-Based Extraction
**Extract using specific schema**

```bash
# Get available schemas first
curl "http://your-server:8001/schemas"

# Extract with specific schema
curl -X POST "http://your-server:8001/extract" \
  -F "file=@document.pdf" \
  -F "schema_id=YOUR_SCHEMA_ID"
```

### 4. Schema Management
**Download and manage schemas**

```bash
# Download all schemas as JSON
curl "http://your-server:8001/download-schemas" > schemas.json

# Download as ZIP file
curl "http://your-server:8001/download-schemas/zip" -o schemas.zip

# Get specific schema
curl "http://your-server:8001/schemas/SCHEMA_ID"
```

---

## 📊 Response Formats

### Classification Response
```json
{
  "filename": "document.pdf",
  "overall_classification": "us_passport",
  "confidence": 0.95,
  "pages": [
    {
      "page_number": 1,
      "classification": "us_passport", 
      "confidence": 0.98
    }
  ]
}
```

### Extraction Response
```json
{
  "extraction_id": "uuid-here",
  "document_type": "us_passport",
  "extracted_data": {
    "full_name": "John Smith",
    "passport_number": "123456789",
    "date_of_birth": "1985-03-15"
  },
  "confidence_score": 0.92
}
```

### Schema List Response
```json
{
  "schemas": [
    {
      "id": "uuid-here",
      "document_type": "us_passport",
      "country": "US",
      "status": "approved",
      "document_schema": { ... }
    }
  ]
}
```

---

## 🔧 Integration Patterns

### Error Handling
```python
def safe_api_call(url, files=None, data=None):
    try:
        response = requests.post(url, files=files, data=data, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}
```

### Batch Processing
```python
def process_documents(file_paths):
    results = []
    for file_path in file_paths:
        with open(file_path, 'rb') as f:
            result = requests.post(
                "http://your-server:8001/auto-extract",
                files={"file": f}
            ).json()
        results.append(result)
    return results
```

### Schema Caching
```python
import time

class SchemaCache:
    def __init__(self):
        self.cache = {}
        self.cache_time = None
        self.ttl = 3600  # 1 hour
    
    def get_schemas(self):
        now = time.time()
        if not self.cache_time or (now - self.cache_time) > self.ttl:
            response = requests.get("http://your-server:8001/schemas")
            self.cache = response.json()
            self.cache_time = now
        return self.cache
```

---

## ⚡ Performance Tips

### File Size Optimization
- **Compress PDFs** before sending (max 50MB)
- **Use appropriate quality** for scanned documents (300 DPI recommended)

### Request Optimization
- **Reuse HTTP connections** with session objects
- **Implement retry logic** with exponential backoff
- **Cache schema data** to reduce API calls

### Monitoring
```python
import time
import logging

def timed_request(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logging.info(f"API call took {duration:.2f} seconds")
        return result
    return wrapper

@timed_request
def extract_document(file_path):
    # Your extraction code here
    pass
```

---

## 🚨 Common Issues & Solutions

### Issue: "Only PDF files are supported"
**Solution:** Ensure file has `.pdf` extension and is a valid PDF

### Issue: Timeout errors
**Solution:** Increase timeout to 300 seconds for large files

### Issue: Low confidence scores
**Solution:** 
- Check document quality (scan resolution, clarity)
- Verify document type matches available schemas
- Consider document preprocessing

### Issue: Schema not found
**Solution:** 
- List available schemas: `GET /schemas`
- Verify schema ID format (UUID)
- Check schema status (must be "approved")

---

## 📝 Environment Setup

### Local Development
```bash
# Set environment variables
export GOOGLE_API_KEY="your-api-key"

# Start services
docker-compose up -d

# Verify services
curl http://localhost:8000/  # Classification
curl http://localhost:8001/  # Extraction
```

### Production Configuration
```python
# Production settings
API_BASE_CLASSIFICATION = "https://your-domain:8000"
API_BASE_EXTRACTION = "https://your-domain:8001"
REQUEST_TIMEOUT = 300
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3
```

---

## 📋 Pre-loaded Document Types

| Document Type | Country | Schema ID Available |
|---------------|---------|---------------------|
| US Passport | US | ✅ |
| US Driver's License | US | ✅ |
| Indian PAN Card | IN | ✅ |
| US Utility Bill | US | ✅ |

### Custom Schemas
Use `/create-schema` endpoint to generate schemas for new document types.

---

## 🔗 Quick Links

- **Full API Documentation**: `API_DOCUMENTATION.md`
- **Classification API Docs**: `http://your-server:8000/docs`
- **Extraction API Docs**: `http://your-server:8001/docs`
- **Health Monitoring**: `http://your-server:8000/` and `http://your-server:8001/`

---

*For detailed examples and advanced usage, see the complete API documentation.*