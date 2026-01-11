
import os
import csv
from pathlib import Path

# Define the uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 1. Fee Structure (Text File)
fee_structure = """
Dr. B.C. Roy Engineering College - Fee Structure (2025-26)

B.Tech Programs:
- Admission Fee (One time): ₹10,000
- Tuition Fee (Per Semester): ₹45,000
- Development Fee (Per Semester): ₹5,000
- Library Fee (Per Semester): ₹1,000
- Total Semester Fee: ₹51,000

M.Tech Programs:
- Admission Fee (One time): ₹15,000
- Tuition Fee (Per Semester): ₹60,000
- Total Semester Fee: ₹60,000 (Scholarships available for GATE qualified)

Hostel Fees:
- Boarding & Lodging (Per Semester): ₹35,000
- Mess Charges (Per Month): ₹4,000 (approx)

Payment Modes:
- Online via College Portal
- Demand Draft in favor of "BCREC" payable at Durgapur
"""

with open(UPLOAD_DIR / "Fee_Structure_2025.txt", "w", encoding="utf-8") as f:
    f.write(fee_structure)


# 2. Courses Offered (CSV)
courses_data = [
    ["Department", "Course Name", "Duration", "Intake", "HOD"],
    ["Computer Science", "B.Tech in CSE", "4 Years", "180", "Dr. A. Kumar"],
    ["Computer Science", "B.Tech in AI & ML", "4 Years", "60", "Dr. S. Roy"],
    ["Electronics", "B.Tech in ECE", "4 Years", "120", "Dr. B. Das"],
    ["Mechanical", "B.Tech in ME", "4 Years", "60", "Dr. C. Bose"],
    ["Civil", "B.Tech in CE", "4 Years", "60", "Dr. D. Gupta"],
    ["Management", "MBA", "2 Years", "60", "Dr. E. Sen"]
]

with open(UPLOAD_DIR / "Courses_Offered.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(courses_data)


# 3. Admission Guidelines (Text)
admission_guidelines = """
Admission Guidelines 2025 - Dr. B.C. Roy Engineering College

Eligibility Criteria for B.Tech:
- Must have passed 10+2 with Physics and Mathematics as compulsory subjects.
- Minimum 45% marks in PCM (40% for reserved categories).
- Must have a valid rank in WBJEE or JEE Main.

Admission Process:
1. Counseling: 90% seats filled through WBJEE Counseling.
2. Management Quota: 10% seats filled directly based on JEE Main/WBJEE rank.
3. Documents Required:
   - Rank Card (WBJEE/JEE Main)
   - 10th & 12th Marksheets
   - Aadhar Card
   - Domicile Certificate

Important Dates:
- Application Start: 1st April 2025
- Counseling Round 1: 15th June 2025
- Classes Begin: 1st August 2025

Contact Admissions:
Phone: +91-343-2567890
Email: admissions@bcrec.ac.in
"""

with open(UPLOAD_DIR / "Admission_Guidelines.txt", "w", encoding="utf-8") as f:
    f.write(admission_guidelines)

print(f"✅ Created 3 sample documents in {UPLOAD_DIR.absolute()}")
