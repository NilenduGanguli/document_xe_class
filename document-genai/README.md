# Unified Document Services (SQLite Edition)

A combined document classification and extraction service with schema management capabilities, using embedded SQLite database and pre-loaded approved schemas.

## Features

### 📋 PDF Document Classification
- Page-by-page classification of multi-page PDFs
- Identifies document types (passport, driver's license, utility bill, etc.)
- Confidence scoring and reasoning for each classification
- Support for mixed document PDFs

### 📊 Document Data Extraction
- Automated schema generation from documents
- Schema-based structured data extraction
- Version-controlled schema management
- Support for multiple document types and countries

### 🗄️ Pre-loaded Approved Schemas
- SQLite database with pre-existing approved schemas
- Schemas loaded from JSON files on startup
- No external database dependency
- Ready-to-use document extraction

### 🔧 Schema Creation
- `/create-schema` endpoint to generate schema definitions from documents
- Export schema definitions compatible with initializer JSON format
- Easy way to create new schema definitions for database loading

### ⚙️ Schema Management
- View all schemas with filtering
- Approve schemas for activation
- Modify existing schemas with version control
- Delete deprecated schemas

## Architecture

The document-services-unified module combines classification and extraction services with an embedded SQLite database:

### Services

1. **Document Classification** (from doc-classify)
   - Classifies PDF documents page-by-page using Gemini AI
   - FastAPI backend on port 8000
   - Streamlit UI on port 8502
   - Original doc-classify functionality
   
2. **Document Extraction** (from document-extraction)
   - Extracts structured data using schema-based approach
   - FastAPI backend on port 8001
   - Streamlit UI on port 8501
   - Original document-extraction interface
   - **SQLite database** for schema storage (embedded, no external dependencies)

3. **Schema Creation Service**
   - `/create-schema` endpoint for generating schema definitions
   - Returns JSON format compatible with database initializer
   - Helps create new schemas for pre-loading

4. **Landing Page**
   - Simple HTML page on port 8080
   - Navigate to either Classification or Extraction UI

### Service Ports

| Port | Service | Description |
|------|---------|-------------|
| 8080 | Landing Page | HTML page to choose service |
| 8000 | Classification API | FastAPI backend for classification |
| 8001 | Extraction API | FastAPI backend for extraction |
| 8502 | Classification UI | Streamlit UI for PDF classification |
| 8501 | Extraction UI | Streamlit UI for document extraction |
| N/A | SQLite Database | Embedded database (no external port) |

### Access Points

**Start Here:**
- **Landing Page**: http://localhost:8080
  - Simple HTML page with links to both UIs
  - Choose between Classification or Extraction

**Classification Service:**
- **Classification UI**: http://localhost:8502
  - Upload PDFs for page-by-page classification
  - View confidence scores and reasoning
  - Original doc-classify Streamlit interface
- **Classification API Docs**: http://localhost:8000/docs
  - Swagger UI for API testing

**Extraction Service:**
- **Extraction UI**: http://localhost:8501
  - Upload documents for data extraction
  - Manage schemas (approve, modify, delete)
  - Original document-extraction Streamlit interface
- **Extraction API Docs**: http://localhost:8001/docs
  - Swagger UI for API testing

### Navigation

Both Streamlit UIs include:
- **🏠 Home** button (top right) → Returns to landing page
- **Cross-service navigation** → Links to the other service UI

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Google API Key (for Gemini LLM)

### 1. Setup Environment

Before running the service, you need to set your Google API key in the `env.sh` file:

```bash
# Edit env.sh and add your Google API key
nano env.sh

# Update this line:
export GOOGLE_API_KEY="your_actual_api_key_here"
```

### 2. Start Services

Using the management script (recommended):

```bash
# Build and start containers
./run.sh build
./run.sh up

# Check status
./run.sh status

# View logs
./run.sh logs
```

Or using docker-compose directly:

```bash
# Set your API key first
export GOOGLE_API_KEY="your_api_key_here"

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access Services

- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: SQLite (embedded, no external access needed)

### 4. Stop Services

Using the management script:

```bash
./run.sh down

# To remove volumes (database data):
docker-compose down -v
```

Or using docker-compose directly:

```bash
docker-compose down

# To remove volumes (database data):
docker-compose down -v
```

## Management Script

The `run.sh` script provides convenient commands for managing the service:

```bash
./run.sh build          # Build Docker images
./run.sh up             # Start all services
./run.sh down           # Stop and remove all services
./run.sh restart        # Restart all services
./run.sh logs           # Show all container logs
./run.sh backend-logs   # Show backend logs only
./run.sh frontend-logs  # Show frontend logs only
./run.sh status         # Show container status and test endpoints
```

## API Endpoints

### Classification
- `POST /classify-pdf` - Classify pages in a PDF document

### Extraction
- `POST /extract` - Extract structured data from documents

### Schema Creation
- `POST /create-schema` - Create schema definition from document (returns JSON format for initializer)

### Schema Management
- `GET /schemas` - Get all schemas
- `PUT /schemas/{schema_id}/approve` - Approve a schema
- `PUT /schemas/{schema_id}/modify` - Modify a schema
- `DELETE /schemas/{schema_id}` - Delete a schema

### Health
- `GET /` - Health check and service info

## Pre-loaded Schemas

The application comes with pre-approved schemas for common document types:

### Included Schemas
- **US Passport** (`schemas/us_passport.json`)
- **US Driver's License** (`schemas/us_drivers_license.json`)
- **US Utility Bill** (`schemas/us_utility_bill.json`)
- **Indian PAN Card** (`schemas/indian_pan_card.json`)

### Schema Loading Process
1. On startup, the application checks if the database is empty
2. If empty, it loads all JSON files from the `schemas/` directory
3. Each schema is marked as `ACTIVE` status (pre-approved)
4. Documents matching these types can be extracted immediately

### Adding New Schemas
1. Use the `/create-schema` endpoint to generate a schema definition from a sample document
2. Save the returned `schema_definition` as a JSON file in the `schemas/` directory
3. Restart the application to load the new schema

## Database Schema

### document_schemas Table (SQLite)

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| document_type | VARCHAR(100) | Document type (e.g., "us_passport") |
| country | VARCHAR(2) | ISO country code |
| document_schema | TEXT | Schema definition (JSON stored as TEXT) |
| status | TEXT | Status: active, in_review, deprecated |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| version | INTEGER | Schema version number |

**Key Features:**
- Uses SQLite embedded database (no external database required)
- TEXT-based JSON schema storage with automatic parsing
- Database file stored in container volume for persistence
- Automatic schema loading from JSON files on startup

## Development

### Local Development (without Docker)

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **No database setup required** - SQLite database is created automatically

3. **Run backend**:
```bash
cd backend
export DATABASE_PATH="/path/to/document_services.db"
export GOOGLE_API_KEY="your_key_here"
python main.py
```

4. **Run frontend** (in another terminal):
```bash
cd frontend
export API_BASE_URL="http://localhost:8000"
streamlit run app.py
```

### Project Structure

```
document-services-unified/
├── schemas/                    # Pre-existing approved schemas (JSON files)
│   ├── us_passport.json       
│   ├── us_drivers_license.json
│   ├── us_utility_bill.json
│   └── indian_pan_card.json
├── backend/
│   ├── main.py                 # Unified FastAPI application
│   └── src/
│       ├── db/                 # Database models and connection (SQLite)
│       ├── extractors/         # Document processing and extraction
│       ├── config/             # LLM and app configuration
│       ├── schemas/            # Pydantic models and classification
│       └── utils/              # Utility functions
├── frontend/
│   └── app.py                  # Unified Streamlit UI
├── docker-compose.yml          # Container orchestration (no external DB)
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies (with aiosqlite)
└── README.md                   # This file
```

## Environment Variables

### Required
- `GOOGLE_API_KEY` - Google Gemini API key

### Optional
- `DATABASE_PATH` - SQLite database file path (default: /app/data/document_services.db)
- `MIN_CLASSIFICATION_CONFIDENCE` - Minimum confidence for extraction (default: 0.7)
- `BACKEND_PORT` - Backend port (default: 8000)
- `FRONTEND_PORT` - Frontend port (default: 8501)

## Usage Examples

### 1. Create a New Schema Definition

```python
import requests

# Upload a sample document to create schema definition
with open("sample_document.pdf", "rb") as f:
    files = [("document", f)]
    response = requests.post("http://localhost:8000/create-schema", files=files)

if response.status_code == 200:
    result = response.json()
    schema_definition = result["schema_definition"]
    
    # Save to JSON file for database loading
    import json
    filename = result["usage_instructions"]["filename_suggestion"]
    with open(f"schemas/{filename}", "w") as f:
        json.dump(schema_definition, f, indent=2)
    
    print(f"Schema definition saved to schemas/{filename}")
    print("Restart the application to load this schema automatically")
```

### 2. Classify a PDF Document

```python
import requests

with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/classify-pdf", files=files)
    
result = response.json()
for page in result["page_classifications"]:
    print(f"Page {page['page']}: {page['document_type']} ({page['confidence']:.2%})")
```

### 3. Extract Data from Documents (using pre-loaded schemas)

```python
import requests

# This will work immediately for supported document types (US Passport, etc.)
with open("us_passport.jpg", "rb") as f:
    files = [("document", f)]
    response = requests.post("http://localhost:8000/extract", files=files)

if response.status_code == 200:
    result = response.json()
    print(f"Extracted data: {result['data']}")
    print(f"Schema used: {result['schema_used']['document_type']}")
    print(f"Schema status: {result['schema_used']['status']}")  # Will be 'active' for pre-loaded schemas
```

### 4. Extract with Approved Schema Only

```python
import requests

schema_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.put(f"http://localhost:8000/schemas/{schema_id}/approve")

if response.status_code == 200:
    print("Schema approved successfully")
```

## Workflow

1. **Document Upload**: Upload documents via the frontend or API
2. **Classification**: System classifies document type and country
3. **Schema Check**: 
   - If active schema exists → Extract data immediately
   - If no schema exists → Generate new schema (awaits approval)
   - If schema in review → Notify user
4. **Schema Approval**: Admin reviews and approves generated schemas
5. **Data Extraction**: Extract structured data using approved schema
6. **Results**: View and download extracted data

## Monitoring

### Check Service Health

```bash
curl http://localhost:8000/
```

### View Logs

```bash
# All services
docker-compose logs -f

# Application logs
docker-compose logs -f document-services-unified
```

### Database Access

```bash
# Connect to SQLite database
docker exec -it document-services-unified sqlite3 /app/data/document_services.db

# List schemas
SELECT id, document_type, country, status, version FROM document_schemas;

# Exit SQLite
.quit
```

## Troubleshooting

### Port Already in Use

```bash
# Change ports in docker-compose.yml
ports:
  - "8001:8000"  # Backend (change 8000 to 8001)
  - "8502:8501"  # Frontend (change 8501 to 8502)
```

### Database Issues

```bash
# Reset database (removes SQLite file)
docker-compose down -v
docker-compose up -d

# View database file
docker exec -it document-services-unified ls -la /app/data/
```

### API Key Issues

```bash
# Verify API key is set
docker-compose exec document-services env | grep GOOGLE_API_KEY

# Update API key
# Edit env.sh file and restart
docker-compose restart document-services
```

## Comparison with Separate Modules

### Before (Separate Modules)
- `doc-classify`: Classification service (port 8004)
- `document-extraction`: Extraction service (port 8005)
- Two separate containers, two separate UIs
- Different endpoints and configurations

### After (Unified Module)
- Single `document-services` module (ports 8000, 8501)
- One container with both services
- Unified frontend with tabbed interface
- Shared database and configuration
- Easier deployment and maintenance

## Migration from Other Modules

For migrating schemas from other document services:

1. Export existing schemas as JSON using the new download APIs:
```bash
# Get all schemas from this service (unified format)
curl http://localhost:8001/download-schemas > all_schemas.json

# Download all schemas as a zip file
curl http://localhost:8001/download-schemas/zip -o schemas.zip

# Individual schemas can be downloaded by ID:
curl http://localhost:8001/download-schema/{schema_id} > specific_schema.json
```

### Schema Export Options

| Endpoint | Response | Use Case |
|----------|----------|----------|
| `/download-schemas` | JSON array with all schemas | Programmatic access |
| `/download-schemas/zip` | ZIP file with individual JSON files | Easy file management |
| `/download-schema/{id}` | Single schema JSON | Specific schema export |

## Support

For issues or questions:
- **Check logs**: `docker-compose logs -f`
  - Container logs show uvicorn API logs with service identifiers ([CLASSIFICATION-API], [EXTRACTION-API])
  - Streamlit logs are suppressed for cleaner output
- **Review API docs**: http://localhost:8001/docs (Extraction) or http://localhost:8000/docs (Classification)
- **Database management**: SQLite embedded, no external dependencies
- **Schema export**: Multiple download endpoints available

## 📚 Documentation

### For Developers & Integration Teams
- **[🚀 API Documentation](API_DOCUMENTATION.md)** - Comprehensive API guide with examples
- **[⚡ Integration Guide](INTEGRATION_GUIDE.md)** - Quick start guide for teams
- **[📋 Endpoints Reference](API_ENDPOINTS_REFERENCE.md)** - Quick lookup for all endpoints

### Key Documentation Sections
- **Authentication & Setup** - Environment configuration
- **Endpoint References** - Complete API specification  
- **Code Examples** - Python, JavaScript, cURL samples
- **Error Handling** - Common issues and solutions
- **Performance Guidelines** - Best practices and optimization

## License

Internal use only - AI Project 25
