# Graduation Planner & Academic Advising System

A Python-based academic decision-support application that analyzes student academic history and helps advisors build structured graduation plans based on GPA, prerequisites, retakes, failed courses, electives, training requirements, and academic regulations.

## Why this project exists
Academic graduation planning is difficult to manage manually when a student has repeated courses, failed attempts, improvement courses, elective substitutions, prerequisite chains, training requirements, and term-specific offerings. This project turns those rules into a repeatable planning workflow.

## Key features
- Student academic-history analysis
- GPA / CGPA and total-point calculations
- Failed-course detection and retake tracking
- Retake grade-cap rules
- D-grade improvement planning
- Prerequisite checking
- Remaining-course analysis
- Elective-list handling
- Semester-by-semester graduation planning
- Summer-training logic
- Off-term graduation exceptions
- Arabic / English support
- Excel export
- Portrait PDF graduation-plan reports
- Desktop launcher / Windows build support

## Tech stack
- Python
- Streamlit
- Pandas
- OpenPyXL
- PyMuPDF
- ReportLab
- Arabic Reshaper / Python Bidi
- PyInstaller

## Privacy
The public repository intentionally excludes real student records and personally identifiable academic data. Use only anonymized or synthetic demo files when testing the project publicly.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

For desktop packaging, see the included Windows build scripts.

## Portfolio note
This repository is a public portfolio version of a real academic workflow tool. Institution-specific data, student records, credentials, and private operational files are not included.
