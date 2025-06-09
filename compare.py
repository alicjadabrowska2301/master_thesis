import json
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import torch
from tqdm import tqdm

# === CONFIGURATION ===
JOBS_PATH = "job_descriptions.json"
SKILLS_PATH = "extracted_skills.json"
OUTPUT_CSV = "job_skill_matches.csv"
SIMILARITY_THRESHOLD = 0.50
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # Multilingual
BATCH_SIZE = 64

# === LOAD JSON ===
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === MAIN SCRIPT ===
def main():
    # Load files
    jobs_data = load_json(JOBS_PATH)
    skills_data = load_json(SKILLS_PATH)

    # Prepare study-acquired skills (tech + soft)
    tech_skills = [s["name"] for s in skills_data["technologies"]]
    soft_skills = [s.get("description", s["name"]) for s in skills_data["soft_skills"]]
    study_skills = tech_skills + soft_skills

    total_study_skills = len(study_skills)

    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)

    # Encode study skills
    print(f"Encoding {total_study_skills} study-acquired skills...")
    study_embeddings = model.encode(study_skills, convert_to_tensor=True, batch_size=BATCH_SIZE, show_progress_bar=True)

    # Prepare results and statistics
    results = []
    study_skill_match_counts = [0] * total_study_skills  # For each study skill, how many job skills it matched
    job_skill_counter = {}  # For each job skill, how many times it appears (across all jobs)
    print(f"Processing {len(jobs_data)} job descriptions...")
    for job in tqdm(jobs_data, desc="Jobs"):
        job_title = job.get("title", "")
        company = job.get("company", "")

        # Extract individual job skill entries
        job_skill_texts = []
        for field in ["requirements", "technologies_expected", "technologies_optional", "specializations"]:
            val = job.get(field)
            if val:
                if isinstance(val, list):
                    items = val
                else:
                    # Split by both ',' and ';'
                    items = []
                    for part in str(val).split(';'):
                        items.extend([x.strip() for x in part.split(',') if x.strip()])
                job_skill_texts.extend([str(x).strip() for x in items if x and str(x).strip()])

        # Count job skill occurrences
        for skill in job_skill_texts:
            job_skill_counter[skill] = job_skill_counter.get(skill, 0) + 1

        if not job_skill_texts:
            results.append({
                "job_title": job_title,
                "company": company,
                "matched_job_skills": 0,
                "total_job_skills": 0,
                "match_ratio": 0
            })
            continue

        # Encode each job skill individually
        job_embeddings = model.encode(job_skill_texts, convert_to_tensor=True, batch_size=BATCH_SIZE, show_progress_bar=False)

        # Compute pairwise similarity
        similarity_matrix = util.cos_sim(job_embeddings, study_embeddings)  # shape: (job_skills, study_skills)
        match_counts = (similarity_matrix >= SIMILARITY_THRESHOLD).any(dim=1).sum().item()

        # For each study skill, count if it matched any job skill in this job
        study_skill_matches = (similarity_matrix >= SIMILARITY_THRESHOLD).any(dim=0).cpu().numpy()
        study_skill_match_counts = [a + int(b) for a, b in zip(study_skill_match_counts, study_skill_matches)]

        total_job_skills = len(job_skill_texts)
        match_ratio = match_counts / total_job_skills if total_job_skills > 0 else 0

        results.append({
            "job_title": job_title,
            "company": company,
            "matched_job_skills": match_counts,
            "total_job_skills": total_job_skills,
            "match_ratio": match_ratio
        })

    # Export CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Done. Results saved to: {OUTPUT_CSV}")

    # === SUMMARY STATISTICS ===
    # 1. Study skill with most matches
    max_study_idx = int(pd.Series(study_skill_match_counts).idxmax())
    max_study_skill = study_skills[max_study_idx]
    max_study_count = study_skill_match_counts[max_study_idx]
    print(f"\nStudy-acquired skill with most matches: '{max_study_skill}' (matched in {max_study_count} job descriptions)")

    # 2. Job skill needed the most
    if job_skill_counter:
        most_needed_job_skill = max(job_skill_counter, key=job_skill_counter.get)
        most_needed_job_skill_count = job_skill_counter[most_needed_job_skill]
        print(f"Job skill needed the most: '{most_needed_job_skill}' (appeared {most_needed_job_skill_count} times across all jobs)")
    else:
        print("No job skills found in the dataset.")

    # Optionally, save summary to a file
    with open("job_skill_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Study-acquired skill with most matches: '{max_study_skill}' (matched in {max_study_count} job descriptions)\n")
        if job_skill_counter:
            f.write(f"Job skill needed the most: '{most_needed_job_skill}' (appeared {most_needed_job_skill_count} times across all jobs)\n")
        else:
            f.write("No job skills found in the dataset.\n")

    # === FULL LISTS ===
    # 1. Study-acquired skills with match counts
    study_skill_df = pd.DataFrame({
        'study_skill': study_skills,
        'match_count': study_skill_match_counts
    })
    study_skill_df = study_skill_df.sort_values(by='match_count', ascending=False)
    study_skill_df.to_csv('study_skill_match_counts.csv', index=False)
    print("Full study skill match counts saved to: study_skill_match_counts.csv")

    # 2. Job skills with frequencies
    job_skill_df = pd.DataFrame(list(job_skill_counter.items()), columns=['job_skill', 'frequency'])
    job_skill_df = job_skill_df.sort_values(by='frequency', ascending=False)
    job_skill_df.to_csv('job_skill_frequencies.csv', index=False)
    print("Full job skill frequencies saved to: job_skill_frequencies.csv")

if __name__ == "__main__":
    main()
