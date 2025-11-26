# Document Services API Usage Guide

This guide provides detailed documentation for the Document Services APIs, including the Classification API and the Extraction API. These APIs allow you to classify documents, extract structured data, and manage document schemas.

## Base URLs

*   **Classification API**: `http://localhost:8000`
*   **Extraction API**: `http://localhost:8001`

---

## 1. Classification API

The Classification API is responsible for identifying the type of document (e.g., passport, driver's license) and the issuing country.

### Classify PDF Document

Classifies a PDF document page-by-page.

*   **Endpoint**: `POST /classify-pdf`
*   **URL**: `http://localhost:8000/classify-pdf`
*   **Content-Type**: `multipart/form-data`

#### Request Parameters

| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `file` | File (PDF) | The PDF document to classify. | Yes |

#### Example Request (cURL)

```bash
curl -X POST "http://localhost:8000/classify-pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf"
```

#### Example Response

```json
{
  "page_classifications": [
    {
      "page_number": 1,
      "document_type": "passport",
      "country": "US",
      "confidence": 0.98,
      "explanation": "The document contains a US passport header and layout."
    }
  ]
}
```

---

## 2. Extraction API

The Extraction API handles data extraction from documents based on schemas, as well as schema management (creation, approval, modification).

### Extract Data from Document

Extracts structured data from a document. If a schema exists, it uses it; otherwise, it attempts to generate a new schema.

*   **Endpoint**: `POST /extract`
*   **URL**: `http://localhost:8001/extract`
*   **Content-Type**: `multipart/form-data`

#### Request Parameters

| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `document` | File (PDF/Image) | The document file(s) to extract data from. Can upload multiple files. | Yes |

#### Example Request (cURL)

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "document=@/path/to/document.pdf;type=application/pdf"
```

#### Example Response (Extraction Successful)

```json
{
  "status": "extracted",
  "data": {
    "full_name": "John Doe",
    "document_number": "A1234567",
    "date_of_birth": "1980-01-01"
  },
  "classification": {
    "document_type": "passport",
    "country": "US",
    "confidence": 0.99
  },
  "schema_used": {
    "schema_id": "uuid-string",
    "version": 1,
    "status": "active"
  }
}
```

#### Example Response (Schema Generated / Pending Review)

```json
{
  "status": "schema_generated",
  "message": "Schema generated and saved for review Extraction not performed.",
  "classification": {
    "document_type": "new_doc_type",
    "country": "XX",
    "confidence": 0.95
  },
  "generated_schema": {
    "document_type": "new_doc_type",
    "country": "XX",
    "schema": { ... }
  },
  "schema_id": "new-schema-uuid"
}
```

### Extract with Approved Schema Only

Extracts data ONLY if an active (approved) schema exists. Fails otherwise.

*   **Endpoint**: `POST /extract-with-approved-schema`
*   **URL**: `http://localhost:8001/extract-with-approved-schema`

#### Request Parameters

Same as `/extract`.

### Register New Schema

Registers a new document schema without performing extraction.

*   **Endpoint**: `POST /register-schema`
*   **URL**: `http://localhost:8001/register-schema`

#### Request Parameters

Same as `/extract`.

### Create Schema Definition

Generates a schema definition JSON from a document, useful for initializing the database.

*   **Endpoint**: `POST /create-schema`
*   **URL**: `http://localhost:8001/create-schema`

#### Request Parameters

Same as `/extract`.

### Get All Schemas

Retrieves a list of all registered schemas.

*   **Endpoint**: `GET /schemas`
*   **URL**: `http://localhost:8001/schemas`

#### Example Response

```json
{
  "schemas": [
    {
      "id": "uuid-string",
      "document_type": "passport",
      "country": "US",
      "status": "active",
      "version": 1,
      "schema": { ... }
    }
  ],
  "total_count": 1
}
```

### Approve Schema

Approves a schema that is in `in_review` status.

*   **Endpoint**: `PUT /schemas/{schema_id}/approve`
*   **URL**: `http://localhost:8001/schemas/{schema_id}/approve`

#### Path Parameters

| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `schema_id` | String (UUID) | The ID of the schema to approve. | Yes |

### Modify Schema

Modifies an existing schema.

*   **Endpoint**: `PUT /schemas/{schema_id}/modify`
*   **URL**: `http://localhost:8001/schemas/{schema_id}/modify`
*   **Content-Type**: `application/json`

#### Request Body

```json
{
  "modifications": {
    "field_name_to_add": {
      "type": "string",
      "description": "Description of new field",
      "required": false
    },
    "field_name_to_remove": null,
    "field_name_to_update": {
      "description": "Updated description"
    }
  },
  "change_description": "Adding new field and removing obsolete one"
}
```

### Delete Schema

Deletes a schema by ID.

*   **Endpoint**: `DELETE /schemas/{schema_id}`
*   **URL**: `http://localhost:8001/schemas/{schema_id}`

### Download Schemas

Download schemas in JSON format.

*   **Get All**: `GET /download-schemas`
*   **Get Single**: `GET /download-schema/{schema_id}`
*   **Get Zip**: `GET /download-schemas/zip`

---

## 3. Data Models

### Schema Status

*   `active`: Schema is approved and used for extraction.
*   `in_review`: Schema is generated/modified and waiting for approval.
*   `deprecated`: Schema has been replaced by a newer version.

### Document Schema Structure

The `document_schema` field in responses follows this structure:

```json
{
  "field_name": {
    "type": "string | integer | date | boolean",
    "description": "Field description",
    "required": true | false,
    "example": "Example value",
    "pattern": "Regex pattern (optional)"
  }
}
```
