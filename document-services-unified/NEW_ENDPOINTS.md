# New Extraction Endpoints

Two new endpoints have been added to the Document Extraction API (`/backend/extraction_main.py`) without removing any existing functionality.

## 1. POST /register-schema

**Purpose:** Register a new document schema without performing extraction.

**Behavior:**
- Accepts document files for classification and schema generation
- **Returns error (409 Conflict)** if schema already exists with status `IN_REVIEW` or `ACTIVE` (approved)
- Only registers schema if no existing schema found for the document type and country
- Schema is created with status `IN_REVIEW` awaiting approval

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: One or more document files

**Success Response (201):**
```json
{
  "status": "schema_registered",
  "message": "Schema successfully registered and saved for review",
  "classification": {
    "document_type": "passport",
    "country": "US",
    "confidence": 0.95
  },
  "generated_schema": {
    "schema_id": "uuid-here",
    "document_type": "passport",
    "country": "US",
    "confidence": 0.92,
    "schema": { ... },
    "status": "in_review",
    "created_at": "2025-11-17T12:00:00Z"
  }
}
```

**Error Response (409) - Schema Already Exists:**
```json
{
  "detail": {
    "error": "Schema already exists",
    "message": "An approved schema already exists for passport from US",
    "existing_schema": {
      "schema_id": "uuid-here",
      "document_type": "passport",
      "country": "US",
      "version": 1,
      "status": "active",
      "created_at": "2025-11-17T10:00:00Z",
      "updated_at": "2025-11-17T10:30:00Z"
    }
  }
}
```

**Error Response (409) - Schema Already in Review:**
```json
{
  "detail": {
    "error": "Schema already in review",
    "message": "A schema for passport from US is already awaiting approval",
    "existing_schema": {
      "schema_id": "uuid-here",
      "document_type": "passport",
      "country": "US",
      "version": 0,
      "status": "in_review",
      "created_at": "2025-11-17T11:00:00Z",
      "updated_at": "2025-11-17T11:00:00Z"
    }
  }
}
```

## 2. POST /extract-with-approved-schema

**Purpose:** Extract data from documents using ONLY approved (ACTIVE) schemas.

**Behavior:**
- **Returns error (404)** if no schema exists for the document type
- **Returns error (403)** if schema exists but is still `IN_REVIEW` (not approved)
- Only processes extraction if schema status is `ACTIVE` (approved)
- Performs full document extraction and returns structured data

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: One or more document files

**Success Response (200):**
```json
{
  "status": "extracted",
  "data": {
    "full_name": "John Doe",
    "passport_number": "123456789",
    ...
  },
  "classification": {
    "document_type": "passport",
    "country": "US",
    "confidence": 0.95
  },
  "schema_used": {
    "schema_id": "uuid-here",
    "document_type": "passport",
    "country": "US",
    "version": 1,
    "status": "active",
    "created_at": "2025-11-17T10:00:00Z",
    "updated_at": "2025-11-17T10:30:00Z",
    "schema": { ... }
  }
}
```

**Error Response (404) - Schema Not Found:**
```json
{
  "detail": {
    "error": "Schema not found",
    "message": "No approved schema exists for passport from US",
    "classification": {
      "document_type": "passport",
      "country": "US",
      "confidence": 0.95
    }
  }
}
```

**Error Response (403) - Schema Not Approved:**
```json
{
  "detail": {
    "error": "Schema not approved",
    "message": "Schema for passport from US is still in review and not approved for extraction",
    "schema_info": {
      "schema_id": "uuid-here",
      "document_type": "passport",
      "country": "US",
      "status": "in_review",
      "version": 0,
      "created_at": "2025-11-17T11:00:00Z"
    }
  }
}
```

## Existing Endpoints (Unchanged)

All existing endpoints remain fully functional:

1. **POST /extract** - Original extract endpoint (auto-generates schema if needed)
2. **GET /schemas** - List all schemas
3. **PUT /schemas/{schema_id}/approve** - Approve a schema
4. **PUT /schemas/{schema_id}/modify** - Modify a schema
5. **DELETE /schemas/{schema_id}** - Delete a schema
6. **GET /** - Health check

## Schema Status Flow

```
NEW SCHEMA REGISTRATION:
register-schema → IN_REVIEW → (manual approve) → ACTIVE

EXTRACTION:
extract-with-approved-schema → Only works with ACTIVE schemas
                              → Returns error for IN_REVIEW or missing schemas
```

## Testing

You can test these endpoints using:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- cURL or any HTTP client

Example cURL commands:

```bash
# Register a new schema
curl -X POST "http://localhost:8001/register-schema" \
  -F "document=@/path/to/document.pdf"

# Extract with approved schema only
curl -X POST "http://localhost:8001/extract-with-approved-schema" \
  -F "document=@/path/to/document.pdf"
```
