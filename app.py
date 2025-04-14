import streamlit as st
import os
import io
import glob
import pandas as pd
import PyPDF2
import json
import re
import tempfile
import hashlib
from openai_backend import OpenAIBackend
from cv_matching_prompt import get_cv_matching_prompt

try:
    from json_to_pdf import create_cv_pdf, extract_json_from_response

    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False
    st.warning(
        "PDF generation functionality is not available. Please install reportlab package."
    )

backend = OpenAIBackend()

st.set_page_config(
    page_title="CV Matcher",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
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
        color: #333333;
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
    h2, h3, h4, h5, h6, p, li, span, label {
        color: #333333;
    }
    /* All text in Streamlit elements should have proper contrast */
    .stMarkdown, .stText, .stCode, .stTextArea, .stTextInput, .stButton, 
    .stSelectbox, .stRadio, .stCheckbox, .stMultiselect, .stDateInput, 
    .stTimeInput, .stNumberInput, .stFileUploader, .stDownloadButton {
        color: #333333;
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
        color: #333333;
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
    .stTabs [data-baseweb="tab-panel"] {
        color: #333333;
    }
    .stTable, table, td, th, tr {
        color: #333333;
    }
    .stDownloadButton button {
        color: #333333;
    }
    .stTabs [data-baseweb="tab-list"] {
        color: #333333;
    }
    .stTabs [data-baseweb="tab-panel"] p, 
    .stTabs [data-baseweb="tab-panel"] span,
    .stTabs [data-baseweb="tab-panel"] div {
        color: #333333;
    }
    button, .stButton button {
        color: #333333;
    }
</style>
""",
    unsafe_allow_html=True,
)

default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
selected_model = "gpt-4o-mini"
temperature = 0.7
debug_mode = False

st.title("📄 CV Matching System")
st.subheader("Match project requirements with team CVs")


def get_file_hash(file_path):
    """Generate a hash for a file to use in cache invalidation"""
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    except Exception:
        return str(os.path.getmtime(file_path))


def get_directory_hash(directory, pattern="*"):
    """Generate a hash based on files in a directory to use in cache invalidation"""
    if not os.path.exists(directory):
        return "directory_not_found"

    try:
        files = glob.glob(f"{directory}/{pattern}")
        files.sort()
        hash_content = "".join([f"{f}:{os.path.getmtime(f)}" for f in files])
        return hashlib.md5(hash_content.encode()).hexdigest()
    except Exception:
        return str(os.path.getmtime(directory) if os.path.exists(directory) else "0")


@st.cache_data
def extract_text_from_pdf(pdf_file, file_hash=None):
    """Extract text from PDF with caching"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""


@st.cache_data
def load_excel_data(directory_hash=None):
    """Load Excel data with cache invalidation based on directory hash"""
    excel_dir = "/workspace/excel"
    excel_files = glob.glob(f"{excel_dir}/*.xlsx") + glob.glob(f"{excel_dir}/*.xls")

    excel_files = [f for f in excel_files if not os.path.basename(f).startswith("~$")]

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


@st.cache_data
def load_cv_json_data(directory_hash=None):
    """Load CV JSON data with cache invalidation based on directory hash"""
    json_files = glob.glob(f"{json_dir}/*.json")

    if not json_files:
        return None, "No JSON CV files found."

    cv_json_data = []
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                cv_data = json.load(f)
                cv_json_data.append(cv_data)
        except Exception as e:
            st.error(f"Error loading {os.path.basename(json_file)}: {str(e)}")

    combined_text = ""
    for cv in cv_json_data:
        combined_text += f"===== CV: {cv['name']} =====\n\n"

        if "sections" in cv:
            for section_name, section_content in cv["sections"].items():
                combined_text += (
                    f"--- {section_name.upper()} ---\n{section_content}\n\n"
                )

        if "emails" in cv:
            combined_text += f"--- CONTACT ---\nEmail: {', '.join(cv['emails'])}\n"

        if "phones" in cv:
            combined_text += f"Phone: {', '.join(cv['phones'])}\n"

        combined_text += "\n\n"

    return cv_json_data, combined_text


cv_dir = "/workspace/CV_data"
json_dir = "/workspace/CV_json"
pdf_dir = "/workspace/CV_pdf"

os.makedirs(pdf_dir, exist_ok=True)

if not os.path.exists(cv_dir):
    st.warning(f"CV directory not found at {cv_dir}. Falling back to relative path.")
    cv_dir = "CV_data"

if not os.path.exists(json_dir):
    st.warning(
        f"JSON CV directory not found at {json_dir}. Falling back to relative path."
    )
    json_dir = "CV_json"

excel_dir_hash = get_directory_hash("/workspace/excel", "*.xls*")
cv_dir_hash = get_directory_hash(cv_dir, "*.pdf")
json_dir_hash = get_directory_hash(json_dir, "*.json")


@st.cache_data
def get_directory_files(directory, pattern):
    """Get list of files in directory with caching"""
    return glob.glob(f"{directory}/{pattern}")


cv_files = get_directory_files(cv_dir, "*.pdf")
json_files = get_directory_files(json_dir, "*.json")

excel_data_frames, auto_excel_data = load_excel_data(directory_hash=excel_dir_hash)
cv_json_data, json_cv_text = load_cv_json_data(directory_hash=json_dir_hash)

st.info(
    f"Data loaded from {json_dir} ({len(json_files)} files) and /workspace/excel ({len(excel_data_frames)} files)"
)

st.markdown("### Project Description")
st.markdown("Enter the project requirements to match against team CVs.")
project_description = st.text_area(
    "Project description:",
    height=200,
    placeholder="Paste the full project description here...",
    key="project_description",
)

min_match_percentage = st.number_input(
    "Minimum skills match percentage:",
    min_value=30,
    max_value=90,
    value=70,
    step=5,
    help="Only employees with at least this percentage of skills match will be considered feasible. CVs with match % between this value and 90% will be enhanced.",
)

col1, col2 = st.columns([3, 1])
with col2:
    selected_model = st.radio("AI Model", ["gpt-4o-mini", "gpt-4"], horizontal=True)


@st.cache_data
def read_all_cv_pdfs(directory_hash=None):
    """Read all CV PDFs with cache invalidation based on directory hash"""
    cv_texts = []
    files = get_directory_files(cv_dir, "*.pdf")
    for cv_file in files:
        try:
            with open(cv_file, "rb") as f:
                cv_text = extract_text_from_pdf(f, file_hash=get_file_hash(cv_file))
                if cv_text:
                    cv_texts.append(f"File: {os.path.basename(cv_file)}\n\n{cv_text}")
                else:
                    st.warning(
                        f"Could not extract text from {os.path.basename(cv_file)}"
                    )
        except Exception as e:
            st.error(f"Error processing {os.path.basename(cv_file)}: {str(e)}")

    return cv_texts


if st.button("Match Project with Team CVs", type="primary"):
    if not project_description:
        st.error("Please enter a project description.")
    elif len(cv_files) == 0 and len(json_files) == 0:
        st.error(
            f"No CV files found. Please upload some CVs first or convert PDFs to JSON."
        )
    else:
        with st.spinner(f"Analyzing CVs and matching with project requirements..."):
            try:
                if len(json_files) > 0 and cv_json_data:
                    st.info("Using JSON CV data for matching")
                    cv_text_for_matching = json_cv_text
                else:
                    st.info(
                        "Using PDF CV data for matching (consider converting to JSON for better performance)"
                    )
                    cv_texts = read_all_cv_pdfs(directory_hash=cv_dir_hash)

                    if not cv_texts:
                        st.error(
                            "Failed to extract text from any CV files. Please check the files and try again."
                        )
                        st.stop()

                    cv_text_for_matching = "\n\n=====\n\n".join(cv_texts)

                excel_data = auto_excel_data

                cv_matching_system_prompt = get_cv_matching_prompt(
                    minimum_match_percentage=min_match_percentage
                )

                matching_prompt = (
                    f"Project Description:\n\n{project_description}\n\n"
                    f"CV Data:\n\n{cv_text_for_matching}"
                )

                if excel_data:
                    matching_prompt += f"\n\nExcel Data:\n{excel_data}"

                response = backend.generate_response(
                    prompt=matching_prompt,
                    model=selected_model,
                    system_prompt=cv_matching_system_prompt,
                )

                st.session_state.last_matching_result = response

                st.markdown("### Matching Results:")
                st.markdown(
                    f'<div class="response-container">{response}</div>',
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.error(f"Error during CV matching: {str(e)}")
                if debug_mode:
                    import traceback

                    st.markdown(
                        f'<div class="error-message">{traceback.format_exc()}</div>',
                        unsafe_allow_html=True,
                    )

if "last_matching_result" in st.session_state:
    with st.spinner(f"Analyzing CVs and matching with project requirements..."):
        try:
            if PDF_GENERATION_AVAILABLE:
                enable_debug = st.checkbox(
                    "Enable debug mode for CV extraction", value=False
                )
                debug_for_extraction = debug_mode or enable_debug

                st.info("Extracting customized CVs from the response...")
                cv_json_list = extract_json_from_response(
                    st.session_state.last_matching_result, debug=debug_for_extraction
                )

                if cv_json_list and len(cv_json_list) > 0:
                    st.session_state.extracted_cv_json_list = cv_json_list
                    st.success(f"Found {len(cv_json_list)} suitable employee CV(s)")
                else:
                    st.warning(
                        "No CV data could be extracted from the response. This could be due to formatting issues in the AI response."
                    )

                    if debug_for_extraction:
                        st.markdown("### Response for debugging:")
                        st.text_area(
                            "Response text",
                            value=st.session_state.last_matching_result,
                            height=300,
                        )
        except Exception as e:
            st.error(f"Error extracting CV data: {str(e)}")
            if debug_mode:
                import traceback

                st.markdown(
                    f'<div class="error-message">{traceback.format_exc()}</div>',
                    unsafe_allow_html=True,
                )

if "extracted_cv_json_list" in st.session_state and PDF_GENERATION_AVAILABLE:
    cv_json_list = st.session_state.extracted_cv_json_list

    with st.expander("Extracted Customized CVs", expanded=True):
        if len(cv_json_list) > 1:
            tabs = st.tabs(
                [
                    cv_data.get("name", f"Employee {i+1}")
                    for i, cv_data in enumerate(cv_json_list)
                ]
            )

            for i, (tab, cv_json) in enumerate(zip(tabs, cv_json_list)):
                with tab:
                    st.markdown(
                        f"### {cv_json.get('name', f'Employee {i+1}')} CV Data:"
                    )
                    st.markdown(
                        f'<div class="json-code">{json.dumps(cv_json, indent=2)}</div>',
                        unsafe_allow_html=True,
                    )

                    json_str = json.dumps(cv_json, indent=2)
                    employee_name = cv_json.get("name", f"employee_{i+1}").replace(
                        " ", "_"
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label=f"Download {employee_name} JSON CV",
                            data=json_str,
                            file_name=f"{employee_name}_CV.json",
                            mime="application/json",
                        )

                    with col2:
                        pdf_button_key = f"gen_pdf_{i}"
                        if st.button(
                            f"Generate PDF CV for {employee_name}", key=pdf_button_key
                        ):
                            try:
                                with st.spinner(
                                    f"Generating PDF CV for {employee_name}..."
                                ):
                                    with tempfile.NamedTemporaryFile(
                                        delete=False, suffix=".pdf"
                                    ) as tmp_file:
                                        pdf_path = create_cv_pdf(
                                            cv_json,
                                            tmp_file.name,
                                            debug=(
                                                debug_mode
                                                or st.checkbox(
                                                    "Enable debug for PDF generation",
                                                    key=f"debug_pdf_{i}",
                                                )
                                            ),
                                        )

                                        with open(pdf_path, "rb") as pdf_file:
                                            pdf_data = pdf_file.read()

                                        permanent_path = os.path.join(
                                            pdf_dir, f"{employee_name}_CV.pdf"
                                        )
                                        create_cv_pdf(
                                            cv_json, permanent_path, debug=debug_mode
                                        )

                                        st.success(
                                            f"PDF CV for {employee_name} generated successfully"
                                        )
                                        st.download_button(
                                            label=f"Download {employee_name} PDF CV",
                                            data=pdf_data,
                                            file_name=f"{employee_name}_CV.pdf",
                                            mime="application/pdf",
                                        )
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"Error generating PDF: {error_msg}")
                                if debug_mode:
                                    import traceback

                                    st.markdown(
                                        f'<div class="error-message">{traceback.format_exc()}</div>',
                                        unsafe_allow_html=True,
                                    )
        else:
            cv_json = cv_json_list[0]
            st.markdown(
                "The following JSON CV data was extracted from the AI response:"
            )
            st.markdown(
                f'<div class="json-code">{json.dumps(cv_json, indent=2)}</div>',
                unsafe_allow_html=True,
            )

            json_str = json.dumps(cv_json, indent=2)
            employee_name = cv_json.get("name", "cv").replace(" ", "_")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download JSON CV",
                    data=json_str,
                    file_name=f"{employee_name}_CV.json",
                    mime="application/json",
                )

            with col2:
                if st.button("Generate PDF CV"):
                    try:
                        with st.spinner("Generating PDF CV..."):
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=".pdf"
                            ) as tmp_file:
                                pdf_path = create_cv_pdf(
                                    cv_json, tmp_file.name, debug=debug_mode
                                )

                                with open(pdf_path, "rb") as pdf_file:
                                    pdf_data = pdf_file.read()

                                permanent_path = os.path.join(
                                    pdf_dir, f"{employee_name}_CV.pdf"
                                )
                                create_cv_pdf(cv_json, permanent_path, debug=debug_mode)

                                st.success(f"PDF CV generated successfully")
                                st.download_button(
                                    label="Download PDF CV",
                                    data=pdf_data,
                                    file_name=f"{employee_name}_CV.pdf",
                                    mime="application/pdf",
                                )
                    except Exception as e:
                        error_msg = str(e)
                        st.error(f"Error generating PDF: {error_msg}")
                        if debug_mode:
                            import traceback

                            st.markdown(
                                f'<div class="error-message">{traceback.format_exc()}</div>',
                                unsafe_allow_html=True,
                            )
                            st.info(
                                "Try running the script from the command line with: python json_to_pdf.py --input your_json_file.json --debug"
                            )

        if len(cv_json_list) > 1:
            if st.button("Generate PDFs for All Employees", type="primary"):
                try:
                    with st.spinner("Generating PDFs for all employees..."):
                        pdf_paths = []
                        for cv_json in cv_json_list:
                            employee_name = cv_json.get("name", "cv").replace(" ", "_")
                            permanent_path = os.path.join(
                                pdf_dir, f"{employee_name}_CV.pdf"
                            )
                            create_cv_pdf(cv_json, permanent_path, debug=debug_mode)
                            pdf_paths.append(permanent_path)

                        st.success(f"Generated {len(pdf_paths)} PDF CVs successfully")
                        st.info(f"PDF files saved to {pdf_dir} directory")

                        st.markdown("### Generated PDF files:")
                        for path in pdf_paths:
                            filename = os.path.basename(path)
                            st.markdown(f"- {filename}")
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"Error generating PDFs: {error_msg}")
                    if debug_mode:
                        import traceback

                        st.markdown(
                            f'<div class="error-message">{traceback.format_exc()}</div>',
                            unsafe_allow_html=True,
                        )

if "last_matching_result" in st.session_state:
    st.download_button(
        label="Download Matching Results",
        data=st.session_state.last_matching_result,
        file_name="cv_matching_results.txt",
        mime="text/plain",
    )
