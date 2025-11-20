# API Endpoints Reference

## Classification API (Port 8000)

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/` | Health check | - | `{"message": "API running"}` |
| POST | `/classify` | Classify PDF document | `file: PDF` | Classification result with confidence |

## Extraction API (Port 8001)

### Core Processing
| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/` | Health check | - | `{"status": "healthy"}` |
| POST | `/extract` | Extract with specific schema | `file: PDF, schema_id: UUID` | Structured data extraction |
| POST | `/auto-extract` | Auto-classify and extract | `file: PDF` | Classification + extraction |

### Schema Management
| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/schemas` | List all schemas | `?document_type&country&status` | Schema list with filtering |
| GET | `/schemas/{id}` | Get specific schema | - | Single schema details |
| POST | `/create-schema` | Generate new schema | Document samples + metadata | Schema definition |
| POST | `/schemas/{id}/approve` | Approve schema | Approval metadata | Success confirmation |
| PUT | `/schemas/{id}` | Modify schema | Updated schema definition | Updated schema |
| DELETE | `/schemas/{id}` | Delete schema | - | Success confirmation |

### Schema Export
| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/download-schemas` | Download all schemas (JSON) | - | JSON array of schemas |
| GET | `/download-schema/{id}` | Download single schema | - | Single schema JSON |
| GET | `/download-schemas/zip` | Download all schemas (ZIP) | - | ZIP file with JSON files |

### Data Retrieval
| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/extractions` | Get extraction history | `?document_type&limit&offset` | List of extractions |
| GET | `/extractions/{id}` | Get specific extraction | - | Single extraction details |

## Quick curl Examples

```bash
# Health checks
curl http://localhost:8000/
curl http://localhost:8001/

# Document classification
curl -X POST "http://localhost:8000/classify" -F "file=@doc.pdf"

# Auto extraction
curl -X POST "http://localhost:8001/auto-extract" -F "file=@doc.pdf"

# Manual extraction with schema
curl -X POST "http://localhost:8001/extract" -F "file=@doc.pdf" -F "schema_id=uuid"

# Get schemas
curl "http://localhost:8001/schemas"
curl "http://localhost:8001/schemas?status=approved"

# Download schemas
curl "http://localhost:8001/download-schemas" > schemas.json
curl "http://localhost:8001/download-schemas/zip" -o schemas.zip

# Get extraction history
curl "http://localhost:8001/extractions?limit=10"
```

## Response Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid file type or parameters |
| 404 | Not Found | Schema or extraction not found |
| 422 | Validation Error | Invalid request format |
| 500 | Server Error | Processing or database error |

## Common Query Parameters

### `/schemas`
- `document_type`: Filter by document type (e.g., "us_passport")
- `country`: Filter by country code (e.g., "US")
- `status`: Filter by approval status ("approved", "pending", "rejected")

### `/extractions`
- `document_type`: Filter by document type
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)

## File Requirements

### Supported Formats
- **PDF only** (application/pdf)
- **Maximum size**: 50MB
- **Encoding**: Binary upload via multipart/form-data

### Recommended Quality
- **Resolution**: 300 DPI for scanned documents
- **Color**: Color or grayscale
- **Text**: Searchable PDFs preferred (OCR will be applied if needed)

## Authentication

### Environment Variables
- `GOOGLE_API_KEY`: Required for LLM operations
- Set in container environment or docker-compose

### No API Keys Required
- All endpoints are currently open
- Future versions may include API key authentication

## Performance Expectations

### Processing Times
- **Classification**: 2-5 seconds per document
- **Extraction**: 3-8 seconds per document
- **Schema operations**: < 1 second
- **File downloads**: < 1 second

### Concurrent Limits
- **Max concurrent requests**: 10 per service
- **Request timeout**: 300 seconds
- **Rate limiting**: None currently implemented

## Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "ERROR_TYPE",  
  "timestamp": "2025-11-19T10:30:00Z"
}
```

### Common Errors
- `INVALID_FILE_TYPE`: Non-PDF file uploaded
- `SCHEMA_NOT_FOUND`: Invalid schema ID
- `EXTRACTION_FAILED`: Document processing error
- `VALIDATION_ERROR`: Invalid request parameters