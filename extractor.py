import os
from openai import OpenAI

from models import ExtractedSkills
import dotenv
dotenv.load_dotenv()

class SkillExtractor:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") if api_key is None else api_key)

    def extract_skills_from_text(self, text: str) -> ExtractedSkills:
        """
        Extract technologies and skills from academic document text.

        Args:
            text: The text content of the academic document

        Returns:
            ExtractedSkills: Structured object containing categorized skills
        """

        system_prompt = """
        You are an expert in analyzing academic documents and extracting professional skills in a format suitable for job portals like pracuj.pl.
        Your task is to analyze the syllabus/course description and extract:
        
        1. TECHNOLOGIES: Specific, well-known technologies, programming languages, tools, software
           - Extract ONLY concrete, recognizable technology names
           - Examples: "Python", "R", "MATLAB", "Microsoft Project", "SQL", "Java", "Docker", "Azure", "Git"
           - Avoid generic descriptions like "data analysis tools" - be specific
           - If you see "Python libraries for data analysis", extract "Python" and relevant specific libraries if mentioned
           - Categories: Programming Language, Cloud Platform, Database, Framework, DevOps Tool, Software, etc.
           
        2. SOFT SKILLS: Professional competencies and behavioral skills
           - Extract clear, concise skill names that would appear on job offers
           - Examples: "Analytical thinking", "Team collaboration", "Project management", "Problem solving"
           - Avoid overly academic language - make it practical and job-relevant
           - Focus on transferable skills valuable in the workplace
           
        Be precise and extract only skills that are clearly mentioned or strongly implied in the text.
        Categorize technologies by their actual type (Programming Language, Cloud Platform, etc.).
        Make skill names concise and professional - as they would appear on pracuj.pl job offers.
        """

        user_prompt = f"""
        Analyze the following academic syllabus text and extract all technologies and skills in a job-portal format:
        
        {text}
        """

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4.1-nano",  # DONT CHANGE THIS!!!
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=ExtractedSkills,
                temperature=0.1,  # Low temperature for consistent results
            )

            return response.choices[0].message.parsed

        except Exception as e:
            print(f"Error processing text: {e}")
            return ExtractedSkills(
                technologies=[], soft_skills=[], document_title="Error"
            )
