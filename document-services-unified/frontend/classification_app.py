import streamlit as st
import requests
from typing import Optional, Dict, List
import base64
from PIL import Image
import io
import json
import os

# Configuration - use environment variable or default to localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="PDF Document Classifier",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    .sub-header {
        font-size: 1.8rem;
        color: #667eea;
        margin-bottom: 1rem;
    }
    
    .info-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
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
    
    .page-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    
    .confidence-high {
        color: #38ef7d;
        font-weight: bold;
    }
    
    .confidence-medium {
        color: #f5576c;
        font-weight: bold;
    }
    
    .confidence-low {
        color: #ff6b6b;
        font-weight: bold;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📑 PDF Document Classifier</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666; font-size: 1.1rem;">AI-Powered Page-by-Page Document Type Classification</p>', unsafe_allow_html=True)


def check_api_health() -> bool:
    """Check if Classification API is reachable"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def classify_pdf(file) -> Optional[Dict]:
    """Classify PDF document"""
    try:
        file.seek(0)
        file_content = file.read()
        
        if not file_content:
            st.error(f"File {file.name} is empty")
            return None
        
        file.seek(0)
        
        files = {"file": (file.name, file_content, "application/pdf")}
        
        response = requests.post(
            f"{API_BASE_URL}/classify-pdf",
            files=files,
            timeout=300
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code}")
            st.error(f"Response: {response.text}")
            return None
    except Exception as e:
        st.error(f"Classification failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None


def get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence level"""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"


def get_confidence_emoji(confidence: float) -> str:
    """Get emoji based on confidence level"""
    if confidence >= 0.8:
        return "✅"
    elif confidence >= 0.6:
        return "⚠️"
    else:
        return "❌"


def display_pdf_preview(file) -> None:
    """Display PDF preview"""
    if file.type == "application/pdf":
        file.seek(0)
        pdf_bytes = file.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
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


def main():
    """Main application"""
    
    # Sidebar navigation
    with st.sidebar:
        st.header("API Status")
        if check_api_health():
            st.success(f"🟢 Connected to {API_BASE_URL}")
        else:
            st.error(f"🔴 Cannot connect to {API_BASE_URL}")
        
        st.markdown("---")
        
        st.header("Navigation")
        if st.button("📊 Document Extraction", use_container_width=True):
            st.markdown("""
            <script>
                window.open('http://localhost:8501', '_blank');
            </script>
            """, unsafe_allow_html=True)
            st.info("Opening Document Extraction UI in new tab...")
        
        st.markdown("---")
        
        st.header("About")
        st.info("""
        This tool classifies PDF documents page-by-page using AI.
        
        **Features:**
        - Multi-page PDF support
        - Page-by-page classification
        - Confidence scores
        - Classification reasoning
        - Document type detection
        """)
    
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
    
    # Information box
    st.markdown("""
    <div class="info-box">
        <strong>📋 How it works:</strong>
        <ul>
            <li>Upload a PDF document (can contain multiple document types)</li>
            <li>AI analyzes each page and identifies document types</li>
            <li>Get page-by-page classification with confidence scores</li>
            <li>View reasoning for each classification decision</li>
            <li>Export results as JSON</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload PDF Document",
        type=["pdf"],
        help="Upload a PDF file for classification"
    )
    
    if uploaded_file:
        st.markdown("---")
        
        # Show file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{uploaded_file.size / 1024:.2f} KB")
        with col3:
            st.metric("File Type", uploaded_file.type)
        
        st.markdown("---")
        
        # Classify button
        if st.button("🔍 Classify Document", type="primary", use_container_width=True):
            with st.spinner("Analyzing document... This may take a minute."):
                result = classify_pdf(uploaded_file)
                
                if result:
                    page_classifications = result.get("page_classifications", [])
                    
                    if not page_classifications:
                        st.warning("No classifications found. The document might be empty or unreadable.")
                    else:
                        st.markdown("""
                        <div class="success-box">
                            <h3>✅ Classification Complete!</h3>
                            <p>Document has been analyzed page by page.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Show results in columns
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("📄 Document Preview")
                            display_pdf_preview(uploaded_file)
                        
                        with col2:
                            st.subheader("📊 Classification Results")
                            
                            # Summary statistics
                            total_pages = len(page_classifications)
                            unique_types = len(set(p["document_type"] for p in page_classifications))
                            avg_confidence = sum(p["confidence"] for p in page_classifications) / total_pages
                            
                            stat_col1, stat_col2, stat_col3 = st.columns(3)
                            with stat_col1:
                                st.markdown(f"""
                                <div class="metric-card">
                                    <h3 style="margin:0;">{total_pages}</h3>
                                    <p style="margin:0;">Total Pages</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with stat_col2:
                                st.markdown(f"""
                                <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                                    <h3 style="margin:0;">{unique_types}</h3>
                                    <p style="margin:0;">Document Types</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with stat_col3:
                                st.markdown(f"""
                                <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                                    <h3 style="margin:0;">{avg_confidence:.2%}</h3>
                                    <p style="margin:0;">Avg Confidence</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown("---")
                            
                            # Page-by-page results
                            st.markdown("**Page-by-Page Classifications:**")
                            
                            # Scrollable container for pages
                            for page_info in page_classifications:
                                page_num = page_info["page"]
                                doc_type = page_info["document_type"]
                                confidence = page_info["confidence"]
                                reasoning = page_info["reasoning"]
                                
                                confidence_class = get_confidence_class(confidence)
                                confidence_emoji = get_confidence_emoji(confidence)
                                
                                st.markdown(f"""
                                <div class="page-card">
                                    <div style="font-weight: bold; color: #667eea; margin-bottom: 5px;">
                                        📄 Page {page_num}: {doc_type}
                                        <span style="float: right;">
                                            {confidence_emoji} <span class="{confidence_class}">{confidence:.1%}</span>
                                        </span>
                                    </div>
                                    <div style="font-size: 0.9em; color: #666; margin-top: 5px;">
                                        <strong>Reasoning:</strong> {reasoning}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown("---")
                            
                            # Download results
                            st.subheader("💾 Export Results")
                            
                            json_str = json.dumps(result, indent=2)
                            st.download_button(
                                label="📥 Download JSON",
                                data=json_str,
                                file_name=f"classification_{uploaded_file.name}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                            
                            # Show raw JSON in expander
                            with st.expander("View Raw JSON"):
                                st.json(result)


if __name__ == "__main__":
    main()
