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
import subprocess
from openai_backend import OpenAIBackend
from cv_matching_prompt import get_cv_matching_prompt
from past_project_analyzer import analyze_past_projects, extract_matched_employees, post_process_response

try:
    from json_to_pdf import create_cv_pdf, extract_json_from_response

    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False
    st.warning(
        "PDF generation functionality is not available. Please install reportlab package."
    )

def extract_json_from_analysis(analysis_text):
    json_pattern = r'```json\s*(.*?)```'
    match = re.search(json_pattern, analysis_text, re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
        try:
            json_data = json.loads(json_str)
            return json_data
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON: {str(e)}")
            return None
    
    return None

def save_employee_json_files(json_data):
    if not json_data or 'employees' not in json_data:
        return []
    
    os.makedirs("employee_projects", exist_ok=True)
    file_paths = []
    
    for employee in json_data['employees']:
        if 'name' not in employee:
            continue
            
        employee_name = employee['name']
        safe_name = re.sub(r'[^\w\s-]', '', employee_name).strip().replace(' ', '_')
        
        file_path = f"employee_projects/{safe_name}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(employee, f, ensure_ascii=False, indent=2)
            
        file_paths.append(file_path)
        
    return file_paths

def generate_employee_project_pdfs(json_data=None, json_files=None):
    try:
        if os.path.isfile("/workspace/employee_projects_to_pdf.py"):
            pdf_paths = []
            
            if json_data and 'employees' in json_data:
                temp_json_path = "/workspace/temp_employee_projects.json"
                with open(temp_json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                command = f"python3 /workspace/employee_projects_to_pdf.py --input {temp_json_path}"
                process = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if process.returncode != 0:
                    st.error(f"Error generating PDFs: {process.stderr}")
                    return []
                
                for line in process.stdout.splitlines():
                    if line.strip().endswith(".pdf"):
                        pdf_paths.append(line.strip())
                
                if os.path.exists(temp_json_path):
                    os.remove(temp_json_path)
                    
            elif json_files:
                for json_file in json_files:
                    base_name = os.path.basename(json_file).replace('.json', '')
                    pdf_path = f"employee_projects_pdf/{base_name}_projects.pdf"
                    if os.path.exists(pdf_path):
                        pdf_paths.append(pdf_path)
            
            return pdf_paths
        else:
            st.warning("employee_projects_to_pdf.py script not found. PDF generation not available.")
            return []
    except Exception as e:
        st.error(f"Error generating employee project PDFs: {str(e)}")
        return []

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
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    except Exception:
        return str(os.path.getmtime(file_path))


def get_directory_hash(directory, pattern="*"):
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

past_project_min_similarity = st.number_input(
    "Minimum past project similarity (%):",
    min_value=50,
    max_value=90,
    value=60,
    step=5,
    help="Only past projects with at least this percentage similarity to the current project requirements will be considered.",
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
                
                # Analyze past projects
                if past_project_min_similarity > 0:
                    with st.spinner("Analyzing past projects..."):
                        try:
                            # Pass the CV matching results to the past project analyzer
                            past_project_analysis = analyze_past_projects(
                                project_description, 
                                min_similarity=past_project_min_similarity/100.0,
                                matching_result=response
                            )
                            
                            # Add debug output to show what's happening
                            st.info(f"Raw past project analysis result received. Length: {len(past_project_analysis) if past_project_analysis else 0}")
                            
                            if past_project_analysis and "No past project data found" not in past_project_analysis:
                                # Extract matched employees from the CV matching results
                                matched_employees = extract_matched_employees(response)
                                
                                # Add debug output for matched employees
                                st.info(f"Matched employees extracted: {len(matched_employees) if matched_employees else 0}")
                                if matched_employees:
                                    st.info(f"Employee names: {', '.join([emp['name'] for emp in matched_employees])}")
                                
                                # Fall back to hard-coded employees if none found
                                if not matched_employees or len(matched_employees) == 0:
                                    st.warning("No employees found in the CV matching response. Cannot proceed with employee assignment for past project analysis.")
                                    st.info("Please try again with a different project description or check your CV data and the AI's output format.")
                                    
                                    # Display the raw response for debugging this specific error
                                    st.markdown("### Raw CV Matching Response (for debugging 'Matched employees extracted: 0'):")
                                    st.text_area(
                                        "CV Matching AI Output:", 
                                        value=response, 
                                        height=300,
                                        key="debug_cv_matching_response_for_extraction_error"
                                    )
                                    st.stop()  # Stop execution of the current app run
                                
                                # Post-process the response to add matched employees to each project
                                past_project_analysis = post_process_response(past_project_analysis, matched_employees)
                                
                                # Extract JSON from response
                                json_data = extract_json_from_analysis(past_project_analysis)
                                
                                if json_data:
                                    # Save individual JSON files for each employee
                                    file_paths = save_employee_json_files(json_data)
                                    
                                    # Display information about created files
                                    if file_paths:
                                        st.success(f"Created {len(file_paths)} employee JSON files:")
                                        
                                        # Generate PDF files for each employee
                                        pdf_paths = generate_employee_project_pdfs(json_data=json_data)
                                        
                                        # Create columns for JSON and PDF downloads
                                        for i, path in enumerate(file_paths):
                                            col1, col2 = st.columns(2)
                                            
                                            # Display JSON file info and download button
                                            with col1:
                                                st.code(path)
                                                with open(path, 'r') as f:
                                                    file_content = f.read()
                                                
                                                employee_name = os.path.basename(path).replace('.json', '').replace('_', ' ')
                                                st.download_button(
                                                    label=f"Download {employee_name}'s JSON",
                                                    data=file_content,
                                                    file_name=os.path.basename(path),
                                                    mime="application/json"
                                                )
                                            
                                            with col2:
                                                pdf_path = f"employee_projects_pdf/{os.path.basename(path).replace('.json', '_projects.pdf')}"
                                                
                                                if os.path.exists(pdf_path):
                                                    st.code(pdf_path)
                                                    with open(pdf_path, 'rb') as f:
                                                        pdf_content = f.read()
                                                    
                                                    st.download_button(
                                                        label=f"Download {employee_name}'s PDF",
                                                        data=pdf_content,
                                                        file_name=os.path.basename(pdf_path),
                                                        mime="application/pdf"
                                                    )
                                else:
                                    st.warning("No JSON data found in the response. Check if the AI correctly formatted the output.")
                                
                                st.session_state.past_project_analysis = past_project_analysis
                                st.success(f"Past project analysis completed with {len(matched_employees)} employees distributed across matching projects")
                                
                            else:
                                st.warning("No similar past projects found or no project data available")
                                st.code(past_project_analysis[:500] + "..." if past_project_analysis and len(past_project_analysis) > 500 else past_project_analysis)
                                
                        except Exception as e:
                            st.error(f"Error analyzing past projects: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                            st.info("Proceeding with CV matching results only.")

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

if "past_project_analysis" in st.session_state:
    st.markdown("### Past Project Analysis:")
    st.markdown(
        f'<div class="response-container">{st.session_state.past_project_analysis}</div>',
        unsafe_allow_html=True,
    )
    
    st.download_button(
        label="Download Past Project Analysis",
        data=st.session_state.past_project_analysis,
        file_name="past_project_analysis.txt",
        mime="text/plain",
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
                    # Check if the AI explicitly stated no employees met the threshold
                    no_match_message_pattern = r"No employees meet the required \\d+% skills match for customized CV generation\\."
                    if re.search(no_match_message_pattern, st.session_state.last_matching_result):
                        st.info(f"No employees met the {min_match_percentage}% skills match threshold for customized CV generation.")
                    else:
                        st.warning(
                            "No CV data could be extracted from the response. This could be due to formatting issues in the AI response, or no employees meeting the threshold without explicit notification."
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
