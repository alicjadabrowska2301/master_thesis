from markitdown import MarkItDown
from loguru import logger
from pathlib import Path
import re

def extract_polish_content(text):
    """
    Extracts the 'treść' column content from the 'Przedmiotowe efekty uczenia się' section
    for every syllabus item in the Polish document.
    """
    # Regex to find all occurrences of the "Przedmiotowe efekty uczenia się" section
    # and capture the content until the next major section.
    syllabus_sections = re.findall(r'Przedmiotowe efekty uczenia się\s*(.*?)(?=\nTreści programowe zapewniające uzyskanie efektów uczenia się|\Z)', text, re.DOTALL)
    
    extracted_data = []
    for section in syllabus_sections:
        # This updated regex is more robust. Instead of matching headers, it directly
        # finds the content between the 'PEU' code (start of the row) and the 'K2_IZ'
        # code (start of the next column), which is a more reliable pattern.
        contents = re.findall(r'PEU[ _]?[WUK]\d+\s*(.*?)(?=\s*K2[ _]?IZ)', section, re.DOTALL)
        for content in contents:
            # Clean up the captured content by removing potential junk characters
            # like quotes and commas from the start and end, and normalizing whitespace.
            cleaned_content = content.strip().strip('",')
            cleaned_content = ' '.join(cleaned_content.split())

            if cleaned_content:
                extracted_data.append(cleaned_content)
    
    return "\n\n".join(extracted_data)

def extract_english_content(text):
    """
    Extracts the 'Content' from the 'Subject's learning outcomes' tables in the English document.
    """
    # Regex to find all "Subject's learning outcomes" sections and their content
    # until the next major section heading.
    learning_outcomes_sections = re.findall(r"Subject's learning outcomes\s*(.*?)(?=\nProgram content ensuring learning outcomes|\Z)", text, re.DOTALL)
    
    extracted_data = []
    for section in learning_outcomes_sections:
        # Regex to find the content under the "Content" column for each outcome.
        # This regex looks for a PEU code, then lazily captures all characters
        # until it finds a K2_IZ code, which is robust to formatting variations.
        contents = re.findall(r"PEU_\w+\d+\s*(.*?)(?=\s*K2[ _]?IZ)", section, re.DOTALL)
        for content in contents:
            # Clean up the captured content by removing potential junk characters
            # like quotes and commas from the start and end, and normalizing whitespace.
            cleaned_content = content.strip().strip('",')
            cleaned_content = ' '.join(cleaned_content.split())

            if cleaned_content:
                extracted_data.append(cleaned_content)
                
    return "\n\n".join(extracted_data)

def main():
    """
    Main function to process PDF files in the input directory, convert them to markdown,
    and write the results to the output directory.
    """
    md = MarkItDown()
    input_dir = Path("input")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Ensure input directory exists
    if not input_dir.exists():
        logger.warning(f"Input directory '{input_dir}' not found. Creating it.")
        input_dir.mkdir()
        logger.info("Please add your PDF files to the 'input' directory and run the script again.")
        return

    for file in input_dir.iterdir():
        if file.suffix.lower() == '.pdf':
            logger.info(f"Processing {file.name}")
            try:
                # Convert the entire PDF to text first
                result = md.convert(file)
                full_text = result.text_content
                
                # Determine the language and apply the correct extraction function
                if "Przedmiotowe efekty uczenia się" in full_text:
                    logger.info(f"Detected Polish document. Extracting specific content.")
                    extracted_text = extract_polish_content(full_text)
                elif "Subject's learning outcomes" in full_text:
                    logger.info(f"Detected English document. Extracting specific content.")
                    extracted_text = extract_english_content(full_text)
                else:
                    logger.warning(f"Could not determine the document type for {file.name}. Skipping specific extraction.")
                    extracted_text = full_text

                # Write the extracted text to the output file
                output_file = output_dir / f"{file.stem}.md"
                output_file.write_text(extracted_text, encoding="utf-8")
                logger.success(f"Converted {file.name} -> {output_file.name}")

            except Exception as e:
                logger.error(f"Failed to process {file.name}. Error: {e}")

if __name__ == "__main__":
    main()
