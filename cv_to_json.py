
import os
import sys
import json
import re
import argparse
import glob
from datetime import datetime
import PyPDF2

DEFAULT_OUTPUT_DIR = "CV_json"

def extract_text_from_pdf(pdf_path):

    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {str(e)}")
        return ""

def convert_cv_to_json(pdf_path):

    try:
        file_name = os.path.basename(pdf_path).replace('.pdf', '')
        
        cv_text = extract_text_from_pdf(pdf_path)
        
        if not cv_text:
            print(f"Warning: Could not extract text from {pdf_path}")
            return None
        
        cv_data = {
            "filename": os.path.basename(pdf_path),
            "name": file_name,
            "raw_text": cv_text,
            "extracted_at": datetime.now().isoformat()
        }
        
        sections = {}
        
        # Common CV section headers
        possible_sections = [
            "education", "experience", "work experience", "skills", 
            "certifications", "languages", "projects", "summary",
            "professional experience", "technical skills", "contact",
            "personal information", "objective", "achievements", "training"
        ]
        
        for section in possible_sections:
            pattern = re.compile(f"(?i){section}[:\s]*(.+?)(?=(?:{('|').join(possible_sections)})[:\s]|$)", re.DOTALL)
            match = pattern.search(cv_text)
            if match:
                sections[section.lower()] = match.group(1).strip()
        
        cv_data["sections"] = sections
        
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        emails = email_pattern.findall(cv_text)
        if emails:
            cv_data["emails"] = emails
        
        phone_pattern = re.compile(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        phones = phone_pattern.findall(cv_text)
        if phones:
            cv_data["phones"] = phones
        
        return cv_data
    
    except Exception as e:
        print(f"Error converting {pdf_path} to JSON: {str(e)}")
        return None

def save_cv_as_json(cv_data, output_dir):

    try:
        os.makedirs(output_dir, exist_ok=True)
        
        file_name = cv_data["filename"].replace(".pdf", ".json")
        output_path = os.path.join(output_dir, file_name)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving JSON: {str(e)}")
        return None

def process_directory(input_dir, output_dir):

    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} does not exist")
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return []
    
    print(f"Found {len(pdf_files)} PDF files in {input_dir}")
    
    results = []
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file}...")
        cv_data = convert_cv_to_json(pdf_file)
        if cv_data:
            json_path = save_cv_as_json(cv_data, output_dir)
            if json_path:
                results.append(json_path)
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Convert PDF CVs to JSON format")
    parser.add_argument("--input", "-i", default="CV_data", help="Input directory with PDF files")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory for JSON files")
    parser.add_argument("--file", "-f", help="Process a single PDF file instead of a directory")
    
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} does not exist")
            return 1
            
        print(f"Processing single file: {args.file}")
        cv_data = convert_cv_to_json(args.file)
        if cv_data:
            json_path = save_cv_as_json(cv_data, args.output)
            if json_path:
                print(f"Conversion completed successfully. JSON saved to {json_path}")
                return 0
        
        print("Conversion failed")
        return 1
    else:
        results = process_directory(args.input, args.output)
        
        if results:
            print(f"\nConversion completed. {len(results)} JSON files saved to {args.output}")
            return 0
        else:
            print("No files were converted successfully")
            return 1

if __name__ == "__main__":
    sys.exit(main()) 