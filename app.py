import streamlit as st
import os
import io
import glob
import pandas as pd
import PyPDF2
import json
import re
import tempfile
from openai_backend import OpenAIBackend
from cv_matching_prompt import get_cv_matching_prompt

try:
    from json_to_pdf import create_cv_pdf, extract_json_from_response
    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False
    st.warning("PDF generation functionality is not available. Please install reportlab package.")

backend = OpenAIBackend()

st.set_page_config(
    page_title="CV Matcher",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTextInput, .stTextArea {
        padding: 1rem 0;
    }
    .response-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    /* Make header more prominent */
    h1 {
        color: #1E3A8A;
    }
    /* Improve sidebar styling */
    .css-1adrfps {
        background-color: #f8f9fa;
    }
    /* JSON code display */
    .json-code {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
        white-space: pre-wrap;
        overflow-x: auto;
    }
    /* Error message styling */
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        margin-top: 10px;
        white-space: pre-wrap;
        font-family: monospace;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Settings")
    
    models = ["gpt-4o-mini", "gpt-4"]
    default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if default_model not in models:
        default_model = "gpt-4o-mini"
    
    selected_model = st.selectbox(
        "Choose AI Model", 
        models, 
        index=models.index(default_model)
    )
    
    temperature = st.slider(
        "Temperature", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.7, 
        step=0.1,
        help="Higher values make output more random, lower values more deterministic"
    )
    
    debug_mode = st.checkbox("Enable Debug Mode", value=False, help="Show additional debugging information")
    
    st.divider()
    st.markdown("### About")
    st.markdown("This app matches project requirements with team CVs using AI analysis.")
    st.markdown("Built with Streamlit, Python, and OpenAI API.")

st.title("📄 CV Matching System")
st.subheader("Match project requirements with team CVs")

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def load_excel_data():
    excel_dir = "/workspace/excel"
    excel_files = glob.glob(f"{excel_dir}/*.xlsx") + glob.glob(f"{excel_dir}/*.xls")
    
    excel_data_frames = {}
    excel_data_str = ""
    
    if excel_files:
        for excel_file in excel_files:
            try:
                file_name = os.path.basename(excel_file)
                df = pd.read_excel(excel_file)
                excel_data_frames[file_name] = df
                excel_data_str += f"\n\n=== Excel File: {file_name} ===\n"
                excel_data_str += df.to_string()
            except Exception as e:
                st.error(f"Error reading {file_name}: {str(e)}")
    
    return excel_data_frames, excel_data_str

cv_dir = "/workspace/CV_data"
json_dir = "/workspace/CV_json"
pdf_dir = "/workspace/CV_pdf"

os.makedirs(pdf_dir, exist_ok=True)

def load_cv_json_data():
    json_files = glob.glob(f"{json_dir}/*.json")
    
    if not json_files:
        return None, "No JSON CV files found."
    
    cv_json_data = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cv_data = json.load(f)
                cv_json_data.append(cv_data)
        except Exception as e:
            st.error(f"Error loading {os.path.basename(json_file)}: {str(e)}")
    
    combined_text = ""
    for cv in cv_json_data:
        combined_text += f"===== CV: {cv['name']} =====\n\n"
        
        if 'sections' in cv:
            for section_name, section_content in cv['sections'].items():
                combined_text += f"--- {section_name.upper()} ---\n{section_content}\n\n"
        
        if 'emails' in cv:
            combined_text += f"--- CONTACT ---\nEmail: {', '.join(cv['emails'])}\n"
        
        if 'phones' in cv:
            combined_text += f"Phone: {', '.join(cv['phones'])}\n"
        
        combined_text += "\n\n"
    
    return cv_json_data, combined_text

if not os.path.exists(cv_dir):
    st.warning(f"CV directory not found at {cv_dir}. Falling back to relative path.")
    cv_dir = "CV_data"

if not os.path.exists(json_dir):
    st.warning(f"JSON CV directory not found at {json_dir}. Falling back to relative path.")
    json_dir = "CV_json"

cv_files = glob.glob(f"{cv_dir}/*.pdf")
json_files = glob.glob(f"{json_dir}/*.json")

num_cvs = len(cv_files)
num_json_cvs = len(json_files)

excel_data_frames, auto_excel_data = load_excel_data()

cv_json_data, json_cv_text = load_cv_json_data()

st.info(f"Data loaded from /workspace/CV_json ({num_json_cvs} files) and /workspace/excel ({len(excel_data_frames)} files)")

st.markdown("### Project Description")
st.markdown("Enter the project requirements to match against team CVs.")
project_description = st.text_area(
    "Project description:", 
    height=200,
    placeholder="Paste the full project description here...",
    key="project_description"
)

if st.button("Match Project with Team CVs", type="primary"):
    if not project_description:
        st.error("Please enter a project description.")
    elif num_json_cvs == 0 and num_cvs == 0:
        st.error(f"No CV files found. Please upload some CVs first or convert PDFs to JSON.")
    else:
        with st.spinner(f"Analyzing CVs and matching with project requirements..."):
            try:
                if num_json_cvs > 0 and cv_json_data:
                    st.info("Using JSON CV data for matching")
                    cv_text_for_matching = json_cv_text
                else:
                    st.info("Using PDF CV data for matching (consider converting to JSON for better performance)")
                    cv_texts = []
                    for cv_file in cv_files:
                        try:
                            with open(cv_file, "rb") as f:
                                cv_text = extract_text_from_pdf(f)
                                if cv_text:
                                    cv_texts.append(f"File: {os.path.basename(cv_file)}\n\n{cv_text}")
                                else:
                                    st.warning(f"Could not extract text from {os.path.basename(cv_file)}")
                        except Exception as e:
                            st.error(f"Error processing {os.path.basename(cv_file)}: {str(e)}")
                    
                    if not cv_texts:
                        st.error("Failed to extract text from any CV files. Please check the files and try again.")
                        st.stop()
                    
                    cv_text_for_matching = "\n\n=====\n\n".join(cv_texts)
                
                excel_data = auto_excel_data
                
                cv_matching_system_prompt = get_cv_matching_prompt()
                
                matching_prompt = (
                    f"Project Description:\n\n{project_description}\n\n"
                    f"CV Data:\n\n{cv_text_for_matching}"
                )
                
                if excel_data:
                    matching_prompt += f"\n\nExcel Data:\n{excel_data}"
                
                response = backend.generate_response(
                    prompt=matching_prompt,
                    model=selected_model,
                    system_prompt=cv_matching_system_prompt
                )
                
                st.session_state.last_matching_result = response
                
                cv_json = None
                if PDF_GENERATION_AVAILABLE:
                    cv_json = extract_json_from_response(response, debug=debug_mode)
                    if cv_json:
                        st.session_state.extracted_cv_json = cv_json
                
                st.markdown("### Matching Results:")
                st.markdown(f'<div class="response-container">{response}</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error during CV matching: {str(e)}")
                if debug_mode:
                    import traceback
                    st.markdown(f'<div class="error-message">{traceback.format_exc()}</div>', unsafe_allow_html=True)

if "extracted_cv_json" in st.session_state and PDF_GENERATION_AVAILABLE:
    with st.expander("Extracted Customized CV (JSON)", expanded=True):
        cv_json = st.session_state.extracted_cv_json
        st.markdown("The following JSON CV data was extracted from the AI response:")
        st.markdown(f'<div class="json-code">{json.dumps(cv_json, indent=2)}</div>', unsafe_allow_html=True)
        
        json_str = json.dumps(cv_json, indent=2)
        st.download_button(
            label="Download JSON CV",
            data=json_str,
            file_name=f"{cv_json.get('name', 'cv').replace(' ', '_')}_generated.json",
            mime="application/json"
        )
        
        if st.button("Generate PDF CV"):
            try:
                with st.spinner("Generating PDF CV..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        pdf_path = create_cv_pdf(cv_json, tmp_file.name, debug=debug_mode)
                        
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_data = pdf_file.read()
                        
                        employee_name = cv_json.get('name', 'cv').replace(' ', '_')
                        permanent_path = os.path.join(pdf_dir, f"{employee_name}_CV.pdf")
                        create_cv_pdf(cv_json, permanent_path, debug=debug_mode)
                        
                        st.success(f"PDF CV generated successfully")
                        st.download_button(
                            label="Download PDF CV",
                            data=pdf_data,
                            file_name=f"{employee_name}_CV.pdf",
                            mime="application/pdf"
                        )
            except Exception as e:
                error_msg = str(e)
                st.error(f"Error generating PDF: {error_msg}")
                if debug_mode:
                    import traceback
                    st.markdown(f'<div class="error-message">{traceback.format_exc()}</div>', unsafe_allow_html=True)
                    st.info("Try running the script from the command line with: python json_to_pdf.py --input your_json_file.json --debug")

if "last_matching_result" in st.session_state:
    st.download_button(
        label="Download Matching Results",
        data=st.session_state.last_matching_result,
        file_name="cv_matching_results.txt",
        mime="text/plain"
    )
