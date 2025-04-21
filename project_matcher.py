import pandas as pd
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def load_project_data(excel_file_path):

    try:
        df = pd.read_excel(excel_file_path)
        
        if 'Projekte' not in df.columns:
            project_columns = [col for col in df.columns if 'projekt' in col.lower()]
            if not project_columns:
                raise ValueError("No 'Projekte' column or similar found in the Excel file")
            project_column = project_columns[0]
        else:
            project_column = 'Projekte'
        
        name_columns = ['Name', 'Mitarbeiter', 'Employee', 'Vollständiger Name']
        name_column = None
        for col in name_columns:
            if col in df.columns:
                name_column = col
                break
        
        if not name_column:
            for col in df.columns:
                if any(name in col.lower() for name in ['name', 'mitarbeiter', 'employee']):
                    name_column = col
                    break
        
        if not name_column:
            raise ValueError("No column containing employee names found in the Excel file")
        
        employee_projects = {}
        for _, row in df.iterrows():
            name = row[name_column]
            projects = row[project_column]
            
            if pd.isna(name) or pd.isna(projects):
                continue
                
            if not isinstance(projects, str):
                projects = str(projects)
                
            employee_projects[name] = projects
            
        return employee_projects
    
    except Exception as e:
        print(f"Error loading project data: {str(e)}")
        return {}

def extract_technologies_from_text(text):

    technologies = [
        "Java", "Spring", "Spring Boot", "Hibernate", "JPA", "JBoss", "Wildfly", "Tomcat",
        "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js", "Express",
        "PHP", "Laravel", "Symfony", "CodeIgniter", "WordPress",
        "Python", "Django", "Flask", "FastAPI",
        "C#", ".NET", "ASP.NET", "Entity Framework",
        "Ruby", "Ruby on Rails",
        "Go", "Rust", "Kotlin",
        "HTML", "CSS", "SCSS", "SASS", "Bootstrap", "Tailwind",
        "MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQL Server", "SQLite", "Redis",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Firebase",
        "REST", "SOAP", "GraphQL", "gRPC",
        "Git", "SVN", "Jenkins", "CircleCI", "GitHub Actions",
        "Jira", "Confluence", "Trello",
        "jQuery", "Redux", "MobX", "Next.js", "Nuxt.js", "Gatsby",
        "Nginx", "Apache", "Webpack", "Babel", "ESLint",
        "Android", "iOS", "React Native", "Flutter", "Xamarin", "Swift", "Objective-C",
        "WebSockets", "OAuth", "JWT", "SAML", "OpenID Connect"
    ]
    
    found_technologies = []
    text_lower = text.lower()
    
    for tech in technologies:
        pattern = r'\b' + re.escape(tech.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_technologies.append(tech)
    
    return found_technologies

def calculate_similarity(text1, text2):
    text1 = re.sub(r'[^\w\s]', ' ', text1.lower())
    text2 = re.sub(r'[^\w\s]', ' ', text2.lower())
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    except:
        return 0

def match_project_with_past_projects(project_description, min_similarity=0.6):
    excel_file_path = os.path.join("excel", "TimelessSoft_Mitarbeiter_Projektematrix.xlsx")
    
    if not os.path.exists(excel_file_path):
        print(f"Excel file not found at: {excel_file_path}")
        for alt_path in ["./excel/TimelessSoft_Mitarbeiter_Projektematrix.xlsx", "/workspace/excel/TimelessSoft_Mitarbeiter_Projektematrix.xlsx"]:
            if os.path.exists(alt_path):
                excel_file_path = alt_path
                print(f"Found Excel file at alternative path: {excel_file_path}")
                break
        else:
            print("Excel file not found at any expected location.")
            return {}
    
    employee_projects = load_project_data(excel_file_path)
    
    project_technologies = extract_technologies_from_text(project_description)
    
    matches = {}
    
    for employee, projects in employee_projects.items():
        similarity = calculate_similarity(project_description, projects)
        
        past_project_technologies = extract_technologies_from_text(projects)
        
        if project_technologies and past_project_technologies:
            common_technologies = set(project_technologies).intersection(set(past_project_technologies))
            technology_overlap = len(common_technologies) / len(project_technologies) if project_technologies else 0
            
            similarity = (similarity * 0.7) + (technology_overlap * 0.3)
        
        if similarity >= min_similarity:
            matches[employee] = {
                'projects': projects,
                'similarity': similarity,
                'common_technologies': list(common_technologies) if 'common_technologies' in locals() else []
            }
    
    sorted_matches = {k: v for k, v in sorted(matches.items(), 
                                              key=lambda item: item[1]['similarity'], 
                                              reverse=True)}
    
    return sorted_matches

def enhance_matching_results(matching_results, past_project_matches):
    if not past_project_matches:
        return matching_results
    
    past_projects_section = "\n\n### SIMILAR PAST PROJECTS MATCH\n\n"
    past_projects_section += "The following employees have worked on similar projects:\n\n"
    
    for employee, match_info in past_project_matches.items():
        similarity_percentage = round(match_info['similarity'] * 100, 1)
        past_projects_section += f"- **{employee}** - {similarity_percentage}% similarity\n"
        
        if 'common_technologies' in match_info and match_info['common_technologies']:
            common_tech = ", ".join(match_info['common_technologies'])
            past_projects_section += f"  Common technologies: {common_tech}\n"
            
        past_projects_section += f"  Past projects: {match_info['projects'][:300]}...\n\n"
    
    past_projects_section += "\n**Note on Skills Matching:** Employees with very similar past projects (60%+ similarity) receive a +10% bonus to their skills match percentage, as they have demonstrated practical experience with similar requirements.\n"
    
    enhanced_results = matching_results + past_projects_section
    
    return enhanced_results

def get_past_projects_for_prompt(project_description, min_similarity=0.4):
    past_project_matches = match_project_with_past_projects(project_description, min_similarity)
    
    if not past_project_matches:
        return ""
    
    past_projects_data = "\n\n### PAST PROJECT EXPERIENCE\n\n"
    past_projects_data += "The following employees have relevant past project experience:\n\n"
    
    for employee, match_info in past_project_matches.items():
        similarity_percentage = round(match_info['similarity'] * 100, 1)
        past_projects_data += f"- {employee}: {similarity_percentage}% project similarity\n"
        
        past_projects_data += f"  Projects: {match_info['projects'][:500]}...\n\n"
    
    return past_projects_data