#!/usr/bin/env python3

import os
import json
import argparse
import re
import traceback
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import HRFlowable, ListFlowable, ListItem

DEFAULT_OUTPUT_DIR = "CV_pdf"

def create_cv_pdf(json_data, output_path, debug=False):

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if debug:
            print(f"Creating PDF at {output_path}")
            print(f"JSON data: {json.dumps(json_data, indent=2)}")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = getSampleStyleSheet()
        
        style_defs = {
            'Name': ParagraphStyle(
                name='Name',
                fontSize=18,
                leading=22,
                textColor=colors.darkblue,
                spaceAfter=0.3*cm
            ),
            'SectionTitle': ParagraphStyle(
                name='SectionTitle',
                fontSize=14,
                leading=16,
                textColor=colors.darkblue,
                spaceBefore=0.5*cm,
                spaceAfter=0.3*cm
            ),
            'SubTitle': ParagraphStyle(
                name='SubTitle',
                fontSize=12,
                leading=14,
                textColor=colors.black,
                spaceBefore=0.2*cm,
                spaceAfter=0.1*cm
            ),
            'CVNormal': ParagraphStyle(
                name='CVNormal',
                fontSize=10,
                leading=12,
                spaceAfter=0.1*cm,
                parent=styles['Normal']
            )
        }
        
        for style_name, style in style_defs.items():
            try:
                styles.add(style)
            except KeyError:
                if debug:
                    print(f"Style '{style_name}' already exists, updating")
                styles[style_name] = style
        
        elements = []
        
        if "name" not in json_data:
            if debug:
                print("Warning: No name found in JSON data")
            json_data["name"] = "CV"
        
        name = json_data["name"]
        name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(name, styles['Name']))
        
        contact_info = []
        if "contact" in json_data:
            contact = json_data["contact"]
            if "phone" in contact:
                contact_info.append(f"Phone: {contact['phone']}")
            if "email" in contact:
                contact_info.append(f"Email: {contact['email']}")
            if "address" in contact:
                contact_info.append(f"Address: {contact['address']}")
        
        contact_text = " | ".join(contact_info)
        elements.append(Paragraph(contact_text, styles['CVNormal']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue, spaceBefore=0.3*cm, spaceAfter=0.3*cm))
        
        if "education" in json_data:
            elements.append(Paragraph("EDUCATION", styles['SectionTitle']))
            edu = json_data["education"]
            if isinstance(edu, dict):
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                years = edu.get('years', '')
                
                degree = str(degree).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                institution = str(institution).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                years = str(years).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                edu_text = f"<b>{degree}</b>"
                if institution:
                    edu_text += f", {institution}"
                if years:
                    edu_text += f" ({years})"
                elements.append(Paragraph(edu_text, styles['CVNormal']))
            elements.append(Spacer(1, 0.3*cm))
        
        if "reference_projects" in json_data and json_data["reference_projects"]:
            elements.append(Paragraph("REFERENCE PROJECTS", styles['SectionTitle']))
            
            for project in json_data["reference_projects"]:
                project_name = str(project.get('name', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                client = str(project.get('client', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                description = str(project.get('description', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                project_text = f"<b>{project_name}</b>"
                if client:
                    project_text += f" for {client}"
                
                elements.append(Paragraph(project_text, styles['SubTitle']))
                
                if description:
                    elements.append(Paragraph(description, styles['CVNormal']))
                
                if "technologies" in project and project["technologies"]:
                    tech_list = [str(tech).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") 
                               for tech in project["technologies"]]
                    tech_text = "Technologies: " + ", ".join(tech_list)
                    elements.append(Paragraph(tech_text, styles['CVNormal']))
                
                elements.append(Spacer(1, 0.2*cm))
            
            elements.append(Spacer(1, 0.1*cm))
        
        if "work_experience" in json_data and json_data["work_experience"]:
            elements.append(Paragraph("WORK EXPERIENCE", styles['SectionTitle']))
            
            for job in json_data["work_experience"]:
                role = str(job.get('role', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                company = str(job.get('company', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                location = str(job.get('location', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                years = str(job.get('years', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                job_title = f"<b>{role}</b>"
                if company:
                    job_title += f", {company}"
                if location:
                    job_title += f" - {location}"
                if years:
                    job_title += f" ({years})"
                
                elements.append(Paragraph(job_title, styles['SubTitle']))
                
                if "responsibilities" in job and job["responsibilities"]:
                    resp_items = []
                    for resp in job["responsibilities"]:
                        resp_text = str(resp).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        resp_items.append(ListItem(Paragraph(resp_text, styles['CVNormal'])))
                    
                    bullet_list = ListFlowable(
                        resp_items,
                        bulletType='bullet',
                        start='•',
                        bulletFontSize=10,
                        leftIndent=20
                    )
                    elements.append(bullet_list)
                
                if "reference_projects" in job and job["reference_projects"]:
                    elements.append(Paragraph("<b>Project Experience:</b>", styles['CVNormal']))
                    
                    for project in job["reference_projects"]:
                        project_name = str(project.get('name', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        client = str(project.get('client', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        description = str(project.get('description', '')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        
                        project_text = f"<b>{project_name}</b>"
                        if client:
                            project_text += f" for {client}"
                        
                        elements.append(Paragraph(project_text, styles['CVNormal']))
                        
                        if description:
                            elements.append(Paragraph(description, styles['CVNormal']))
                        
                        if "technologies" in project and project["technologies"]:
                            tech_list = [str(tech).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") 
                                        for tech in project["technologies"]]
                            tech_text = "Technologies: " + ", ".join(tech_list)
                            elements.append(Paragraph(tech_text, styles['CVNormal']))
                        
                        elements.append(Spacer(1, 0.1*cm))
                
                elements.append(Spacer(1, 0.2*cm))
        
        if "technical_skills" in json_data and json_data["technical_skills"]:
            elements.append(Paragraph("TECHNICAL SKILLS", styles['SectionTitle']))
            
            skills = json_data["technical_skills"]
            for skill_category, description in skills.items():
                if skill_category != "Added Skills":  # Handle added skills separately
                    category = str(skill_category).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    desc = str(description).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    elements.append(Paragraph(f"<b>{category}:</b> {desc}", styles['CVNormal']))
            
            if "Added Skills" in skills:
                added_skills = str(skills["Added Skills"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                elements.append(Paragraph("<b>Added Skills:</b> " + added_skills, styles['CVNormal']))
            
            elements.append(Spacer(1, 0.3*cm))
        
        if "soft_skills" in json_data and json_data["soft_skills"]:
            elements.append(Paragraph("SOFT SKILLS", styles['SectionTitle']))
            soft_skills = [str(skill).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") 
                           for skill in json_data["soft_skills"]]
            soft_skills_text = ", ".join(soft_skills)
            elements.append(Paragraph(soft_skills_text, styles['CVNormal']))
            elements.append(Spacer(1, 0.3*cm))
        
        if "languages" in json_data and json_data["languages"]:
            elements.append(Paragraph("LANGUAGES", styles['SectionTitle']))
            languages = [str(lang).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") 
                         for lang in json_data["languages"]]
            languages_text = ", ".join(languages)
            elements.append(Paragraph(languages_text, styles['CVNormal']))
        
        if debug:
            print(f"Building PDF with {len(elements)} elements")
        
        doc.build(elements)
        if debug:
            print(f"PDF created successfully at {output_path}")
        
        return output_path
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        print(traceback.format_exc())
        raise

def extract_json_from_response(response_text, debug=False):

    try:
        if debug:
            print("Extracting JSON from response text")
            print(f"Response text (first 100 chars): {response_text[:100]}...")
        

        employee_cv_pattern = r'CUSTOMIZED CV FOR ([^\n"]+?)[\s\n]*```json\s*([\s\S]*?)\s*```'
        matches = re.findall(employee_cv_pattern, response_text, re.DOTALL)
        
        if matches and len(matches) > 0:
            if debug:
                print(f"Found {len(matches)} employee CVs in the response")
            
            all_cv_data = []
            for employee_name, json_str in matches:
                try:
                    json_str = json_str.strip()
                    cv_data = json.loads(json_str)
                    if "name" not in cv_data or not cv_data["name"]:
                        cv_data["name"] = employee_name.strip()
                    all_cv_data.append(cv_data)
                    if debug:
                        print(f"Extracted CV data for {employee_name}")
                except json.JSONDecodeError as e:
                    if debug:
                        print(f"Error parsing JSON for {employee_name}: {e}")
                        print(f"JSON string: {json_str[:100]}...")
            
            if all_cv_data:
                return all_cv_data
        
        alt_cv_pattern = r'### CUSTOMIZED CV FOR ([^\n"]+?)[\s\n]*```json\s*([\s\S]*?)\s*```'
        alt_matches = re.findall(alt_cv_pattern, response_text, re.DOTALL)
        
        if alt_matches and len(alt_matches) > 0:
            if debug:
                print(f"Found {len(alt_matches)} employee CVs with alternative pattern")
            
            all_cv_data = []
            for employee_name, json_str in alt_matches:
                try:
                    json_str = json_str.strip()
                    cv_data = json.loads(json_str)
                    if "name" not in cv_data or not cv_data["name"]:
                        cv_data["name"] = employee_name.strip()
                    all_cv_data.append(cv_data)
                    if debug:
                        print(f"Extracted CV data for {employee_name}")
                except json.JSONDecodeError as e:
                    if debug:
                        print(f"Error parsing JSON for {employee_name}: {e}")
            
            if all_cv_data:
                return all_cv_data
        
        json_pattern = r'```json\s*(.*?)\s*```'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            if debug:
                print(f"Found JSON block between markers: {json_str[:100]}...")
            try:
                return [json.loads(json_str)]
            except json.JSONDecodeError as e:
                if debug:
                    print(f"Error parsing JSON from markers: {e}")
                    print(f"Full JSON string: {json_str}")
        
        cv_section_pattern = r'CUSTOMIZED CV FOR PROJECT[\s\S]*?```json\s*(.*?)\s*```'
        cv_section_match = re.search(cv_section_pattern, response_text, re.DOTALL)
        
        if cv_section_match:
            json_str = cv_section_match.group(1)
            if debug:
                print(f"Found JSON in CUSTOMIZED CV section: {json_str[:100]}...")
            try:
                return [json.loads(json_str)]
            except json.JSONDecodeError as e:
                if debug:
                    print(f"Error parsing JSON from CV section: {e}")
        
        try:
            json_pattern = r'({[\s\S]*})'
            json_match = re.search(json_pattern, response_text)
            if json_match:
                json_str = json_match.group(1)
                if debug:
                    print(f"Found JSON object directly: {json_str[:100]}...")
                try:
                    parsed = json.loads(json_str)
                    if "name" in parsed and ("contact" in parsed or "education" in parsed or "work_experience" in parsed):
                        return [parsed]
                except Exception as e:
                    if debug:
                        print(f"Error parsing direct JSON object: {e}")
        except json.JSONDecodeError:
            if debug:
                print("Could not parse direct JSON object")
        
        if debug:
            print("Could not extract valid JSON from the response")
        return None
    except Exception as e:
        print(f"Error in extract_json_from_response: {str(e)}")
        if debug:
            import traceback
            print(traceback.format_exc())
        return None

def main():
    parser = argparse.ArgumentParser(description="Convert JSON CV data to PDF")
    parser.add_argument("--input", "-i", help="Path to JSON file containing CV data")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory for PDF files")
    parser.add_argument("--response", "-r", help="Path to text file containing LLM model response")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    debug = args.debug
    
    os.makedirs(args.output, exist_ok=True)
    
    json_data = None
    
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: File {args.input} does not exist")
            return 1
            
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return 1
    elif args.response:
        if not os.path.exists(args.response):
            print(f"Error: File {args.response} does not exist")
            return 1
            
        try:
            with open(args.response, 'r', encoding='utf-8') as f:
                response_text = f.read()
                json_data = extract_json_from_response(response_text, debug=debug)
        except Exception as e:
            print(f"Error processing response file: {str(e)}")
            return 1
    else:
        print("Error: Either --input or --response argument is required")
        return 1
    
    if json_data is None:
        print("Error: Could not load JSON data")
        return 1
    
    if "name" in json_data:
        name = json_data["name"].replace(" ", "_")
        output_file = f"{name}_CV.pdf"
    else:
        output_file = f"CV_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    output_path = os.path.join(args.output, output_file)
    
    try:
        pdf_path = create_cv_pdf(json_data, output_path, debug=debug)
        print(f"Successfully created PDF CV at {pdf_path}")
        return 0
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    main() 