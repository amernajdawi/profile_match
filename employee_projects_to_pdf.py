#!/usr/bin/env python3

import os
import json
import argparse
import traceback
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import HRFlowable, ListFlowable, ListItem

DEFAULT_OUTPUT_DIR = "employee_projects_pdf"

def create_employee_project_pdf(employee_data, output_path, debug=False):
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if debug:
            print(f"Creating PDF at {output_path}")
            print(f"Employee data: {json.dumps(employee_data, indent=2)}")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = getSampleStyleSheet()
        
        name_style = ParagraphStyle(
            name='NameStyle',
            fontSize=18,
            leading=22,
            textColor=colors.darkblue,
            spaceAfter=0.3*cm
        )
        
        section_title_style = ParagraphStyle(
            name='SectionTitleStyle',
            fontSize=14,
            leading=16,
            textColor=colors.darkblue,
            spaceBefore=0.5*cm,
            spaceAfter=0.3*cm
        )
        
        project_title_style = ParagraphStyle(
            name='ProjectTitleStyle',
            fontSize=12,
            leading=14,
            textColor=colors.darkblue,
            spaceBefore=0.2*cm,
            spaceAfter=0.1*cm
        )
        
        normal_style = ParagraphStyle(
            name='NormalStyle',
            fontSize=10,
            leading=12,
            spaceAfter=0.1*cm,
            parent=styles['Normal']
        )
        
        elements = []
        
        employee_name = employee_data.get("name", "Employee")
        elements.append(Paragraph(employee_name, name_style))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue, spaceBefore=0.3*cm, spaceAfter=0.3*cm))
        
        elements.append(Paragraph("ASSIGNED PROJECTS", section_title_style))
        
        if "projects" in employee_data and employee_data["projects"]:
            for project in employee_data["projects"]:
                project_number = project.get("project_number", "")
                project_name = project.get("project_name", "Unnamed Project")
                similarity = project.get("enhanced_similarity", project.get("similarity", 0))
                technologies_used = project.get("technologies_used", [])
                matching_technologies = project.get("matching_technologies", [])
                description = project.get("description", "")
                
                enhanced_technologies = project.get("enhanced_technologies", [])
                if enhanced_technologies:
                    for tech in enhanced_technologies:
                        if tech not in technologies_used:
                            technologies_used.append(tech)
                
                project_title = f"Project {project_number} - {project_name}"
                elements.append(Paragraph(project_title, project_title_style))
                
                if description:
                    elements.append(Paragraph(f"<b>Description:</b> {description}", normal_style))
                
                if technologies_used:
                    tech_text = f"<b>Technologies Used:</b> {', '.join(technologies_used)}"
                    elements.append(Paragraph(tech_text, normal_style))
                
                elements.append(Spacer(1, 0.5*cm))
        else:
            elements.append(Paragraph("No projects assigned.", normal_style))
        
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

def process_employee_json_files(directory="employee_projects", output_dir=DEFAULT_OUTPUT_DIR, debug=False):
    os.makedirs(output_dir, exist_ok=True)
    
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    
    if debug:
        print(f"Found {len(json_files)} JSON files in {directory}")
    
    pdf_paths = []
    
    for json_file in json_files:
        try:
            file_path = os.path.join(directory, json_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                employee_data = json.load(f)
            
            employee_name = employee_data.get("name", "employee").replace(" ", "_")
            output_path = os.path.join(output_dir, f"{employee_name}_projects.pdf")
            
            pdf_path = create_employee_project_pdf(employee_data, output_path, debug=debug)
            pdf_paths.append(pdf_path)
            
            if debug:
                print(f"Created PDF for {employee_name} at {pdf_path}")
            
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
            if debug:
                print(traceback.format_exc())
    
    return pdf_paths

def process_json_data(json_data, output_dir=DEFAULT_OUTPUT_DIR, debug=False):
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_paths = []
    
    if "employees" not in json_data:
        print("Error: JSON data does not contain 'employees' field")
        return pdf_paths
    
    for employee in json_data["employees"]:
        try:
            employee_name = employee.get("name", "employee").replace(" ", "_")
            output_path = os.path.join(output_dir, f"{employee_name}_projects.pdf")
            
            pdf_path = create_employee_project_pdf(employee, output_path, debug=debug)
            pdf_paths.append(pdf_path)
            
            if debug:
                print(f"Created PDF for {employee_name} at {pdf_path}")
            
        except Exception as e:
            print(f"Error processing employee {employee.get('name', 'unknown')}: {str(e)}")
            if debug:
                print(traceback.format_exc())
    
    return pdf_paths

def main():
    parser = argparse.ArgumentParser(description="Convert employee project data to PDF")
    parser.add_argument("--input", "-i", help="Path to JSON file containing employee project data")
    parser.add_argument("--directory", "-d", default="employee_projects", help="Directory containing employee JSON files")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory for PDF files")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    debug = args.debug
    
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: File {args.input} does not exist")
            return 1
            
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            pdf_paths = process_json_data(json_data, output_dir=args.output, debug=debug)
            
            if pdf_paths:
                print(f"Successfully created {len(pdf_paths)} PDF files:")
                for path in pdf_paths:
                    print(f"  - {path}")
                return 0
            else:
                print("No PDF files were created.")
                return 1
                
        except Exception as e:
            print(f"Error processing JSON file: {str(e)}")
            if debug:
                print(traceback.format_exc())
            return 1
    else:
        if not os.path.exists(args.directory):
            print(f"Error: Directory {args.directory} does not exist")
            return 1
            
        pdf_paths = process_employee_json_files(directory=args.directory, output_dir=args.output, debug=debug)
        
        if pdf_paths:
            print(f"Successfully created {len(pdf_paths)} PDF files:")
            for path in pdf_paths:
                print(f"  - {path}")
            return 0
        else:
            print("No PDF files were created.")
            return 1

if __name__ == "__main__":
    main() 