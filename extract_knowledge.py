import json
import csv
import re
import os
from pathlib import Path

# Paths
UPLOAD_DIR = Path("backend/uploads")
DATA_DIR = Path("backend/data")
OUTPUT_FILE = DATA_DIR / "knowledge_graph.json"

def extract_courses():
    courses = []
    csv_file = UPLOAD_DIR / "Courses_Offered.csv"
    if not csv_file.exists():
        print(f"Warning: {csv_file} not found.")
        return []

    print(f"Extracting courses from {csv_file}...")
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean keys (remove spaces/BWS)
                clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
                courses.append(clean_row)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
    return courses

def extract_fees():
    txt_file = UPLOAD_DIR / "Fee_Structure_2025.txt"
    if not txt_file.exists():
        print(f"Warning: {txt_file} not found.")
        return None

    print(f"Extracting fees from {txt_file}...")
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return content # Store payload for now, or use LLM later to structure it
    except Exception as e:
        print(f"Error reading Fees: {e}")
        return None

def main():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    
    knowledge = {
        "courses": extract_courses(),
        "fees_raw": extract_fees(),
        "meta": {
            "version": "1.0",
            "generated_by": "extract_knowledge.py"
        }
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(knowledge, f, indent=2)
        
    print(f"Successfully generated {OUTPUT_FILE}")
    print(f"Counts: {len(knowledge['courses'])} courses found.")

if __name__ == "__main__":
    main()
