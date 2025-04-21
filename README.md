# CV Matching System

A system that matches CVs with project requirements to identify suitable candidates.

## Features

- **CV Processing**: Convert PDF CVs to structured JSON format
- **Project Matching**: Match project requirements with team CVs
- **Past Project Analysis**: Match new project requirements with employees' past projects
- **CV Enhancement**: Generate customized CVs for qualified candidates
- **PDF Generation**: Create PDF CVs
- **Web Interface**:  Streamlit interface

## Main Components

- `app.py` - Streamlit web application (web interface)
- `cv_to_json.py` - Converts PDF CVs to JSON format (for using them in the app)
- `cv_matching_prompt.py` - AI prompt for matching CVs to projects 
- `process_cv_matches.py` - Backend logic for CV matching
- `project_matcher.py` - Analyzes similarity between new projects and past projects
- `json_to_pdf.py` - Converts CV JSON data to formatted PDF files (step will be after LLM Model)
- `openai_backend.py` - Handles OpenAI API interactions

## How to Use

1. Place CV PDFs in the `CV_data` directory
2. Run `python cv_to_json.py` to convert them to JSON
3. Ensure your past project data is in an Excel file in the `excel` directory with a "Projekte" column
4. Start the application with `docker compose up` in CMD or Terminal 
5. In web interface enter your project description `http://localhost:8501/`
6. Set the minimum match percentage (default: 70%) and past project similarity (default: 60%)
7. Click "Match Project with Team CVs"
8. View results and download generated PDFs

## Requirements

- OpenAI API key (set in `.env` file) and the LLM model (gpt-4o-mini)

## Directory Structure

- `CV_data/` - PDF CV files
- `CV_json/` - JSON CV data
- `CV_pdf/` - Generated PDF files
- `excel/` - Reference project data and past project history

## process_cv_matches.py

The `process_cv_matches.py` file is a key component of the CV Matching System that handles the backend logic for matching CVs with project requirements.

### What it Does:
- Takes a project description and CV data as input.
- Uses the OpenAI API (via `openai_backend.py`) to analyze the project description and match it against the CVs.

### Main Functions:
- `process_project_match()`: Sends the project description and CV data to the AI model and gets back matching results.
- `load_cv_json_data()`: Loads CV data from JSON files in the `CV_json` directory.
- `extract_text_from_pdf()`: Extracts text from PDF files.
- `load_cv_pdf_data()`: Loads CV data from PDF files in the `CV_data` directory.

### Process Flow:
After receiving responses from the AI model, it extracts the JSON data of matching candidates.

For each matching candidate:
- Saves the CV data as JSON.
- Generates a formatted PDF CV using `json_to_pdf.py`.

---

This file can be:
- Run as a standalone script to process matches from the command line.
- Imported and used by the web application (`app.py`).
