"""
Unified Document Services Frontend
Combines document classification and extraction into a single Streamlit interface
"""
import streamlit as st
import requests
import json
import os
from typing import Optional, Dict, Any, List
import base64
from io import BytesIO
from PIL import Image
import pandas as pd
from datetime import datetime

# Configuration
st.set_page_config(
    page_title="Unified Document Services",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Custom CSS
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
    
    .service-tab {
        font-size: 1.3rem;
        font-weight: 600;
        padding: 0.5rem 1rem;
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
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .classification-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .schema-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-active { background: #38ef7d; color: white; }
    .status-review { background: #ffd93d; color: #333; }
    .status-deprecated { background: #6c757d; color: white; }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📄 Unified Document Services</h1>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50/667eea/FFFFFF?text=Document+Services", use_container_width=True)
    st.markdown("### 🔧 Service Options")
    
    service_mode = st.radio(
        "Select Service:",
        ["📋 PDF Classification", "📊 Document Extraction", "⚙️ Schema Management"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 📡 API Status")
    
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        if response.status_code == 200:
            st.success("✅ API Connected")
            service_info = response.json()
            st.caption(f"Version: {service_info.get('version', 'N/A')}")
        else:
            st.error("⚠️ API Error")
    except:
        st.error("❌ API Disconnected")
    
    st.markdown("---")
    st.caption(f"**API:** `{API_BASE_URL}`")

# ============================================================================
# SERVICE 1: PDF CLASSIFICATION
# ============================================================================

if service_mode == "📋 PDF Classification":
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### 📋 PDF Document Classification")
    st.markdown("Upload a PDF to classify each page into document types")
    st.markdown('</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF document for page-by-page classification"
    )
    
    if uploaded_file:
        st.markdown(f"**📄 File:** {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("🔍 Classify PDF", type="primary", use_container_width=True):
            with st.spinner("Analyzing PDF pages..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{API_BASE_URL}/classify-pdf", files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.markdown("### ✅ Classification Complete")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Summary metrics
                        classifications = result.get("page_classifications", [])
                        total_pages = len(classifications)
                        unique_types = len(set(c["document_type"] for c in classifications))
                        avg_confidence = sum(c["confidence"] for c in classifications) / total_pages if total_pages > 0 else 0
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Pages", total_pages)
                        with col2:
                            st.metric("Unique Types", unique_types)
                        with col3:
                            st.metric("Avg Confidence", f"{avg_confidence:.2%}")
                        
                        st.markdown("---")
                        
                        # Detailed results
                        st.markdown("### 📑 Page-by-Page Classification")
                        
                        for classification in classifications:
                            with st.expander(
                                f"📄 Page {classification['page']}: {classification['document_type']} "
                                f"(Confidence: {classification['confidence']:.2%})"
                            ):
                                col1, col2 = st.columns([1, 3])
                                with col1:
                                    st.metric("Confidence", f"{classification['confidence']:.2%}")
                                with col2:
                                    st.write("**Reasoning:**")
                                    st.write(classification['reasoning'])
                        
                        # Download results
                        st.markdown("---")
                        st.download_button(
                            label="📥 Download Classification Results (JSON)",
                            data=json.dumps(result, indent=2),
                            file_name=f"classification_{uploaded_file.name}.json",
                            mime="application/json"
                        )
                        
                    else:
                        st.error(f"❌ Classification failed: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ============================================================================
# SERVICE 2: DOCUMENT EXTRACTION
# ============================================================================

elif service_mode == "📊 Document Extraction":
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### 📊 Document Data Extraction")
    st.markdown("Extract structured data from documents using schema-based extraction")
    st.markdown('</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Choose document file(s)",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="Upload one or more document images or PDFs"
    )
    
    if uploaded_files:
        st.markdown(f"**📄 {len(uploaded_files)} file(s) selected**")
        
        for uploaded_file in uploaded_files:
            st.caption(f"• {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("🚀 Extract Data", type="primary", use_container_width=True):
            with st.spinner("Extracting data from documents..."):
                try:
                    files = [
                        ("document", (f.name, f.getvalue(), f.type))
                        for f in uploaded_files
                    ]
                    
                    response = requests.post(f"{API_BASE_URL}/extract", files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        status = result.get("status")
                        
                        if status == "extracted":
                            st.markdown('<div class="success-box">', unsafe_allow_html=True)
                            st.markdown("### ✅ Extraction Successful")
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Classification info
                            classification = result.get("classification", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Document Type", classification.get("document_type"))
                            with col2:
                                st.metric("Country", classification.get("country"))
                            with col3:
                                st.metric("Confidence", f"{classification.get('confidence', 0):.2%}")
                            
                            st.markdown("---")
                            
                            # Extracted data
                            st.markdown("### 📋 Extracted Data")
                            extracted_data = result.get("data", {})
                            
                            # Display as formatted JSON
                            st.json(extracted_data)
                            
                            # Schema info
                            schema_used = result.get("schema_used", {})
                            st.markdown("---")
                            st.markdown("### 📐 Schema Used")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption("**Schema ID:**")
                                st.code(schema_used.get("schema_id", "N/A"))
                            with col2:
                                st.caption("**Version:**")
                                st.info(f"v{schema_used.get('version', 'N/A')}")
                            with col3:
                                st.caption("**Status:**")
                                status_val = schema_used.get("status", "unknown")
                                st.info(status_val.upper())
                            
                            # Download results
                            st.markdown("---")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button(
                                    label="📥 Download Extracted Data (JSON)",
                                    data=json.dumps(extracted_data, indent=2),
                                    file_name=f"extracted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                            with col2:
                                st.download_button(
                                    label="📥 Download Full Result (JSON)",
                                    data=json.dumps(result, indent=2),
                                    file_name=f"extraction_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                        
                        elif status == "schema_generated":
                            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                            st.markdown("### ⚠️ Schema Generated - Awaiting Approval")
                            st.markdown(result.get("message", ""))
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            schema_id = result.get("schema_id")
                            st.info(f"**Schema ID:** `{schema_id}`")
                            st.caption("Please approve the schema in the Schema Management section before extracting data.")
                            
                            # Show generated schema
                            generated_schema = result.get("generated_schema", {})
                            st.json(generated_schema.get("schema", {}))
                        
                        elif status == "pending_review":
                            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                            st.markdown("### ⚠️ Schema Pending Review")
                            st.markdown(result.get("message", ""))
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            schema_info = result.get("schema", {})
                            st.info(f"**Schema ID:** `{schema_info.get('schema_id')}`")
                    
                    elif response.status_code == 201:
                        result = response.json()
                        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                        st.markdown("### ⚠️ New Schema Generated")
                        st.markdown(result.get("message", ""))
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.info(f"**Schema ID:** `{result.get('schema_id')}`")
                        
                    elif response.status_code == 422:
                        result = response.json()
                        st.warning("⚠️ Low confidence classification")
                        st.json(result)
                    
                    else:
                        st.error(f"❌ Extraction failed: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ============================================================================
# SERVICE 3: SCHEMA MANAGEMENT
# ============================================================================

elif service_mode == "⚙️ Schema Management":
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Schema Management")
    st.markdown("View, approve, modify, and delete document schemas")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tabs for different schema operations
    tab1, tab2, tab3 = st.tabs(["📋 View Schemas", "✅ Approve Schema", "🗑️ Delete Schema"])
    
    with tab1:
        st.markdown("### 📋 All Schemas")
        
        if st.button("🔄 Refresh Schemas", use_container_width=True):
            st.rerun()
        
        try:
            response = requests.get(f"{API_BASE_URL}/schemas")
            
            if response.status_code == 200:
                result = response.json()
                schemas = result.get("schemas", [])
                total_count = result.get("total_count", 0)
                
                st.info(f"**Total Schemas:** {total_count}")
                
                if schemas:
                    # Filter options
                    col1, col2 = st.columns(2)
                    with col1:
                        status_filter = st.multiselect(
                            "Filter by Status:",
                            ["active", "in_review", "deprecated"],
                            default=["active", "in_review"]
                        )
                    with col2:
                        doc_types = list(set(s["document_type"] for s in schemas))
                        type_filter = st.multiselect(
                            "Filter by Document Type:",
                            doc_types,
                            default=doc_types
                        )
                    
                    # Filter schemas
                    filtered_schemas = [
                        s for s in schemas
                        if s["status"] in status_filter and s["document_type"] in type_filter
                    ]
                    
                    st.markdown(f"**Showing {len(filtered_schemas)} schema(s)**")
                    
                    for schema in filtered_schemas:
                        with st.expander(
                            f"📄 {schema['document_type']} ({schema['country']}) - v{schema['version']} "
                            f"[{schema['status'].upper()}]"
                        ):
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.caption("**Schema ID:**")
                                st.code(schema['id'][:12] + "...")
                            with col2:
                                st.caption("**Version:**")
                                st.info(f"v{schema['version']}")
                            with col3:
                                st.caption("**Status:**")
                                status_class = f"status-{schema['status'].replace('_', '-')}"
                                st.markdown(
                                    f'<span class="status-badge {status_class}">{schema["status"].upper()}</span>',
                                    unsafe_allow_html=True
                                )
                            with col4:
                                st.caption("**Created:**")
                                st.caption(schema['created_at'][:10])
                            
                            st.markdown("---")
                            st.markdown("**Schema Definition:**")
                            st.json(schema['schema'])
                else:
                    st.info("No schemas found")
            else:
                st.error(f"Failed to fetch schemas: {response.text}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.markdown("### ✅ Approve Schema")
        st.caption("Approve a schema in IN_REVIEW status to make it active")
        
        schema_id_to_approve = st.text_input(
            "Schema ID:",
            placeholder="Enter schema UUID to approve",
            help="Copy the schema ID from the View Schemas tab"
        )
        
        if schema_id_to_approve:
            if st.button("✅ Approve Schema", type="primary", use_container_width=True):
                try:
                    response = requests.put(f"{API_BASE_URL}/schemas/{schema_id_to_approve}/approve")
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Schema approved successfully!")
                        st.json(result)
                    else:
                        st.error(f"Failed to approve schema: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab3:
        st.markdown("### 🗑️ Delete Schema")
        st.warning("⚠️ This action cannot be undone!")
        
        schema_id_to_delete = st.text_input(
            "Schema ID:",
            placeholder="Enter schema UUID to delete",
            help="Copy the schema ID from the View Schemas tab"
        )
        
        if schema_id_to_delete:
            confirm = st.checkbox("I understand this action is permanent")
            
            if confirm:
                if st.button("🗑️ Delete Schema", type="primary", use_container_width=True):
                    try:
                        response = requests.delete(f"{API_BASE_URL}/schemas/{schema_id_to_delete}")
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("✅ Schema deleted successfully!")
                            st.json(result.get("deleted_schema"))
                        else:
                            st.error(f"Failed to delete schema: {response.text}")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666;">'
    '© 2025 Unified Document Services | Powered by FastAPI & Streamlit'
    '</div>',
    unsafe_allow_html=True
)
