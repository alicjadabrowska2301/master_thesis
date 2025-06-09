import json
from pathlib import Path
from typing import Dict, List, Set
from loguru import logger

from extractor import SkillExtractor
from models import ExtractedSkills, TechnologySkill, SoftSkill


class SkillDeduplicator:
    """Helper class to deduplicate skills across multiple documents."""
    
    def __init__(self):
        self.unique_technologies: Dict[str, TechnologySkill] = {}
        self.unique_soft_skills: Dict[str, SoftSkill] = {}
        self.document_titles: List[str] = []
    
    def add_extracted_skills(self, skills: ExtractedSkills) -> None:
        """Add skills from a document to the deduplicated collection."""
        
        # Add document title
        if skills.document_title and skills.document_title != "Error":
            self.document_titles.append(skills.document_title)
        
        # Deduplicate technologies by name (case-insensitive)
        for tech in skills.technologies:
            tech_key = tech.name.lower().strip()
            if tech_key and tech_key not in self.unique_technologies:
                self.unique_technologies[tech_key] = tech
        
        # Deduplicate soft skills by name (case-insensitive)
        for skill in skills.soft_skills:
            skill_key = skill.name.lower().strip()
            if skill_key and skill_key not in self.unique_soft_skills:
                self.unique_soft_skills[skill_key] = skill
    
    def get_deduplicated_skills(self) -> ExtractedSkills:
        """Return the deduplicated skills as an ExtractedSkills object."""
        return ExtractedSkills(
            technologies=list(self.unique_technologies.values()),
            soft_skills=list(self.unique_soft_skills.values()),
            document_title=f"Combined skills from {len(self.document_titles)} documents"
        )


def process_markdown_files(output_dir: Path) -> ExtractedSkills:
    """
    Process all markdown files in the output directory and extract skills.
    
    Args:
        output_dir: Path to the directory containing markdown files
        
    Returns:
        ExtractedSkills: Deduplicated skills from all documents
    """
    
    # Initialize the skill extractor
    extractor = SkillExtractor()
    deduplicator = SkillDeduplicator()
    
    # Get all markdown files
    md_files = list(output_dir.glob("*.md"))
    
    if not md_files:
        logger.warning(f"No markdown files found in {output_dir}")
        return ExtractedSkills(technologies=[], soft_skills=[], document_title="No documents found")
    
    logger.info(f"Found {len(md_files)} markdown files to process")
    
    # Process each markdown file
    for md_file in md_files:
        logger.info(f"Processing {md_file.name}")
        
        try:
            # Read the markdown content
            content = md_file.read_text(encoding="utf-8")
            
            # Extract skills using the SkillExtractor
            extracted_skills = extractor.extract_skills_from_text(content)
            
            # Set document title from filename if not extracted
            if not extracted_skills.document_title or extracted_skills.document_title == "Error":
                extracted_skills.document_title = md_file.stem
            
            # Add to deduplicator
            deduplicator.add_extracted_skills(extracted_skills)
            
            logger.success(f"Extracted {len(extracted_skills.technologies)} technologies and {len(extracted_skills.soft_skills)} soft skills from {md_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to process {md_file.name}: {e}")
            continue
    
    # Get deduplicated results
    final_skills = deduplicator.get_deduplicated_skills()
    
    logger.info(f"Final results after deduplication:")
    logger.info(f"  - {len(final_skills.technologies)} unique technologies")
    logger.info(f"  - {len(final_skills.soft_skills)} unique soft skills")
    
    return final_skills


def save_to_json(skills: ExtractedSkills, output_file: Path) -> None:
    """
    Save the extracted skills to a JSON file.
    
    Args:
        skills: The extracted and deduplicated skills
        output_file: Path where to save the JSON file
    """
    
    # Convert Pydantic models to dictionaries
    skills_dict = skills.model_dump()
    
    # Pretty print JSON with proper formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(skills_dict, f, ensure_ascii=False, indent=2)
    
    logger.success(f"Skills saved to {output_file}")


def main():
    """
    Main function to process markdown files and extract skills to JSON.
    """
    
    # Define paths
    output_dir = Path("output")
    json_output_file = Path("extracted_skills.json")
    
    # Check if output directory exists
    if not output_dir.exists():
        logger.error(f"Output directory '{output_dir}' not found. Please run the main.py script first to generate markdown files.")
        return
    
    try:
        # Process all markdown files and extract skills
        logger.info("Starting skill extraction from markdown files...")
        final_skills = process_markdown_files(output_dir)
        
        # Save results to JSON
        save_to_json(final_skills, json_output_file)
        
        # Print summary
        print("\n" + "="*50)
        print("SKILL EXTRACTION SUMMARY")
        print("="*50)
        print(f"Documents processed: {len(list(output_dir.glob('*.md')))}")
        print(f"Unique technologies found: {len(final_skills.technologies)}")
        print(f"Unique soft skills found: {len(final_skills.soft_skills)}")
        print(f"Results saved to: {json_output_file}")
        print("="*50)
        
        # Print some examples
        if final_skills.technologies:
            print(f"\nSample technologies:")
            for tech in final_skills.technologies[:5]:
                print(f"  - {tech.name} ({tech.category})")
            if len(final_skills.technologies) > 5:
                print(f"  ... and {len(final_skills.technologies) - 5} more")
        
        if final_skills.soft_skills:
            print(f"\nSample soft skills:")
            for skill in final_skills.soft_skills[:5]:
                print(f"  - {skill.name} ({skill.description})")
            if len(final_skills.soft_skills) > 5:
                print(f"  ... and {len(final_skills.soft_skills) - 5} more")
        
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise


if __name__ == "__main__":
    main()