#!/usr/bin/env python3


import os
import sys
import json
import argparse
import tempfile
from openai_backend import OpenAIBackend
from cv_matching_prompt import get_cv_matching_prompt
from json_to_pdf import extract_json_from_response, create_cv_pdf

def process_project_match(project_description, cv_data, model="gpt-4o-mini", debug=False):

    try:
        backend = OpenAIBackend()
        
        if debug:
            print("Matching project with CVs...")
            
        cv_matching_system_prompt = get_cv_matching_prompt()
        
        matching_prompt = (
            f"Project Description:\n\n{project_description}\n\n"
            f"CV Data:\n\n{cv_data}"
        )
        
        response = backend.generate_response(
            prompt=matching_prompt,
            model=model,
            system_prompt=cv_matching_system_prompt
        )
        
        if debug:
            print("Response received. Extracting JSON data...")
            
        cv_json_list = extract_json_from_response(response, debug=debug)
        
        if cv_json_list:
            if debug:
                print(f"Found {len(cv_json_list)} suitable employee(s).")
        else:
            print("No suitable employees found or could not extract JSON data.")
            
        return response, cv_json_list
    except Exception as e:
        print(f"Error processing match: {str(e)}")
        if debug:
            import traceback
            print(traceback.format_exc())
        return None, None

def load_cv_json_data(json_dir):
    import glob
    
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
            print(f"Error loading {os.path.basename(json_file)}: {str(e)}")
    
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

def extract_text_from_pdf(pdf_file):
    import PyPDF2
    
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""

def load_cv_pdf_data(cv_dir):
    import glob
    
    cv_files = glob.glob(f"{cv_dir}/*.pdf")
    
    if not cv_files:
        return "No PDF CV files found."
    
    cv_texts = []
    for cv_file in cv_files:
        try:
            with open(cv_file, "rb") as f:
                cv_text = extract_text_from_pdf(f)
                if cv_text:
                    cv_texts.append(f"File: {os.path.basename(cv_file)}\n\n{cv_text}")
                else:
                    print(f"Could not extract text from {os.path.basename(cv_file)}")
        except Exception as e:
            print(f"Error processing {os.path.basename(cv_file)}: {str(e)}")
    
    if not cv_texts:
        return "Failed to extract text from any CV files."
    
    return "\n\n=====\n\n".join(cv_texts)

def main():
    parser = argparse.ArgumentParser(description="Process project descriptions and match with employee CVs")
    parser.add_argument("--project", "-p", help="Path to project description file")
    parser.add_argument("--project_text", "-t", help="Project description text")
    parser.add_argument("--cv_json_dir", "-j", default="/workspace/CV_json", help="Directory containing JSON CV files")
    parser.add_argument("--cv_pdf_dir", "-c", default="/workspace/CV_data", help="Directory containing PDF CV files")
    parser.add_argument("--output_dir", "-o", default="/workspace/CV_pdf", help="Output directory for PDF files")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="OpenAI model to use (gpt-4o-mini or gpt-4)")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    project_description = None
    if args.project:
        if not os.path.exists(args.project):
            print(f"Error: Project file {args.project} does not exist")
            return 1
            
        try:
            with open(args.project, 'r', encoding='utf-8') as f:
                project_description = f.read()
        except Exception as e:
            print(f"Error reading project file: {str(e)}")
            return 1
    elif args.project_text:
        project_description = args.project_text
    else:
        print("Error: Either --project or --project_text argument is required")
        return 1
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    cv_data = None
    cv_json_data, json_cv_text = load_cv_json_data(args.cv_json_dir)
    
    if cv_json_data:
        print(f"Using JSON CV data for matching ({len(cv_json_data)} CVs found)")
        cv_data = json_cv_text
    else:
        print("No JSON CV data found, trying PDF CVs...")
        cv_data = load_cv_pdf_data(args.cv_pdf_dir)
        
    if not cv_data or cv_data.startswith("No") or cv_data.startswith("Failed"):
        print("Error: No CV data found")
        return 1
    
    response, cv_json_list = process_project_match(
        project_description, 
        cv_data,
        model=args.model,
        debug=args.debug
    )
    
    if not response:
        print("Error: Failed to get a response from the model")
        return 1
    
    with open(os.path.join(args.output_dir, "cv_matching_results.txt"), "w", encoding="utf-8") as f:
        f.write(response)
    
    if not cv_json_list:
        print("No suitable employees found or could not extract JSON data")
        return 1
    
    for cv_json in cv_json_list:
        employee_name = cv_json.get('name', 'cv').replace(' ', '_')
        
        json_path = os.path.join(args.output_dir, f"{employee_name}_CV.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_json, f, indent=2)
        
        print(f"Saved JSON for {employee_name}")
        
        try:
            pdf_path = os.path.join(args.output_dir, f"{employee_name}_CV.pdf")
            create_cv_pdf(cv_json, pdf_path, debug=args.debug)
            print(f"Generated PDF for {employee_name}")
        except Exception as e:
            print(f"Error generating PDF for {employee_name}: {str(e)}")
            if args.debug:
                import traceback
                print(traceback.format_exc())
    
    print(f"Processing complete. Found {len(cv_json_list)} suitable employee(s).")
    print(f"Results saved to {args.output_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 