from pydantic import BaseModel, Field
from typing import List
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class TechnologySkill(BaseModel):
    name: str = Field(description="Specific technology name (e.g., 'Python', 'Docker', 'Azure', 'Kubernetes')")
    category: str = Field(description="Technology category like 'Programming Language', 'Cloud Platform', 'DevOps Tool', 'Database', 'Framework', etc.")

class SoftSkill(BaseModel):
    name: str = Field(description="Soft skill name (e.g., 'Problem solving', 'Team collaboration', 'Communication')")
    description: str = Field(description="Brief description of the skill context")

class ExtractedSkills(BaseModel):
    technologies: List[TechnologySkill] = Field(description="List of technical skills and technologies")
    soft_skills: List[SoftSkill] = Field(description="List of soft skills and competencies")
    document_title: str = Field(description="Title or subject name from the document")
