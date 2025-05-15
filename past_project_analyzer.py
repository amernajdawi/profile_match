import os
import pandas as pd
import glob
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai_backend import OpenAIBackend
from project_matching_prompt import get_project_matching_prompt

def extract_technologies_from_text(text):
    technologies = [
        "Java", "Spring", "Spring Boot", "Hibernate", "JPA", "JBoss", "Wildfly", "Tomcat",
        "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js", "Express",
        "PHP", "Laravel", "Symfony", "CodeIgniter", "WordPress",
        "Python", "Django", "Flask", "FastAPI",
        "C#", ".NET", "ASP.NET", "Entity Framework",
        "Ruby", "Ruby on Rails",
        "Go", "Rust", "Kotlin",
        "HTML", "HTML5", "CSS", "SCSS", "SASS", "Bootstrap", "Tailwind",
        "MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQL Server", "SQLite", "Redis", "MariaDB",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Firebase",
        "REST", "SOAP", "GraphQL", "gRPC", "REST-API", "API",
        "Git", "SVN", "Jenkins", "CircleCI", "GitHub", "GitHub Actions", "GitHub CI/CD", "GitLab",
        "Jira", "Confluence", "Trello", "DevOps", "Scrum", "Kanban", "Agile", "SAFe",
        "jQuery", "Redux", "MobX", "Next.js", "Nuxt.js", "Gatsby",
        "Nginx", "Apache", "Webpack", "Babel", "ESLint",
        "Android", "iOS", "React Native", "Flutter", "Xamarin", "Swift", "Objective-C",
        "WebSockets", "OAuth", "JWT", "SAML", "OpenID Connect", "Microservices", "CI/CD",
        "Magnolia", "AngularJS", "Bitbucket", "Cordova", "Shopware", "NodeJS", "JUnit",
        "JAVA", "SmartGWT", "Windows Server", "OpenCart", "xtCommerce", 
        "yii-Framework", "C#.NET", "Silverlight", "DSGVO", "Vaadin"
    ]
    
    found_technologies = []
    text_lower = text.lower()
    
    for tech in technologies:
        pattern = r'\b' + re.escape(tech.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_technologies.append(tech)
    
    return found_technologies

def load_projects_from_excel():
    excel_dir = "/workspace/excel"
    excel_files = glob.glob(f"{excel_dir}/*.xlsx") + glob.glob(f"{excel_dir}/*.xls")
    
    excel_files = [f for f in excel_files if not os.path.basename(f).startswith("~$")]
    
    if not excel_files:
        print("No Excel files found.")
        return []
    
    excel_file_path = excel_files[0]
    
    try:
        df = pd.read_excel(excel_file_path)
        
        if 'Projekte' not in df.columns:
            print("No 'Projekte' column found in Excel file.")
            return []
            
        project_rows = []
        tech_rows = []
        
        for i, row in df.iterrows():
            if pd.isna(row['Projekte']):
                continue
                
            if row['Projekte'].startswith('Eingesetzte Technologien:'):
                tech_rows.append(i)
            else:
                project_rows.append(i)
                
        projects = []
        
        for i in project_rows:
            project_name = df.iloc[i]['Projekte']
            
            if pd.isna(project_name) or len(str(project_name).strip()) == 0:
                continue
                
            tech_text = ""
            if i+1 in tech_rows:
                tech_text = df.iloc[i+1]['Projekte']
                if pd.isna(tech_text):
                    tech_text = ""
                    
            project_entry = {
                'name': project_name,
                'technologies_text': tech_text,
                'technologies': extract_technologies_from_text(f"{project_name} {tech_text}")
            }
            
            projects.append(project_entry)
            
        return projects
        
    except Exception as e:
        print(f"Error loading Excel data: {str(e)}")
        return []

def extract_matched_employees(matching_result):
    if not matching_result:
        return []
        
    # Regex pattern to find lines like:
    # - Christian Tu - 40% - ASP.NET, SharePoint, ...
    # Accommodates optional leading hyphen and whitespace.
    # Name capture is now more flexible: ([\w\s.-]+?)
    # Skills capture stops before a newline that is NOT immediately followed by a continuation of skills (e.g. indented list)
    # or a newline followed by another hyphen (next employee) or end of string or BARRIERS.
    pattern = r'^-?\s*([\w\s\'.-]+?)\s*-\s*(\d+)%\s*-\s*(.+?)(?=\n(?:\s*-\s*[\w\s\'-.]+\s*-|BARRIERS:|\Z)|\Z)'
    
    # Find all matches; re.MULTILINE allows ^ to match start of each line
    matches = re.findall(pattern, matching_result, re.MULTILINE | re.DOTALL)
    
    employees = []
    for match in matches:
        if len(match) >= 3:
            name = match[0].strip()
            # Further clean name if it was captured with a leading '-' from a previous version or error
            if name.startswith('-'):
                name = name[1:].strip()
            
            match_percentage = match[1].strip()
            skills = match[2].strip()
            
            employees.append({
                'name': name,
                'match_percentage': match_percentage,
                'skills': skills
            })
    
    return employees

def analyze_past_projects(project_description, min_similarity=0.6, matching_result=None):
    projects = load_projects_from_excel()
    
    if not projects:
        return "No past project data found in Excel files."
    
    matched_employees = []
    if matching_result:
        matched_employees = extract_matched_employees(matching_result)
    
    past_projects_data = ""
    project_counter = 1
    
    for project in projects:
        project_text = f"{project['name']}"
        if project['technologies_text']:
            project_text += f"\n{project['technologies_text']}"
            
        past_projects_data += f"### Project {project_counter}:\n{project_text}\n\n"
        project_counter += 1
    
    project_technologies = extract_technologies_from_text(project_description)
    tech_list = ", ".join(project_technologies)
    
    matched_employees_data = ""
    if matched_employees:
        matched_employees_data = "\n\nMATCHED EMPLOYEES:\n"
        for emp in matched_employees:
            matched_employees_data += f"- {emp['name']} - {emp['match_percentage']}% - {emp['skills']}\n"
    
    prompt = (
        f"Project Description:\n\n{project_description}\n\n"
        f"Extracted Technologies: {tech_list}\n"
        f"{matched_employees_data}\n"
        f"Past Projects Data:\n\n{past_projects_data}"
    )
    
    system_prompt = get_project_matching_prompt(minimum_similarity=int(min_similarity * 100))
    
    backend = OpenAIBackend()
    
    response = backend.generate_response(
        prompt=prompt,
        model="gpt-4o-mini",  
        system_prompt=system_prompt,
    )
    
    return response

def post_process_response(response, matched_employees):
    if not response:
        return response
    
    versatile_employees = []
    for line in response.split('\n'):
        if "Most versatile employees:" in line:
            employees_part = line.split(':', 1)[1].strip()
            versatile_employees = [name.strip() for name in employees_part.split(',')]
            break
    
    employee_names = []
    if versatile_employees:
        employee_names = versatile_employees
    elif matched_employees:
        employee_names = [emp["name"] for emp in matched_employees]
    
    if not employee_names:
        return response
    
    print(f"Employee names for distribution: {employee_names}")
    
    experience_levels = {}
    for emp in matched_employees:
        name = emp["name"]
        years_match = re.search(r'(\d+)\+\s*Jahre', emp.get("skills", ""))
        if years_match:
            years = int(years_match.group(1))
            experience_levels[name] = years
        else:
            experience_levels[name] = 4
    
    print(f"Experience levels: {experience_levels}")
    
    lines = response.split('\n')
    detected_projects = []
    
    for i, line in enumerate(lines):
        if any(pattern in line for pattern in ["Project ", "### Project "]) and " : " in line:
            detected_projects.append(i)
    
    if len(detected_projects) < 4:
        for i, line in enumerate(lines):
            if i not in detected_projects:
                if ("project" in line.lower() or "Project" in line) and (" : " in line or " - " in line):
                    detected_projects.append(i)
    
    if len(detected_projects) < 4:
        print("Using looser pattern to find more projects...")
        for i, line in enumerate(lines):
            if i not in detected_projects and len(line.strip()) > 10:
                if any(tech in line for tech in ["Java", "Spring", "Web", "Application", "Software", "Development"]):
                    detected_projects.append(i)
                    if len(detected_projects) >= 4:
                        break
    
    print(f"Found {len(detected_projects)} projects: {detected_projects}")
    
    if not detected_projects:
        return response
    
    num_projects = len(detected_projects)
    distribution = {}
    
    sorted_employees = sorted(employee_names, key=lambda x: experience_levels.get(x, 0), reverse=True)
    
    for emp in employee_names:
        distribution[emp] = 1
    
    remaining_projects = num_projects - len(employee_names)
    employee_idx = 0
    while remaining_projects > 0 and employee_idx < len(sorted_employees):
        distribution[sorted_employees[employee_idx]] += 1
        remaining_projects -= 1
        employee_idx = (employee_idx + 1) % len(sorted_employees)
    
    total_assigned = sum(distribution.values())
    if total_assigned > num_projects:
        for emp in sorted(employee_names, key=lambda x: experience_levels.get(x, 0)):
            if distribution[emp] > 0:
                distribution[emp] -= 1
                total_assigned -= 1
                if total_assigned <= num_projects:
                    break
    
    print(f"Project distribution based on experience: {distribution}")
    
    project_assignments = {}  
    assignment_list = []
    for emp, count in distribution.items():
        for _ in range(count):
            assignment_list.append(emp)
    
    while len(assignment_list) < num_projects:
        assignment_list.append(employee_names[len(assignment_list) % len(employee_names)])
    
    for idx, project_idx in enumerate(detected_projects):
        if idx < len(assignment_list):
            employee = assignment_list[idx]
            
            line = lines[project_idx]
            
            if ' : ' in line:
                project_part = line.split(' : ')[0]
                lines[project_idx] = f"{project_part} : {employee}"
            else:
                project_match = re.match(r'(### Project \d+ - .+?) (-|:)', line)
                if project_match:
                    project_part = project_match.group(1)
                    lines[project_idx] = f"{project_part} : {employee}"
                else:
                    lines[project_idx] = f"{line} : {employee}"
                
            project_assignments[idx] = employee
    
    json_start_index = response.find('```json')
    json_end_index = response.find('```', json_start_index + 6) if json_start_index != -1 else -1
    
    if json_start_index != -1 and json_end_index != -1:
        json_content = response[json_start_index + 7:json_end_index].strip()
        
        try:
            json_data = json.loads(json_content)
            
            project_technologies = {}
            for i, line in enumerate(lines):
                if i > 0 and "Technologies Used:" in line:
                    for proj_idx in detected_projects:
                        if proj_idx < i and (i - proj_idx) < 10:  
                            proj_line = lines[proj_idx]
                            proj_match = re.search(r'Project\s+(\d+)', proj_line)
                            if proj_match:
                                proj_num = int(proj_match.group(1))
                                tech_text = line.replace("Technologies Used:", "").strip()
                                
                                if proj_num not in project_technologies:
                                    project_technologies[proj_num] = {}
                                
                                project_technologies[proj_num]["all_techs"] = [t.strip() for t in tech_text.split(",")]
                            break
            
            if "projects" in json_data and isinstance(json_data["projects"], list):
                for i, project in enumerate(json_data["projects"]):
                    if i < len(assignment_list):
                        project["assigned_employee"] = assignment_list[i]
                        
                        if "project_number" in project and "enhanced_technologies" in project:
                            for tech in project.get("enhanced_technologies", []):
                                if tech not in project["technologies_used"]:
                                    project["technologies_used"].append(tech)
                
                if "summary" in json_data:
                    enhanced_count = sum(1 for p in json_data["projects"] if "enhanced_technologies" in p and p["enhanced_technologies"])
                    json_data["summary"]["enhanced_projects_count"] = enhanced_count
                
                updated_json = json.dumps(json_data, indent=2)
                updated_response = response[:json_start_index + 7] + '\n' + updated_json + '\n' + response[json_end_index:]
                lines = updated_response.split('\n')
            
            else:
                project_details = {}
                in_project_section = False
                current_project = None
                
                for i, line in enumerate(lines):
                    if re.search(r'### Project (\d+)', line):
                        in_project_section = True
                        match = re.search(r'Project (\d+) - (.+?)(?:\s+:|$)', line)
                        if match:
                            proj_num = int(match.group(1))
                            proj_name = match.group(2).strip()
                            
                            similarity = 90
                            
                            current_project = {
                                "number": proj_num,
                                "name": proj_name,
                                "similarity": similarity,
                                "techs_used": [],
                                "matching_techs": [],
                                "enhanced_techs": [],
                                "enhanced_similarity": 90,
                                "description": ""
                            }
                            project_details[proj_num] = current_project
                    
                    elif in_project_section and current_project:
                        if "Technologies Used:" in line:
                            techs = line.split(":", 1)[1].strip()
                            current_project["techs_used"] = [t.strip() for t in techs.split(",")]
                        elif "Matching Technologies:" in line:
                            techs = line.split(":", 1)[1].strip()
                            current_project["matching_techs"] = [t.strip() for t in techs.split(",")]
                        elif "Project Description:" in line:
                            desc = line.split(":", 1)[1].strip()
                            current_project["description"] = desc
                
                for i, emp in enumerate(employee_names):
                    patterns = [
                        f'[Employee {i+1} Name from Matched CVs]',
                        f'[Employee {i+1} Name]',
                        f'Employee {i+1}',
                        f'[Different Employee Name from Matched CVs]'
                    ]
                    
                    for pattern in patterns:
                        json_content = json_content.replace(pattern, emp)
                
                employee_to_projects = {}
                for idx, employee in project_assignments.items():
                    if idx < len(detected_projects):
                        project_idx = detected_projects[idx]
                        project_line = lines[project_idx]
                        match = re.search(r'Project (\d+)', project_line)
                        if match:
                            proj_num = int(match.group(1))
                            if proj_num in project_details:
                                if employee not in employee_to_projects:
                                    employee_to_projects[employee] = []
                                employee_to_projects[employee].append(project_details[proj_num])
                
                remaining_placeholders = [
                    '[Employee Name from Matched CVs]',
                    '[Employee Name]',
                    '[Different Employee Name]'
                ]
                
                emp_idx = 0
                for placeholder in remaining_placeholders:
                    while placeholder in json_content:
                        name = employee_names[emp_idx % len(employee_names)]
                        json_content = json_content.replace(placeholder, name, 1)
                        emp_idx += 1
                
                for proj_num, details in project_details.items():
                    json_content = json_content.replace(f'"project_number": [#]', f'"project_number": {details["number"]}', 1)
                    
                    json_content = json_content.replace(f'"project_name": "[Project Name]"', f'"project_name": "{details["name"]}"', 1)
                    
                    json_content = json_content.replace(f'"similarity": [Original Similarity %]', f'"similarity": {details["similarity"]}', 1)
                    
                    tech_used_json = json.dumps(details["techs_used"])
                    json_content = json_content.replace(f'"technologies_used": ["Tech1", "Tech2", ...]', f'"technologies_used": {tech_used_json}', 1)
                    
                    matching_tech_json = json.dumps(details["matching_techs"])
                    json_content = json_content.replace(f'"matching_technologies": ["Tech1", "Tech2", ...]', f'"matching_technologies": {matching_tech_json}', 1)
                    
                    json_content = json_content.replace(f'"enhanced_technologies": ["Additional Tech1", "Additional Tech2", ...]', 
                                                  f'"enhanced_technologies": []', 1)
                    
                    json_content = json_content.replace(f'"enhanced_similarity": [Enhanced Similarity %]', 
                                                 f'"enhanced_similarity": {details["enhanced_similarity"]}', 1)
                    
                    json_content = json_content.replace(f'"description": "[Brief description of the project]"', 
                                                  f'"description": "{details["description"]}"', 1)
                
                json_content = re.sub(r'//.*$', '', json_content, flags=re.MULTILINE)
                
                updated_response = response[:json_start_index + 7] + '\n' + json_content + '\n' + response[json_end_index:]
                lines = updated_response.split('\n')
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {str(e)}")
            for i, emp in enumerate(employee_names):
                patterns = [
                    f'[Employee {i+1} Name from Matched CVs]',
                    f'[Employee {i+1} Name]',
                    f'Employee {i+1}',
                    f'[Different Employee Name from Matched CVs]'
                ]
                
                for pattern in patterns:
                    json_content = json_content.replace(pattern, emp)
            
            remaining_placeholders = [
                '[Employee Name from Matched CVs]',
                '[Employee Name]',
                '[Different Employee Name]'
            ]
            
            emp_idx = 0
            for placeholder in remaining_placeholders:
                while placeholder in json_content:
                    name = employee_names[emp_idx % len(employee_names)]
                    json_content = json_content.replace(placeholder, name, 1)
                    emp_idx += 1
            
            json_content = re.sub(r'//.*$', '', json_content, flags=re.MULTILINE)
            
            updated_response = response[:json_start_index + 7] + '\n' + json_content + '\n' + response[json_end_index:]
            lines = updated_response.split('\n')
    
    return '\n'.join(lines) 