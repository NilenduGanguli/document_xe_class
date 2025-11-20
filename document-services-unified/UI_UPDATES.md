# Extraction UI Updates

## Summary of Changes

The extraction frontend has been updated to align with the new backend endpoints and provide better visibility of schema IDs throughout the application.

## New Features

### 1. New Page: "Register Schema" (📝)

**Location:** First item in navigation menu

**Purpose:** Dedicated interface for registering new document schemas using the `/register-schema` endpoint.

**Features:**
- Upload sample documents to generate a new schema
- Automatic document classification
- Schema generation with IN_REVIEW status
- **Prominent display of Schema ID** in a highlighted box after successful registration
- Error handling for duplicate schemas:
  - Shows error if schema already exists (ACTIVE status)
  - Shows error if schema is already IN_REVIEW
  - Displays existing schema information including Schema ID
- Visual feedback with success/error messages
- Detailed schema field display with types, descriptions, and examples

**User Flow:**
1. Navigate to "Register Schema"
2. Upload sample document(s)
3. Click "Register Schema"
4. System generates and saves schema with IN_REVIEW status
5. Schema ID is displayed prominently for reference
6. User can then approve schema in "View All Schemas" page

### 2. Updated Page: "Extract & View" (🔍)

**Changes:**
- Now uses the `/extract-with-approved-schema` endpoint
- **Only works with APPROVED (ACTIVE) schemas**
- Enhanced error handling:
  - 404 Error: No approved schema found
  - 403 Error: Schema exists but is still IN_REVIEW
  - Displays Schema ID prominently in error messages
- Success response shows Schema ID used for extraction in a highlighted box
- Better visual feedback for different scenarios

**User Flow:**
1. Navigate to "Extract & View"
2. Upload document(s)
3. Click "Extract Data"
4. If approved schema exists: Data is extracted and Schema ID is shown
5. If no schema: Error message with suggestion to register schema
6. If schema not approved: Error message with Schema ID and link to approve

### 3. Schema ID Display Enhancement

Schema IDs are now **prominently displayed** in the following locations:

#### Register Schema Page
- **After successful registration:** Large, highlighted box with Schema ID
- **In error responses:** Schema ID of existing/conflicting schema

#### Extract & View Page
- **Success:** Schema ID used for extraction (highlighted in green box)
- **Error (403):** Schema ID of the unapproved schema (highlighted box)

#### View All Schemas Page
- Schema ID displayed in schema details: `st.write(f"**Schema ID:** `{schema['id']}`")`
- Visible in every schema's expanded view

#### Modify Schemas Page
- Schema ID shown in current schema information section

## Technical Implementation

### New API Functions

```python
def register_document_schema(files: List) -> Optional[Dict]:
    """Register a new document schema using the /register-schema endpoint"""
    # Calls POST /register-schema
    # Returns success or detailed error information

def extract_with_approved_schema(files: List) -> Optional[Dict]:
    """Extract data using only approved schemas"""
    # Calls POST /extract-with-approved-schema
    # Returns extracted data or detailed error information
```

### Enhanced Error Handling

Both new functions return structured error information:

```python
{
    "error": True,
    "status_code": 409,  # or 403, 404, etc.
    "detail": {
        "error": "Schema already exists",
        "message": "Detailed message",
        "existing_schema": {
            "schema_id": "uuid-here",
            ...
        }
    }
}
```

### Visual Design for Schema IDs

Schema IDs are displayed in styled boxes:

```html
<div class="info-box">
    <h4>📌 Schema ID</h4>
    <code style="font-size: 1.2em; background: white; color: #667eea; padding: 10px; border-radius: 5px; display: block;">
        uuid-value-here
    </code>
</div>
```

## Navigation Flow

Updated navigation order:
1. **📝 Register Schema** (NEW) - First step in workflow
2. **📤 Upload Documents** - Original endpoint (auto-generates if needed)
3. **📚 View All Schemas** - View and approve schemas
4. **✏️ Modify Schemas** - Edit existing schemas
5. **🔍 Extract & View** (UPDATED) - Extract with approved schemas only

## User Workflow

### Recommended Flow for New Document Types:

1. **Register Schema:**
   - Go to "Register Schema"
   - Upload sample documents
   - System generates schema with IN_REVIEW status
   - **Copy the Schema ID** for reference

2. **Approve Schema:**
   - Go to "View All Schemas"
   - Find the schema (use Schema ID if needed)
   - Click "Approve" button
   - Schema becomes ACTIVE

3. **Extract Data:**
   - Go to "Extract & View"
   - Upload documents of the same type
   - System extracts data using approved schema
   - **Schema ID is shown** in extraction results

### Alternative Flow (Original Behavior):

1. **Upload Documents:**
   - Go to "Upload Documents"
   - Upload documents
   - If no schema exists, system auto-generates one
   - Schema requires approval before extraction

## Backend Endpoints Used

The UI now integrates with all extraction endpoints:

- `POST /register-schema` - Register new schemas only
- `POST /extract-with-approved-schema` - Extract with approved schemas only
- `POST /extract` - Original endpoint (auto-generates if needed)
- `GET /schemas` - List all schemas
- `PUT /schemas/{schema_id}/approve` - Approve schemas
- `PUT /schemas/{schema_id}/modify` - Modify schemas
- `DELETE /schemas/{schema_id}` - Delete schemas

## Benefits

1. **Clear Workflow Separation:**
   - Schema registration is separate from extraction
   - Users can register schemas without uploading documents for extraction

2. **Better Error Handling:**
   - Clear messages when schemas don't exist
   - Clear messages when schemas aren't approved yet
   - Helpful suggestions for next steps

3. **Schema ID Visibility:**
   - Schema IDs are prominently displayed everywhere
   - Easier to track and reference specific schemas
   - Better for debugging and support

4. **Controlled Extraction:**
   - Extract & View only works with approved schemas
   - Prevents accidental extraction with unapproved schemas
   - More predictable behavior

## Testing

Access the updated UI at: **http://localhost:8501**

Test the new features:
1. Try registering a new schema
2. Try registering a duplicate schema (should show error)
3. Try extracting without approved schema (should show error)
4. Approve a schema and then extract (should work)
5. Verify Schema IDs are displayed in all locations
