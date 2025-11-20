import streamlit as st
import requests
import json
import os
import html
from pathlib import Path
from typing import Optional, Dict, Any, List
import base64
from io import BytesIO
from PIL import Image
import pandas as pd
from datetime import datetime

# Configuration
st.set_page_config(
    page_title="Document Extraction System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration - Read from environment variable or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #667eea;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    
    .info-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .schema-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .schema-card:hover {
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #667eea;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-active {
        background: #38ef7d;
        color: white;
    }
    
    .status-review {
        background: #ffd93d;
        color: #333;
    }
    
    .status-deprecated {
        background: #6c757d;
        color: white;
    }
    
    .field-row {
        background: #f8f9fa;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 5px;
        border-left: 3px solid #667eea;
    }
    
    .extraction-result {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def display_header():
    """Display the main header with navigation"""
    # Navigation button to home
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🏠 Home", key="home_btn"):
            st.markdown("""
            <script>
                window.open('http://localhost:8080', '_blank');
            </script>
            """, unsafe_allow_html=True)
            st.info("Opening home page in new tab...")
    
    st.markdown('<h1 class="main-header">📄 Document Extraction System</h1>', unsafe_allow_html=True)
    st.markdown("---")

def check_api_health() -> bool:
    """Check if API is reachable"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_document_for_schema(files: List) -> Optional[Dict]:
    """Upload document to generate schema"""
    try:
        file_data = []
        for uploaded_file in files:
            # Reset file pointer to beginning before reading
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            
            # Ensure we have content
            if not file_content:
                st.error(f"File {uploaded_file.name} is empty after reading")
                return None
            
            # Reset again for potential re-use
            uploaded_file.seek(0)
            
            # Ensure correct content type
            content_type = uploaded_file.type
            if not content_type:
                # Fallback based on file extension
                if uploaded_file.name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif uploaded_file.name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif uploaded_file.name.lower().endswith('.png'):
                    content_type = 'image/png'
            
            # Debug info
            st.info(f"Uploading: {uploaded_file.name} | Type: {content_type} | Size: {len(file_content)} bytes")
            
            file_data.append(
                ("document", (uploaded_file.name, file_content, content_type))
            )
        
        response = requests.post(
            f"{API_BASE_URL}/extract",
            files=file_data,
            timeout=600  # Increased to 10 minutes for LLM processing
        )
        
        if response.status_code in [200, 201, 202]:
            return response.json()
        else:
            st.error(f"Error: {response.status_code}")
            st.error(f"Response: {response.text}")
            return None
    except Exception as e:
        st.error(f"Upload failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def register_document_schema(files: List) -> Optional[Dict]:
    """Register a new document schema using the /register-schema endpoint"""
    try:
        file_data = []
        for uploaded_file in files:
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            
            if not file_content:
                st.error(f"File {uploaded_file.name} is empty after reading")
                return None
            
            uploaded_file.seek(0)
            
            content_type = uploaded_file.type
            if not content_type:
                if uploaded_file.name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif uploaded_file.name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif uploaded_file.name.lower().endswith('.png'):
                    content_type = 'image/png'
            
            st.info(f"Uploading: {uploaded_file.name} | Type: {content_type} | Size: {len(file_content)} bytes")
            
            file_data.append(
                ("document", (uploaded_file.name, file_content, content_type))
            )
        
        response = requests.post(
            f"{API_BASE_URL}/register-schema",
            files=file_data,
            timeout=600
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            # Return error details for better handling
            try:
                error_data = response.json()
                return {"error": True, "status_code": response.status_code, "detail": error_data}
            except:
                return {"error": True, "status_code": response.status_code, "detail": response.text}
    except Exception as e:
        st.error(f"Registration failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def extract_with_approved_schema(files: List) -> Optional[Dict]:
    """Extract data using only approved schemas"""
    try:
        file_data = []
        for uploaded_file in files:
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            
            if not file_content:
                st.error(f"File {uploaded_file.name} is empty after reading")
                return None
            
            uploaded_file.seek(0)
            
            content_type = uploaded_file.type
            if not content_type:
                if uploaded_file.name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif uploaded_file.name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif uploaded_file.name.lower().endswith('.png'):
                    content_type = 'image/png'
            
            st.info(f"Uploading: {uploaded_file.name} | Type: {content_type} | Size: {len(file_content)} bytes")
            
            file_data.append(
                ("document", (uploaded_file.name, file_content, content_type))
            )
        
        response = requests.post(
            f"{API_BASE_URL}/extract-with-approved-schema",
            files=file_data,
            timeout=600
        )
        
        if response.status_code in [200]:
            return response.json()
        else:
            # Return error details for better handling
            try:
                error_data = response.json()
                return {"error": True, "status_code": response.status_code, "detail": error_data}
            except:
                return {"error": True, "status_code": response.status_code, "detail": response.text}
    except Exception as e:
        st.error(f"Extraction failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def get_all_schemas() -> Optional[List[Dict]]:
    """Fetch all schemas from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/schemas", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("schemas", [])
        return None
    except Exception as e:
        st.error(f"Failed to fetch schemas: {str(e)}")
        return None

def approve_schema(schema_id: str) -> Optional[Dict]:
    """Approve a schema"""
    try:
        response = requests.put(
            f"{API_BASE_URL}/schemas/{schema_id}/approve",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Approval failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Approval failed: {str(e)}")
        return None

def modify_schema(schema_id: str, modifications: Dict, description: str) -> Optional[Dict]:
    """Modify a schema"""
    try:
        payload = {
            "modifications": modifications,
            "change_description": description
        }
        response = requests.put(
            f"{API_BASE_URL}/schemas/{schema_id}/modify",
            json=payload,
            timeout=30
        )
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"Modification failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Modification failed: {str(e)}")
        return None

def delete_schema(schema_id: str) -> bool:
    """Delete a schema"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/schemas/{schema_id}",
            timeout=30
        )
        if response.status_code in [200, 204]:
            return True
        else:
            st.error(f"Deletion failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"Deletion failed: {str(e)}")
        return False

def display_document(file) -> None:
    """Display uploaded document"""
    if file.type == "application/pdf":
        # Display PDF using base64 encoding and iframe
        file.seek(0)
        pdf_bytes = file.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create an embedded PDF viewer
        pdf_display = f'''
        <div style="width:100%; height:600px; border:1px solid #ddd; border-radius:5px; overflow:hidden;">
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="100%" 
                type="application/pdf"
                style="border:none;">
                <p>Your browser does not support PDFs. 
                <a href="data:application/pdf;base64,{base64_pdf}" download="{file.name}">Download the PDF</a> instead.</p>
            </iframe>
        </div>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        st.caption(f"📄 {file.name} ({file.size / 1024:.2f} KB)")
        
    elif file.type.startswith("image/"):
        # Display image
        file.seek(0)
        image = Image.open(file)
        st.image(image, caption=f"{file.name} ({file.size / 1024:.2f} KB)", use_container_width=True)

def format_status_badge(status: str) -> str:
    """Format status as styled badge"""
    status_classes = {
        "active": "status-active",
        "in_review": "status-review",
        "deprecated": "status-deprecated"
    }
    status_text = status.replace("_", " ").title()
    css_class = status_classes.get(status.lower(), "status-review")
    return f'<span class="status-badge {css_class}">{status_text}</span>'

# Page Functions
def page_register_schema():
    """Page for registering new document schemas"""
    st.markdown('<h2 class="sub-header">📝 Register New Document Schema</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📋 Schema Registration Process:</strong>
        <ul>
            <li>Upload sample document(s) to generate a new schema</li>
            <li>System will classify the document type automatically</li>
            <li>Schema will be created with IN_REVIEW status</li>
            <li>⚠️ Registration fails if schema already exists (IN_REVIEW or ACTIVE)</li>
            <li>After registration, schema must be approved before use</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📁 Upload Sample Documents")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload sample document(s) for schema generation",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Upload one or more sample documents to generate the schema",
        key="register_schema_uploader"
    )
    
    # Debug info
    if uploaded_files is None or len(uploaded_files) == 0:
        st.info("👆 Please upload one or more documents above to get started")
    
    # Show document preview
    if uploaded_files:
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📎 Uploaded Sample Documents")
            if len(uploaded_files) == 1:
                file = uploaded_files[0]
                st.write(f"**{file.name}** ({file.size / 1024:.2f} KB)")
                file.seek(0)
                display_document(file)
            else:
                for idx, file in enumerate(uploaded_files):
                    with st.expander(f"📄 Document {idx + 1}: {file.name}", expanded=(idx == 0)):
                        st.write(f"Size: {file.size / 1024:.2f} KB")
                        file.seek(0)
                        display_document(file)
        
        with col2:
            st.subheader("📊 Upload Summary")
            st.metric("Total Documents", len(uploaded_files))
            total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
            st.metric("Total Size", f"{total_size:.2f} MB")
        
        st.markdown("---")
        
        if st.button("📝 Register Schema", type="primary", use_container_width=True):
            with st.spinner("Registering schema... This may take a few minutes."):
                result = register_document_schema(uploaded_files)
                
                if result:
                    # Handle error responses
                    if result.get("error"):
                        status_code = result.get("status_code")
                        detail = result.get("detail")
                        
                        if status_code == 409:
                            # Schema already exists
                            st.markdown("""
                            <div class="warning-box">
                                <h3>⚠️ Schema Already Exists</h3>
                                <p>A schema for this document type already exists and cannot be registered again.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if isinstance(detail, dict):
                                error_info = detail.get("detail", {})
                                if isinstance(error_info, dict):
                                    st.error(f"**Error:** {error_info.get('error', 'Unknown error')}")
                                    st.info(f"**Message:** {error_info.get('message', 'No message')}")
                                    
                                    existing = error_info.get('existing_schema', {})
                                    if existing:
                                        st.markdown("---")
                                        st.subheader("Existing Schema Information")
                                        
                                        # Display Schema ID prominently
                                        st.markdown(f"""
                                        <div class="info-box">
                                            <h4>📌 Schema ID</h4>
                                            <code style="font-size: 1.2em;">{existing.get('schema_id', 'N/A')}</code>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Document Type", existing.get('document_type', 'N/A'))
                                        with col2:
                                            st.metric("Country", existing.get('country', 'N/A'))
                                        with col3:
                                            st.metric("Version", existing.get('version', 'N/A'))
                                        
                                        st.write(f"**Status:** {format_status_badge(existing.get('status', 'unknown'))}", unsafe_allow_html=True)
                                        st.write(f"**Created:** {existing.get('created_at', 'N/A')}")
                                        st.write(f"**Updated:** {existing.get('updated_at', 'N/A')}")
                        else:
                            st.error(f"Registration failed with status code: {status_code}")
                            st.error(f"Details: {detail}")
                    
                    # Handle success response
                    elif result.get("status") == "schema_registered":
                        st.markdown("""
                        <div class="success-box">
                            <h3>✅ Schema Registered Successfully!</h3>
                            <p>The schema has been created and is now pending review.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Display Schema ID prominently
                        schema_id = result.get("generated_schema", {}).get("schema_id") or result.get("schema_id")
                        st.markdown(f"""
                        <div class="info-box">
                            <h4>📌 Registered Schema ID</h4>
                            <code style="font-size: 1.2em; background: white; color: #667eea; padding: 10px; border-radius: 5px; display: block;">{schema_id}</code>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("📄 Document Classification")
                            classification = result.get("classification", {})
                            st.metric("Document Type", classification.get("document_type", "N/A"))
                            st.metric("Country", classification.get("country", "N/A"))
                            st.metric("Confidence", f"{classification.get('confidence', 0):.2%}")
                        
                        with col2:
                            st.subheader("📋 Schema Information")
                            schema_info = result.get("generated_schema", {})
                            st.metric("Status", "IN_REVIEW")
                            st.metric("Total Fields", len(schema_info.get("schema", {})))
                            st.metric("Schema Confidence", f"{schema_info.get('confidence', 0):.2%}")
                        
                        st.markdown("---")
                        st.subheader("📝 Generated Schema Fields")
                        
                        schema_fields = schema_info.get("schema", {})
                        for field_name, field_props in schema_fields.items():
                            field_type = field_props.get('type', 'unknown')
                            field_desc = field_props.get('description', 'No description')
                            field_required = "✓" if field_props.get('required', False) else "✗"
                            field_example = field_props.get('example', 'N/A')
                            
                            st.markdown(f"""
                            <div style="margin-bottom: 10px; padding: 10px; background-color: #f8f9fa; border-left: 3px solid #667eea; border-radius: 3px;">
                                <div style="font-weight: bold; color: #667eea; margin-bottom: 5px;">
                                    {html.escape(field_name)}
                                    <span style="float: right; font-size: 0.9em;">
                                        <span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">{html.escape(field_type)}</span>
                                        <span style="margin-left: 5px;">Required: {field_required}</span>
                                    </span>
                                </div>
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 3px;">
                                    <strong>Description:</strong> {html.escape(str(field_desc))}
                                </div>
                                <div style="font-size: 0.85em; color: #666;">
                                    <strong>Example:</strong> <code>{html.escape(str(field_example))}</code>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.info("💡 Next step: Go to 'View All Schemas' to approve this schema before using it for extraction.")
                    else:
                        st.warning(f"Unexpected response status: {result.get('status')}")
                        st.json(result)

def page_upload_documents():
    """Page for uploading documents and extracting data with approved schemas"""
    st.markdown('<h2 class="sub-header">📤 Upload Documents for Data Extraction</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📋 Instructions:</strong>
        <ul>
            <li>Upload one or more documents (PDF, JPEG, PNG)</li>
            <li>System will classify the document type automatically</li>
            <li>Data extraction uses ONLY APPROVED (ACTIVE) schemas</li>
            <li>⚠️ Extraction fails if no approved schema exists</li>
            <li>⚠️ Extraction fails if schema is still IN_REVIEW</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📁 Upload Documents")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose document(s)",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Upload one or more documents for processing",
        key="upload_documents_uploader"
    )
    
    # Debug info
    if uploaded_files is None or len(uploaded_files) == 0:
        st.info("👆 Please upload one or more documents above to extract data")
    
    # Show document preview immediately after upload
    if uploaded_files:
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📎 Uploaded Documents Preview")
            # Single document - full display
            if len(uploaded_files) == 1:
                file = uploaded_files[0]
                st.write(f"**{file.name}** ({file.size / 1024:.2f} KB)")
                file.seek(0)
                display_document(file)
            else:
                # Multiple documents - expandable
                for idx, file in enumerate(uploaded_files):
                    with st.expander(f"📄 Document {idx + 1}: {file.name}", expanded=(idx == 0)):
                        st.write(f"Size: {file.size / 1024:.2f} KB")
                        file.seek(0)
                        display_document(file)
        
        with col2:
            st.subheader("📊 Upload Summary")
            st.metric("Total Documents", len(uploaded_files))
            total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
            st.metric("Total Size", f"{total_size:.2f} MB")
        
        st.markdown("---")
        
        if st.button("🚀 Extract Data", type="primary", use_container_width=True):
            with st.spinner("Extracting data... This may take a few minutes."):
                result = extract_with_approved_schema(uploaded_files)
                
                if result:
                    # Handle error responses
                    if result.get("error"):
                        status_code = result.get("status_code")
                        detail = result.get("detail")
                        
                        if status_code == 404:
                            # Schema not found
                            st.markdown("""
                            <div class="warning-box">
                                <h3>❌ No Approved Schema Found</h3>
                                <p>No approved schema exists for this document type.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if isinstance(detail, dict):
                                error_info = detail.get("detail", {})
                                if isinstance(error_info, dict):
                                    st.error(f"**Error:** {error_info.get('error', 'Schema not found')}")
                                    st.info(f"**Message:** {error_info.get('message', 'Please register and approve a schema first')}")
                                    
                                    classification = error_info.get('classification', {})
                                    if classification:
                                        st.markdown("---")
                                        st.subheader("Document Classification")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Document Type", classification.get('document_type', 'N/A'))
                                        with col2:
                                            st.metric("Country", classification.get('country', 'N/A'))
                                        with col3:
                                            st.metric("Confidence", f"{classification.get('confidence', 0):.2%}")
                            
                            st.info("💡 Tip: Register a new schema for this document type in 'Register Schema' page.")
                        
                        elif status_code == 403:
                            # Schema exists but not approved
                            st.markdown("""
                            <div class="warning-box">
                                <h3>⏳ Schema Not Yet Approved</h3>
                                <p>A schema exists but is still pending review.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if isinstance(detail, dict):
                                error_info = detail.get("detail", {})
                                if isinstance(error_info, dict):
                                    st.error(f"**Error:** {error_info.get('error', 'Schema not approved')}")
                                    st.info(f"**Message:** {error_info.get('message', 'Schema must be approved before extraction')}")
                                    
                                    schema_info = error_info.get('schema_info', {})
                                    if schema_info:
                                        st.markdown("---")
                                        
                                        # Display Schema ID prominently
                                        st.markdown(f"""
                                        <div class="info-box">
                                            <h4>📌 Schema ID</h4>
                                            <code style="font-size: 1.2em;">{schema_info.get('schema_id', 'N/A')}</code>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        st.subheader("Schema Information")
                                        col1, col2, col3, col4 = st.columns(4)
                                        with col1:
                                            st.metric("Document Type", schema_info.get('document_type', 'N/A'))
                                        with col2:
                                            st.metric("Country", schema_info.get('country', 'N/A'))
                                        with col3:
                                            st.metric("Version", schema_info.get('version', 'N/A'))
                                        with col4:
                                            st.write(f"**Status:** {format_status_badge(schema_info.get('status', 'unknown'))}", unsafe_allow_html=True)
                                        
                                        st.write(f"**Created:** {schema_info.get('created_at', 'N/A')}")
                            
                            st.info("💡 Tip: Go to 'View All Schemas' to approve this schema.")
                        else:
                            st.error(f"Extraction failed with status code: {status_code}")
                            st.error(f"Details: {detail}")
                    
                    # Handle success response
                    elif result.get("status") == "extracted":
                        st.markdown("""
                        <div class="success-box">
                            <h3>✅ Data Extracted Successfully!</h3>
                            <p>An approved schema was found and data has been extracted.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Display Schema ID prominently
                        schema_used = result.get("schema_used", {})
                        schema_id = schema_used.get("schema_id", "N/A")
                        st.markdown(f"""
                        <div class="success-box">
                            <h4>📌 Schema ID Used</h4>
                            <code style="font-size: 1.1em; background: white; color: #11998e; padding: 8px; border-radius: 5px; display: block;">{schema_id}</code>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show document preview and extracted data side by side
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("📄 Document Preview")
                            if len(uploaded_files) == 1:
                                file = uploaded_files[0]
                                st.caption(f"**{file.name}** ({file.size / 1024:.2f} KB)")
                                file.seek(0)
                                display_document(file)
                            else:
                                for idx, file in enumerate(uploaded_files):
                                    with st.expander(f"Document {idx + 1}: {file.name}", expanded=(idx == 0)):
                                        st.caption(f"Size: {file.size / 1024:.2f} KB")
                                        file.seek(0)
                                        display_document(file)
                        
                        with col2:
                            st.subheader("📋 Extracted Data")
                            
                            # Metadata
                            with st.expander("Extraction Metadata", expanded=True):
                                metadata = {
                                    "Document Type": result["classification"]["document_type"],
                                    "Country": result["classification"]["country"],
                                    "Confidence": f"{result['classification']['confidence']:.2%}",
                                    "Schema Version": schema_used.get("version", "N/A"),
                                    "Schema Status": schema_used.get("status", "N/A")
                                }
                                for key, value in metadata.items():
                                    st.metric(key, value)
                            
                            # Display extracted data with HTML escaping
                            st.markdown("---")
                            st.markdown("**Extracted Fields:**")
                            extracted_data = result["data"]
                            for field, value in extracted_data.items():
                                escaped_value = html.escape(str(value)) if value else ""
                                field_label = html.escape(field.replace('_', ' ').title())
                                
                                st.markdown(f"""
                                <div class="extraction-result">
                                    <strong>{field_label}:</strong><br/>
                                    <code>{escaped_value}</code>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Download option
                            st.markdown("---")
                            st.download_button(
                                label="📥 Download JSON",
                                data=json.dumps(result["data"], indent=2),
                                file_name=f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                    else:
                        st.warning(f"Unexpected response: {result.get('status', 'unknown')}")
                        st.json(result)

def page_view_schemas():
    """Page for viewing all schemas"""
    st.markdown('<h2 class="sub-header">📚 All Schemas</h2>', unsafe_allow_html=True)
    
    # Fetch schemas
    with st.spinner("Loading schemas..."):
        schemas = get_all_schemas()
    
    if not schemas:
        st.warning("No schemas found in the system.")
        return
    
    # Statistics
    st.subheader("📊 Schema Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    active_count = sum(1 for s in schemas if s["status"] == "active")
    review_count = sum(1 for s in schemas if s["status"] == "in_review")
    deprecated_count = sum(1 for s in schemas if s["status"] == "deprecated")
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0;">{len(schemas)}</h3>
            <p style="margin:0;">Total Schemas</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <h3 style="margin:0;">{active_count}</h3>
            <p style="margin:0;">Active</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h3 style="margin:0;">{review_count}</h3>
            <p style="margin:0;">Pending Review</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
            <h3 style="margin:0;">{deprecated_count}</h3>
            <p style="margin:0;">Deprecated</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox(
            "Filter by Status",
            ["All", "active", "in_review", "deprecated"]
        )
    with col2:
        filter_type = st.selectbox(
            "Filter by Document Type",
            ["All"] + list(set(s["document_type"] for s in schemas))
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Created Date (Newest)", "Created Date (Oldest)", "Document Type", "Version"]
        )
    
    # Apply filters
    filtered_schemas = schemas
    if filter_status != "All":
        filtered_schemas = [s for s in filtered_schemas if s["status"] == filter_status]
    if filter_type != "All":
        filtered_schemas = [s for s in filtered_schemas if s["document_type"] == filter_type]
    
    # Apply sorting
    if sort_by == "Created Date (Newest)":
        filtered_schemas = sorted(filtered_schemas, key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "Created Date (Oldest)":
        filtered_schemas = sorted(filtered_schemas, key=lambda x: x["created_at"])
    elif sort_by == "Document Type":
        filtered_schemas = sorted(filtered_schemas, key=lambda x: x["document_type"])
    elif sort_by == "Version":
        filtered_schemas = sorted(filtered_schemas, key=lambda x: x["version"], reverse=True)
    
    st.write(f"**Showing {len(filtered_schemas)} of {len(schemas)} schemas**")
    
    # Display schemas
    for schema in filtered_schemas:
        # Format status text for expander (plain text, no HTML)
        status_text = schema['status'].replace('_', ' ').title()
        
        with st.expander(
            f"📄 {schema['document_type'].upper()} ({schema['country']}) - Version {schema['version']} - {status_text}",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Schema Details")
                st.write(f"**Schema ID:** `{schema['id']}`")
                st.write(f"**Document Type:** {schema['document_type']}")
                st.write(f"**Country:** {schema['country']}")
                st.write(f"**Version:** {schema['version']}")
                st.write(f"**Status:** {format_status_badge(schema['status'])}", unsafe_allow_html=True)
                st.write(f"**Created:** {schema['created_at']}")
                st.write(f"**Updated:** {schema['updated_at']}")
            
            with col2:
                st.subheader("Quick Actions")
                if schema['status'] == 'in_review':
                    if st.button(f"✅ Approve", key=f"approve_{schema['id']}", use_container_width=True):
                        with st.spinner("Approving schema..."):
                            result = approve_schema(schema['id'])
                            if result:
                                st.success("Schema approved successfully!")
                                st.rerun()
                
                if schema['status'] in ['active', 'in_review']:
                    if st.button(f"✏️ Modify", key=f"modify_btn_{schema['id']}", use_container_width=True):
                        st.session_state.modifying_schema = schema['id']
                        st.rerun()
                
                # Delete option for all schemas
                if st.button(f"🗑️ Delete", key=f"delete_btn_{schema['id']}", use_container_width=True):
                    st.session_state.deleting_schema = schema['id']
                    st.rerun()
            
            # Show delete confirmation if this schema is being deleted
            if st.session_state.get('deleting_schema') == schema['id']:
                st.markdown("---")
                st.error("⚠️ **DANGER ZONE: DELETE SCHEMA**")
                st.warning("This action cannot be undone. The schema will be permanently deleted from the database.")
                
                st.json({
                    "ID": schema['id'],
                    "Type": schema['document_type'],
                    "Country": schema['country'],
                    "Version": schema['version'],
                    "Status": schema['status']
                })
                
                confirm_text = st.text_input(
                    "Type 'DELETE' to confirm deletion:",
                    key=f"delete_confirm_{schema['id']}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⚠️ Confirm Delete", key=f"confirm_delete_{schema['id']}", type="secondary", use_container_width=True):
                        if confirm_text == "DELETE":
                            with st.spinner("Deleting schema..."):
                                if delete_schema(schema['id']):
                                    st.session_state.deleting_schema = None
                                    st.success("✅ Schema deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete schema.")
                        else:
                            st.error("Please type 'DELETE' to confirm deletion.")
                
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_{schema['id']}", use_container_width=True):
                        st.session_state.deleting_schema = None
                        st.rerun()
            
            st.subheader("Schema Fields")
            schema_fields = schema['schema']
            
            # Display fields in a nice format
            for field_name, field_props in schema_fields.items():
                st.markdown(f"""
                <div class="field-row">
                    <strong>{field_name}</strong> ({field_props.get('type', 'unknown')})<br/>
                    <small>{field_props.get('description', 'No description')}</small><br/>
                    <small>Required: {'Yes' if field_props.get('required', False) else 'No'}</small>
                    {f"<br/><small>Example: {field_props.get('example')}</small>" if field_props.get('example') else ""}
                </div>
                """, unsafe_allow_html=True)

def page_modify_schema():
    """Page for modifying schemas"""
    st.markdown('<h2 class="sub-header">✏️ Modify Schema</h2>', unsafe_allow_html=True)
    
    # Fetch schemas
    schemas = get_all_schemas()
    if not schemas:
        st.warning("No schemas available.")
        return
    
    # Filter for modifiable schemas
    modifiable_schemas = [s for s in schemas if s['status'] in ['active', 'in_review']]
    
    if not modifiable_schemas:
        st.info("No schemas available for modification. Only Active and In Review schemas can be modified.")
        return
    
    # Schema selection
    schema_options = [f"{s['document_type']} ({s['country']}) - v{s['version']}" for s in modifiable_schemas]
    selected_idx = st.selectbox("Select Schema to Modify", range(len(schema_options)), format_func=lambda x: schema_options[x])
    
    selected_schema = modifiable_schemas[selected_idx]
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Current Schema")
        st.json({
            "ID": selected_schema['id'],
            "Type": selected_schema['document_type'],
            "Country": selected_schema['country'],
            "Version": selected_schema['version'],
            "Status": selected_schema['status']
        })
    
    with col2:
        st.subheader("Modification Type")
        modification_type = st.radio(
            "Choose action",
            ["Add New Field", "Update Existing Field", "Remove Field"]
        )
    
    st.markdown("---")
    
    modifications = {}
    
    if modification_type == "Add New Field":
        st.subheader("➕ Add New Field")
        col1, col2 = st.columns(2)
        
        with col1:
            field_name = st.text_input("Field Name", placeholder="e.g., middle_name")
            field_type = st.selectbox("Field Type", ["string", "integer", "boolean", "date", "number"])
            required = st.checkbox("Required Field")
        
        with col2:
            description = st.text_area("Description", placeholder="Describe this field...")
            example = st.text_input("Example Value", placeholder="e.g., John")
        
        if field_name:
            modifications[field_name] = {
                "type": field_type,
                "description": description,
                "required": required,
                "example": example
            }
    
    elif modification_type == "Update Existing Field":
        st.subheader("📝 Update Existing Field")
        
        existing_fields = list(selected_schema['schema'].keys())
        field_to_update = st.selectbox("Select Field to Update", existing_fields)
        
        current_field = selected_schema['schema'][field_to_update]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Current Values:**")
            st.json(current_field)
        
        with col2:
            st.write("**New Values:**")
            new_type = st.selectbox("Field Type", ["string", "integer", "boolean", "date", "number"],
                                   index=["string", "integer", "boolean", "date", "number"].index(current_field.get("type", "string")))
            new_required = st.checkbox("Required", value=current_field.get("required", False))
            new_description = st.text_area("Description", value=current_field.get("description", ""))
            new_example = st.text_input("Example", value=str(current_field.get("example", "")))
        
        modifications[field_to_update] = {
            "type": new_type,
            "description": new_description,
            "required": new_required,
            "example": new_example
        }
    
    elif modification_type == "Remove Field":
        st.subheader("🗑️ Remove Field")
        
        existing_fields = list(selected_schema['schema'].keys())
        field_to_remove = st.selectbox("Select Field to Remove", existing_fields)
        
        st.warning(f"⚠️ You are about to remove the field: **{field_to_remove}**")
        st.json(selected_schema['schema'][field_to_remove])
        
        modifications[field_to_remove] = None
    
    change_description = st.text_area(
        "Change Description",
        placeholder="Describe the reason for this modification...",
        help="Provide context for this change"
    )
    
    st.markdown("---")
    
    # Action buttons
    col1, col2 = st.columns([3, 1])
    
    with col1:
        submit_button = st.button("💾 Submit Modifications", type="primary", use_container_width=True)
    
    with col2:
        delete_button = st.button("🗑️ Delete Schema", use_container_width=True)
    
    # Handle Submit
    if submit_button:
        if not modifications:
            st.error("No modifications specified.")
        elif not change_description:
            st.warning("Please provide a change description.")
        else:
            with st.spinner("Applying modifications..."):
                result = modify_schema(selected_schema['id'], modifications, change_description)
                
                if result:
                    st.success("✅ Schema modified successfully!")
                    st.json(result)
                    st.info("The modified schema is now in 'In Review' status and needs approval.")
                    st.rerun()
    
    # Handle Delete - use session state for confirmation flow
    if delete_button:
        st.session_state.confirming_delete = selected_schema['id']
    
    if st.session_state.get('confirming_delete') == selected_schema['id']:
        st.markdown("---")
        st.error("⚠️ **DANGER ZONE: DELETE SCHEMA**")
        st.warning("This action cannot be undone. The schema will be permanently deleted from the database.")
        
        st.json({
            "ID": selected_schema['id'],
            "Type": selected_schema['document_type'],
            "Country": selected_schema['country'],
            "Version": selected_schema['version'],
            "Status": selected_schema['status']
        })
        
        confirm_text = st.text_input(
            "Type 'DELETE' to confirm deletion:",
            key="delete_confirm_input"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚠️ Confirm Delete", type="secondary", use_container_width=True):
                if confirm_text == "DELETE":
                    with st.spinner("Deleting schema..."):
                        if delete_schema(selected_schema['id']):
                            st.session_state.confirming_delete = None
                            st.success("✅ Schema deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete schema.")
                else:
                    st.error("Please type 'DELETE' to confirm deletion.")
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirming_delete = None
                st.rerun()

def page_extract_and_view():
    """Page for extracting data and viewing results alongside documents"""
    st.markdown('<h2 class="sub-header">🔍 Extract & View Results</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📋 How it works:</strong>
        <ul>
            <li>Upload document(s) for data extraction</li>
            <li>System uses ONLY APPROVED (ACTIVE) schemas</li>
            <li>View extracted data alongside the original document</li>
            <li>Download results in JSON format</li>
            <li>⚠️ Extraction fails if schema doesn't exist or is still IN_REVIEW</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Upload document(s) for extraction",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="extract_view_uploader"
    )
    
    # Show document preview immediately after upload
    if uploaded_files:
        st.markdown("---")
        st.subheader("📎 Uploaded Documents Preview")
        
        # Create columns for preview
        if len(uploaded_files) == 1:
            # Single document - full width
            with st.container():
                file = uploaded_files[0]
                st.write(f"**{file.name}** ({file.size / 1024:.2f} KB)")
                file.seek(0)
                display_document(file)
        else:
            # Multiple documents - show in grid
            for idx, file in enumerate(uploaded_files):
                with st.expander(f"📄 Document {idx + 1}: {file.name}", expanded=(idx == 0)):
                    st.write(f"Size: {file.size / 1024:.2f} KB")
                    file.seek(0)
                    display_document(file)
        
        st.markdown("---")
    
    if uploaded_files and st.button("🚀 Extract Data", type="primary", use_container_width=True):
        with st.spinner("Extracting data... This may take a moment."):
            result = extract_with_approved_schema(uploaded_files)
            
            if result:
                # Handle error responses
                if result.get("error"):
                    status_code = result.get("status_code")
                    detail = result.get("detail")
                    
                    if status_code == 404:
                        # Schema not found
                        st.markdown("""
                        <div class="warning-box">
                            <h3>❌ No Approved Schema Found</h3>
                            <p>No approved schema exists for this document type.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if isinstance(detail, dict):
                            error_info = detail.get("detail", {})
                            if isinstance(error_info, dict):
                                st.error(f"**Error:** {error_info.get('error', 'Schema not found')}")
                                st.info(f"**Message:** {error_info.get('message', 'Please register and approve a schema first')}")
                                
                                classification = error_info.get('classification', {})
                                if classification:
                                    st.markdown("---")
                                    st.subheader("Document Classification")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Document Type", classification.get('document_type', 'N/A'))
                                    with col2:
                                        st.metric("Country", classification.get('country', 'N/A'))
                                    with col3:
                                        st.metric("Confidence", f"{classification.get('confidence', 0):.2%}")
                        
                        st.info("💡 Tip: Register a new schema for this document type first.")
                    
                    elif status_code == 403:
                        # Schema exists but not approved
                        st.markdown("""
                        <div class="warning-box">
                            <h3>⏳ Schema Not Yet Approved</h3>
                            <p>A schema exists but is still pending review.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if isinstance(detail, dict):
                            error_info = detail.get("detail", {})
                            if isinstance(error_info, dict):
                                st.error(f"**Error:** {error_info.get('error', 'Schema not approved')}")
                                st.info(f"**Message:** {error_info.get('message', 'Schema must be approved before extraction')}")
                                
                                schema_info = error_info.get('schema_info', {})
                                if schema_info:
                                    st.markdown("---")
                                    
                                    # Display Schema ID prominently
                                    st.markdown(f"""
                                    <div class="info-box">
                                        <h4>📌 Schema ID</h4>
                                        <code style="font-size: 1.2em;">{schema_info.get('schema_id', 'N/A')}</code>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.subheader("Schema Information")
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Document Type", schema_info.get('document_type', 'N/A'))
                                    with col2:
                                        st.metric("Country", schema_info.get('country', 'N/A'))
                                    with col3:
                                        st.metric("Version", schema_info.get('version', 'N/A'))
                                    with col4:
                                        st.write(f"**Status:** {format_status_badge(schema_info.get('status', 'unknown'))}", unsafe_allow_html=True)
                                    
                                    st.write(f"**Created:** {schema_info.get('created_at', 'N/A')}")
                        
                        st.info("💡 Tip: Go to 'View All Schemas' to approve this schema.")
                    else:
                        st.error(f"Extraction failed with status code: {status_code}")
                        st.error(f"Details: {detail}")
                
                # Handle success response
                elif result.get("status") == "extracted":
                    st.success("✅ Data extracted successfully!")
                    
                    # Two column layout
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.subheader("📄 Original Document(s)")
                        for idx, file in enumerate(uploaded_files):
                            with st.expander(f"Document {idx + 1}: {file.name}", expanded=idx==0):
                                file.seek(0)  # Reset file pointer
                                display_document(file)
                    
                    with col2:
                        st.subheader("📊 Extracted Data")
                        
                        # Display Schema ID prominently
                        schema_used = result.get("schema_used", {})
                        schema_id = schema_used.get("schema_id", "N/A")
                        st.markdown(f"""
                        <div class="success-box">
                            <h4>📌 Schema ID Used</h4>
                            <code style="font-size: 1.1em; background: white; color: #11998e; padding: 8px; border-radius: 5px; display: block;">{schema_id}</code>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Metadata
                        with st.expander("Extraction Metadata", expanded=True):
                            metadata = {
                                "Document Type": result["classification"]["document_type"],
                                "Country": result["classification"]["country"],
                                "Confidence": f"{result['classification']['confidence']:.2%}",
                                "Schema Version": schema_used.get("version", "N/A"),
                                "Schema Status": schema_used.get("status", "N/A")
                            }
                            for key, value in metadata.items():
                                st.metric(key, value)
                        
                        # Extracted data
                        with st.expander("Extracted Fields", expanded=True):
                            extracted_data = result["data"]
                            
                            for field, value in extracted_data.items():
                                # Escape HTML characters to prevent rendering issues with special characters
                                escaped_value = html.escape(str(value)) if value else ""
                                field_label = html.escape(field.replace('_', ' ').title())
                                
                                st.markdown(f"""
                                <div class="extraction-result">
                                    <strong>{field_label}:</strong><br/>
                                    <code>{escaped_value}</code>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Download option
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(result["data"], indent=2),
                            file_name=f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Unexpected response: {result.get('status', 'unknown')}")
                    st.json(result)

# Main App
def main():
    display_header()
    
    # Check API health
    if not check_api_health():
        st.error("⚠️ Cannot connect to API server. Please ensure the backend service is running at " + API_BASE_URL)
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["📝 Register Schema", "📤 Upload Documents", "📚 View All Schemas", "✏️ Modify Schemas", "🔍 Extract & View"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"**API Status:** 🟢 Connected\n\n**Endpoint:** {API_BASE_URL}")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Other Services")
    if st.sidebar.button("🏷️ PDF Classification", use_container_width=True):
        st.sidebar.markdown("""
        <script>
            window.open('http://localhost:8502', '_blank');
        </script>
        """, unsafe_allow_html=True)
        st.sidebar.info("Opening PDF Classification UI in new tab...")
    
    # Page routing
    if page == "📝 Register Schema":
        page_register_schema()
    elif page == "📤 Upload Documents":
        page_upload_documents()
    elif page == "📚 View All Schemas":
        page_view_schemas()
    elif page == "✏️ Modify Schemas":
        page_modify_schema()
    elif page == "🔍 Extract & View":
        page_extract_and_view()

if __name__ == "__main__":
    main()
