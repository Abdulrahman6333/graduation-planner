
import re
import os
import base64
import html as html_lib
import json
import sys
import unicodedata
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, List, Dict, Set

import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import streamlit.components.v1 as components

try:
    import pymupdf as fitz
except Exception:
    try:
        import fitz  # legacy PyMuPDF import
    except Exception:
        fitz = None

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    )
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_PDF_OK = True
except Exception:
    ARABIC_PDF_OK = False


# =========================================================
# App config
# =========================================================

st.set_page_config(
    page_title="Graduation Planner | Eng. Khedr",
    page_icon="🎓",
    layout="wide",
)



st.markdown(
    """
    <style>
    :root{
        color-scheme: light;
        --app-bg:#F5F6F8;
        --card:#FFFFFF;
        --text:#20242A;
        --muted:#596273;
        --border:#D9DEE7;
        --primary:#243B53;
        --primary-2:#102A43;
        --accent:#D9822B;
    }
    html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
        background:var(--app-bg)!important;color:var(--text)!important;
    }
    [data-testid="stSidebar"],[data-testid="stSidebarContent"]{
        background:#FFFFFF!important;color:var(--text)!important;border-right:1px solid var(--border)!important;
    }
    [data-testid="stHeader"]{
        background:rgba(255,255,255,.98)!important;border-bottom:1px solid var(--border)!important;
    }
    h1,h2,h3,h4,h5,h6{color:var(--primary-2)!important;font-weight:800!important}
    p,span,label,li,div,.stMarkdown,[data-testid="stWidgetLabel"],[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stCaptionContainer"]{
        color:var(--text)!important;
    }
    [data-testid="stCaptionContainer"]{color:var(--muted)!important}
    div[data-testid="stMetric"],div[data-testid="stExpander"],div[data-testid="stVerticalBlockBorderWrapper"]{
        background:var(--card)!important;border:1px solid var(--border)!important;border-radius:10px!important;box-shadow:none!important;
    }
    div[data-testid="stMetric"]{padding:12px!important}
    div[data-testid="stMetricValue"]{color:var(--primary-2)!important;font-weight:900!important}
    div[data-testid="stExpander"] summary{background:#FAFAFB!important;color:var(--primary-2)!important;font-weight:800!important}
    button[data-baseweb="tab"]{
        background:#FFFFFF!important;color:#344054!important;border:1px solid var(--border)!important;border-radius:8px 8px 0 0!important;font-weight:700!important;
    }
    button[data-baseweb="tab"][aria-selected="true"]{
        background:var(--primary)!important;color:#FFFFFF!important;border-color:var(--primary)!important;box-shadow:inset 0 -3px 0 var(--accent)!important;
    }
    div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,input,textarea{
        background:#FFFFFF!important;color:var(--text)!important;border:1px solid #AEB7C4!important;border-radius:8px!important;
    }
    div[data-baseweb="popover"],ul[role="listbox"]{background:#FFFFFF!important;border:1px solid #AEB7C4!important;color:var(--text)!important}
    li[role="option"]{background:#FFFFFF!important;color:var(--text)!important}
    li[role="option"]:hover,li[role="option"][aria-selected="true"]{background:#E9EEF5!important;color:var(--primary-2)!important}
    .stButton>button,.stDownloadButton>button{
        background:#FFFFFF!important;color:var(--primary)!important;border:1px solid var(--primary)!important;border-radius:8px!important;font-weight:800!important;
    }
    .stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{
        background:var(--primary)!important;color:#FFFFFF!important;border-color:var(--primary)!important;
    }
    .stButton>button:hover,.stDownloadButton>button:hover{background:var(--primary-2)!important;color:#FFFFFF!important;border-color:var(--primary-2)!important}
    [data-testid="stAlert"]{border-radius:8px!important;border-width:1px!important;color:var(--text)!important}
    [data-testid="stDataFrame"]{background:#FFFFFF!important;border:1px solid var(--border)!important;border-radius:8px!important}
    hr{border-color:var(--border)!important}
    /* Course-card colors are intentionally quiet; type is clear by border. */
    .stApp div[style*="background:#FFF0F0"],.stApp div[style*="background:#FFF8D8"],.stApp div[style*="background:#EAF4FF"],.stApp div[style*="background:#F4EEFF"],.stApp div[style*="background:#DFF7EA"]{
        background:#FFFFFF!important;border-color:#B8C2CC!important;
    }
    .stApp div[style*="background:#FFF0F0"]{border-right:6px solid #B42318!important}
    .stApp div[style*="background:#FFF8D8"]{border-right:6px solid #B54708!important}
    .stApp div[style*="background:#EAF4FF"]{border-right:6px solid #175CD3!important}
    .stApp div[style*="background:#F4EEFF"]{border-right:6px solid #6941C6!important}
    .stApp div[style*="background:#DFF7EA"]{border-right:6px solid #027A48!important}
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <style>
    /* v42: force Streamlit/BaseWeb widgets into a clean light UI.
       This fixes black dropdown menus caused by browser/OS dark mode. */

    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    section.main,
    .main,
    .block-container {
        background: #F6F7F9 !important;
        color: #1F2933 !important;
    }

    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {
        background: #FFFFFF !important;
        color: #1F2933 !important;
    }

    /* All normal text */
    .stApp, .stApp * {
        text-shadow: none !important;
    }

    .stApp h1, .stApp h2, .stApp h3,
    .stApp h4, .stApp h5, .stApp h6 {
        color: #102A43 !important;
    }

    .stApp p, .stApp span, .stApp label,
    .stApp div, .stApp li, .stApp small {
        color: #1F2933 !important;
    }

    /* Select input closed state */
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] div {
        color: #1F2933 !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #9AA6B2 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] svg {
        color: #1F2933 !important;
        fill: #1F2933 !important;
    }

    /* Dropdown / menu open state */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] *,
    ul[role="listbox"],
    ul[role="listbox"] *,
    li[role="option"],
    li[role="option"] * {
        background-color: #FFFFFF !important;
        color: #1F2933 !important;
        border-color: #CBD2D9 !important;
    }

    div[data-baseweb="popover"] {
        border: 1px solid #CBD2D9 !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14) !important;
    }

    li[role="option"],
    div[role="option"] {
        background-color: #FFFFFF !important;
        color: #1F2933 !important;
    }

    li[role="option"]:hover,
    div[role="option"]:hover,
    li[role="option"][aria-selected="true"],
    div[role="option"][aria-selected="true"] {
        background-color: #E8F1FA !important;
        color: #102A43 !important;
    }

    /* Inputs, file uploader, buttons */
    input, textarea,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #FFFFFF !important;
        color: #1F2933 !important;
        border-color: #9AA6B2 !important;
    }

    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] div {
        background-color: #FFFFFF !important;
        color: #1F2933 !important;
        border-color: #CBD2D9 !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #243B53 !important;
        border: 1px solid #243B53 !important;
    }

    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        background-color: #243B53 !important;
        color: #FFFFFF !important;
        border-color: #243B53 !important;
    }

    /* Alerts */
    [data-testid="stAlert"] div,
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span {
        color: #1F2933 !important;
    }

    /* Replace dark course/table blocks if browser dark mode overrides inline styles */
    .stApp [style*="background:#0"],
    .stApp [style*="background: #0"],
    .stApp [style*="background-color:#0"],
    .stApp [style*="background-color: #0"],
    .stApp [style*="background: rgb(0"],
    .stApp [style*="background-color: rgb(0"] {
        background: #FFFFFF !important;
        color: #1F2933 !important;
        border-color: #CBD2D9 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


UNIVERSITY_NAME = "Delta University For Science And Technology"
PROGRAM_BRAND = "DevOps Mechatronics"
APP_DEVELOPER = "Eng. Khedr"
UNIVERSITY_LOGO_BYTES = base64.b64decode(
    """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"""
)


def university_logo_bytes() -> bytes:
    return UNIVERSITY_LOGO_BYTES


# =========================================================
# Persistent report identity settings
# =========================================================

def _app_writable_directory() -> Path:
    """
    Store settings beside the desktop application so the advisor name
    and corrected student names remain available for future students.
    """
    try:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


SETTINGS_FILE = _app_writable_directory() / "graduation_planner_settings.json"


def load_local_settings() -> Dict:
    defaults = {
        "advisor_name": "",
        "student_names": {},
        "training1_required_hours": 65,
        "training2_required_hours": 101,
    }
    try:
        if SETTINGS_FILE.exists():
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                defaults["advisor_name"] = str(loaded.get("advisor_name", ""))
                names = loaded.get("student_names", {})
                if isinstance(names, dict):
                    defaults["student_names"] = {
                        str(key): str(value) for key, value in names.items()
                    }
                defaults["training1_required_hours"] = int(
                    loaded.get("training1_required_hours", 65)
                )
                defaults["training2_required_hours"] = int(
                    loaded.get("training2_required_hours", 101)
                )
    except Exception:
        pass
    return defaults


def save_local_settings(
    advisor_name: str,
    student_names: Dict[str, str],
    training1_required_hours: int = 65,
    training2_required_hours: int = 101,
):
    payload = {
        "advisor_name": str(advisor_name or "").strip(),
        "student_names": {
            str(key): str(value).strip()
            for key, value in (student_names or {}).items()
            if str(value).strip()
        },
        "training1_required_hours": int(training1_required_hours),
        "training2_required_hours": int(training2_required_hours),
    }
    SETTINGS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )



def safe_student_report_filename(
    student_name: str,
    student_id: str,
    extension: str,
    is_ar: bool = False,
    suffix: str = "",
) -> str:
    """
    Build a Windows-safe download filename using the student's corrected name.
    Arabic names are preserved.
    """
    name = unicodedata.normalize("NFKC", str(student_name or "")).strip()

    # Remove Windows-invalid filename characters and control characters.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", name)
    name = re.sub(r"\s+", " ", name).strip(" .")

    if not name:
        name = str(student_id or "student").strip()

    report_text = "خطة التخرج" if is_ar else "Graduation Plan"
    suffix_text = f" - {suffix}" if suffix else ""
    ext = str(extension or "").lstrip(".")

    return f"{name} - {report_text}{suffix_text}.{ext}"


def clean_extracted_student_name(value: str) -> str:
    """
    Remove PDF control characters. If the extracted result is clearly mojibake,
    return an empty value so the advisor can type the correct name.
    """
    text = "".join(
        char for char in str(value or "")
        if unicodedata.category(char) not in {"Cc", "Cs"}
    ).strip()
    if not text:
        return ""

    useful = sum(
        char.isalpha() or char.isdigit() or char.isspace()
        or char in "-_.'"
        for char in text
    )
    if useful / max(1, len(text)) < 0.65:
        return ""
    return text


# =========================================================
# Constants
# =========================================================

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0,
    "F": 0.0, "W": 0.0, "PASS": 0.0, "FAIL": 0.0,
}
PASSING = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "PASS"}
GRADE_OPTIONS = ["Select", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"]


def retake_max_allowed_grade(attempts_count) -> str:
    """
    One failed attempt -> maximum retake grade B+.
    Two or more failed attempts -> maximum retake grade C.
    """
    try:
        attempts = int(attempts_count)
    except Exception:
        attempts = 1
    return "B+" if attempts <= 1 else "C"


def retake_grade_options(attempts_count) -> List[str]:
    max_grade = retake_max_allowed_grade(attempts_count)
    start_index = GRADE_OPTIONS.index(max_grade)
    return ["Select"] + GRADE_OPTIONS[start_index:]


def cap_retake_grade(grade: str, attempts_count) -> str:
    value = str(grade or "Select")
    if value == "Select":
        return value
    max_grade = retake_max_allowed_grade(attempts_count)
    return max_grade if point_of_grade(value) > point_of_grade(max_grade) else value


def gpa_letter_grade(gpa: float) -> str:
    """
    Convert SGPA/CGPA to the corresponding letter grade on the 4.0 scale.
    """
    value = max(0.0, min(4.0, float(gpa or 0.0)))
    if value >= 4.0:
        return "A"
    if value >= 3.7:
        return "A-"
    if value >= 3.3:
        return "B+"
    if value >= 3.0:
        return "B"
    if value >= 2.7:
        return "B-"
    if value >= 2.3:
        return "C+"
    if value >= 2.0:
        return "C"
    if value >= 1.7:
        return "C-"
    if value >= 1.3:
        return "D+"
    if value >= 1.0:
        return "D"
    return "F"


def gpa_grade_description(gpa: float, is_ar: bool = False) -> str:
    letter = gpa_letter_grade(gpa)
    if is_ar:
        descriptions = {
            "A": "ممتاز",
            "A-": "ممتاز",
            "B+": "جيد جدًا مرتفع",
            "B": "جيد جدًا",
            "B-": "جيد جدًا منخفض",
            "C+": "جيد مرتفع",
            "C": "جيد",
            "C-": "جيد منخفض",
            "D+": "مقبول مرتفع",
            "D": "مقبول",
            "F": "راسب",
        }
    else:
        descriptions = {
            "A": "Excellent",
            "A-": "Excellent",
            "B+": "Very Good High",
            "B": "Very Good",
            "B-": "Very Good Low",
            "C+": "Good High",
            "C": "Good",
            "C-": "Good Low",
            "D+": "Pass High",
            "D": "Pass",
            "F": "Fail",
        }
    return f"{letter} — {descriptions[letter]}"




# Actual elective course codes by list.
# If the student passes any course from a list, the list requirement is satisfied.
ELECTIVE_LISTS = {
    "List 1": {"ECE312", "ECE313", "ECE314", "ECE315", "ECE317", "ECE372"},
    "List 2": {"MEC369", "MEC372", "MEC373", "MEC374", "MEC375", "MEC376", "MEC391"},
    "List 3": {"MEC463", "MEC464", "MEC465", "MEC466", "MEC491"},
    "List 4": {"ECE451", "ECE481", "ECE482", "ECE483", "ECE484", "ECE485"},
    "List 5": {"MEC466", "MEC472", "MEC482", "MEC483", "MEC484", "MEC493", "MEC494", "MEC495", "MEC496"},
}

ELECTIVE_PLACEHOLDERS = {
    "ECE3XX-L1": "List 1",
    "MEC3XX-L2": "List 2",
    "MEC4XX-L3": "List 3",
    "ECE4XX-L4": "List 4",
    "MEC4XX-L5": "List 5",
}


HUMANITIES_REPLACEMENT_OPTIONS = {
    "GENXXX-A": "List A",
    "GENXXX-B1": "List B — Slot 1",
    "GENXXX-B2": "List B — Slot 2",
}

# Actual Humanities elective codes can appear in the transcript instead of
# GENXXX placeholders. Extend these sets when the department confirms more
# real codes. These lists are used to satisfy GENXXX-A/B1/B2 placeholders.
HUMANITIES_LIST_A_CODES = {
    "GEN003",
    "GEN004",
    "GEN005",
    "GEN005E",
    "GEN006",
    "GEN303",
    "GEN304",
    "GEN401",
    "GEN402",
    "GEN404",
    "GEN505",
}
HUMANITIES_LIST_B_CODES = {
    "GEN102",
    "GEN103",
    "GEN202",
    "GEN203",
    "GEN302",
    "GEN310",
    "GEN403",
}

HUMANITIES_LIST_A_LABEL = "University Requirements-Elective (List A)"
HUMANITIES_LIST_B_LABEL = "University Requirements-Elective (List B)"


def humanities_replacement_label(code: str, is_ar: bool = False) -> str:
    ncode = norm(code)
    labels_ar = {
        "GENXXX-A": "مادة بديلة من List A",
        "GENXXX-B1": "مادة بديلة من List B — الخانة الأولى",
        "GENXXX-B2": "مادة بديلة من List B — الخانة الثانية",
    }
    labels_en = {
        "GENXXX-A": "Alternative course from List A",
        "GENXXX-B1": "Alternative course from List B — Slot 1",
        "GENXXX-B2": "Alternative course from List B — Slot 2",
    }
    return (labels_ar if is_ar else labels_en).get(ncode, str(code))


def list_replacement_course_name(target_code: str, failed_code: str, is_ar: bool = False) -> str:
    base = humanities_replacement_label(target_code, is_ar)
    if is_ar:
        return f"{base} بدلًا من {failed_code}"
    return f"{base} replacing {failed_code}"




@dataclass
class Course:
    code: str
    name: str
    hours: int
    level: str
    semester: str
    category: str
    prereq: Tuple[str, ...] = ()


# =========================================================
# Course database - advisor can review/edit later
# =========================================================

COURSES: List[Course] = [
    Course("GEN001", "Introduction to Information and Communication Technology", 2, "L0", "Fall", "University"),
    Course("GEN002", "English Language I", 2, "L0", "Fall", "University"),
    Course("BAS011", "Engineering Mathematics (1)", 3, "L0", "Fall", "Faculty"),
    Course("BAS021", "Engineering Physics (1)", 3, "L0", "Fall", "Faculty"),
    Course("MEC 021", "Engineering Mechanics (1)", 3, "L0", "Fall", "Faculty"),
    Course("MEC 051", "Engineering Drawing and Projection", 3, "L0", "Fall", "Faculty"),

    Course("BAS012", "Engineering Mathematics (2)", 3, "L0", "Spring", "Faculty"),
    Course("BAS022", "Engineering Physics (2)", 3, "L0", "Spring", "Faculty", ("BAS021",)),
    Course("BAS031", "Engineering Chemistry", 3, "L0", "Spring", "Faculty"),
    Course("ECE 001", "Introduction to Computer Programming", 2, "L0", "Spring", "Faculty"),
    Course("MEC 022", "Engineering Mechanics (2)", 3, "L0", "Spring", "Faculty", ("MEC 021",)),
    Course("MEC 052", "Fundamentals of Manufacturing Engineering", 3, "L0", "Spring", "Faculty"),

    Course("GEN101", "English Language II", 2, "L1", "Fall", "University", ("GEN002",)),
    Course("BAS111", "Engineering Mathematics (3)", 3, "L1", "Fall", "Faculty", ("BAS011", "BAS012")),
    Course("ECE 111", "Electrical Circuits Analysis", 3, "L1", "Fall", "Program General", ("BAS022",)),
    Course("ECE 112", "Fundamentals of Electronics", 3, "L1", "Fall", "Program General", ("BAS022",)),
    Course("MEC 111", "Material Science", 3, "L1", "Fall", "Program General"),
    Course("MEC 151", "Computer Aided Drawing", 2, "L1", "Fall", "Faculty", ("MEC 051",)),

    Course("GENXXX-A", "Humanities Elective - List A", 2, "L1", "Spring", "University Elective"),
    Course("BAS113", "Statistics & Operation Research", 3, "L1", "Spring", "Faculty", ("BAS011", "BAS012")),
    Course("ECE 113", "Advanced Electronics", 3, "L1", "Spring", "Program General", ("ECE 112",)),
    Course("ECE 114", "Advanced Electrical Circuits Analysis", 3, "L1", "Spring", "Program General", ("ECE 111",)),
    Course("MEC 131", "Thermodynamics", 2, "L1", "Spring", "Program General"),
    Course("MEC 141", "Introduction to Mechatronics", 3, "L1", "Spring", "Program General"),

    Course("GEN201", "Technical Report Writing I", 2, "L2", "Fall", "University", ("GEN002",)),
    Course("CIV280", "Fundamentals of Projects Management", 2, "L2", "Fall", "Faculty"),
    Course("ECE 212", "Power Electronics", 3, "L2", "Fall", "Program General", ("ECE 113",)),
    Course("MEC 213", "Electrical Power Machines", 2, "L2", "Fall", "Program General", ("ECE 114",)),
    Course("MEC 211", "Fluid Mechanics", 3, "L2", "Fall", "Program General"),
    Course("MEC 221", "Kinematics of Machines", 3, "L2", "Fall", "Program General", ("MEC 022",)),
    Course("MEC 231", "Heat and Mass Transfer", 3, "L2", "Fall", "Program General", ("MEC 131",)),

    Course("GENXXX-B1", "Humanities Elective - List B", 2, "L2", "Spring", "University Elective"),
    Course("ECE 211", "Digital and Logic Circuits", 3, "L2", "Spring", "Program General", ("ECE 001",)),
    Course("MEC 222", "Digital Signal Processing", 3, "L2", "Spring", "Program General", ("BAS111",)),
    Course("ECE 231", "Electromagnetic Theory", 3, "L2", "Spring", "Program General", ("BAS111",)),
    Course("ECE 252", "Automatic Control Systems", 3, "L2", "Spring", "Program General", ("BAS111", "ECE 114")),
    Course("MEC 261", "Dynamics of Machines", 3, "L2", "Spring", "Program General", ("MEC 221",)),
    Course("MEC 200", "Practical Training-Mechatronics Eng. (1)", 1, "L2", "Summer", "Training"),

    Course("GENXXX-B2", "Humanities Elective - List B", 2, "L3", "Fall", "University Elective"),
    Course("ECE 351", "Microprocessors (1)", 3, "L3", "Fall", "Program General", ("ECE 112",)),
    Course("MEC 321", "Stress Analysis", 3, "L3", "Fall", "Program General", ("MEC 111",)),
    Course("MEC 361", "Mechatronics Measurements and Devices", 3, "L3", "Fall", "Program General", ("MEC 141",)),
    Course("MEC 362", "Machine Design", 3, "L3", "Fall", "Program General", ("MEC 261",)),
    Course("ECE3XX-L1", "Elective 1 - List 1", 2, "L3", "Fall", "Elective"),

    # Official chart places MEC 354 in Spring, but the actual department
    # offering used for advising is Fall.
    Course("MEC 354", "Microcontroller Applications", 3, "L3", "Fall", "Program Specialized", ("ECE 252",)),
    Course("MEC 355", "Embedded Systems Design", 3, "L3", "Spring", "Program Specialized", ("ECE 252",)),
    Course("MEC 365", "Data Networking", 3, "L3", "Spring", "Program General", ("ECE 211",)),
    Course("MEC 363", "Hydraulic and Pneumatic Systems", 2, "L3", "Spring", "Program Specialized", ("MEC 361",)),
    Course("MEC 371", "CAD/CAM", 2, "L3", "Spring", "Program Specialized", ("MEC 151",)),
    Course("MEC 381", "Robotics Systems and Control", 3, "L3", "Spring", "Program Specialized", ("MEC 361", "ECE 252")),
    Course("MEC 300", "Practical Training-Mechatronics Eng. (2)", 1, "L3", "Summer", "Training", ("MEC 200",)),

    Course("MEC 453", "PLC and SCADA Systems", 4, "L4", "Fall", "Program Specialized", ("ECE 252",)),
    Course("MEC 492", "Advanced Mechatronic Systems", 2, "L4", "Fall", "Program Specialized", ("MEC 361",)),
    Course("MEC3XX-L2", "Elective 2 - List 2", 2, "L4", "Fall", "Elective"),
    Course("MEC4XX-L3", "Elective 3 - List 3", 2, "L4", "Fall", "Elective"),
    Course("MEC 400a", "Graduation Project-Mechatronics Eng. (1)", 3, "L4", "Fall", "Graduation", ("MEC 300",)),

    Course("MEC 456", "Concurrent Systems", 2, "L4", "Spring", "Program Specialized", ("MEC 354",)),
    Course("MEC 481", "Advanced Robotics", 2, "L4", "Spring", "Program Specialized", ("MEC 381",)),
    Course("MEC 485", "Modern Manufacturing Processes", 2, "L4", "Spring", "Program Specialized", ("MEC 381",)),
    Course("ECE4XX-L4", "Elective 4 - List 4", 2, "L4", "Spring", "Elective"),
    Course("MEC4XX-L5", "Elective 5 - List 5", 2, "L4", "Spring", "Elective", ("MEC 381",)),
    Course("MEC 400b", "Graduation Project-Mechatronics Eng. (2)", 4, "L4", "Spring", "Graduation", ("MEC 400a",)),
]

COURSE_BY_NORM = {re.sub(r"\s+", "", c.code.upper()): c for c in COURSES}


# =========================================================
# Helpers
# =========================================================

def norm(code: str) -> str:
    return re.sub(r"\s+", "", str(code).upper())



def elective_list_for_code(code: str):
    ncode = norm(code)
    if ncode in ELECTIVE_PLACEHOLDERS:
        return ELECTIVE_PLACEHOLDERS[ncode]
    for list_name, codes in ELECTIVE_LISTS.items():
        if ncode in codes:
            return list_name
    return None


def satisfied_elective_lists(best: pd.DataFrame, extra_passed: Set[str] = None) -> Set[str]:
    passed = passed_codes(best)
    if extra_passed:
        passed = passed.union({norm(x) for x in extra_passed})

    satisfied = set()
    for list_name, codes in ELECTIVE_LISTS.items():
        if passed.intersection(codes):
            satisfied.add(list_name)
    return satisfied


def point_of_grade(grade: str) -> float:
    return GRADE_POINTS.get(str(grade).upper(), 0.0)


def cumulative_status(cgpa: float, passed_hours: float) -> str:
    if passed_hours >= 160 and cgpa >= 2.0:
        return "Graduation requirements met"
    if cgpa >= 2.0:
        return "CGPA target met; complete remaining requirements"
    return f"Below graduation CGPA by {max(0.0, 2.0 - cgpa):.3f}"


def is_passing_grade(grade: str) -> bool:
    return str(grade).upper() in PASSING


def extract_pdf_text(uploaded_file) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF could not be loaded. Run INSTALL_AND_TEST.bat, then restart the app.")
    data = uploaded_file.read()
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)


def infer_status(cgpa: float) -> str:
    if cgpa < 1.7:
        return "Probation"
    if cgpa < 2.0:
        return "Supervision"
    return "Regular"


def parse_header(text: str) -> Dict:
    def get(pattern: str, default: str = ""):
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else default

    cgpa = float(get(r"CGPA\s*:\s*([0-9.]+)", "0") or 0)
    passed_hours = float(get(r"Total\s+Passed\s+Hrs\s*:\s*([0-9]+)", "0") or 0)
    registered_hours = float(get(r"Total\s+Registered\s+Hrs\s*:\s*([0-9]+)", "0") or 0)
    tpoints = re.findall(r"T\.?\s*Points\s*:\s*([0-9.]+)", text, re.I)

    # GPA basis:
    # CGPA = T.Points / T.Hours, therefore T.Hours = T.Points / CGPA.
    # Do not use Total Registered Hours as the GPA denominator because it can
    # include repeated registrations and withdrawals.
    extracted_points = float(tpoints[-1]) if tpoints else 0.0
    calculated_points = round(cgpa * passed_hours, 3)
    total_points = extracted_points if extracted_points > 0 else calculated_points
    gpa_hours_from_tpoints = (
        round(total_points / cgpa, 3)
        if cgpa > 0 and total_points > 0
        else 0.0
    )

    return {
        "student_id": get(r"Student\s+ID\s*:\s*([0-9]+)", ""),
        "student_name": get(r"Student\s+Name\s*:\s*([^\n]+)", ""),
        "passed_hours": passed_hours,
        "registered_hours": registered_hours,
        "level": get(r"Educational\s+Level\s*:\s*([0-9]+\s+of\s+[0-9]+)", ""),
        "cgpa": cgpa,
        "program": get(r"Academic\s+Program\s*:\s*([^\n]+)", ""),
        "academic_status": get(r"Academic\s+Status\s*:\s*([^\n]+)", "") or infer_status(cgpa),
        "total_points": total_points,
        "gpa_hours_from_tpoints": gpa_hours_from_tpoints,
        "extracted_total_points": extracted_points,
        "points_source": "PDF T.Points / CGPA" if extracted_points > 0 else "CGPA × Passed Hours",
    }


def parse_courses(text: str) -> pd.DataFrame:
    rows = []
    current_term = ""
    lines = [" ".join(x.strip().split()) for x in text.splitlines() if x.strip()]
    code_re = r"^(BAS00[A-Z]|(?:BAS|GEN|ECE|MEC|CIV)\s*\d{3}[A-Za-z]?)$"
    grade_re = r"^(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D|F|PASS|FAIL|W)$"

    i = 0
    while i < len(lines):
        line = lines[i]

        tm = re.search(r"(\d{4}-\d{4})\s+(Fall|Spring|Summer)", line, re.I)
        if tm:
            current_term = f"{tm.group(1)} {tm.group(2)}"
            i += 1
            continue

        # One-line rows
        m = re.match(
            r"^((?:BAS00[A-Z])|(?:(?:BAS|GEN|ECE|MEC|CIV)\s*\d{3}[A-Za-z]?))\s+(.+?)\s+"
            r"(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D|F|PASS|FAIL|W)\s+(\d+)(?:\s+\d+)?(?:\s+TR)?$",
            line, re.I
        )
        if m:
            code, name, grade, hours = m.group(1).strip(), m.group(2).strip(), m.group(3).upper(), int(m.group(4))
            rows.append({
                "term": current_term,
                "code": code,
                "name": name,
                "grade": grade,
                "hours": hours,
                "points": point_of_grade(grade),
                "passed": is_passing_grade(grade),
                "ncode": norm(code),
            })
            i += 1
            continue

        # Multi-line rows: code / name / grade / hours / remark
        if re.match(code_re, line, re.I) and i + 3 < len(lines):
            code = line
            name = lines[i + 1]
            grade = lines[i + 2].upper()
            hours_line = lines[i + 3]
            if re.match(grade_re, grade, re.I) and re.match(r"^\d+$", hours_line):
                hours = int(hours_line)
                rows.append({
                    "term": current_term,
                    "code": code,
                    "name": name,
                    "grade": grade,
                    "hours": hours,
                    "points": point_of_grade(grade),
                    "passed": is_passing_grade(grade),
                    "ncode": norm(code),
                })
                i += 5
                continue

        i += 1

    cols = ["term", "code", "name", "grade", "hours", "points", "passed", "ncode"]
    return pd.DataFrame(rows, columns=cols)


def best_attempts(attempts: pd.DataFrame) -> pd.DataFrame:
    cols = ["term", "code", "name", "grade", "hours", "points", "passed", "ncode"]
    if attempts.empty:
        return pd.DataFrame(columns=cols)

    out = []
    for _, group in attempts.groupby("ncode", sort=False):
        g = group.copy()
        g["_idx"] = range(len(g))
        best = g.sort_values(["points", "_idx"], ascending=[False, False]).iloc[0].drop("_idx")
        out.append(best)
    return pd.DataFrame(out, columns=cols)


def passed_codes(best: pd.DataFrame) -> Set[str]:
    if best.empty:
        return set()
    return set(best[best["passed"]]["ncode"].tolist())


def corona_pass_candidates(attempts: pd.DataFrame) -> pd.DataFrame:
    cols = ["term", "code", "name", "grade", "hours", "ncode"]
    if attempts.empty:
        return pd.DataFrame(columns=cols)
    df = attempts[(attempts["grade"].eq("PASS")) & (attempts["hours"] > 0)].copy()
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates(subset=["term", "ncode"], keep="last")


def attempted_gpa_hours_from_history(best: pd.DataFrame, corona_excluded_hours: float = 0.0) -> float:
    """Count each distinct GPA-bearing course once, including F attempts."""
    if best is None or best.empty:
        return 0.0
    excluded = {"PASS", "FAIL", "W"}
    df = best[(~best["grade"].astype(str).str.upper().isin(excluded)) & (best["hours"] > 0)].copy()
    return max(0.0, float(df["hours"].sum()) - float(corona_excluded_hours))


def calculate_gpa_hours(passed_hours: float, corona_excluded_hours: float) -> float:
    return max(0.0, float(passed_hours) - float(corona_excluded_hours))


def corrected_cgpa(total_points: float, gpa_hours: float) -> float:
    return float(total_points) / float(gpa_hours) if gpa_hours > 0 else 0.0


def withdrawn_courses(attempts: pd.DataFrame, best: pd.DataFrame) -> pd.DataFrame:
    """
    W means Withdrawn, not failed:
    - no GPA points
    - no GPA hours
    - no failed-attempt count
    - course returns as a normal new/remaining course when registered again
    """
    cols = ["code", "name", "grade", "hours", "term", "status"]
    if attempts is None or attempts.empty:
        return pd.DataFrame(columns=cols)

    passed = passed_codes(best)
    rows = []
    for ncode, group in attempts.groupby("ncode", sort=False):
        if ncode in passed:
            continue

        withdrawn = group[
            group["grade"].astype(str).str.upper().eq("W")
        ]
        if withdrawn.empty:
            continue

        actual_failures = group[
            group["grade"].astype(str).str.upper().eq("F")
        ]
        if not actual_failures.empty:
            continue

        latest = withdrawn.iloc[-1]
        rows.append({
            "code": latest["code"],
            "name": latest["name"],
            "grade": "W",
            "hours": int(latest["hours"]),
            "term": latest["term"],
            "status": "Withdrawn — register again as a new course",
        })

    return pd.DataFrame(rows, columns=cols)


def failed_retake_courses(
    attempts: pd.DataFrame,
    best: pd.DataFrame,
    extra_passed: Set[str] = None,
    planned_failed: Set[str] = None,
) -> pd.DataFrame:
    """
    Shows only real failed/retake requirements.

    Elective rule:
    If the student failed one course from an elective list but passed another
    course from the same list, the failed elective is removed because the list
    requirement is already satisfied.
    """
    cols = [
        "code", "name", "effective_grade", "latest_grade", "hours",
        "attempts_count", "max_allowed_grade", "last_term", "retake_reason", "elective_list"
    ]
    if attempts.empty:
        return pd.DataFrame(columns=cols)

    passed = passed_codes(best)
    if extra_passed:
        passed = passed.union({norm(x) for x in extra_passed})

    satisfied_lists = satisfied_elective_lists(best, extra_passed)
    completed_humanities = humanities_completed_slots(best, extra_passed)

    best_map = {}
    if not best.empty:
        for _, r in best.iterrows():
            best_map[r["ncode"]] = r

    rows = []
    for ncode, group in attempts.groupby("ncode", sort=False):
        group = group.reset_index(drop=True)

        # W is withdrawal, not failure. Count only actual F attempts.
        failure_group = group[
            group["grade"].astype(str).str.upper().eq("F")
        ].copy()
        if failure_group.empty:
            continue

        # If there is any successful attempt in the transcript, this course
        # is already passed and must not appear as Retake Failed.
        any_passed_attempt = bool(
            group["grade"].astype(str).str.upper().isin(PASSING).any()
        )
        if any_passed_attempt:
            continue

        latest = failure_group.iloc[-1]
        best_row = best_map.get(ncode)

        effective_grade = best_row["grade"] if best_row is not None else latest["grade"]
        effective_passed = bool(best_row is not None and best_row["passed"])
        list_name = elective_list_for_code(latest["code"])

        # A different passed elective in the same program elective list satisfies the requirement.
        if list_name and list_name in satisfied_lists and ncode not in passed:
            continue

        # Humanities List A/B rule:
        # If the student failed a List A/B course but then passed another course
        # from the same list, the failed course is replaced and must not appear as
        # Retake Failed. The replacement course keeps full grade scale from A+.
        humanities_family = _humanities_row_slot(latest)
        if humanities_family == "A" and "GENXXX-A" in completed_humanities and ncode not in passed:
            continue
        if humanities_family == "B" and (
            "GENXXX-B1" in completed_humanities
            or "GENXXX-B2" in completed_humanities
        ) and ncode not in passed:
            continue

        if not effective_passed:
            failure_count = len(failure_group)
            rows.append({
                "code": latest["code"],
                "name": latest["name"],
                "effective_grade": effective_grade,
                "latest_grade": latest["grade"],
                "hours": int(latest["hours"]),
                "attempts_count": failure_count,
                "max_allowed_grade": retake_max_allowed_grade(failure_count),
                "last_term": latest["term"],
                "retake_reason": "Actual F attempt; W withdrawals are excluded",
                "elective_list": list_name or "",
            })

    # Add courses predicted as failed in a saved planned term.
    if planned_failed:
        existing = {norm(x["code"]) for x in rows}
        for code in planned_failed:
            ncode = norm(code)
            if ncode in existing:
                continue
            c = course_obj_by_code(code)
            rows.append({
                "code": code,
                "name": c.name if c else code,
                "effective_grade": "F",
                "latest_grade": "F",
                "hours": c.hours if c else 0,
                "attempts_count": 1,
                "max_allowed_grade": retake_max_allowed_grade(1),
                "last_term": "Planned Term",
                "retake_reason": "Expected F in saved plan",
                "elective_list": elective_list_for_code(code) or "",
            })

    return pd.DataFrame(rows, columns=cols)

def d_grade_courses(best: pd.DataFrame) -> pd.DataFrame:
    """
    Only D grade courses, not D+.
    These are improvement candidates.
    """
    cols = ["code", "name", "current_grade", "hours", "current_points", "term"]
    if best.empty:
        return pd.DataFrame(columns=cols)
    df = best[best["grade"].eq("D") & (best["hours"] > 0)].copy()
    if df.empty:
        return pd.DataFrame(columns=cols)
    df = df.rename(columns={"grade": "current_grade", "points": "current_points"})
    return df[cols]


def missing_prereq(course: Course, passed: Set[str]) -> List[str]:
    return [p for p in course.prereq if norm(p) not in passed]


def _humanities_row_slot(row) -> str:
    """Return GENXXX-A/B1/B2-like slot family for a transcript row."""
    ncode = norm(row.get("code", ""))
    if ncode == "GENXXX-A" or ncode in HUMANITIES_LIST_A_CODES:
        return "A"
    if ncode in {"GENXXX-B1", "GENXXX-B2"} or ncode in HUMANITIES_LIST_B_CODES:
        return "B"

    name = str(row.get("name", "") or "").upper()
    compact_name = re.sub(r"[^A-Z0-9]+", " ", name)
    is_humanities = (
        "HUMANITIES" in compact_name
        or "HUMANITY" in compact_name
        or "HUMAN RIGHTS" in compact_name
        or "MARKETING SKILLS" in compact_name
    )
    is_list_a = bool(
        re.search(r"\bLIST\s*A\b", compact_name)
        or re.search(r"\bLISTA\b", compact_name)
    )
    is_list_b = bool(
        re.search(r"\bLIST\s*B\b", compact_name)
        or re.search(r"\bLISTB\b", compact_name)
    )

    if is_humanities and ("MARKETING SKILLS" in compact_name):
        return "A"
    if is_humanities and is_list_a:
        return "A"
    if is_humanities and is_list_b:
        return "B"
    return ""


def humanities_slot_grade(best: pd.DataFrame, slot_code: str) -> str:
    """
    Best detected grade for a Humanities slot.
    Supports real transcript course codes/names, not only GENXXX placeholders.
    """
    if best is None or best.empty:
        return ""

    target = norm(slot_code)
    target_family = "A" if target == "GENXXX-A" else "B"
    rows = []
    for _, row in best.iterrows():
        family = _humanities_row_slot(row)
        if family != target_family:
            continue
        if str(row.get("grade", "")).upper() in {"PASS", "FAIL", "W"}:
            continue
        rows.append(row)

    if not rows:
        return ""

    # For List B slots, use the first/second distinct detected List B course.
    if target in {"GENXXX-B1", "GENXXX-B2"}:
        distinct = []
        seen = set()
        for row in rows:
            ncode = norm(row.get("code", ""))
            if ncode in seen:
                continue
            seen.add(ncode)
            distinct.append(row)
        slot_index = 0 if target == "GENXXX-B1" else 1
        if len(distinct) <= slot_index:
            return ""
        return str(distinct[slot_index].get("grade", ""))

    # List A has one slot; return the strongest detected grade.
    best_row = sorted(
        rows,
        key=lambda r: point_of_grade(str(r.get("grade", ""))),
        reverse=True,
    )[0]
    return str(best_row.get("grade", ""))


def humanities_completed_slots(
    best: pd.DataFrame,
    extra_passed: Set[str] = None,
) -> Set[str]:
    """
    Resolve the three Humanities requirements:
    - GENXXX-A  : one passed List A course
    - GENXXX-B1 : first passed List B course
    - GENXXX-B2 : second passed List B course

    The transcript may contain the real elective course code rather than the
    curriculum placeholder. Therefore, completion is detected from:
    1) an explicitly passed placeholder code;
    2) a passed course name containing Humanities + List A/List B;
    3) planned passed placeholder codes.
    """
    completed = set()
    manual_completed = st.session_state.get(
        "humanities_manual_completed",
        set(),
    )
    manual_incomplete = {
        norm(x)
        for x in st.session_state.get(
            "humanities_manual_incomplete",
            set(),
        )
    }
    completed.update({norm(x) for x in manual_completed})

    if extra_passed:
        normalized_extra = {norm(x) for x in extra_passed}
        completed.update(
            normalized_extra.intersection(
                {"GENXXX-A", "GENXXX-B1", "GENXXX-B2"}
            )
        )

    if best is None or best.empty:
        return completed

    passed_df = best[
        best["passed"]
        & (best["hours"] > 0)
    ].copy()
    if passed_df.empty:
        return completed

    # Exact placeholder codes from the transcript.
    exact_passed = set(passed_df["ncode"].astype(str))
    completed.update(
        exact_passed.intersection(
            {"GENXXX-A", "GENXXX-B1", "GENXXX-B2"}
        )
    )

    list_a_courses = []
    list_b_courses = []

    for _, row in passed_df.iterrows():
        ncode = norm(row.get("code", ""))
        family = _humanities_row_slot(row)
        if family == "A":
            list_a_courses.append(ncode)
        elif family == "B":
            list_b_courses.append(ncode)

    if list_a_courses:
        completed.add("GENXXX-A")

    # List B has two distinct required slots.
    distinct_b = list(dict.fromkeys(list_b_courses))
    if len(distinct_b) >= 1:
        completed.add("GENXXX-B1")
    if len(distinct_b) >= 2:
        completed.add("GENXXX-B2")

    completed = {code for code in completed if norm(code) not in manual_incomplete}
    return completed


def remaining_courses(
    best: pd.DataFrame,
    extra_passed: Set[str] = None,
    planned_scheduled: Set[str] = None,
) -> pd.DataFrame:
    cols = ["level", "semester", "code", "name", "hours", "category", "status", "missing_prerequisites", "unlocks_next"]
    passed = passed_codes(best)
    if extra_passed:
        passed = passed.union({norm(x) for x in extra_passed})

    scheduled = {norm(x) for x in (planned_scheduled or set())}
    satisfied_lists = satisfied_elective_lists(best, extra_passed)
    completed_humanities = humanities_completed_slots(
        best,
        extra_passed,
    )

    rows = []
    for c in COURSES:
        ncode = norm(c.code)

        # Already passed or already assigned to a saved term.
        if ncode in passed or ncode in scheduled:
            continue

        # Hide completed Humanities placeholder slots even when the transcript
        # contains the real elective course code instead of GENXXX-A/B1/B2.
        if ncode in completed_humanities:
            continue

        # Elective list placeholder is completed if any actual course in that list passed.
        list_name = elective_list_for_code(c.code)
        if ncode in ELECTIVE_PLACEHOLDERS and list_name in satisfied_lists:
            continue

        miss = missing_prereq(c, passed)

        was_withdrawn = False
        if best is not None and not best.empty:
            withdrawn_match = best[
                best["ncode"].astype(str).eq(ncode)
                & best["grade"].astype(str).str.upper().eq("W")
            ]
            was_withdrawn = not withdrawn_match.empty

        status = (
            "withdrawn — register as new"
            if was_withdrawn and not miss
            else "available" if not miss
            else "blocked"
        )
        rows.append({
            "level": c.level,
            "semester": c.semester,
            "code": c.code,
            "name": c.name,
            "hours": c.hours,
            "category": c.category,
            "status": status,
            "missing_prerequisites": ", ".join(miss),
            "unlocks_next": unlocks_text(c.code),
        })

    return pd.DataFrame(rows, columns=cols)


def print_current_page(label: str):
    components.html(
        f"""
        <style>
        .print-btn {{
            border: 1px solid #cbd5e1;
            background: #ffffff;
            color: #111827;
            border-radius: 8px;
            padding: 8px 14px;
            cursor: pointer;
            font-family: Arial, sans-serif;
            font-size: 14px;
        }}
        @media print {{
            @page {{ size: A4 landscape; margin: 10mm; }}
            html, body {{ background: #ffffff !important; }}
        }}
        </style>
        <button class="print-btn" onclick="window.parent.print()">🖨️ {label}</button>
        """,
        height=48,
    )


def available_course_codes_for_term(best, extra_passed, planned_scheduled, semester):
    df = remaining_courses(best, extra_passed, planned_scheduled)
    if df.empty:
        return set()
    df = df[df["status"].isin(["available", "withdrawn — register as new"])]
    if semester in ["Fall", "Spring"]:
        df = df[df["semester"] == semester]
    return set(df["code"].astype(str).tolist())


def rebuild_planned_state_from_terms(terms):
    planned_passed = set()
    planned_improved_d = set()
    planned_scheduled = set()
    planned_failed = set()

    for term in terms:
        plan_df = term.get("plan_df", pd.DataFrame())
        if plan_df is None or plan_df.empty:
            continue

        for _, row in plan_df.iterrows():
            expected_grade = str(row.get("expected_grade", ""))
            course_code = str(row.get("course", ""))
            course_type = str(row.get("type", ""))

            planned_scheduled.add(course_code)

            if expected_grade in PASSING:
                planned_failed.discard(course_code)
                if course_type in ["New / Remaining", "Withdrawn / New", "Off-Term Graduation Exception", "Retake Failed"]:
                    planned_passed.add(course_code)
                elif course_type == "Improvement D" and point_of_grade(expected_grade) > point_of_grade("D"):
                    planned_improved_d.add(course_code)
            else:
                planned_failed.add(course_code)

    return {
        "planned_passed": planned_passed,
        "planned_improved_d": planned_improved_d,
        "planned_scheduled": planned_scheduled,
        "planned_failed": planned_failed,
    }


def apply_rebuilt_state(terms):
    rebuilt = rebuild_planned_state_from_terms(terms)
    st.session_state.planned_passed = rebuilt["planned_passed"]
    st.session_state.planned_improved_d = rebuilt["planned_improved_d"]
    st.session_state.planned_scheduled = rebuilt["planned_scheduled"]
    st.session_state.planned_failed = rebuilt["planned_failed"]


def load_term_for_edit(term, term_index):
    """
    Queue a saved term for editing.

    Widget values are not changed here because the edit button is clicked
    after Streamlit has already created the planning widgets in the same run.
    The queued values are applied safely at the start of the next rerun.
    """
    plan_df = term.get("plan_df", pd.DataFrame()).copy()

    # Remove the selected term and all later dependent terms.
    st.session_state.terms = st.session_state.terms[:term_index]
    apply_rebuilt_state(st.session_state.terms)

    payload = {
        "term_name": term.get("term_type", term.get("term_name", "Fall")),
        "term_number": term_index + 1,
        "new": [],
        "retakes": [],
        "improve": [],
        "offterm": [],
        "grades": {},
    }

    if plan_df is not None and not plan_df.empty:
        for _, row in plan_df.iterrows():
            code = str(row.get("course", ""))
            course_type = str(row.get("type", ""))
            grade = str(row.get("expected_grade", "Select"))

            if course_type == "New / Remaining":
                payload["new"].append(code)
                payload["grades"][f"new_{code}"] = grade
            elif course_type == "Off-Term Graduation Exception":
                payload["offterm"].append(code)
                payload["grades"][f"off_{code}"] = grade
            elif course_type == "Retake Failed":
                payload["retakes"].append(code)
                payload["grades"][f"ret_{code}"] = grade
            elif course_type == "Improvement D":
                payload["improve"].append(code)
                payload["grades"][f"imp_{code}"] = grade

    st.session_state["pending_term_edit"] = payload
    st.session_state.newly_unlocked = []


def apply_pending_term_edit():
    """
    Apply queued edit values before the planning widgets are instantiated.
    """
    payload = st.session_state.get("pending_term_edit")
    if not payload:
        return

    # These assignments are safe here because the widgets have not been created yet.
    for key in [
        "plan_term",
        "plan_new",
        "plan_retakes",
        "plan_improve",
        "plan_offterm",
        "allow_offterm_exception",
    ]:
        st.session_state.pop(key, None)

    st.session_state["plan_term"] = payload.get("term_name", "Fall")
    st.session_state["plan_new"] = list(payload.get("new", []))
    st.session_state["plan_retakes"] = list(payload.get("retakes", []))
    st.session_state["plan_improve"] = list(payload.get("improve", []))
    st.session_state["plan_offterm"] = list(payload.get("offterm", []))
    st.session_state["allow_offterm_exception"] = bool(payload.get("offterm", []))

    for grade_key, grade_value in payload.get("grades", {}).items():
        st.session_state[grade_key] = grade_value

    st.session_state["editing_term_number"] = payload.get("term_number")
    st.session_state["pending_term_edit"] = None


def graduation_numbers(header: Dict) -> Dict:
    passed_hours = float(header.get("passed_hours", 0))
    total_points = float(header.get("total_points", 0))
    remaining_hours = max(0, 160 - passed_hours)
    target_points = 320.0
    gap = target_points - total_points
    req_gpa_remaining = gap / remaining_hours if remaining_hours > 0 else 0
    return {
        "passed_hours": passed_hours,
        "total_points": total_points,
        "remaining_hours": remaining_hours,
        "target_points": target_points,
        "points_gap": gap,
        "required_gpa_remaining": req_gpa_remaining,
    }


def course_obj_by_code(code: str):
    return COURSE_BY_NORM.get(norm(code))



def courses_unlocked_by(code: str) -> List[str]:
    """
    Direct next courses whose prerequisite list contains this course.
    """
    ncode = norm(code)
    unlocked = []
    for course in COURSES:
        prereqs = {norm(p) for p in course.prereq}
        if ncode in prereqs:
            unlocked.append(course.code)
    return unlocked


def unlocks_text(code: str) -> str:
    unlocked = courses_unlocked_by(code)
    return ", ".join(unlocked)


def requirement_type_from_code(code: str, fallback: str = "") -> str:
    """
    Human-readable requirement type for advisor clarity.
    """
    code_s = str(code)
    if code_s == "GENXXX-A":
        return "University Elective - List A"
    if code_s == "GENXXX-B1" or code_s == "GENXXX-B2":
        return "University Elective - List B"
    if code_s == "ECE3XX-L1":
        return "Elective List 1"
    if code_s == "MEC3XX-L2":
        return "Elective List 2"
    if code_s == "MEC4XX-L3":
        return "Elective List 3"
    if code_s == "ECE4XX-L4":
        return "Elective List 4"
    if code_s == "MEC4XX-L5":
        return "Elective List 5"
    return fallback or "Unknown"


def course_label(code: str, source_df: pd.DataFrame = None) -> str:
    """
    Shows code, complete name, hours, semester and requirement type.
    A lock marker identifies courses that open later prerequisites.
    """
    c = course_obj_by_code(code)
    unlocked = unlocks_text(code)
    unlock_suffix = f" 🔓 → {unlocked}" if unlocked else ""

    if c:
        req_type = requirement_type_from_code(c.code, c.category)
        return (
            f"{c.code} — {c.name} "
            f"({c.hours} hrs | {c.semester}) "
            f"[{req_type}]{unlock_suffix}"
        )

    if source_df is not None and not source_df.empty and "code" in source_df.columns:
        row = source_df[
            source_df["code"].astype(str).apply(norm) == norm(code)
        ]
        if not row.empty:
            r = row.iloc[0]
            name = str(r.get("name", ""))
            req_type = str(
                r.get("requirement_type", r.get("category", ""))
            )
            hours = r.get("hours", "")
            semester = str(r.get("semester", ""))
            details = []
            if str(hours) not in {"", "nan"}:
                details.append(f"{hours} hrs")
            if semester and semester != "nan":
                details.append(semester)
            details_text = f" ({' | '.join(details)})" if details else ""
            requirement_text = f" [{req_type}]" if req_type and req_type != "nan" else ""
            return (
                f"{code} — {name}{details_text}"
                f"{requirement_text}{unlock_suffix}"
            )

    return f"{code}{unlock_suffix}"


def _course_visual_record(
    code: str,
    source_df: pd.DataFrame = None,
) -> Dict:
    c = course_obj_by_code(code)
    if c:
        return {
            "code": c.code,
            "name": c.name,
            "hours": c.hours,
            "semester": c.semester,
            "level": c.level,
            "requirement": requirement_type_from_code(
                c.code,
                c.category,
            ),
            "prerequisites": ", ".join(c.prereq) if c.prereq else "",
            "unlocks": courses_unlocked_by(c.code),
        }

    if (
        source_df is not None
        and not source_df.empty
        and "code" in source_df.columns
    ):
        rows = source_df[
            source_df["code"].astype(str).apply(norm) == norm(code)
        ]
        if not rows.empty:
            row = rows.iloc[0]
            return {
                "code": str(row.get("code", code)),
                "name": str(row.get("name", "")),
                "hours": row.get("hours", ""),
                "semester": str(row.get("semester", "")),
                "level": str(row.get("level", "")),
                "requirement": str(
                    row.get(
                        "requirement_type",
                        row.get("category", ""),
                    )
                ),
                "prerequisites": str(
                    row.get(
                        "prerequisite",
                        row.get("missing_prerequisites", ""),
                    )
                ),
                "unlocks": courses_unlocked_by(code),
            }

    return {
        "code": str(code),
        "name": "",
        "hours": "",
        "semester": "",
        "level": "",
        "requirement": "",
        "prerequisites": "",
        "unlocks": courses_unlocked_by(code),
    }


def _recursive_unlocked_courses(
    selected_codes: List[str],
    max_depth: int = 4,
) -> Dict[str, Dict]:
    selected_norms = {norm(code) for code in selected_codes}
    discovered = {}
    frontier = [(str(code), 0) for code in selected_codes]
    visited = set(selected_norms)

    while frontier:
        parent_code, depth = frontier.pop(0)
        if depth >= max_depth:
            continue

        for child_code in courses_unlocked_by(parent_code):
            child_norm = norm(child_code)
            if child_norm in visited:
                continue

            visited.add(child_norm)
            discovered[child_norm] = {
                "code": child_code,
                "opened_by": parent_code,
                "depth": depth + 1,
            }
            frontier.append((child_code, depth + 1))

    return discovered


def render_course_dependency_panel(
    selected_codes: List[str],
    title: str,
    is_ar: bool = False,
    source_df: pd.DataFrame = None,
    compact: bool = False,
):
    """
    Yellow cards = selected courses.
    Blue cards = courses opened by the selected prerequisite chain.
    """
    selected_codes = [
        str(code)
        for code in selected_codes
        if str(code).strip()
    ]
    if not selected_codes:
        return

    selected_records = [
        _course_visual_record(code, source_df)
        for code in selected_codes
    ]
    unlocked_map = _recursive_unlocked_courses(selected_codes)

    with st.container(border=True):
        st.markdown(f"### {title}")
        st.markdown(
            (
                "<div style='display:flex;gap:10px;flex-wrap:wrap;"
                "margin-bottom:10px'>"
                "<span style='background:#FFF3BF;border:1px solid #E5B700;"
                "padding:5px 10px;border-radius:10px;font-weight:700'>"
                "المادة المختارة</span>"
                "<span style='background:#E7F3FF;border:1px solid #3694E5;"
                "padding:5px 10px;border-radius:10px;font-weight:700'>"
                "مادة اتفتحت بسبب الاختيار</span>"
                "</div>"
            )
            if is_ar else
            (
                "<div style='display:flex;gap:10px;flex-wrap:wrap;"
                "margin-bottom:10px'>"
                "<span style='background:#FFF3BF;border:1px solid #E5B700;"
                "padding:5px 10px;border-radius:10px;font-weight:700'>"
                "Selected course</span>"
                "<span style='background:#E7F3FF;border:1px solid #3694E5;"
                "padding:5px 10px;border-radius:10px;font-weight:700'>"
                "Course unlocked by selection</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        selected_html = []
        for record in selected_records:
            unlocked = record.get("unlocks", [])
            unlocked_text = (
                ", ".join(unlocked)
                if unlocked else
                ("لا تفتح مادة مباشرة" if is_ar else "No direct unlock")
            )
            prerequisites = (
                record.get("prerequisites", "")
                or ("لا يوجد" if is_ar else "None")
            )

            detail_lines = ""
            if not compact:
                detail_lines = f"""
                  <div style="margin-top:5px;color:#4B5563;font-size:12px">
                    {'الساعات' if is_ar else 'Hours'}:
                    <b>{html_lib.escape(str(record.get('hours', '')))}</b>
                    &nbsp; | &nbsp;
                    {'الترم' if is_ar else 'Semester'}:
                    <b>{html_lib.escape(str(record.get('semester', '')))}</b>
                    &nbsp; | &nbsp;
                    {'المستوى' if is_ar else 'Level'}:
                    <b>{html_lib.escape(str(record.get('level', '')))}</b>
                  </div>
                  <div style="margin-top:4px;color:#4B5563;font-size:12px">
                    {'النوع' if is_ar else 'Requirement'}:
                    <b>{html_lib.escape(str(record.get('requirement', '')))}</b>
                  </div>
                  <div style="margin-top:4px;color:#4B5563;font-size:12px">
                    {'المتطلبات السابقة' if is_ar else 'Prerequisites'}:
                    <b>{html_lib.escape(str(prerequisites))}</b>
                  </div>
                """

            selected_html.append(
                f"""
                <div style="
                    background:#FFF8D8;
                    border:1.5px solid #E5B700;
                    border-right:6px solid #E5B700;
                    border-radius:12px;
                    padding:11px;
                    margin-bottom:8px;
                ">
                  <div style="font-size:14px;font-weight:800;color:#4B3A00">
                    {html_lib.escape(str(record.get('code', '')))}
                    — {html_lib.escape(str(record.get('name', '')))}
                  </div>
                  {detail_lines}
                  <div style="margin-top:6px;color:#095D9F;font-size:12px">
                    🔓 {'تفتح مباشرة' if is_ar else 'Directly unlocks'}:
                    <b>{html_lib.escape(str(unlocked_text))}</b>
                  </div>
                </div>
                """
            )

        st.markdown("".join(selected_html), unsafe_allow_html=True)

        if unlocked_map:
            st.markdown(
                "**المواد التي اتفتحت في مسار المتطلبات:**"
                if is_ar else
                "**Courses opened through the prerequisite chain:**"
            )

            unlocked_html = []
            for child in sorted(
                unlocked_map.values(),
                key=lambda item: (
                    int(item.get("depth", 0)),
                    str(item.get("code", "")),
                ),
            ):
                record = _course_visual_record(child.get("code", ""))
                depth = int(child.get("depth", 1))
                depth_label = (
                    f"مستوى الفتح {depth}"
                    if is_ar else
                    f"Unlock level {depth}"
                )

                unlocked_html.append(
                    f"""
                    <div style="
                        background:#EAF4FF;
                        border:1px solid #3694E5;
                        border-right:6px solid #3694E5;
                        border-radius:12px;
                        padding:9px 11px;
                        margin-bottom:7px;
                    ">
                      <div style="font-size:14px;font-weight:800;color:#075A9C">
                        {html_lib.escape(str(record.get('code', '')))}
                        — {html_lib.escape(str(record.get('name', '')))}
                      </div>
                      <div style="margin-top:4px;color:#374151;font-size:12px">
                        {'اتفتحت بسبب' if is_ar else 'Opened by'}:
                        <b>{html_lib.escape(str(child.get('opened_by', '')))}</b>
                        &nbsp; | &nbsp;
                        {html_lib.escape(depth_label)}
                        &nbsp; | &nbsp;
                        {'الساعات' if is_ar else 'Hours'}:
                        <b>{html_lib.escape(str(record.get('hours', '')))}</b>
                        &nbsp; | &nbsp;
                        {'الترم' if is_ar else 'Semester'}:
                        <b>{html_lib.escape(str(record.get('semester', '')))}</b>
                      </div>
                    </div>
                    """
                )

            st.markdown(
                "".join(unlocked_html),
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "المواد المختارة لا تفتح مواد أخرى مباشرة."
                if is_ar else
                "The selected courses do not directly unlock other courses."
            )


def highlight_unlocking_course_rows(row):
    has_unlocks = bool(str(row.get("unlocks_next", "")).strip())
    style = (
        "background-color: #EAF4FF; color: #075A9C;"
        if has_unlocks else ""
    )
    return [style] * len(row)


def add_course_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds readable columns for tables: Course Display and Requirement Type.
    """
    if df.empty or "code" not in df.columns:
        return df

    out = df.copy()
    req_types = []
    displays = []
    for _, row in out.iterrows():
        code = row.get("code", "")
        c = course_obj_by_code(code)
        fallback = row.get("category", "")
        req_type = requirement_type_from_code(code, c.category if c else fallback)
        req_types.append(req_type)
        name = row.get("name", c.name if c else "")
        displays.append(f"{code} — {name}")
    out["course_display"] = displays
    out["requirement_type"] = req_types
    out["unlocks_next"] = out["code"].apply(unlocks_text)
    return out


def curriculum_df() -> pd.DataFrame:
    rows = []
    for c in COURSES:
        rows.append({
            "level": c.level,
            "semester": c.semester,
            "code": c.code,
            "name": c.name,
            "hours": c.hours,
            "requirement_type": requirement_type_from_code(c.code, c.category),
            "prerequisite": ", ".join(c.prereq) if c.prereq else "",
            "unlocks_next": unlocks_text(c.code),
        })
    return pd.DataFrame(rows)



# Excel does not allow some control characters that may be extracted from PDFs.
EXCEL_ILLEGAL_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def excel_safe_value(value):
    """Remove characters that openpyxl/Excel cannot store in worksheet cells."""
    if isinstance(value, str):
        return EXCEL_ILLEGAL_CHARACTERS.sub("", value)
    return value


def sanitize_excel_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return an Excel-safe copy without changing numeric values."""
    if df is None:
        return pd.DataFrame()
    cleaned = df.copy()
    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(excel_safe_value)
    cleaned.columns = [excel_safe_value(str(column)) for column in cleaned.columns]
    return cleaned


def sanitize_excel_rows(rows):
    """Clean list-of-lists data before exporting to Excel."""
    return [
        [excel_safe_value(value) for value in row]
        for row in rows
    ]

def build_excel_report(
    header: Dict,
    attempts: pd.DataFrame,
    best: pd.DataFrame,
    terms: List[Dict],
    current_result: Dict = None,
    is_ar: bool = False,
    advisor_name: str = "",
    expected_grad_term: str = "",
    logo_bytes: bytes = None,
) -> bytes:
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.drawing.image import Image as XLImage

    output = BytesIO()
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_terms = list(terms)
    if current_result and not current_result.get("plan_df", pd.DataFrame()).empty:
        all_terms.append({
            "term_name": "Current Unsaved Term" if not is_ar else "الترم الحالي غير المحفوظ",
            "saved_date": report_date,
            "plan_df": current_result["plan_df"],
            "term_registered_hours": current_result["term_registered_hours"],
            "term_sgpa": current_result["term_sgpa"],
            "new_passed_hours": current_result["new_passed_hours"],
            "new_gpa_hours": current_result.get("new_gpa_hours", current_result["new_passed_hours"]),
            "new_total_points": current_result["new_total_points"],
            "new_cgpa": current_result["new_cgpa"],
        })

    latest = all_terms[-1] if all_terms else {}
    final_cgpa = latest.get("new_cgpa", header.get("cgpa", 0))
    final_passed = latest.get("new_passed_hours", header.get("passed_hours", 0))
    final_gpa_hours = latest.get("new_gpa_hours", header.get("gpa_hours", header.get("passed_hours", 0)))
    final_points = latest.get("new_total_points", header.get("total_points", 0))
    final_status = _report_status(final_cgpa, final_passed, is_ar)
    final_hours_note = _graduation_hours_note(final_passed, is_ar)

    training_report = _saved_training_status(header, all_terms, is_ar)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_rows = [
            [UNIVERSITY_NAME, PROGRAM_BRAND],
            ["Graduation Plan Report" if not is_ar else "تقرير خطة التخرج", ""],
            ["Report Date" if not is_ar else "تاريخ التقرير", report_date],
            ["Student Name" if not is_ar else "اسم الطالب", header.get("student_name", "")],
            ["Student ID" if not is_ar else "كود الطالب", header.get("student_id", "")],
            ["Academic Program" if not is_ar else "البرنامج الأكاديمي", header.get("program", "")],
            ["Academic Advisor" if not is_ar else "المرشد الأكاديمي", advisor_name],
            ["Expected Graduation Term" if not is_ar else "الترم المتوقع للتخرج", expected_grad_term],
            ["Initial CGPA" if not is_ar else "المعدل الحالي", header.get("cgpa", 0)],
            ["Initial Passed Hours" if not is_ar else "الساعات المجتازة", header.get("passed_hours", 0)],
            ["Corona Excluded Hours" if not is_ar else "ساعات كورونا المستبعدة", header.get("corona_excluded_hours", 0)],
            ["Initial GPA Hours" if not is_ar else "ساعات حساب المعدل", header.get("gpa_hours", header.get("passed_hours", 0))],
            ["Initial Total Points" if not is_ar else "إجمالي النقاط الحالي", header.get("total_points", 0)],
            ["Final Expected CGPA" if not is_ar else "المعدل المتوقع النهائي", final_cgpa],
            ["Final Expected Passed Hours" if not is_ar else "الساعات المتوقعة النهائية", final_passed],
            ["Graduation Hours Explanation" if not is_ar else "توضيح ساعات التخرج", final_hours_note],
            ["Final Expected GPA Hours" if not is_ar else "ساعات حساب المعدل النهائية", final_gpa_hours],
            ["Final Expected Total Points" if not is_ar else "إجمالي النقاط النهائي", final_points],
            ["Final Status" if not is_ar else "الحالة النهائية", final_status],
            ["Training 1 Status" if not is_ar else "حالة تدريب 1", training_report["training1_status"]],
            ["Training 2 Status" if not is_ar else "حالة تدريب 2", training_report["training2_status"]],
            ["Training Progress" if not is_ar else "متابعة التدريب", training_report["headline"]],
        ]
        pd.DataFrame(sanitize_excel_rows(summary_rows)).to_excel(writer, sheet_name="Student Summary", index=False, header=False)

        plan_summary = []
        combined_rows = []
        for i, term in enumerate(all_terms, start=1):
            plan = term.get("plan_df", pd.DataFrame()).copy()
            if plan.empty:
                continue
            plan.insert(0, "Term No.", i)
            plan.insert(1, "Term", term.get("term_name", ""))
            plan.insert(2, "Saved Date", term.get("saved_date", ""))
            plan = sanitize_excel_dataframe(plan)
            plan.to_excel(writer, sheet_name=f"Term {i}", index=False)
            combined_rows.append(plan)
            plan_summary.append({
                "No.": i,
                "Term": term.get("term_name", ""),
                "Saved Date": term.get("saved_date", ""),
                "Registered Hours": term.get("term_registered_hours", 0),
                "Expected SGPA": term.get("term_sgpa", 0),
                "Term Grade": gpa_grade_description(term.get("term_sgpa", 0), is_ar),
                "Passed Hours After": term.get("new_passed_hours", 0),
                "GPA Hours After": term.get("new_gpa_hours", term.get("new_passed_hours", 0)),
                "Total Points After": term.get("new_total_points", 0),
                "CGPA After": term.get("new_cgpa", 0),
                "Cumulative Grade": gpa_grade_description(term.get("new_cgpa", 0), is_ar),
                "Next Regular-Term Load": regular_load_limit_for_cgpa(
                    term.get("new_cgpa", 0)
                ),
            })

        sanitize_excel_dataframe(pd.DataFrame(plan_summary)).to_excel(writer, sheet_name="Plan Summary", index=False)
        if combined_rows:
            sanitize_excel_dataframe(pd.concat(combined_rows, ignore_index=True)).to_excel(writer, sheet_name="Graduation Plan", index=False)
        final_summary_rows = [
            ["Final Expected CGPA", final_cgpa],
            ["Final Cumulative Grade", gpa_grade_description(final_cgpa, is_ar)],
            ["Final Expected Passed Hours", final_passed],
            ["Final Expected GPA Hours", final_gpa_hours],
            ["Final Expected Total Points", final_points],
            ["Final Status", final_status],
            ["Academic Advisor Signature", ""],
            ["Student Signature", ""],
            ["Department Approval", ""],
        ]
        pd.DataFrame(sanitize_excel_rows(final_summary_rows)).to_excel(
            writer,
            sheet_name="Final Summary",
            index=False,
            header=False,
        )

        wb = writer.book

        if "Student Summary" in wb.sheetnames:
            summary_ws = wb["Student Summary"]
            summary_ws.merge_cells("D1:G1")
            summary_ws["D1"] = UNIVERSITY_NAME
            summary_ws["D1"].font = Font(bold=True, size=15, color="0B5FA5")
            summary_ws["D1"].alignment = Alignment(horizontal="center")
            summary_ws.merge_cells("D2:G2")
            summary_ws["D2"] = PROGRAM_BRAND
            summary_ws["D2"].font = Font(bold=True, size=12, color="F28C00")
            summary_ws["D2"].alignment = Alignment(horizontal="center")
            summary_ws.merge_cells("D3:G11")

            if logo_bytes:
                try:
                    xl_logo = XLImage(BytesIO(logo_bytes))
                    xl_logo.width = 170
                    xl_logo.height = 154
                    summary_ws.add_image(xl_logo, "E3")
                except Exception:
                    pass

            for col in ["C", "D", "E", "F", "G"]:
                summary_ws.column_dimensions[col].width = 18

        navy = "123C69"
        blue = "1F6F8B"
        light = "EAF1F8"
        green = "E8F5E9"
        thin_side = Side(style="thin", color="CBD5E1")
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        for ws in wb.worksheets:
            # Final safety pass for values created directly by openpyxl/pandas.
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str):
                        cell.value = excel_safe_value(cell.value)

            ws.sheet_view.showGridLines = False
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.orientation = "landscape"
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.oddFooter.center.text = (
                f"{UNIVERSITY_NAME} | {PROGRAM_BRAND} | {report_date}"
            )
            ws.freeze_panes = "A2" if ws.title not in ["Student Summary", "Final Summary"] else None

            for row in ws.iter_rows():
                for cell in row:
                    cell.border = border
                    cell.alignment = Alignment(vertical="center", wrap_text=True)

            if ws.title in ["Student Summary", "Final Summary"]:
                if ws.title == "Student Summary":
                    ws.merge_cells("A1:B1")
                    ws["A1"].fill = PatternFill("solid", fgColor=navy)
                    ws["A1"].font = Font(color="FFFFFF", bold=True, size=16)
                    ws["A1"].alignment = Alignment(horizontal="center")
                for r in range(2 if ws.title == "Student Summary" else 1, ws.max_row + 1):
                    ws[f"A{r}"].fill = PatternFill("solid", fgColor=light)
                    ws[f"A{r}"].font = Font(bold=True)
                ws.column_dimensions["A"].width = 34
                ws.column_dimensions["B"].width = 38
            else:
                for cell in ws[1]:
                    cell.fill = PatternFill("solid", fgColor=navy)
                    cell.font = Font(color="FFFFFF", bold=True)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                ws.auto_filter.ref = ws.dimensions
                ws.print_title_rows = "1:1"
                for col_idx in range(1, ws.max_column + 1):
                    max_len = 0
                    for row_idx in range(1, min(ws.max_row, 250) + 1):
                        value = ws.cell(row_idx, col_idx).value
                        max_len = max(max_len, len(str(value)) if value is not None else 0)
                    ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 2, 12), 34)

            ws.print_area = ws.dimensions

    return output.getvalue()

def compute_one_term(
    header: Dict,
    new_course_codes: List[str],
    retake_df: pd.DataFrame,
    improvement_df: pd.DataFrame,
    expected_grades: Dict[str, str],
    offterm_course_codes: List[str] = None,
) -> Dict:
    """
    New courses add attempted GPA hours even when the grade is F.
    Retakes replace the old F points without repeating GPA hours.
    D improvements add only the point difference.
    """
    current_hours = float(header.get("passed_hours", 0))
    current_gpa_hours = float(header.get("gpa_hours", current_hours))
    current_cgpa = float(header.get("cgpa", 0))
    header_points = float(header.get("total_points", 0))
    calculated_current_points = current_cgpa * current_gpa_hours

    # Protect the planner from a wrongly extracted historical T.Points value.
    current_points = (
        header_points
        if abs(header_points - calculated_current_points) <= 0.15
        else calculated_current_points
    )

    rows = []
    term_registered_hours = 0.0
    term_quality_points_for_sgpa = 0.0
    added_hours = 0.0
    added_points = 0.0
    improvement_gain = 0.0

    offterm_course_codes = offterm_course_codes or []
    offterm_set = {norm(code) for code in offterm_course_codes}

    # New / remaining courses, including approved off-term graduation exceptions
    all_new_codes = list(dict.fromkeys(list(new_course_codes) + list(offterm_course_codes)))
    for code in all_new_codes:
        c = course_obj_by_code(code)
        if not c:
            continue
        is_offterm = norm(code) in offterm_set
        grade_key = f"OFF::{code}" if is_offterm else f"NEW::{code}"
        grade = expected_grades.get(grade_key, "Select")
        gp = point_of_grade(grade)
        term_registered_hours += c.hours
        term_quality_points_for_sgpa += gp * c.hours

        passed = is_passing_grade(grade)
        if passed:
            added_hours += c.hours
        added_points += gp * c.hours

        rows.append({
            "course": code,
            "name": c.name,
            "type": "Off-Term Graduation Exception" if is_offterm else "New / Remaining",
            "requirement_type": requirement_type_from_code(code, c.category),
            "current_grade": "-",
            "expected_grade": grade,
            "hours": c.hours,
            "effect": (
                "Adds GPA attempted hours and points; passed hours increase if passed"
                if passed else
                "F adds attempted GPA hours with zero points"
            ),
            "points_effect": gp * c.hours,
            "unlocks_next": unlocks_text(code),
        })

    # Retake failed courses
    for _, r in retake_df.iterrows():
        code = r["code"]
        attempts_count = int(r.get("attempts_count", 1) or 1)
        max_allowed_grade = retake_max_allowed_grade(attempts_count)
        entered_grade = expected_grades.get(f"RET::{code}", "Select")
        grade = cap_retake_grade(entered_grade, attempts_count)
        gp = point_of_grade(grade)
        hours = int(r["hours"])
        term_registered_hours += hours
        term_quality_points_for_sgpa += gp * hours

        passed = is_passing_grade(grade)
        if passed:
            added_hours += hours
            added_points += gp * hours

        rows.append({
            "course": code,
            "name": r["name"],
            "type": "Retake Failed",
            "requirement_type": requirement_type_from_code(code, ""),
            "current_grade": r.get("effective_grade", r.get("latest_grade", "")),
            "expected_grade": grade,
            "attempts_count": attempts_count,
            "max_allowed_grade": max_allowed_grade,
            "grade_cap_applied": (
                entered_grade != grade
                and entered_grade not in {"", "Select"}
            ),
            "hours": hours,
            "effect": (
                f"Retake cap: {max_allowed_grade}; replace F points without repeating GPA hours"
                if passed else
                f"Retake cap: {max_allowed_grade}; F remains zero points"
            ),
            "points_effect": gp * hours if passed else 0,
            "unlocks_next": unlocks_text(code),
        })

    # Improvement D only
    for _, r in improvement_df.iterrows():
        code = r["code"]
        grade = expected_grades.get(f"IMP::{code}", "Select")
        gp = point_of_grade(grade)
        current_gp = float(r["current_points"])
        hours = int(r["hours"])
        gain = max(0, (gp - current_gp) * hours)

        # Improvement can be part of semester load; it does not add passed hours.
        term_registered_hours += hours
        term_quality_points_for_sgpa += gp * hours
        improvement_gain += gain

        rows.append({
            "course": code,
            "name": r["name"],
            "type": "Improvement D",
            "requirement_type": requirement_type_from_code(code, ""),
            "current_grade": r["current_grade"],
            "expected_grade": grade,
            "hours": hours,
            "effect": "Point difference only",
            "points_effect": gain,
            "unlocks_next": unlocks_text(code),
        })

    new_total_points = current_points + added_points + improvement_gain
    new_passed_hours = current_hours + added_hours
    first_time_attempted_hours = sum(
        course_obj_by_code(code).hours
        for code in all_new_codes
        if course_obj_by_code(code) is not None
    )
    new_gpa_hours = current_gpa_hours + first_time_attempted_hours
    new_cgpa = new_total_points / new_gpa_hours if new_gpa_hours else 0
    sgpa = term_quality_points_for_sgpa / term_registered_hours if term_registered_hours else 0

    return {
        "plan_df": pd.DataFrame(rows),
        "term_registered_hours": term_registered_hours,
        "term_sgpa": sgpa,
        "added_hours": added_hours,
        "added_points": added_points,
        "improvement_gain": improvement_gain,
        "new_total_points": new_total_points,
        "new_passed_hours": new_passed_hours,
        "new_gpa_hours": new_gpa_hours,
        "new_cgpa": new_cgpa,
        "term_grade": gpa_grade_description(sgpa, False),
        "cumulative_grade": gpa_grade_description(new_cgpa, False),
        "next_regular_load": regular_load_limit_for_cgpa(new_cgpa),
        "next_regular_load_description": registration_load_description(new_cgpa, False),
    }



def _graduation_hours_note(final_hours: float, is_ar: bool = False) -> str:
    value = float(final_hours or 0)
    if value > 160:
        extra = value - 160
        return (
            f"الساعات المتوقعة {value:.0f}: تشمل {extra:.0f} ساعة زيادة عن متطلب التخرج 160 ساعة."
            if is_ar else
            f"Expected passed hours are {value:.0f}, including {extra:.0f} hours above the 160-hour graduation requirement."
        )
    if value == 160:
        return (
            "الساعات المتوقعة تساوي متطلب التخرج: 160 ساعة."
            if is_ar else
            "Expected passed hours equal the 160-hour graduation requirement."
        )
    remaining = 160 - value
    return (
        f"ما زال يحتاج {remaining:.0f} ساعة للوصول إلى 160 ساعة."
        if is_ar else
        f"{remaining:.0f} hours are still needed to reach 160."
    )


def _report_status(final_cgpa: float, final_hours: float, is_ar: bool = False) -> str:
    hours_note = _graduation_hours_note(final_hours, is_ar)
    if final_hours >= 160 and final_cgpa >= 2:
        return (
            f"مستوفي متطلبات التخرج. {hours_note}"
            if is_ar else
            f"Graduation requirements completed. {hours_note}"
        )
    if final_cgpa >= 2:
        return (
            f"وصل لمعدل 2.00 ويحتاج استكمال المتطلبات. {hours_note}"
            if is_ar else
            f"CGPA target met; complete remaining requirements. {hours_note}"
        )
    gap = max(0, 2-final_cgpa)
    return (
        f"يحتاج رفع المعدل بمقدار {gap:.3f} للوصول إلى 2.00. {hours_note}"
        if is_ar else
        f"Needs {gap:.3f} CGPA to reach 2.00. {hours_note}"
    )




def build_graduation_report_html(
    header: Dict,
    terms: List[Dict],
    advisor_name: str = "",
    expected_grad_term: str = "",
    is_ar: bool = False,
    logo_bytes: bytes = None,
) -> str:
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    direction = "rtl" if is_ar else "ltr"
    title = "تقرير خطة التخرج" if is_ar else "Graduation Plan Report"
    university_name = UNIVERSITY_NAME
    program_brand = PROGRAM_BRAND

    latest = terms[-1] if terms else {}
    final_cgpa = float(latest.get("new_cgpa", header.get("cgpa", 0)))
    final_hours = float(latest.get("new_passed_hours", header.get("passed_hours", 0)))
    final_gpa_hours = float(
        latest.get("new_gpa_hours", header.get("gpa_hours", final_hours))
    )
    final_points = float(
        latest.get("new_total_points", header.get("total_points", 0))
    )
    remaining_hours = max(0.0, 160.0 - float(header.get("passed_hours", 0)))
    final_status = _report_status(final_cgpa, final_hours, is_ar)
    training_report = _saved_training_status(header, terms, is_ar)

    logo_html = ""
    if logo_bytes:
        mime = "image/png"
        logo_html = (
            f'<img class="logo" src="data:{mime};base64,'
            f'{base64.b64encode(logo_bytes).decode("ascii")}">'
        )

    summary_rows = []
    term_pages = []

    for i, term in enumerate(terms, start=1):
        plan_df = term.get("plan_df", pd.DataFrame())
        course_rows = []
        for _, row in plan_df.iterrows():
            course_rows.append(
                f"""
                <tr>
                  <td>{html_lib.escape(str(row.get('course','')))}</td>
                  <td>{html_lib.escape(str(row.get('name','')))}</td>
                  <td>{html_lib.escape(str(row.get('type','')))}</td>
                  <td>{html_lib.escape(str(row.get('requirement_type','')))}</td>
                  <td>{html_lib.escape(str(row.get('current_grade','-')))}</td>
                  <td><b>{html_lib.escape(str(row.get('expected_grade','')))}</b></td>
                  <td>{row.get('hours',0)}</td>
                </tr>
                """
            )

        term_pages.append(
            f"""
            <section class="page term-page">
              <div class="page-heading">
                <div>
                  <div style="font-size:11px;font-weight:800;color:#333333">
                    {html_lib.escape(UNIVERSITY_NAME)}
                  </div>
                  <div style="font-size:10px;font-weight:700;color:#666666">
                    {html_lib.escape(PROGRAM_BRAND)}
                  </div>
                  <div class="eyebrow">{'الخطة الدراسية' if is_ar else 'STUDY PLAN'}</div>
                  <h2>{'الترم' if is_ar else 'Term'} {i}: {html_lib.escape(str(term.get('term_name','')))}</h2>
                </div>
                <div class="term-badge">{term.get('term_registered_hours',0):.0f} {'ساعة' if is_ar else 'Hours'}</div>
              </div>

              <table class="courses">
                <thead>
                  <tr>
                    <th>{'الكود' if is_ar else 'Code'}</th>
                    <th>{'اسم المادة' if is_ar else 'Course Name'}</th>
                    <th>{'النوع' if is_ar else 'Type'}</th>
                    <th>{'المتطلب' if is_ar else 'Requirement'}</th>
                    <th>{'الحالي' if is_ar else 'Current'}</th>
                    <th>{'المتوقع' if is_ar else 'Expected'}</th>
                    <th>{'الساعات' if is_ar else 'Hours'}</th>
                  </tr>
                </thead>
                <tbody>{''.join(course_rows)}</tbody>
              </table>

              <div class="term-kpis">
                <div><span>{'ساعات الترم' if is_ar else 'Term Hours'}</span><strong>{term.get('term_registered_hours',0):.0f}</strong></div>
                <div><span>SGPA</span><strong>{term.get('term_sgpa',0):.3f}</strong></div>
                <div><span>{'تقدير الترم' if is_ar else 'Term Grade'}</span><strong>{html_lib.escape(gpa_grade_description(term.get('term_sgpa',0), is_ar))}</strong></div>
                <div><span>{'الساعات بعد الترم' if is_ar else 'Passed Hours After'}</span><strong>{term.get('new_passed_hours',0):.0f}</strong></div>
                <div><span>CGPA</span><strong>{term.get('new_cgpa',0):.3f}</strong></div>
                <div><span>{'التقدير التراكمي' if is_ar else 'Cumulative Grade'}</span><strong>{html_lib.escape(gpa_grade_description(term.get('new_cgpa',0), is_ar))}</strong></div>
                <div><span>{'ساعات الترم العادي التالي' if is_ar else 'Next Regular-Term Load'}</span><strong>{regular_load_limit_for_cgpa(term.get('new_cgpa',0))}</strong></div>
              </div>

              <div class="term-signatures">
                <div>{'توقيع المرشد' if is_ar else 'Advisor Initials'}: __________________</div>
                <div>{'تاريخ المراجعة' if is_ar else 'Review Date'}: __________________</div>
              </div>
            </section>
            """
        )

        summary_rows.append(
            f"""
            <tr>
              <td>{i}</td>
              <td>{html_lib.escape(str(term.get('term_name','')))}</td>
              <td>{term.get('term_registered_hours',0):.0f}</td>
              <td>{term.get('term_sgpa',0):.3f}</td>
              <td>{html_lib.escape(gpa_grade_description(term.get('term_sgpa',0), is_ar))}</td>
              <td>{term.get('new_passed_hours',0):.0f}</td>
              <td>{term.get('new_cgpa',0):.3f}</td>
              <td>{html_lib.escape(gpa_grade_description(term.get('new_cgpa',0), is_ar))}</td>
              <td>{regular_load_limit_for_cgpa(term.get('new_cgpa',0))}</td>
            </tr>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="{'ar' if is_ar else 'en'}" dir="{direction}">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
@page {{ size: A4 landscape; margin: 10mm; }}
* {{ box-sizing: border-box; }}
html,body {{ margin:0; background:#f1f1f1; color:#172033; font-family:Tahoma,Arial,sans-serif; }}
.page {{
  width:277mm; min-height:190mm; margin:10mm auto; padding:11mm 13mm;
  background:white; box-shadow:0 4px 22px rgba(15,23,42,.12);
  position:relative; page-break-after:always;
}}
.page:last-child {{ page-break-after:auto; }}
.brand-header {{
  display:grid; grid-template-columns:75px 1fr 75px; align-items:center;
  padding-bottom:10px; border-bottom:4px solid #222222;
}}
.logo {{ width:66px; height:58px; object-fit:contain; }}
.title {{ text-align:center; }}
.university-name {{
  color:#333333; font-size:16px; font-weight:800;
  line-height:1.25; margin-bottom:2px;
}}
.program-brand {{
  color:#666666; font-size:12px; font-weight:700; margin-top:2px;
}}
.title h1 {{ margin:0; color:#222222; font-size:27px; }}
.title p {{ margin:5px 0 0; color:#697789; font-size:12px; }}
.meta {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:15px 0; }}
.card {{ border:1px solid #d7e0ea; border-radius:7px; padding:9px; background:#fbfdff; }}
.label,.eyebrow {{ color:#66768a; font-size:10px; }}
.value {{ font-weight:700; margin-top:3px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:12px 0; }}
.term-kpis {{ display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin:12px 0; }}
.kpis .card strong,.term-kpis strong {{ display:block; color:#222222; font-size:20px; margin-top:3px; }}
h2 {{ color:#222222; margin:0; font-size:20px; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; }}
th,td {{ border:1px solid #cfdae6; padding:6px 7px; font-size:10px; vertical-align:top; }}
th {{ background:#222222; color:white; }}
tbody tr:nth-child(even) {{ background:#F5F5F5; }}
.summary th,.summary td {{ text-align:center; }}
.result {{
  margin-top:14px; border:2px solid '#333333';
  border-radius:9px; padding:14px; text-align:center; background:#fbfefc;
}}
.result .big {{ font-size:26px; color:#222222; font-weight:800; }}
.summary-page {{ padding-bottom:40mm; }}
.signatures {{
  position:absolute; left:13mm; right:13mm; bottom:17mm;
  display:grid; grid-template-columns:repeat(3,1fr);
  gap:45px; margin:0; text-align:center;
}}
.sign {{ border-top:1px solid #253247; padding-top:7px; }}
.page-heading {{ display:flex; justify-content:space-between; align-items:center; padding-bottom:9px; border-bottom:3px solid #222222; margin-bottom:12px; }}
.term-badge {{ background:#222222; color:white; border-radius:18px; padding:7px 14px; font-weight:700; }}
.term-kpis div {{ border:1px solid #d7e0ea; border-radius:7px; padding:8px; background:#f8fbfe; }}
.term-kpis span {{ color:#66768a; font-size:10px; }}
.term-signatures {{ display:flex; justify-content:space-between; margin-top:17px; color:#536174; font-size:11px; }}
.training-status {{ display:grid; grid-template-columns:1fr 1fr 2fr; gap:8px; margin:12px 0; }}
.training-status > div {{ border:1px solid #c9d8e7; background:#f7fbff; border-radius:7px; padding:9px; }}
.training-status span {{ display:block; color:#66768a; font-size:10px; }}
.training-status strong {{ display:block; color:#222222; margin-top:3px; font-size:12px; }}
.training-headline {{ display:flex; align-items:center; font-weight:700; color:#222222; }}
.footer {{ position:absolute; bottom:7mm; left:13mm; right:13mm; text-align:center; color:#718096; font-size:9px; border-top:1px solid #d7e0ea; padding-top:5px; }}
@media print {{
  html,body {{ background:white; filter:grayscale(1); }}
  .page {{ margin:0; box-shadow:none; width:auto; min-height:0; }}
}}
</style>
</head>
<body>
<section class="page summary-page">
  <header class="brand-header">
    <div>{logo_html}</div>
    <div class="title">
      <div class="university-name">{html_lib.escape(university_name)}</div>
      <div class="program-brand">{html_lib.escape(program_brand)}</div>
      <h1>{title}</h1>
      <p>{'خطة أكاديمية رسمية مبنية على السجل الدراسي والتقديرات المتوقعة' if is_ar else 'Formal academic plan based on student history and expected grades'}</p>
    </div>
    <div></div>
  </header>

  <div class="meta">
    <div class="card"><div class="label">{'اسم الطالب' if is_ar else 'Student Name'}</div><div class="value">{html_lib.escape(str(header.get('student_name','')))}</div></div>
    <div class="card"><div class="label">{'كود الطالب' if is_ar else 'Student ID'}</div><div class="value">{html_lib.escape(str(header.get('student_id','')))}</div></div>
    <div class="card"><div class="label">{'البرنامج' if is_ar else 'Program'}</div><div class="value">{html_lib.escape(str(header.get('program','')))}</div></div>
    <div class="card"><div class="label">{'المرشد الأكاديمي' if is_ar else 'Academic Advisor'}</div><div class="value">{html_lib.escape(advisor_name)}</div></div>
    <div class="card"><div class="label">{'التخرج المتوقع' if is_ar else 'Expected Graduation'}</div><div class="value">{html_lib.escape(expected_grad_term)}</div></div>
    <div class="card"><div class="label">{'تاريخ إعداد الخطة' if is_ar else 'Plan Date'}</div><div class="value">{report_date}</div></div>
  </div>

  <div class="kpis">
    <div class="card"><div class="label">{'المعدل الحالي' if is_ar else 'Current CGPA'}</div><strong>{header.get('cgpa',0):.3f}</strong></div>
    <div class="card"><div class="label">{'الساعات المجتازة' if is_ar else 'Passed Hours'}</div><strong>{header.get('passed_hours',0):.0f}</strong></div>
    <div class="card"><div class="label">{'الساعات المتبقية' if is_ar else 'Remaining Hours'}</div><strong>{remaining_hours:.0f}</strong></div>
    <div class="card"><div class="label">{'المعدل المتوقع' if is_ar else 'Expected Final CGPA'}</div><strong>{final_cgpa:.3f}</strong></div>
  </div>

  <div class="training-status">
    <div>
      <span>{'حالة تدريب 1' if is_ar else 'Training 1'}</span>
      <strong>{html_lib.escape(training_report['training1_status'])}</strong>
    </div>
    <div>
      <span>{'حالة تدريب 2' if is_ar else 'Training 2'}</span>
      <strong>{html_lib.escape(training_report['training2_status'])}</strong>
    </div>
    <div class="training-headline">{html_lib.escape(training_report['headline'])}</div>
  </div>

  <h2 style="margin:14px 0 8px">{'ملخص الخطة الدراسية' if is_ar else 'Graduation Plan Summary'}</h2>
  <table class="summary">
    <thead><tr>
      <th>#</th><th>{'الترم' if is_ar else 'Term'}</th><th>{'الساعات' if is_ar else 'Hours'}</th>
      <th>SGPA</th><th>{'تقدير الترم' if is_ar else 'Term Grade'}</th>
      <th>{'الساعات بعد الترم' if is_ar else 'Passed Hours After'}</th>
      <th>CGPA</th><th>{'التقدير التراكمي' if is_ar else 'Cumulative Grade'}</th>
      <th>{'ساعات الترم التالي' if is_ar else 'Next Regular Load'}</th>
    </tr></thead>
    <tbody>{''.join(summary_rows)}</tbody>
  </table>

  <div class="result">
    <div class="label">{'النتيجة النهائية المتوقعة' if is_ar else 'Expected Final Result'}</div>
    <div class="big">CGPA {final_cgpa:.3f}</div>
    <div><b>{html_lib.escape(gpa_grade_description(final_cgpa, is_ar))}</b></div>
    <div>{final_status}</div>
    <div style="margin-top:5px;font-size:11px">
      {'الساعات المتوقعة' if is_ar else 'Expected Passed Hours'}: {final_hours:.0f}
      &nbsp;|&nbsp; {'النقاط' if is_ar else 'Total Points'}: {final_points:.1f}
      &nbsp;|&nbsp; {'ساعات المعدل' if is_ar else 'GPA Hours'}: {final_gpa_hours:.0f}
    </div>
  </div>

  <div class="signatures">
    <div class="sign">{'توقيع المرشد الأكاديمي' if is_ar else 'Academic Advisor Signature'}</div>
    <div class="sign">{'توقيع الطالب' if is_ar else 'Student Signature'}</div>
    <div class="sign">{'اعتماد القسم' if is_ar else 'Department Approval'}</div>
  </div>
  <div class="footer">{html_lib.escape(UNIVERSITY_NAME)} | {html_lib.escape(PROGRAM_BRAND)} | {report_date}</div>
</section>

{''.join(term_pages)}
</body>
</html>"""



def _pdf_font_name():
    if not REPORTLAB_OK:
        return "Helvetica"
    candidates = [
        r"C:\\Windows\\Fonts\\arial.ttf", r"C:\\Windows\\Fonts\\tahoma.ttf", r"C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("PlannerUnicode", path))
                return "PlannerUnicode"
            except Exception:
                pass
    return "Helvetica"


def _contains_arabic(value) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", str(value or "")))


def _pdf_text(value, is_ar=False):
    """
    Shape every Arabic string for ReportLab, even inside an English report.

    This is required for Arabic student/advisor names. ReportLab otherwise
    renders Arabic letters disconnected and in the wrong visual order.
    """
    text = str(value or "")
    if ARABIC_PDF_OK and _contains_arabic(text):
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


def _pdf_value_paragraph(value, normal_style, rtl_style):
    """Use right alignment for Arabic identity values inside English reports."""
    style = rtl_style if _contains_arabic(value) else normal_style
    return Paragraph(_pdf_text(value), style)


def build_pdf_report(
    header: Dict,
    terms: List[Dict],
    advisor_name: str = "",
    expected_grad_term: str = "",
    is_ar: bool = False,
    logo_bytes: bytes = None,
) -> bytes:
    if not REPORTLAB_OK:
        raise RuntimeError(
            "PDF packages are missing. Run INSTALL_AND_TEST.bat again."
        )

    output = BytesIO()
    font_name = _pdf_font_name()
    # Final downloadable report is portrait A4.
    page_size = A4

    doc = SimpleDocTemplate(
        output,
        pagesize=page_size,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=25 * mm,
        title="Graduation Plan Report",
        author="Graduation Planner",
    )

    styles = getSampleStyleSheet()
    align = TA_RIGHT if is_ar else TA_LEFT

    title_style = ParagraphStyle(
        "ProfessionalTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3 * mm,
    )
    section_style = ParagraphStyle(
        "ProfessionalSection",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=11,
        leading=14,
        alignment=align,
        textColor=colors.HexColor("#222222"),
        spaceBefore=3 * mm,
        spaceAfter=2 * mm,
    )
    body_style = ParagraphStyle(
        "ProfessionalBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=7.2,
        leading=9.0,
        alignment=align,
    )
    rtl_value_style = ParagraphStyle(
        "ArabicIdentityValue",
        parent=body_style,
        alignment=TA_RIGHT,
    )
    small_style = ParagraphStyle(
        "ProfessionalSmall",
        parent=body_style,
        fontSize=6.3,
        leading=7.6,
    )
    center_style = ParagraphStyle(
        "ProfessionalCenter",
        parent=body_style,
        alignment=TA_CENTER,
    )
    kpi_label_style = ParagraphStyle(
        "KpiLabel",
        parent=center_style,
        fontSize=6.5,
        textColor=colors.HexColor("#64748B"),
    )
    kpi_value_style = ParagraphStyle(
        "KpiValue",
        parent=center_style,
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#222222"),
    )

    latest = terms[-1] if terms else {}
    final_cgpa = float(latest.get("new_cgpa", header.get("cgpa", 0)))
    final_hours = float(
        latest.get("new_passed_hours", header.get("passed_hours", 0))
    )
    final_gpa_hours = float(
        latest.get("new_gpa_hours", header.get("gpa_hours", final_hours))
    )
    final_points = float(
        latest.get("new_total_points", header.get("total_points", 0))
    )
    remaining_hours = max(
        0.0, 160.0 - float(header.get("passed_hours", 0))
    )
    status = _report_status(final_cgpa, final_hours, is_ar)
    training_report = _saved_training_status(header, terms, is_ar)

    story = []
    title = "تقرير خطة التخرج" if is_ar else "Graduation Plan Report"
    university_name = UNIVERSITY_NAME
    program_brand = PROGRAM_BRAND

    # ---------------- Summary page ----------------
    if logo_bytes:
        try:
            logo = RLImage(BytesIO(logo_bytes), width=23 * mm, height=21 * mm)
            university_title = [
                Paragraph(
                    _pdf_text(university_name, is_ar),
                    ParagraphStyle(
                        "UniversityBrand",
                        parent=title_style,
                        fontSize=13,
                        leading=15,
                        textColor=colors.HexColor("#333333"),
                        spaceAfter=1 * mm,
                    ),
                ),
                Paragraph(
                    _pdf_text(program_brand, is_ar),
                    ParagraphStyle(
                        "ProgramBrand",
                        parent=title_style,
                        fontSize=10,
                        leading=12,
                        textColor=colors.HexColor("#666666"),
                        spaceAfter=1.5 * mm,
                    ),
                ),
                Paragraph(_pdf_text(title, is_ar), title_style),
            ]
            header_table = Table(
                [[logo, university_title, ""]],
                colWidths=[25 * mm, 140 * mm, 25 * mm],
            )
            header_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 2.2, colors.HexColor("#222222")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ])
            )
            story.append(header_table)
        except Exception:
            story.append(
                Paragraph(
                    _pdf_text(
                        f"{university_name}<br/>{program_brand}<br/>{title}",
                        is_ar,
                    ),
                    title_style,
                )
            )
    else:
        story.append(
            Paragraph(
                _pdf_text(
                    f"{university_name}<br/>{program_brand}<br/>{title}",
                    is_ar,
                ),
                title_style,
            )
        )

    subtitle = (
        "خطة أكاديمية رسمية مبنية على السجل الدراسي والتقديرات المتوقعة"
        if is_ar else
        "Formal academic plan based on student history and expected grades"
    )
    story.append(Paragraph(_pdf_text(subtitle, is_ar), center_style))
    story.append(Spacer(1, 4 * mm))

    meta_rows = [
        [
            "اسم الطالب" if is_ar else "Student Name",
            header.get("student_name", ""),
            "كود الطالب" if is_ar else "Student ID",
            header.get("student_id", ""),
            "البرنامج" if is_ar else "Program",
            header.get("program", ""),
        ],
        [
            "المرشد الأكاديمي" if is_ar else "Academic Advisor",
            advisor_name,
            "التخرج المتوقع" if is_ar else "Expected Graduation",
            expected_grad_term,
            "تاريخ الخطة" if is_ar else "Plan Date",
            datetime.now().strftime("%Y-%m-%d"),
        ],
    ]
    meta_data = []
    for row in meta_rows:
        rendered_row = []
        for cell_index, value in enumerate(row):
            # Value cells are 1, 3 and 5. Arabic names are right-aligned.
            if cell_index in {1, 3, 5}:
                rendered_row.append(
                    _pdf_value_paragraph(
                        value,
                        body_style,
                        rtl_value_style,
                    )
                )
            else:
                rendered_row.append(
                    Paragraph(_pdf_text(value, is_ar), body_style)
                )
        meta_data.append(rendered_row)

    meta_table = Table(
        meta_data,
        colWidths=[
            20 * mm, 45 * mm,
            20 * mm, 35 * mm,
            20 * mm, 50 * mm,
        ],
    )
    meta_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CFDAE6")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E6E6E6")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E6E6E6")),
            ("BACKGROUND", (4, 0), (4, -1), colors.HexColor("#E6E6E6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    kpi_values = [
        (
            "المعدل الحالي" if is_ar else "Current CGPA",
            f"{header.get('cgpa', 0):.3f}",
        ),
        (
            "الساعات المجتازة" if is_ar else "Passed Hours",
            f"{header.get('passed_hours', 0):.0f}",
        ),
        (
            "الساعات المتبقية" if is_ar else "Remaining Hours",
            f"{remaining_hours:.0f}",
        ),
        (
            "المعدل المتوقع" if is_ar else "Expected Final CGPA",
            f"{final_cgpa:.3f}",
        ),
    ]
    kpi_cells = []
    for label, value in kpi_values:
        kpi_cells.append([
            Paragraph(_pdf_text(label, is_ar), kpi_label_style),
            Paragraph(_pdf_text(value, is_ar), kpi_value_style),
        ])

    kpi_table = Table(
        [[cell for pair in kpi_cells for cell in pair]],
        colWidths=[27 * mm, 20 * mm] * 4,
    )
    kpi_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (1, 0), 0.7, colors.HexColor("#CFDAE6")),
            ("BOX", (2, 0), (3, 0), 0.7, colors.HexColor("#CFDAE6")),
            ("BOX", (4, 0), (5, 0), 0.7, colors.HexColor("#CFDAE6")),
            ("BOX", (6, 0), (7, 0), 0.7, colors.HexColor("#CFDAE6")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFE")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 3 * mm))

    training_table = Table(
        [[
            Paragraph(
                _pdf_text(
                    "حالة تدريب 1" if is_ar else "Training 1",
                    is_ar,
                ),
                kpi_label_style,
            ),
            Paragraph(
                _pdf_text(training_report["training1_status"], is_ar),
                body_style,
            ),
            Paragraph(
                _pdf_text(
                    "حالة تدريب 2" if is_ar else "Training 2",
                    is_ar,
                ),
                kpi_label_style,
            ),
            Paragraph(
                _pdf_text(training_report["training2_status"], is_ar),
                body_style,
            ),
            Paragraph(
                _pdf_text(training_report["headline"], is_ar),
                body_style,
            ),
        ]],
        colWidths=[20 * mm, 35 * mm, 20 * mm, 35 * mm, 80 * mm],
    )
    training_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C9D8E7")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FBFF")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(training_table)
    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            _pdf_text(
                "ملخص الخطة الدراسية"
                if is_ar else
                "Graduation Plan Summary",
                is_ar,
            ),
            section_style,
        )
    )

    summary_headers = [
        "#",
        "الترم" if is_ar else "Term",
        "الساعات" if is_ar else "Hours",
        "SGPA",
        "تقدير الترم" if is_ar else "Term Grade",
        "الساعات بعد الترم" if is_ar else "Passed Hours After",
        "CGPA",
        "التقدير التراكمي" if is_ar else "Cumulative Grade",
        "ساعات الترم التالي" if is_ar else "Next Load",
    ]
    summary_data = [[
        Paragraph(_pdf_text(value, is_ar), center_style)
        for value in summary_headers
    ]]
    for index, term in enumerate(terms, start=1):
        summary_data.append([
            Paragraph(str(index), center_style),
            Paragraph(_pdf_text(term.get("term_name", ""), is_ar), body_style),
            Paragraph(f"{term.get('term_registered_hours', 0):.0f}", center_style),
            Paragraph(f"{term.get('term_sgpa', 0):.3f}", center_style),
            Paragraph(_pdf_text(gpa_grade_description(term.get('term_sgpa', 0), is_ar), is_ar), small_style),
            Paragraph(f"{term.get('new_passed_hours', 0):.0f}", center_style),
            Paragraph(f"{term.get('new_cgpa', 0):.3f}", center_style),
            Paragraph(_pdf_text(gpa_grade_description(term.get('new_cgpa', 0), is_ar), is_ar), small_style),
            Paragraph(
                f"{regular_load_limit_for_cgpa(term.get('new_cgpa', 0))}",
                center_style,
            ),
        ])

    summary_table = Table(
        summary_data,
        colWidths=[7 * mm, 34 * mm, 14 * mm, 14 * mm, 23 * mm, 22 * mm, 14 * mm, 34 * mm, 28 * mm],
        repeatRows=1,
    )
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CFDAE6")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor("#F6F9FC"),
            ]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))

    result_color = (
        colors.HexColor("#20854F")
        if final_cgpa >= 2 and final_hours >= 160
        else colors.HexColor("#C17A17")
    )
    result_data = [[
        Paragraph(
            _pdf_text(
                "النتيجة النهائية المتوقعة"
                if is_ar else
                "Expected Final Result",
                is_ar,
            ),
            body_style,
        ),
        Paragraph(
            _pdf_text(
                f"CGPA {final_cgpa:.3f} — {gpa_grade_description(final_cgpa, is_ar)}",
                is_ar,
            ),
            body_style,
        ),
        Paragraph(_pdf_text(status, is_ar), center_style),
        Paragraph(
            _pdf_text(
                (
                    f"الساعات المتوقعة: {final_hours:.0f} | النقاط: {final_points:.1f}"
                    if is_ar else
                    f"Expected Passed Hours: {final_hours:.0f} | Total Points: {final_points:.1f}"
                ),
                is_ar,
            ),
            center_style,
        ),
    ]]
    result_table = Table(
        result_data,
        colWidths=[38 * mm, 40 * mm, 55 * mm, 57 * mm],
    )
    result_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.2, result_color),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBFEFC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(result_table)

    story.append(Spacer(1, 2 * mm))

    # Signatures are drawn at a fixed position by the first-page callback,
    # so they always remain on page 1 and cannot flow onto page 2.

    # ---------------- Term sections flow naturally ----------------
    # Terms are not forced onto separate pages; multiple short terms may fit on one page.
    for index, term in enumerate(terms, start=1):
        story.append(Spacer(1, 4 * mm))

        heading_data = [[
            Paragraph(
                _pdf_text(
                    f"الترم {index}: {term.get('term_name', '')}"
                    if is_ar else
                    f"Term {index}: {term.get('term_name', '')}",
                    is_ar,
                ),
                title_style,
            ),
            Paragraph(
                _pdf_text(
                    f"{term.get('term_registered_hours', 0):.0f} ساعة"
                    if is_ar else
                    f"{term.get('term_registered_hours', 0):.0f} Hours",
                    is_ar,
                ),
                center_style,
            ),
        ]]
        heading_table = Table(
            heading_data,
            colWidths=[155 * mm, 35 * mm],
        )
        heading_table.setStyle(
            TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 2.2, colors.HexColor("#222222")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E6E6E6")),
                ("BOX", (1, 0), (1, 0), 0.8, colors.HexColor("#222222")),
                ("TOPPADDING", (1, 0), (1, 0), 7),
                ("BOTTOMPADDING", (1, 0), (1, 0), 7),
            ])
        )
        story.append(heading_table)
        story.append(Spacer(1, 4 * mm))

        headers = [
            "الكود" if is_ar else "Code",
            "اسم المادة" if is_ar else "Course Name",
            "النوع" if is_ar else "Type",
            "المتطلب" if is_ar else "Requirement",
            "الحالي" if is_ar else "Current",
            "المتوقع" if is_ar else "Expected",
            "الساعات" if is_ar else "Hours",
        ]
        course_data = [[
            Paragraph(_pdf_text(value, is_ar), center_style)
            for value in headers
        ]]

        plan_df = term.get("plan_df", pd.DataFrame())
        for _, row in plan_df.iterrows():
            values = [
                row.get("course", ""),
                row.get("name", ""),
                row.get("type", ""),
                row.get("requirement_type", ""),
                row.get("current_grade", "-"),
                row.get("expected_grade", ""),
                row.get("hours", ""),
            ]
            course_data.append([
                Paragraph(
                    _pdf_text(value, is_ar),
                    center_style if position in {0, 4, 5, 6} else small_style,
                )
                for position, value in enumerate(values)
            ])

        course_table = Table(
            course_data,
            colWidths=[
                18 * mm,
                50 * mm,
                27 * mm,
                34 * mm,
                18 * mm,
                23 * mm,
                20 * mm,
            ],
            repeatRows=1,
        )
        course_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CFDAE6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F6F9FC"),
                ]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(course_table)
        story.append(Spacer(1, 5 * mm))

        term_kpis = [
            (
                "ساعات الترم" if is_ar else "Term Hours",
                f"{term.get('term_registered_hours', 0):.0f}",
            ),
            ("SGPA", f"{term.get('term_sgpa', 0):.3f}"),
            (
                "الساعات بعد الترم" if is_ar else "Passed Hours After",
                f"{term.get('new_passed_hours', 0):.0f}",
            ),
            ("CGPA", f"{term.get('new_cgpa', 0):.3f}"),
        ]
        term_kpi_data = []
        for label, value in term_kpis:
            term_kpi_data.extend([
                Paragraph(_pdf_text(label, is_ar), kpi_label_style),
                Paragraph(value, kpi_value_style),
            ])

        term_kpi_table = Table(
            [term_kpi_data],
            colWidths=[27 * mm, 20 * mm] * 4,
        )
        term_kpi_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (1, 0), 0.7, colors.HexColor("#CFDAE6")),
                ("BOX", (2, 0), (3, 0), 0.7, colors.HexColor("#CFDAE6")),
                ("BOX", (4, 0), (5, 0), 0.7, colors.HexColor("#CFDAE6")),
                ("BOX", (6, 0), (7, 0), 0.7, colors.HexColor("#CFDAE6")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFE")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(term_kpi_table)
        story.append(Spacer(1, 3 * mm))

        grade_table = Table(
            [[
                Paragraph(
                    _pdf_text("تقدير الترم" if is_ar else "Term Grade", is_ar),
                    kpi_label_style,
                ),
                Paragraph(
                    _pdf_text(
                        gpa_grade_description(term.get("term_sgpa", 0), is_ar),
                        is_ar,
                    ),
                    body_style,
                ),
                Paragraph(
                    _pdf_text(
                        "التقدير التراكمي" if is_ar else "Cumulative Grade",
                        is_ar,
                    ),
                    kpi_label_style,
                ),
                Paragraph(
                    _pdf_text(
                        gpa_grade_description(term.get("new_cgpa", 0), is_ar),
                        is_ar,
                    ),
                    body_style,
                ),
                Paragraph(
                    _pdf_text(
                        "ساعات الترم التالي" if is_ar else "Next Regular Load",
                        is_ar,
                    ),
                    kpi_label_style,
                ),
                Paragraph(
                    f"{regular_load_limit_for_cgpa(term.get('new_cgpa', 0))}",
                    body_style,
                ),
            ]],
            colWidths=[23 * mm, 39 * mm, 25 * mm, 42 * mm, 30 * mm, 31 * mm],
        )
        grade_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CFDAE6")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFE")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(grade_table)
        story.append(Spacer(1, 9 * mm))

        review_table = Table(
            [[
                Paragraph(
                    _pdf_text(
                        "توقيع المرشد"
                        if is_ar else
                        "Advisor Initials",
                        is_ar,
                    ),
                    body_style,
                ),
                "________________________",
                Paragraph(
                    _pdf_text(
                        "تاريخ المراجعة"
                        if is_ar else
                        "Review Date",
                        is_ar,
                    ),
                    body_style,
                ),
                "________________________",
            ]],
            colWidths=[28 * mm, 67 * mm, 28 * mm, 67 * mm],
        )
        review_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(review_table)

    def footer(canvas, doc_obj):
        canvas.saveState()

        # Main signatures are fixed on the summary page.
        if doc_obj.page == 1:
            signature_labels = [
                "توقيع المرشد الأكاديمي"
                if is_ar else
                "Academic Advisor Signature",
                "توقيع الطالب"
                if is_ar else
                "Student Signature",
                "اعتماد القسم"
                if is_ar else
                "Department Approval",
            ]
            centers = [
                page_size[0] / 6,
                page_size[0] / 2,
                page_size[0] * 5 / 6,
            ]
            half_line = 22 * mm

            canvas.setStrokeColor(colors.HexColor("#253247"))
            canvas.setLineWidth(0.7)
            canvas.setFillColor(colors.HexColor("#253247"))
            canvas.setFont(font_name, 8)

            for center_x, label in zip(centers, signature_labels):
                canvas.line(
                    center_x - half_line,
                    18.5 * mm,
                    center_x + half_line,
                    18.5 * mm,
                )
                canvas.drawCentredString(
                    center_x,
                    13.4 * mm,
                    _pdf_text(label, is_ar),
                )

        canvas.setStrokeColor(colors.HexColor("#BDBDBD"))
        canvas.line(10 * mm, 9 * mm, page_size[0] - 10 * mm, 9 * mm)
        canvas.setFont(font_name, 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))
        student_id = str(header.get("student_id", ""))
        footer_text = (
            f"{UNIVERSITY_NAME} | {PROGRAM_BRAND} | Student {student_id} | "
            f"{datetime.now().strftime('%Y-%m-%d')} | Page {doc_obj.page}"
        )
        canvas.drawCentredString(page_size[0] / 2, 5.5 * mm, footer_text)
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )
    return output.getvalue()



# =========================================================
# Automatic graduation-plan helpers
# =========================================================

def clear_auto_plan_state():
    st.session_state["auto_plan_draft"] = []
    st.session_state["auto_plan_notes"] = []
    st.session_state["auto_unscheduled_courses"] = []
    st.session_state["pending_course_relocation"] = None
    st.session_state["auto_edit_revision"] = int(st.session_state.get("auto_edit_revision", 0)) + 1
    st.session_state["auto_plan_version"] = int(st.session_state.get("auto_plan_version", 0)) + 1
    for key in list(st.session_state.keys()):
        if str(key).startswith("auto_grade_"):
            st.session_state.pop(key, None)


def course_offering_semester(code: str) -> str:
    c = course_obj_by_code(code)
    if c:
        return c.semester
    list_name = elective_list_for_code(code)
    if list_name:
        for placeholder, mapped_list in ELECTIVE_PLACEHOLDERS.items():
            if mapped_list == list_name:
                pc = course_obj_by_code(placeholder)
                if pc:
                    return pc.semester
    return "Any"


def _level_number(level: str) -> int:
    m = re.search(r"(\d+)", str(level))
    return int(m.group(1)) if m else 99


def _requirement_satisfied(record: Dict, passed: Set[str]) -> bool:
    ncode = norm(record.get("code", ""))
    if record.get("type") == "Improvement D":
        return False
    if ncode in passed:
        return True
    list_name = elective_list_for_code(record.get("code", ""))
    if ncode in ELECTIVE_PLACEHOLDERS and list_name:
        return bool(passed.intersection(ELECTIVE_LISTS.get(list_name, set())))
    return False



def _training_hours_rule_met(
    record: Dict,
    passed: Set[str],
    passed_hours_before_term: float,
    training1_required_hours: int = 65,
    training2_required_hours: int = 101,
) -> bool:
    """
    Training eligibility is based on cumulative passed hours.
    Training 2 also requires Training 1 to have been completed earlier.
    """
    ncode = norm(record.get("code", ""))
    hours = float(passed_hours_before_term or 0)

    if ncode == "MEC200":
        return hours >= float(training1_required_hours)

    if ncode == "MEC300":
        return (
            hours >= float(training2_required_hours)
            and "MEC200" in passed
        )

    return True


def _training_rule_diagnostic(
    record: Dict,
    passed: Set[str],
    passed_hours_before_term: float,
    is_ar: bool = False,
    training1_required_hours: int = 65,
    training2_required_hours: int = 101,
) -> str:
    ncode = norm(record.get("code", ""))
    hours = float(passed_hours_before_term or 0)

    if ncode == "MEC200" and hours < training1_required_hours:
        missing = training1_required_hours - hours
        return (
            (
                f"تدريب 1 يحتاج {training1_required_hours} ساعة مجتازة. "
                f"الطالب لديه {hours:.0f} ساعة ويحتاج {missing:.0f} ساعة إضافية."
            )
            if is_ar else
            (
                f"Training 1 requires {training1_required_hours} passed hours. "
                f"The student has {hours:.0f} and needs {missing:.0f} more."
            )
        )

    if ncode == "MEC300":
        reasons = []
        if "MEC200" not in passed:
            reasons.append(
                "يجب إنهاء تدريب 1 قبل تدريب 2"
                if is_ar else
                "Training 1 must be completed before Training 2"
            )
        if hours < training2_required_hours:
            missing = training2_required_hours - hours
            reasons.append(
                (
                    f"تدريب 2 يحتاج {training2_required_hours} ساعة مجتازة؛ "
                    f"المتوفر {hours:.0f} ويحتاج {missing:.0f} ساعة إضافية"
                )
                if is_ar else
                (
                    f"Training 2 requires {training2_required_hours} passed hours; "
                    f"the student has {hours:.0f} and needs {missing:.0f} more"
                )
            )
        return "؛ ".join(reasons) if is_ar else "; ".join(reasons)

    return ""


def _saved_training2_rule_diagnostic(
    header: Dict,
    best: pd.DataFrame,
    terms: List[Dict],
    is_ar: bool = False,
) -> str:
    """
    Check MEC 300 chronologically using passed hours before its term.
    Unfinished lower-level courses do not block training when the required
    cumulative hours have already been achieved.
    """
    passed = passed_codes(best)
    passed_hours = float(header.get("passed_hours", 0))
    t1_required = int(
        header.get(
            "training1_required_hours",
            st.session_state.get("training1_required_hours", 65),
        )
    )
    t2_required = int(
        header.get(
            "training2_required_hours",
            st.session_state.get("training2_required_hours", 101),
        )
    )

    for term in terms:
        plan_df = term.get("plan_df", pd.DataFrame())
        if plan_df is None or plan_df.empty:
            continue

        current_codes = {
            norm(row.get("course", ""))
            for _, row in plan_df.iterrows()
        }

        if "MEC300" in current_codes:
            fake_record = {"code": "MEC 300"}
            if not _training_hours_rule_met(
                fake_record,
                passed,
                passed_hours,
                t1_required,
                t2_required,
            ):
                return _training_rule_diagnostic(
                    fake_record,
                    passed,
                    passed_hours,
                    is_ar,
                    t1_required,
                    t2_required,
                )
            return ""

        # Passed courses add their hours only after the term is completed.
        for _, row in plan_df.iterrows():
            if (
                str(row.get("type", "")) != "Improvement D"
                and str(row.get("expected_grade", "")).upper() in PASSING
            ):
                code = norm(row.get("course", ""))
                if code not in passed:
                    passed.add(code)
                    passed_hours += float(row.get("hours", 0) or 0)

    return ""


def _training_rule_met(
    record: Dict,
    passed: Set[str],
    remaining_records: List[Dict] = None,
    passed_hours_before_term: float = None,
) -> bool:
    """
    Backward-compatible wrapper used by the planner.
    """
    if passed_hours_before_term is None:
        passed_hours_before_term = float(
            st.session_state.get("auto_plan_base_header", {}).get("passed_hours", 0)
        )
    return _training_hours_rule_met(
        record,
        passed,
        passed_hours_before_term,
        int(st.session_state.get("training1_required_hours", 65)),
        int(st.session_state.get("training2_required_hours", 101)),
    )



def _record_prerequisites_met(
    record: Dict,
    passed: Set[str],
    remaining_records: List[Dict],
    passed_hours_before_term: float = 0,
) -> bool:
    prereqs = {norm(x) for x in record.get("prereq", [])}
    if not prereqs.issubset(passed):
        return False
    return _training_hours_rule_met(
        record,
        passed,
        passed_hours_before_term,
        int(st.session_state.get("training1_required_hours", 65)),
        int(st.session_state.get("training2_required_hours", 101)),
    )


def _academic_term_label(academic_year_start: int, term_type: str) -> str:
    return f"{academic_year_start}-{academic_year_start + 1} {term_type}"


def _next_academic_term(term_type: str, academic_year_start: int):
    if term_type == "Fall":
        return "Spring", academic_year_start
    if term_type == "Spring":
        return "Summer", academic_year_start
    return "Fall", academic_year_start + 1



def regular_load_limit_for_cgpa(cgpa: float) -> int:
    """
    Regular-semester registration load:
    - CGPA from 0.00 through 1.00: 12 hours
    - CGPA above 1.00 through 1.50: 15 hours
    - CGPA above 1.50: 19 hours
    """
    value = max(0.0, float(cgpa or 0.0))
    if value <= 1.0:
        return 12
    if value <= 1.5:
        return 15
    return 19


def registration_load_description(cgpa: float, is_ar: bool = False) -> str:
    value = max(0.0, float(cgpa or 0.0))
    hours = regular_load_limit_for_cgpa(value)

    if value <= 1.0:
        bracket_ar = "المعدل من 0.00 إلى 1.00"
        bracket_en = "CGPA 0.00 to 1.00"
    elif value <= 1.5:
        bracket_ar = "المعدل أكبر من 1.00 وحتى 1.50"
        bracket_en = "CGPA above 1.00 through 1.50"
    else:
        bracket_ar = "المعدل أكبر من 1.50"
        bracket_en = "CGPA above 1.50"

    return (
        f"{hours} ساعة — {bracket_ar}"
        if is_ar else
        f"{hours} hours — {bracket_en}"
    )


def _save_automatic_records(records: List[Dict], replace_saved: bool):
    """Save automatic-plan records from a normal or download-button callback."""
    if replace_saved:
        st.session_state.terms = list(records)
    else:
        st.session_state.terms.extend(list(records))

    apply_rebuilt_state(st.session_state.terms)
    st.session_state.newly_unlocked = []
    st.session_state["editing_term_number"] = None
    st.session_state["auto_saved_notice"] = (
        "Automatic graduation plan saved successfully."
        if not IS_AR else
        "تم حفظ خطة التخرج التلقائية بنجاح."
    )


def render_print_report_button(report_html: str, label: str):
    """
    Open the professional HTML report in a new browser window and show
    the browser print dialog. The base64 payload avoids JavaScript quoting issues.
    """
    payload = base64.b64encode(report_html.encode("utf-8")).decode("ascii")
    components.html(
        f"""
        <style>
        .print-report-btn {{
            width: 100%;
            border: 0;
            border-radius: 8px;
            background: #173f6b;
            color: white;
            padding: 10px 14px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
        }}
        .print-report-btn:hover {{ background: #0f3156; }}
        </style>
        <button class="print-report-btn" onclick="openAndPrint()">
            🖨️ {label}
        </button>
        <script>
        function openAndPrint() {{
            const decoded = decodeURIComponent(escape(atob("{payload}")));
            const popup = window.open("", "_blank");
            if (!popup) {{
                alert("Please allow pop-ups to print the report.");
                return;
            }}
            popup.document.open();
            popup.document.write(decoded);
            popup.document.close();
            popup.focus();
            setTimeout(() => popup.print(), 700);
        }}
        </script>
        """,
        height=58,
    )


def _saved_training_status(header: Dict, terms: List[Dict], is_ar: bool = False) -> Dict:
    """
    Training status used in PDF, Excel and HTML reports.
    It considers training completed before the plan plus expected passing grades.
    """
    t1_done = bool(header.get("training1_completed_before_plan", False))
    t2_done = bool(header.get("training2_completed_before_plan", False))
    training2_rule_valid = bool(header.get("training2_rule_valid", True))
    training2_rule_reason = str(header.get("training2_rule_reason", "")).strip()
    t1_term = "Before current plan" if t1_done else ""
    t2_term = "Before current plan" if t2_done else ""

    for term in terms:
        plan_df = term.get("plan_df", pd.DataFrame())
        if plan_df is None or plan_df.empty:
            continue

        for _, row in plan_df.iterrows():
            code = norm(row.get("course", ""))
            grade = str(row.get("expected_grade", "")).upper()
            if grade not in PASSING:
                continue
            if code == "MEC200":
                t1_done = True
                t1_term = str(term.get("term_name", ""))
            elif code == "MEC300":
                if training2_rule_valid:
                    t2_done = True
                    t2_term = str(term.get("term_name", ""))

    # Find the planned Training 2 term even before its grade is marked as passed.
    t2_planned_term = ""
    for term in terms:
        plan_df = term.get("plan_df", pd.DataFrame())
        if plan_df is None or plan_df.empty:
            continue
        for _, row in plan_df.iterrows():
            if norm(row.get("course", "")) == "MEC300":
                t2_planned_term = str(term.get("term_name", ""))
                break
        if t2_planned_term:
            break

    if not training2_rule_valid and t2_planned_term:
        headline = (
            (
                f"تدريب 2 مخطط في {t2_planned_term} لكنه غير مسموح حاليًا: "
                f"{training2_rule_reason}"
            )
            if is_ar else
            (
                f"Training 2 is planned in {t2_planned_term}, but it is not currently allowed: "
                f"{training2_rule_reason}"
            )
        )
    elif t2_done:
        headline = (
            "تم إنهاء تدريب 2 واستكمال متطلبات التدريب بالكامل."
            if is_ar else
            "Training 2 is completed; all training requirements are complete."
        )
    elif t1_done and t2_planned_term:
        headline = (
            f"تم إنهاء تدريب 1، وسيتم تسجيل تدريب 2 في {t2_planned_term}."
            if is_ar else
            f"Training 1 is completed; Training 2 is scheduled in {t2_planned_term}."
        )
    elif t1_done:
        headline = (
            "تم إنهاء تدريب 1، ويجب تحديد ترم لاحق لتسجيل تدريب 2."
            if is_ar else
            "Training 1 is completed; a later term must be selected for Training 2."
        )
    else:
        headline = (
            "تدريب 1 لم يُستكمل بعد."
            if is_ar else
            "Training 1 has not been completed yet."
        )

    return {
        "training1_status": (
            (f"مكتمل — {t1_term}" if is_ar else f"Completed — {t1_term}")
            if t1_done else
            ("غير مكتمل" if is_ar else "Not completed")
        ),
        "training2_status": (
            (f"مكتمل — {t2_term}" if is_ar else f"Completed — {t2_term}")
            if t2_done else
            (
                (f"مخطط في {t2_planned_term}" if is_ar else f"Planned in {t2_planned_term}")
                if t2_planned_term else
                ("غير محدد" if is_ar else "Not scheduled")
            )
        ),
        "headline": headline,
    }


def _live_training_messages(
    best: pd.DataFrame,
    draft: List[Dict],
    grade_values: Dict[str, str],
    is_ar: bool = False,
) -> List[tuple]:
    """Live training progress messages while the advisor enters expected grades."""
    passed_initial = passed_codes(best)
    t1_done_before = "MEC200" in passed_initial
    t2_done_before = "MEC300" in passed_initial

    locations = {}
    grades = {}
    for term in draft:
        for item in term.get("courses", []):
            code = norm(item.get("code", ""))
            if code in {"MEC200", "MEC300"}:
                locations[code] = term.get("term_name", "")
                grades[code] = grade_values.get(item.get("grade_key"), "Select")

    messages = []

    if t2_done_before:
        messages.append((
            "success",
            "تم إنهاء تدريب 1 وتدريب 2 بالفعل، ومتطلبات التدريب مكتملة."
            if is_ar else
            "Training 1 and Training 2 were already completed; training requirements are complete.",
        ))
        return messages

    t1_expected_done = t1_done_before or grades.get("MEC200") in PASSING
    t2_expected_done = t2_done_before or grades.get("MEC300") in PASSING

    if t1_done_before:
        messages.append((
            "success",
            "تدريب 1 منتهٍ بالفعل."
            if is_ar else
            "Training 1 was already completed.",
        ))
    elif "MEC200" in locations:
        grade = grades.get("MEC200", "Select")
        if grade in PASSING:
            messages.append((
                "success",
                (
                    f"بعد إنهاء {locations['MEC200']} سيتم اعتبار تدريب 1 مكتملًا."
                    if is_ar else
                    f"After {locations['MEC200']}, Training 1 will be completed."
                ),
            ))
        elif grade == "Select":
            messages.append((
                "info",
                (
                    f"تدريب 1 مسجل في {locations['MEC200']}؛ أدخل التقدير المتوقع لتحديث حالته."
                    if is_ar else
                    f"Training 1 is scheduled in {locations['MEC200']}; enter its expected grade to update the status."
                ),
            ))
        else:
            messages.append((
                "warning",
                (
                    f"تدريب 1 في {locations['MEC200']} غير ناجح بالتقدير الحالي."
                    if is_ar else
                    f"Training 1 in {locations['MEC200']} is not passed with the current grade."
                ),
            ))
    else:
        messages.append((
            "warning",
            "تدريب 1 غير موجود في الخطة."
            if is_ar else
            "Training 1 is not scheduled in the plan.",
        ))

    if t2_expected_done:
        if t2_done_before:
            messages.append((
                "success",
                "تدريب 2 منتهٍ بالفعل، وتم استكمال التدريب بالكامل."
                if is_ar else
                "Training 2 was already completed; all training requirements are complete.",
            ))
        else:
            messages.append((
                "success",
                (
                    f"بعد إنهاء {locations.get('MEC300', '')} سيتم استكمال تدريب 2 ومتطلبات التدريب بالكامل."
                    if is_ar else
                    f"After {locations.get('MEC300', '')}, Training 2 and all training requirements will be completed."
                ),
            ))
    elif t1_expected_done and "MEC300" in locations:
        messages.append((
            "info",
            (
                f"بعد نجاح تدريب 1، تدريب 2 مسجل في {locations['MEC300']}."
                if is_ar else
                f"After passing Training 1, Training 2 is scheduled in {locations['MEC300']}."
            ),
        ))
    elif t1_expected_done:
        messages.append((
            "warning",
            "تدريب 1 سيكتمل، لكن لازم تحدد ترم لاحق لتسجيل تدريب 2."
            if is_ar else
            "Training 1 will be completed, but a later term still needs to be selected for Training 2.",
        ))

    return messages



def _auto_priority(record: Dict):
    type_priority = {
        "Retake Failed": 0,
        "New / Remaining": 1,
        "Improvement D": 3,
    }.get(record.get("type"), 2)
    unlock_priority = -len(courses_unlocked_by(record.get("code", "")))
    category = str(record.get("category", ""))
    category_priority = 0 if category in {"Training", "Graduation"} else 1
    return (
        type_priority,
        category_priority,
        unlock_priority,
        _level_number(record.get("level", "")),
        -int(record.get("hours", 0)),
        str(record.get("code", "")),
    )


def _select_courses_to_capacity(candidates: List[Dict], capacity: int, max_courses: int = None) -> List[Dict]:
    """Priority-first selection, then fill remaining credit space."""
    selected = []
    used = 0
    for record in sorted(candidates, key=_auto_priority):
        hours = int(record.get("hours", 0))
        if (
            hours > 0
            and used + hours <= capacity
            and (max_courses is None or len(selected) < max_courses)
        ):
            selected.append(record)
            used += hours

    # Try to fill any remaining space with unselected eligible records.
    selected_ids = {id(r) for r in selected}
    for record in sorted(candidates, key=lambda r: (int(r.get("hours", 0)), _auto_priority(r))):
        if id(record) in selected_ids:
            continue
        hours = int(record.get("hours", 0))
        if (
            hours > 0
            and used + hours <= capacity
            and (max_courses is None or len(selected) < max_courses)
        ):
            selected.append(record)
            selected_ids.add(id(record))
            used += hours
    return selected


def generate_automatic_plan(
    best: pd.DataFrame,
    attempts: pd.DataFrame,
    extra_passed: Set[str],
    planned_scheduled: Set[str],
    planned_failed: Set[str],
    selected_improvements: List[str],
    start_term: str,
    academic_year_start: int,
    starting_cgpa: float,
    starting_passed_hours: float,
    elective_replacements: Dict[str, str] = None,
    max_terms: int = 15,
):
    """
    Generate a prerequisite-aware graduation plan.

    Regular load:
    - CGPA 0.00 to 1.00: 12 hours
    - CGPA above 1.00 to 1.50: 15 hours
    - CGPA above 1.50: 19 hours
    - Maximum 7 courses in a regular semester
    Summer load: up to 9 hours with no regular-semester course-count rule.
    Final regular term may reach 22 hours; final graduation summer may reach 12 hours.
    """
    notes = []
    passed = passed_codes(best).union({norm(x) for x in (extra_passed or set())})
    passed_hours_running = float(starting_passed_hours or 0)

    elective_replacements = {
        str(code): str(target)
        for code, target in (elective_replacements or {}).items()
        if str(target) in HUMANITIES_REPLACEMENT_OPTIONS
    }
    replacement_norm_map = {
        norm(code): norm(target)
        for code, target in elective_replacements.items()
    }

    retakes = failed_retake_courses(attempts, best, extra_passed, planned_failed)
    if not retakes.empty:
        hidden_codes = {
            norm(x) for x in (planned_scheduled or set())
            if norm(x) not in {norm(y) for y in (planned_failed or set())}
        }
        retakes = retakes[~retakes["code"].astype(str).apply(norm).isin(hidden_codes)].copy()

    # A failed List A/B elective may be replaced by a different course from
    # the same list. In that case it is not a retake and no B+/C+ cap applies.
    if not retakes.empty and replacement_norm_map:
        retakes = retakes[
            ~retakes["code"].astype(str).apply(norm).isin(
                set(replacement_norm_map.keys())
            )
        ].copy()

    retake_norms = set(retakes["code"].astype(str).apply(norm).tolist()) if not retakes.empty else set()
    retake_lists = {
        elective_list_for_code(code)
        for code in (retakes["code"].tolist() if not retakes.empty else [])
        if elective_list_for_code(code)
    }

    remaining_df = remaining_courses(best, extra_passed, planned_scheduled)
    records = []

    if not retakes.empty:
        for _, row in retakes.iterrows():
            c = course_obj_by_code(row["code"])
            records.append({
                "code": str(row["code"]),
                "name": str(row.get("name", "")),
                "hours": int(row.get("hours", 0)),
                "type": "Retake Failed",
                "semester": course_offering_semester(row["code"]),
                "level": c.level if c else "",
                "category": c.category if c else "Retake",
                "prereq": tuple(c.prereq) if c else (),
                "current_grade": str(row.get("effective_grade", row.get("latest_grade", "F"))),
                "attempts_count": int(row.get("attempts_count", 1) or 1),
                "max_allowed_grade": str(
                    row.get(
                        "max_allowed_grade",
                        retake_max_allowed_grade(row.get("attempts_count", 1)),
                    )
                ),
            })

    if not remaining_df.empty:
        for _, row in remaining_df.iterrows():
            ncode = norm(row["code"])
            list_name = elective_list_for_code(row["code"])
            if ncode in retake_norms:
                continue
            # When a failed real elective is being retaken, do not also schedule
            # the placeholder for the same elective list.
            if ncode in ELECTIVE_PLACEHOLDERS and list_name in retake_lists:
                continue
            c = course_obj_by_code(row["code"])
            if not c:
                continue
            records.append({
                "code": c.code,
                "name": c.name,
                "hours": int(c.hours),
                "type": "New / Remaining",
                "semester": c.semester,
                "level": c.level,
                "category": c.category,
                "prereq": tuple(c.prereq),
                "current_grade": "-",
            })

    # Mark the selected List A/B placeholder as a new alternative course.
    # New-course grade options remain unrestricted and start at A+.
    for failed_code, target_code in elective_replacements.items():
        target_norm = norm(target_code)
        matching_record = next(
            (
                record for record in records
                if norm(record.get("code", "")) == target_norm
            ),
            None,
        )

        if matching_record is None:
            c = course_obj_by_code(target_code)
            if c and target_norm not in passed and target_norm not in {
                norm(code) for code in (planned_scheduled or set())
            }:
                matching_record = {
                    "code": c.code,
                    "name": c.name,
                    "hours": int(c.hours),
                    "type": "New / Remaining",
                    "semester": c.semester,
                    "level": c.level,
                    "category": c.category,
                    "prereq": tuple(c.prereq),
                    "current_grade": "-",
                }
                records.append(matching_record)

        if matching_record is not None:
            matching_record["is_list_ab_replacement"] = True
            matching_record["replacement_for"] = failed_code
            matching_record["name"] = list_replacement_course_name(
                target_code,
                failed_code,
                False,
            )
            matching_record["current_grade"] = "-"
            matching_record["max_allowed_grade"] = "A+"

    improvement_lookup = d_grade_courses(best)
    selected_improvement_norms = {norm(x) for x in (selected_improvements or [])}
    if not improvement_lookup.empty:
        for _, row in improvement_lookup.iterrows():
            if norm(row["code"]) not in selected_improvement_norms:
                continue
            c = course_obj_by_code(row["code"])
            records.append({
                "code": str(row["code"]),
                "name": str(row.get("name", "")),
                "hours": int(row.get("hours", 0)),
                "type": "Improvement D",
                "semester": course_offering_semester(row["code"]),
                "level": c.level if c else "",
                "category": c.category if c else "Improvement",
                "prereq": (),
                "current_grade": "D",
                "current_points": float(row.get("current_points", 1.0)),
            })

    regular_capacity = regular_load_limit_for_cgpa(starting_cgpa)
    term_type = start_term
    year_start = int(academic_year_start)
    plan = []
    skipped_empty_terms = 0

    for _ in range(max_terms * 3):
        # Remove completed requirements and elective placeholders satisfied by a
        # real elective course already passed/planned.
        records = [r for r in records if not _requirement_satisfied(r, passed)]
        if not records:
            break

        eligible = [
            r for r in records
            if _record_prerequisites_met(
                r,
                passed,
                records,
                passed_hours_running,
            )
        ]
        final_capacity = 12 if term_type == "Summer" else 22

        # Final term: all remaining records must already be prerequisite-eligible.
        # In a final regular term, opposite-semester courses are allowed as
        # graduation exceptions.
        remaining_hours = sum(int(r.get("hours", 0)) for r in records)
        training_waits_for_summer = (
            term_type != "Summer"
            and any(
                r.get("category") == "Training" or r.get("semester") == "Summer"
                for r in records
            )
        )
        can_finish_now = (
            len(eligible) == len(records)
            and remaining_hours <= final_capacity
            and not training_waits_for_summer
            and (term_type == "Summer" or len(records) <= 7)
        )

        if can_finish_now:
            selected = list(sorted(records, key=_auto_priority))
        else:
            capacity = 9 if term_type == "Summer" else regular_capacity
            if term_type == "Summer":
                offered = eligible
            else:
                offered = [
                    r for r in eligible
                    if r.get("semester") in {term_type, "Any"}
                ]
            selected = _select_courses_to_capacity(offered, capacity, None if term_type == "Summer" else 7)

        if not selected:
            skipped_empty_terms += 1
            term_type, year_start = _next_academic_term(term_type, year_start)
            if skipped_empty_terms >= 4:
                notes.append(
                    "Automatic planning stopped because remaining prerequisites or course offerings could not be resolved."
                )
                break
            continue

        skipped_empty_terms = 0
        selected_ids = {id(r) for r in selected}
        term_courses = []
        for record in selected:
            item = dict(record)
            if term_type == "Summer":
                is_offterm = record.get("semester") not in {"Summer", "Any"}
            else:
                is_offterm = record.get("semester") not in {term_type, "Any"}
            if is_offterm and record.get("type") == "New / Remaining":
                item["type"] = "Off-Term Graduation Exception"
            item["offterm"] = is_offterm
            item["unlocks_next"] = unlocks_text(record.get("code", ""))
            term_courses.append(item)

        plan.append({
            "term_type": term_type,
            "term_name": _academic_term_label(year_start, term_type),
            "academic_year_start": year_start,
            "capacity": final_capacity if can_finish_now else (9 if term_type == "Summer" else regular_capacity),
            "is_final_term": can_finish_now,
            "courses": term_courses,
        })

        # The planning sequence assumes every scheduled required/retake course
        # will be passed. Actual grades are entered later and validated.
        for record in selected:
            if record.get("type") != "Improvement D":
                code = norm(record.get("code", ""))
                if code not in passed:
                    passed.add(code)
                    passed_hours_running += float(record.get("hours", 0) or 0)
        records = [r for r in records if id(r) not in selected_ids]
        term_type, year_start = _next_academic_term(term_type, year_start)

        if len(plan) >= max_terms and records:
            notes.append(f"Plan reached the maximum of {max_terms} terms with requirements still remaining.")
            break

    if records:
        notes.append(
            "Some requirements were not scheduled: "
            + ", ".join(str(r.get("code", "")) for r in records[:15])
        )

    return plan, notes


def _best_grade_for_exact_code(best: pd.DataFrame, code: str) -> str:
    if best is None or best.empty:
        return ""
    ncode = norm(code)
    rows = best[best["ncode"].astype(str).eq(ncode)]
    if rows.empty:
        return ""
    return str(rows.iloc[-1].get("grade", ""))


def _recovery_unlock_count(code: str) -> int:
    return len(courses_unlocked_by(code))


def _recovery_candidate_score(
    record: Dict,
    current_points: float,
    current_gpa_hours: float,
    current_cgpa: float,
    target_cgpa: float,
) -> float:
    """
    Higher score means the course is more useful for reaching the target.
    Point-difference improvements are usually the most efficient, while
    prerequisite-opening new courses receive an unlock bonus.
    """
    hours = max(1.0, float(record.get("hours", 0) or 0))
    gp = point_of_grade(record.get("expected_grade", "F"))
    record_type = str(record.get("type", ""))

    if record_type in {
        "Improvement D",
        "List A/B Alternative Improvement",
    }:
        current_gp = float(record.get("current_points", 0) or 0)
        direct_gain = max(0.0, (gp - current_gp) * hours)
        projected_delta = direct_gain / max(1.0, current_gpa_hours)
    else:
        projected_cgpa = (
            (current_points + gp * hours) /
            max(1.0, current_gpa_hours + hours)
        )
        projected_delta = projected_cgpa - current_cgpa
        direct_gain = max(0.0, (gp - target_cgpa) * hours)

    type_bonus = {
        "Improvement D": 280.0,
        "List A/B Alternative Improvement": 260.0,
        "Retake Failed": 210.0,
        "New / Remaining": 90.0,
    }.get(record_type, 0.0)

    preferred_bonus = 260.0 if record.get("preferred_new", False) else 0.0
    unlock_bonus = 85.0 * int(record.get("unlock_count", 0) or 0)

    return (
        type_bonus
        + preferred_bonus
        + unlock_bonus
        + projected_delta * 1800.0
        + direct_gain * 12.0
    )


def _build_recovery_candidates(
    best: pd.DataFrame,
    attempts: pd.DataFrame,
    extra_passed: Set[str],
    planned_scheduled: Set[str],
    planned_failed: Set[str],
    planned_improved_d: Set[str],
    include_retakes: bool,
    include_improvements: bool,
    include_new_courses: bool,
    expected_retake_grade: str,
    expected_improvement_grade: str,
    expected_new_grade: str,
    preferred_new_codes: List[str],
    excluded_retake_codes: Set[str],
    list_alternative_configs: List[Dict],
    list_alternative_points_only: bool,
) -> List[Dict]:
    records = []
    preferred_norms = {norm(code) for code in (preferred_new_codes or [])}
    excluded_norms = {norm(code) for code in (excluded_retake_codes or set())}

    if include_retakes:
        retakes = failed_retake_courses(
            attempts,
            best,
            extra_passed,
            planned_failed,
        )
        if not retakes.empty:
            hidden_codes = {
                norm(code)
                for code in (planned_scheduled or set())
                if norm(code) not in {
                    norm(x) for x in (planned_failed or set())
                }
            }
            retakes = retakes[
                ~retakes["code"].astype(str).apply(norm).isin(hidden_codes)
            ].copy()
            if excluded_norms:
                retakes = retakes[
                    ~retakes["code"].astype(str).apply(norm).isin(
                        excluded_norms
                    )
                ].copy()

            for _, row in retakes.iterrows():
                attempts_count = int(row.get("attempts_count", 1) or 1)
                expected_grade = cap_retake_grade(
                    expected_retake_grade,
                    attempts_count,
                )
                if expected_grade not in PASSING:
                    continue

                c = course_obj_by_code(row.get("code", ""))
                code = str(row.get("code", ""))
                records.append({
                    "code": code,
                    "name": str(row.get("name", code)),
                    "hours": int(row.get("hours", 0) or 0),
                    "type": "Retake Failed",
                    "semester": course_offering_semester(code),
                    "category": c.category if c else "Retake",
                    "prereq": tuple(c.prereq) if c else (),
                    "current_grade": str(
                        row.get(
                            "effective_grade",
                            row.get("latest_grade", "F"),
                        )
                    ),
                    "current_points": 0.0,
                    "expected_grade": expected_grade,
                    "attempts_count": attempts_count,
                    "max_allowed_grade": retake_max_allowed_grade(
                        attempts_count
                    ),
                    "unlock_count": _recovery_unlock_count(code),
                    "unlocks_next": unlocks_text(code),
                    "preferred_new": False,
                })

    if include_improvements:
        improvement_df = d_grade_courses(best)
        if not improvement_df.empty:
            improved_norms = {
                norm(code)
                for code in (planned_improved_d or set())
            }
            improvement_df = improvement_df[
                ~improvement_df["code"].astype(str).apply(norm).isin(
                    improved_norms
                )
            ].copy()

            for _, row in improvement_df.iterrows():
                expected_grade = expected_improvement_grade
                if point_of_grade(expected_grade) > point_of_grade("B+"):
                    expected_grade = "B+"
                current_gp = float(row.get("current_points", 1.0) or 1.0)
                if point_of_grade(expected_grade) <= current_gp:
                    continue

                code = str(row.get("code", ""))
                records.append({
                    "code": code,
                    "name": str(row.get("name", code)),
                    "hours": int(row.get("hours", 0) or 0),
                    "type": "Improvement D",
                    "semester": course_offering_semester(code),
                    "category": "Improvement",
                    "prereq": (),
                    "current_grade": "D",
                    "current_points": current_gp,
                    "expected_grade": expected_grade,
                    "unlock_count": 0,
                    "unlocks_next": "",
                    "preferred_new": False,
                })

    if include_new_courses:
        remaining_df = remaining_courses(
            best,
            extra_passed,
            planned_scheduled,
        )
        if not remaining_df.empty:
            for _, row in remaining_df.iterrows():
                c = course_obj_by_code(row.get("code", ""))
                if not c:
                    continue
                if expected_new_grade not in PASSING:
                    continue

                code = str(c.code)
                row_status = str(row.get("status", ""))
                is_withdrawn = row_status.startswith("withdrawn")
                records.append({
                    "code": code,
                    "name": str(c.name),
                    "hours": int(c.hours),
                    "type": (
                        "Withdrawn / New"
                        if is_withdrawn else
                        "New / Remaining"
                    ),
                    "semester": c.semester,
                    "category": c.category,
                    "prereq": tuple(c.prereq),
                    "current_grade": "W" if is_withdrawn else "-",
                    "current_points": 0.0,
                    "expected_grade": expected_new_grade,
                    "unlock_count": _recovery_unlock_count(code),
                    "unlocks_next": unlocks_text(code),
                    "preferred_new": norm(code) in preferred_norms,
                })

    # A different course from a completed List A/B slot is not a retake.
    # It keeps the full grade scale from A+.
    for config in list_alternative_configs or []:
        if not config.get("enabled", False):
            continue

        slot_code = str(config.get("slot_code", ""))
        current_grade = str(config.get("current_grade", ""))
        expected_grade = str(config.get("expected_grade", ""))

        if current_grade not in GRADE_POINTS or expected_grade not in PASSING:
            continue
        if point_of_grade(expected_grade) <= point_of_grade(current_grade):
            continue

        slot_course = course_obj_by_code(slot_code)
        hours = int(slot_course.hours if slot_course else 2)
        synthetic_code = f"ALT-{norm(slot_code)}"

        records.append({
            "code": synthetic_code,
            "name": (
                f"Alternative course from "
                f"{humanities_replacement_label(slot_code, False)}"
            ),
            "hours": hours,
            "type": "List A/B Alternative Improvement",
            "semester": (
                slot_course.semester
                if slot_course else
                "Any"
            ),
            "category": "University Elective Replacement",
            "prereq": (),
            "current_grade": current_grade,
            "current_points": point_of_grade(current_grade),
            "expected_grade": expected_grade,
            "slot_code": slot_code,
            # Alternative from the same List A/B slot uses full grade scale
            # from A+ but does not repeat already-counted slot hours.
            "points_only": True,
            "unlock_count": 0,
            "unlocks_next": "",
            "preferred_new": False,
        })

    # Defensive de-duplication: one academic course may appear only once
    # in the candidate pool, even if it was discovered through more than one
    # source (for example remaining courses and withdrawn courses).
    unique_records = []
    seen_codes = set()
    for item in records:
        ncode = norm(item.get("code", ""))
        if not ncode or ncode in seen_codes:
            continue
        seen_codes.add(ncode)
        unique_records.append(item)

    return unique_records


def generate_cgpa_recovery_plan(
    header: Dict,
    best: pd.DataFrame,
    attempts: pd.DataFrame,
    extra_passed: Set[str],
    planned_scheduled: Set[str],
    planned_failed: Set[str],
    planned_improved_d: Set[str],
    start_term: str,
    academic_year_start: int,
    target_cgpa: float,
    include_retakes: bool,
    include_improvements: bool,
    include_new_courses: bool,
    expected_retake_grade: str,
    expected_improvement_grade: str,
    expected_new_grade: str,
    preferred_new_codes: List[str],
    excluded_retake_codes: Set[str],
    list_alternative_configs: List[Dict],
    list_alternative_points_only: bool = True,
    max_terms: int = 12,
):
    """
    Build a term-by-term academic recovery plan until the expected CGPA
    reaches the requested target.

    Priorities:
    1. Efficient D and List A/B point-difference improvements.
    2. Failed courses, using B+/C+ retake limits.
    3. New courses, especially those selected by the advisor or those
       that unlock more courses.
    """
    target = max(0.0, float(target_cgpa or 2.0))
    passed = passed_codes(best).union(
        {norm(code) for code in (extra_passed or set())}
    )

    current_passed_hours = float(header.get("passed_hours", 0) or 0)
    current_gpa_hours = float(
        header.get("gpa_hours", current_passed_hours) or 0
    )
    current_cgpa = float(header.get("cgpa", 0) or 0)
    header_points = float(header.get("total_points", 0) or 0)
    calculated_points = current_cgpa * current_gpa_hours
    current_points = (
        header_points
        if abs(header_points - calculated_points) <= 0.15
        else calculated_points
    )

    if current_cgpa >= target:
        return [], [
            (
                f"Student already has CGPA {current_cgpa:.3f}, "
                f"which meets the target {target:.2f}."
            )
        ]

    records = _build_recovery_candidates(
        best=best,
        attempts=attempts,
        extra_passed=extra_passed,
        planned_scheduled=planned_scheduled,
        planned_failed=planned_failed,
        planned_improved_d=planned_improved_d,
        include_retakes=include_retakes,
        include_improvements=include_improvements,
        include_new_courses=include_new_courses,
        expected_retake_grade=expected_retake_grade,
        expected_improvement_grade=expected_improvement_grade,
        expected_new_grade=expected_new_grade,
        preferred_new_codes=preferred_new_codes,
        excluded_retake_codes=excluded_retake_codes,
        list_alternative_configs=list_alternative_configs,
        list_alternative_points_only=list_alternative_points_only,
    )

    plan = []
    notes = []
    term_type = start_term
    year_start = int(academic_year_start)
    skipped_terms = 0

    for _ in range(max_terms * 3):
        if current_cgpa >= target:
            break
        if not records:
            break

        capacity = (
            9
            if term_type == "Summer"
            else regular_load_limit_for_cgpa(current_cgpa)
        )
        max_courses = None if term_type == "Summer" else 7

        eligible = []
        for record in records:
            record_type = str(record.get("type", ""))
            prereqs = {norm(x) for x in record.get("prereq", [])}

            if not prereqs.issubset(passed):
                continue

            if record_type not in {
                "Improvement D",
                "List A/B Alternative Improvement",
            }:
                if not _training_hours_rule_met(
                    record,
                    passed,
                    current_passed_hours,
                    int(
                        st.session_state.get(
                            "training1_required_hours",
                            65,
                        )
                    ),
                    int(
                        st.session_state.get(
                            "training2_required_hours",
                            101,
                        )
                    ),
                ):
                    continue

            offered = (
                term_type == "Summer"
                or record.get("semester") in {
                    term_type,
                    "Any",
                    "",
                }
            )
            if not offered:
                continue

            item = dict(record)
            item["_recovery_score"] = _recovery_candidate_score(
                item,
                current_points,
                current_gpa_hours,
                current_cgpa,
                target,
            )
            eligible.append(item)

        if not eligible:
            skipped_terms += 1
            term_type, year_start = _next_academic_term(
                term_type,
                year_start,
            )
            if skipped_terms >= 4:
                notes.append(
                    "Recovery planning stopped because no eligible course "
                    "could be scheduled in four consecutive terms."
                )
                break
            continue

        skipped_terms = 0
        selected = []
        selected_norms = set()
        used_hours = 0

        for item in sorted(
            eligible,
            key=lambda row: (
                -float(row.get("_recovery_score", 0)),
                -int(row.get("unlock_count", 0) or 0),
                int(row.get("hours", 0) or 0),
            ),
        ):
            item_norm = norm(item.get("code", ""))
            if not item_norm or item_norm in selected_norms:
                continue

            hours = int(item.get("hours", 0) or 0)
            if hours <= 0:
                continue
            if used_hours + hours > capacity:
                continue
            if max_courses is not None and len(selected) >= max_courses:
                continue
            selected.append(item)
            selected_norms.add(item_norm)
            used_hours += hours

        if not selected:
            term_type, year_start = _next_academic_term(
                term_type,
                year_start,
            )
            continue

        rows = []
        term_quality_points = 0.0
        added_hours = 0.0
        added_points = 0.0
        improvement_gain = 0.0
        selected_codes = set()

        for item in selected:
            code = str(item.get("code", ""))
            selected_codes.add(code)
            hours = int(item.get("hours", 0) or 0)
            grade = str(item.get("expected_grade", "F"))
            gp = point_of_grade(grade)
            record_type = str(item.get("type", ""))

            term_quality_points += gp * hours
            points_effect = 0.0
            effect = ""

            if record_type in {
                "Improvement D",
                "List A/B Alternative Improvement",
            }:
                current_gp = float(item.get("current_points", 0) or 0)
                gain = max(0.0, (gp - current_gp) * hours)

                if (
                    record_type == "List A/B Alternative Improvement"
                    and not item.get("points_only", True)
                ):
                    added_hours += hours
                    added_points += gp * hours
                    points_effect = gp * hours
                    effect = (
                        "Alternative List A/B course: full A+ scale; "
                        "adds hours and points"
                    )
                else:
                    improvement_gain += gain
                    points_effect = gain
                    effect = (
                        "Point difference only; passed hours are not repeated"
                    )
            else:
                added_hours += hours
                added_points += gp * hours
                points_effect = gp * hours
                effect = (
                    "Withdrawn course registered as new; old W is ignored"
                    if record_type == "Withdrawn / New"
                    else "Adds passed hours and points"
                )

                ncode = norm(code)
                if ncode not in passed:
                    passed.add(ncode)

            rows.append({
                "course": code,
                "name": item.get("name", ""),
                "type": record_type,
                "requirement_type": requirement_type_from_code(
                    item.get("slot_code", code),
                    item.get("category", ""),
                ),
                "current_grade": item.get("current_grade", "-"),
                "expected_grade": grade,
                "hours": hours,
                "effect": effect,
                "points_effect": points_effect,
                "unlocks_next": item.get("unlocks_next", ""),
                "recovery_priority": round(
                    float(item.get("_recovery_score", 0)),
                    1,
                ),
            })

        new_total_points = (
            current_points + added_points + improvement_gain
        )
        new_passed_hours = current_passed_hours + added_hours
        new_gpa_hours = current_gpa_hours + added_hours
        new_cgpa = (
            new_total_points / new_gpa_hours
            if new_gpa_hours > 0 else 0.0
        )
        term_sgpa = (
            term_quality_points / used_hours
            if used_hours > 0 else 0.0
        )

        record = {
            "term_name": _academic_term_label(year_start, term_type),
            "term_type": term_type,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "plan_df": pd.DataFrame(rows),
            "term_registered_hours": used_hours,
            "term_sgpa": term_sgpa,
            "new_passed_hours": new_passed_hours,
            "new_gpa_hours": new_gpa_hours,
            "new_total_points": new_total_points,
            "new_cgpa": new_cgpa,
            "term_grade": gpa_grade_description(term_sgpa, False),
            "cumulative_grade": gpa_grade_description(new_cgpa, False),
            "next_regular_load": regular_load_limit_for_cgpa(new_cgpa),
            "recovery_plan": True,
            "target_cgpa": target,
        }
        plan.append(record)

        records = [
            item
            for item in records
            if str(item.get("code", "")) not in selected_codes
        ]

        current_points = new_total_points
        current_passed_hours = new_passed_hours
        current_gpa_hours = new_gpa_hours
        current_cgpa = new_cgpa

        term_type, year_start = _next_academic_term(
            term_type,
            year_start,
        )

        if len(plan) >= max_terms:
            notes.append(
                f"Recovery plan reached the maximum of {max_terms} terms."
            )
            break

    if plan and plan[-1].get("new_cgpa", 0) >= target:
        notes.append(
            (
                f"Target reached: expected CGPA "
                f"{plan[-1]['new_cgpa']:.3f} after "
                f"{len(plan)} term(s)."
            )
        )
    elif current_cgpa < target:
        notes.append(
            (
                f"Target {target:.2f} was not reached. "
                f"Highest expected CGPA from the selected options is "
                f"{current_cgpa:.3f}. Add more new courses, improvements, "
                f"or List A/B alternatives."
            )
        )

    return plan, notes





def _recovery_normalize_item(item: Dict) -> Dict:
    out = dict(item)
    out["code"] = str(out.get("code", ""))
    out["name"] = str(out.get("name", out["code"]))
    out["hours"] = int(out.get("hours", 0) or 0)
    out["type"] = str(out.get("type", "New / Remaining"))
    out["expected_grade"] = str(out.get("expected_grade", "B+"))
    out["semester"] = str(
        out.get("semester", course_offering_semester(out["code"]))
    )
    out["prereq"] = tuple(out.get("prereq", ()) or ())
    out["current_points"] = float(out.get("current_points", 0) or 0)
    out["points_only"] = bool(out.get("points_only", True))
    out["unlocks_next"] = str(
        out.get("unlocks_next", unlocks_text(out["code"]))
    )
    return out


def _recovery_build_editor(
    records: List[Dict],
    candidate_pool: List[Dict],
):
    candidate_map = {
        norm(item.get("code", "")): _recovery_normalize_item(item)
        for item in candidate_pool
    }
    used = set()
    draft = []

    for record in records:
        term_name = str(record.get("term_name", ""))
        term_type = str(record.get("term_type", "")) or (
            "Summer" if "Summer" in term_name
            else "Spring" if "Spring" in term_name
            else "Fall"
        )
        year_match = re.search(r"(\d{4})", term_name)
        year_start = int(year_match.group(1)) if year_match else datetime.now().year
        courses = []

        plan_df = record.get("plan_df", pd.DataFrame())
        if plan_df is not None and not plan_df.empty:
            for _, row in plan_df.iterrows():
                code = str(row.get("course", ""))
                ncode = norm(code)
                item = dict(candidate_map.get(ncode, {}))

                if not item:
                    c = course_obj_by_code(code)
                    item = {
                        "code": code,
                        "name": str(row.get("name", c.name if c else code)),
                        "hours": int(row.get("hours", c.hours if c else 0) or 0),
                        "type": str(row.get("type", "New / Remaining")),
                        "semester": c.semester if c else term_type,
                        "category": c.category if c else str(
                            row.get("requirement_type", "")
                        ),
                        "prereq": tuple(c.prereq) if c else (),
                        "current_grade": str(row.get("current_grade", "-")),
                        "current_points": point_of_grade(
                            row.get("current_grade", "")
                        ),
                        "expected_grade": str(
                            row.get("expected_grade", "B+")
                        ),
                        "points_only": (
                            "point difference"
                            in str(row.get("effect", "")).lower()
                        ),
                        "unlocks_next": str(
                            row.get("unlocks_next", unlocks_text(code))
                        ),
                    }

                item = _recovery_normalize_item(item)
                item["expected_grade"] = str(
                    row.get("expected_grade", item["expected_grade"])
                )
                item["current_grade"] = str(
                    row.get("current_grade", item.get("current_grade", "-"))
                )
                # Old generated plans may already contain a duplicate.
                # Keep only the first occurrence globally.
                if ncode in used:
                    continue
                courses.append(item)
                used.add(ncode)

        draft.append({
            "term_name": term_name,
            "term_type": term_type,
            "academic_year_start": year_start,
            "courses": courses,
        })

    unscheduled = []
    unscheduled_seen = set()
    for item in candidate_pool:
        ncode = norm(item.get("code", ""))
        if not ncode or ncode in used or ncode in unscheduled_seen:
            continue
        unscheduled_seen.add(ncode)
        unscheduled.append(_recovery_normalize_item(item))

    return draft, unscheduled


def _recovery_item_label(item: Dict, is_ar: bool = False) -> str:
    unlocks = str(item.get("unlocks_next", ""))
    unlock_text = (
        f" — تفتح: {unlocks}" if is_ar and unlocks
        else f" — Unlocks: {unlocks}" if unlocks
        else ""
    )
    return (
        f"{item.get('code','')} — {item.get('name','')} "
        f"({item.get('hours',0)} {'ساعة' if is_ar else 'hrs'} | "
        f"{item.get('type','')} | {item.get('expected_grade','')})"
        f"{unlock_text}"
    )


def _recovery_grade_options(item: Dict) -> List[str]:
    item_type = str(item.get("type", ""))
    if item_type == "Retake Failed":
        return retake_grade_options(item.get("attempts_count", 1))
    if item_type == "Improvement D":
        return [
            "Select", "B+", "B", "B-", "C+",
            "C", "C-", "D+", "D", "F",
        ]
    return GRADE_OPTIONS


def _recovery_find_item(draft, unscheduled, code):
    ncode = norm(code)
    for term in draft:
        for item in term.get("courses", []):
            if norm(item.get("code", "")) == ncode:
                return dict(item)
    for item in unscheduled:
        if norm(item.get("code", "")) == ncode:
            return dict(item)
    return None


def _recovery_remove_everywhere(draft, unscheduled, code):
    ncode = norm(code)
    for term in draft:
        term["courses"] = [
            item for item in term.get("courses", [])
            if norm(item.get("code", "")) != ncode
        ]
    unscheduled[:] = [
        item for item in unscheduled
        if norm(item.get("code", "")) != ncode
    ]


def _recovery_move_course(code: str, target_index=None, unschedule=False) -> bool:
    draft = [
        {**dict(term), "courses": [dict(i) for i in term.get("courses", [])]}
        for term in st.session_state.get("recovery_plan_draft", [])
    ]
    unscheduled = [
        dict(i) for i in st.session_state.get(
            "recovery_unscheduled_courses", []
        )
    ]

    item = _recovery_find_item(draft, unscheduled, code)
    if item is None:
        return False
    if not unschedule and (
        target_index is None
        or target_index < 0
        or target_index >= len(draft)
    ):
        return False

    _recovery_remove_everywhere(draft, unscheduled, code)
    if unschedule:
        unscheduled.append(item)
    else:
        draft[target_index]["courses"].append(item)

    st.session_state["recovery_plan_draft"] = draft
    st.session_state["recovery_unscheduled_courses"] = unscheduled
    st.session_state["recovery_editor_revision"] = int(
        st.session_state.get("recovery_editor_revision", 0)
    ) + 1
    return True


def _recovery_add_term():
    draft = [
        {**dict(term), "courses": [dict(i) for i in term.get("courses", [])]}
        for term in st.session_state.get("recovery_plan_draft", [])
    ]

    if draft:
        last_type = str(draft[-1].get("term_type", "Fall"))
        last_year = int(
            draft[-1].get("academic_year_start", datetime.now().year)
        )
        next_type, next_year = _next_academic_term(last_type, last_year)
    else:
        next_type = st.session_state.get("recovery_start_term", "Fall")
        next_year = int(
            st.session_state.get(
                "recovery_start_year", datetime.now().year
            )
        )

    draft.append({
        "term_name": _academic_term_label(next_year, next_type),
        "term_type": next_type,
        "academic_year_start": next_year,
        "courses": [],
    })
    st.session_state["recovery_plan_draft"] = draft
    st.session_state["recovery_editor_revision"] = int(
        st.session_state.get("recovery_editor_revision", 0)
    ) + 1


def _recovery_delete_empty_term(index: int) -> bool:
    """Backward-compatible wrapper."""
    return _recovery_delete_term(index)


def _recovery_delete_term(index: int) -> bool:
    draft = [
        {**dict(term), "courses": [dict(i) for i in term.get("courses", [])]}
        for term in st.session_state.get("recovery_plan_draft", [])
    ]
    if index < 0 or index >= len(draft):
        return False

    removed_courses = [
        dict(i) for i in draft[index].get("courses", [])
    ]

    unscheduled = [
        dict(i)
        for i in st.session_state.get("recovery_unscheduled_courses", [])
    ]
    unscheduled_norms = {norm(i.get("code", "")) for i in unscheduled}
    for item in removed_courses:
        ncode = norm(item.get("code", ""))
        if ncode and ncode not in unscheduled_norms:
            unscheduled.append(item)
            unscheduled_norms.add(ncode)

    del draft[index]
    st.session_state["recovery_plan_draft"] = draft
    st.session_state["recovery_unscheduled_courses"] = unscheduled
    st.session_state["recovery_editor_revision"] = int(
        st.session_state.get("recovery_editor_revision", 0)
    ) + 1
    return True


def _clean_draft_from_already_passed_courses(
    draft: List[Dict],
    best: pd.DataFrame,
) -> List[Dict]:
    """Remove already-passed transcript courses from generated drafts."""
    passed = passed_codes(best)
    cleaned = []
    for term in draft or []:
        new_term = {
            **dict(term),
            "courses": [],
        }
        seen = set()
        for item in term.get("courses", []):
            ncode = norm(item.get("code", ""))
            item_type = str(item.get("type", ""))
            if (
                ncode in passed
                and item_type in {
                    "Retake Failed",
                    "New / Remaining",
                    "Withdrawn / New",
                }
            ):
                continue
            if not ncode or ncode in seen:
                continue
            seen.add(ncode)
            new_term["courses"].append(dict(item))
        cleaned.append(new_term)
    return cleaned


def calculate_recovery_editor_plan(
    base_header: Dict,
    draft: List[Dict],
    best: pd.DataFrame,
    target_cgpa: float,
):
    running = dict(base_header)
    passed = passed_codes(best)
    results, warnings = [], []
    reached_term = ""

    for term in draft:
        courses = [dict(i) for i in term.get("courses", [])]
        if not courses:
            continue

        term_name = str(term.get("term_name", ""))
        term_type = str(term.get("term_type", "Fall"))
        cgpa_before = float(running.get("cgpa", 0) or 0)
        nonempty_terms = [
            t for t in draft if t.get("courses")
        ]
        is_final_term = (
            term is nonempty_terms[-1]
            if nonempty_terms else False
        )
        capacity = (
            (12 if is_final_term else 9)
            if term_type == "Summer"
            else regular_load_limit_for_cgpa(cgpa_before)
        )
        term_hours = sum(int(i.get("hours", 0) or 0) for i in courses)

        if term_hours > capacity:
            warnings.append(
                (
                    f"{term_name}: الساعات {term_hours} أكبر من المسموح {capacity}."
                    if IS_AR else
                    f"{term_name}: {term_hours} hours exceed the allowed {capacity}."
                )
            )

        current_points = float(
            running.get(
                "total_points",
                float(running.get("cgpa", 0))
                * float(running.get("gpa_hours", 0)),
            )
        )
        current_passed = float(running.get("passed_hours", 0))
        current_gpa_hours = float(
            running.get("gpa_hours", current_passed)
        )

        rows = []
        term_quality = 0.0
        add_hours = add_points = improve_gain = 0.0
        pass_after = set()

        for item in courses:
            code = str(item.get("code", ""))
            item_type = str(item.get("type", "New / Remaining"))
            grade = str(item.get("expected_grade", "Select"))
            # A previous W attempt has no SGPA/CGPA effect. The selected
            # expected grade belongs to the new registration and uses the
            # full scale up to A+.
            if item_type == "Retake Failed":
                grade = cap_retake_grade(
                    grade, item.get("attempts_count", 1)
                )

            hours = int(item.get("hours", 0) or 0)
            gp = point_of_grade(grade)
            term_quality += gp * hours

            prereqs = {norm(x) for x in item.get("prereq", ())}
            missing = sorted(prereqs - passed)
            if missing:
                warnings.append(
                    (
                        f"{term_name}: المادة {code} قبل متطلباتها "
                        f"{', '.join(missing)}."
                        if IS_AR else
                        f"{term_name}: {code} is before prerequisites "
                        f"{', '.join(missing)}."
                    )
                )

            points_effect = 0.0
            if item_type in {
                "Improvement D",
                "List A/B Alternative Improvement",
            } and bool(item.get("points_only", True)):
                old_gp = float(item.get("current_points", 0) or 0)
                gain = max(0.0, (gp - old_gp) * hours)
                improve_gain += gain
                points_effect = gain
                effect = (
                    "فرق النقاط فقط بدون تكرار الساعات"
                    if IS_AR else
                    "Point difference only; hours not repeated"
                )
            else:
                if item_type == "Retake Failed":
                    if grade in PASSING:
                        add_hours += hours
                        add_points += gp * hours
                        points_effect = gp * hours
                        pass_after.add(norm(code))
                    effect = (
                        "استبدال نقاط الرسوب دون تكرار ساعات المعدل"
                        if IS_AR else
                        "Replace failed-course points without repeating GPA hours"
                    )
                else:
                    if grade in PASSING:
                        add_hours += hours
                        pass_after.add(norm(code))
                    add_points += gp * hours
                    points_effect = gp * hours
                    effect = (
                        "تضاف ساعات المعدل، وتضاف ساعات النجاح عند الاجتياز"
                        if IS_AR else
                        "Adds GPA hours; passed hours increase when passed"
                    )

            rows.append({
                "course": code,
                "name": item.get("name", ""),
                "type": item_type,
                "requirement_type": requirement_type_from_code(
                    item.get("slot_code", code),
                    item.get("category", ""),
                ),
                "current_grade": item.get("current_grade", "-"),
                "expected_grade": grade,
                "hours": hours,
                "effect": effect,
                "points_effect": points_effect,
                "unlocks_next": item.get(
                    "unlocks_next", unlocks_text(code)
                ),
            })

        new_points = current_points + add_points + improve_gain
        new_passed = current_passed + add_hours
        first_time_attempted_hours = sum(
            int(item.get("hours", 0) or 0)
            for item in courses
            if str(item.get("type", "")) not in {
                "Retake Failed",
                "Improvement D",
                "List A/B Alternative Improvement",
            }
        )
        new_gpa_hours = current_gpa_hours + first_time_attempted_hours
        new_cgpa = (
            new_points / new_gpa_hours if new_gpa_hours else 0.0
        )
        sgpa = term_quality / term_hours if term_hours else 0.0

        results.append({
            "term_name": term_name,
            "term_type": term_type,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "plan_df": pd.DataFrame(rows),
            "term_registered_hours": term_hours,
            "term_sgpa": sgpa,
            "new_passed_hours": new_passed,
            "new_gpa_hours": new_gpa_hours,
            "new_total_points": new_points,
            "new_cgpa": new_cgpa,
            "term_grade": gpa_grade_description(sgpa, False),
            "cumulative_grade": gpa_grade_description(new_cgpa, False),
            "next_regular_load": regular_load_limit_for_cgpa(new_cgpa),
            "recovery_plan": True,
            "target_cgpa": target_cgpa,
            "cgpa_before_term": cgpa_before,
            "allowed_hours": capacity,
        })

        passed.update(pass_after)
        running = {
            **running,
            "passed_hours": new_passed,
            "gpa_hours": new_gpa_hours,
            "total_points": new_points,
            "cgpa": new_cgpa,
        }

        if not reached_term and new_cgpa >= float(target_cgpa):
            reached_term = term_name

    if reached_term:
        warnings.append(
            (
                f"تم الوصول للمعدل المستهدف في {reached_term}."
                if IS_AR else
                f"Target CGPA is reached in {reached_term}."
            )
        )
    return results, warnings


def _auto_base_type(item: Dict) -> str:
    base = str(item.get("base_type", item.get("type", "New / Remaining")))
    if base == "Off-Term Graduation Exception":
        base = "New / Remaining"
    return base


def _auto_adjust_item_for_term(item: Dict, term_type: str) -> Dict:
    """Keep the academic type, while marking off-term placement clearly."""
    adjusted = dict(item)
    base_type = _auto_base_type(adjusted)
    adjusted["base_type"] = base_type

    original_semester = str(adjusted.get("semester", "Any"))
    is_offterm = original_semester not in {term_type, "Any"}

    if base_type == "New / Remaining" and is_offterm:
        adjusted["type"] = "Off-Term Graduation Exception"
    else:
        adjusted["type"] = base_type

    adjusted["offterm"] = is_offterm
    adjusted["unlocks_next"] = unlocks_text(adjusted.get("code", ""))
    return adjusted


def _auto_nonempty_terms(draft: List[Dict]) -> List[Dict]:
    return [term for term in draft if term.get("courses")]


def _auto_resequence_terms(draft: List[Dict], start_term: str, year_start: int) -> List[Dict]:
    """
    Compress the plan after deleting/merging terms, then refresh labels,
    capacities and off-term markings.
    """
    compact = [dict(term) for term in draft if term.get("courses")]
    term_type = start_term
    academic_year = int(year_start)

    starting_cgpa = float(
        st.session_state.get("auto_plan_base_header", {}).get("cgpa", 0)
    )
    regular_capacity = regular_load_limit_for_cgpa(starting_cgpa)

    for index, term in enumerate(compact):
        term["term_type"] = term_type
        term["academic_year_start"] = academic_year
        term["term_name"] = _academic_term_label(academic_year, term_type)
        term["courses"] = [
            _auto_adjust_item_for_term(item, term_type)
            for item in term.get("courses", [])
        ]
        term["locked"] = bool(term.get("locked", False))

        is_final = index == len(compact) - 1
        term["is_final_term"] = is_final
        term["capacity"] = (
            (12 if term_type == "Summer" else 22)
            if is_final
            else (9 if term_type == "Summer" else regular_capacity)
        )

        term_type, academic_year = _next_academic_term(term_type, academic_year)

    return compact


def _auto_all_items(draft: List[Dict], unscheduled: List[Dict]) -> List[Dict]:
    items = []
    seen = set()
    for term in draft:
        for item in term.get("courses", []):
            code = norm(item.get("code", ""))
            if code and code not in seen:
                items.append(dict(item))
                seen.add(code)
    for item in unscheduled:
        code = norm(item.get("code", ""))
        if code and code not in seen:
            items.append(dict(item))
            seen.add(code)
    return items


def _auto_find_item(draft: List[Dict], unscheduled: List[Dict], code: str):
    ncode = norm(code)
    for term in draft:
        for item in term.get("courses", []):
            if norm(item.get("code", "")) == ncode:
                return dict(item)
    for item in unscheduled:
        if norm(item.get("code", "")) == ncode:
            return dict(item)
    return None


def _auto_remove_code_everywhere(draft: List[Dict], unscheduled: List[Dict], code: str):
    ncode = norm(code)
    for term in draft:
        term["courses"] = [
            item for item in term.get("courses", [])
            if norm(item.get("code", "")) != ncode
        ]
    unscheduled[:] = [
        item for item in unscheduled
        if norm(item.get("code", "")) != ncode
    ]


def _auto_move_course_to_term(course_code: str, target_index: int):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]
    unscheduled = [
        dict(item) for item in st.session_state.get("auto_unscheduled_courses", [])
    ]

    item = _auto_find_item(draft, unscheduled, course_code)
    if item is None or target_index < 0 or target_index >= len(draft):
        return False

    _auto_remove_code_everywhere(draft, unscheduled, course_code)
    draft[target_index]["courses"].append(
        _auto_adjust_item_for_term(item, draft[target_index].get("term_type", "Fall"))
    )

    start_term = st.session_state.get("auto_start_term", "Fall")
    start_year = int(st.session_state.get("auto_year_start", datetime.now().year))
    st.session_state["auto_plan_draft"] = _auto_resequence_terms(
        draft, start_term, start_year
    )
    st.session_state["auto_unscheduled_courses"] = unscheduled
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True


def _auto_remove_course_from_term(course_code: str, source_index: int):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]
    unscheduled = [
        dict(item) for item in st.session_state.get("auto_unscheduled_courses", [])
    ]

    if source_index < 0 or source_index >= len(draft):
        return False

    ncode = norm(course_code)
    found = None
    kept = []
    for item in draft[source_index].get("courses", []):
        if norm(item.get("code", "")) == ncode and found is None:
            found = dict(item)
        else:
            kept.append(item)
    if found is None:
        return False

    draft[source_index]["courses"] = kept
    _auto_remove_code_everywhere([], unscheduled, course_code)
    unscheduled.append(found)

    start_term = st.session_state.get("auto_start_term", "Fall")
    start_year = int(st.session_state.get("auto_year_start", datetime.now().year))
    st.session_state["auto_plan_draft"] = _auto_resequence_terms(
        draft, start_term, start_year
    )
    st.session_state["auto_unscheduled_courses"] = unscheduled
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True


def _auto_delete_term(term_index: int):
    return _auto_delete_empty_term(term_index)


def _auto_merge_with_previous(term_index: int):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]

    if term_index <= 0 or term_index >= len(draft):
        return False, "No previous term."
    if draft[term_index].get("locked", False) or draft[term_index - 1].get("locked", False):
        return (
            False,
            "Unlock both terms before merging."
            if not IS_AR else
            "افتح تعديل الترمين قبل الدمج."
        )

    combined = (
        list(draft[term_index - 1].get("courses", []))
        + list(draft[term_index].get("courses", []))
    )

    # Remove duplicates while preserving order.
    unique = []
    seen = set()
    for item in combined:
        code = norm(item.get("code", ""))
        if code and code not in seen:
            unique.append(item)
            seen.add(code)

    draft[term_index - 1]["courses"] = unique
    del draft[term_index]

    start_term = st.session_state.get("auto_start_term", "Fall")
    start_year = int(st.session_state.get("auto_year_start", datetime.now().year))
    refreshed = _auto_resequence_terms(draft, start_term, start_year)

    previous_index = min(term_index - 1, len(refreshed) - 1)
    merged_hours = sum(
        int(item.get("hours", 0))
        for item in refreshed[previous_index].get("courses", [])
    )
    limit = int(refreshed[previous_index].get("capacity", 0))
    if merged_hours > limit:
        return False, f"Combined hours are {merged_hours}, above the allowed {limit}."

    st.session_state["auto_plan_draft"] = refreshed
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True, ""


def _auto_add_next_term():
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]

    # Add a temporary empty term; it stays visible until the advisor adds a course.
    if draft:
        last_type = draft[-1].get("term_type", "Fall")
        last_year = int(draft[-1].get("academic_year_start", datetime.now().year))
        next_type, next_year = _next_academic_term(last_type, last_year)
    else:
        next_type = st.session_state.get("auto_start_term", "Fall")
        next_year = int(st.session_state.get("auto_year_start", datetime.now().year))

    starting_cgpa = float(
        st.session_state.get("auto_plan_base_header", {}).get("cgpa", 0)
    )
    regular_capacity = regular_load_limit_for_cgpa(starting_cgpa)
    draft.append({
        "term_type": next_type,
        "term_name": _academic_term_label(next_year, next_type),
        "academic_year_start": next_year,
        "capacity": 12 if next_type == "Summer" else regular_capacity,
        "is_final_term": True,
        "courses": [],
        "locked": False,
    })

    # Refresh old final-term flags without removing the newly added empty term.
    for i, term in enumerate(draft):
        is_final = i == len(draft) - 1
        term["is_final_term"] = is_final
        term_type = term.get("term_type", "Fall")
        term["capacity"] = (
            (12 if term_type == "Summer" else 22)
            if is_final
            else (9 if term_type == "Summer" else regular_capacity)
        )

    st.session_state["auto_plan_draft"] = draft
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1


def _auto_course_location(code: str, draft: List[Dict], unscheduled: List[Dict]) -> str:
    ncode = norm(code)
    for term in draft:
        if any(norm(item.get("code", "")) == ncode for item in term.get("courses", [])):
            return term.get("term_name", "")
    if any(norm(item.get("code", "")) == ncode for item in unscheduled):
        return "Unscheduled"
    return ""


def _auto_editor_option_label(code: str, draft: List[Dict], unscheduled: List[Dict]) -> str:
    item = _auto_find_item(draft, unscheduled, code)
    if item is None:
        return code
    location = _auto_course_location(code, draft, unscheduled)
    return (
        f"{item.get('code')} — {item.get('name', '')} "
        f"[{item.get('hours', 0)} hrs | currently: {location}]"
    )


def _auto_validation(
    draft: List[Dict],
    unscheduled: List[Dict],
    best: pd.DataFrame,
    extra_passed: Set[str],
    term_results: List[Dict] = None,
):
    errors = []
    warnings = []

    passed = passed_codes(best).union({norm(x) for x in (extra_passed or set())})
    seen = set()
    nonempty = _auto_nonempty_terms(draft)

    for term_index, term in enumerate(nonempty):
        courses = term.get("courses", [])
        term_hours = sum(int(item.get("hours", 0)) for item in courses)
        is_final = term_index == len(nonempty) - 1
        term_type = term.get("term_type", "Fall")

        base_cgpa = float(
            st.session_state.get("auto_plan_base_header", {}).get("cgpa", 0)
        )
        if term_index == 0:
            cgpa_before_term = base_cgpa
        elif term_results and term_index - 1 < len(term_results):
            cgpa_before_term = float(term_results[term_index - 1].get("new_cgpa", base_cgpa))
        else:
            cgpa_before_term = base_cgpa

        regular_capacity = regular_load_limit_for_cgpa(cgpa_before_term)
        standard_limit = 9 if term_type == "Summer" else regular_capacity
        final_limit = 12 if term_type == "Summer" else 22
        applicable_limit = final_limit if is_final else standard_limit

        if term_hours > applicable_limit:
            warnings.append(
                (
                    f"{term.get('term_name')}: {term_hours} hours exceed the normal "
                    f"{applicable_limit}-hour limit. Advisor override will be recorded."
                )
                if not IS_AR else
                (
                    f"{term.get('term_name')}: عدد الساعات {term_hours} يتجاوز الحد المعتاد "
                    f"{applicable_limit} ساعة، وسيتم اعتباره تجاوزًا بموافقة المرشد."
                )
            )

        if term_type != "Summer" and len(courses) > 7:
            warnings.append(
                (
                    f"{term.get('term_name')}: {len(courses)} courses exceed the regular-semester "
                    "maximum of 7 courses. Advisor override will be recorded."
                )
                if not IS_AR else
                (
                    f"{term.get('term_name')}: عدد المواد {len(courses)} يتجاوز الحد الأقصى "
                    "للترم العادي وهو 7 مواد، وسيتم اعتباره تجاوزًا بموافقة المرشد."
                )
            )

        remaining_from_here = [
            item
            for future_term in nonempty[term_index:]
            for item in future_term.get("courses", [])
        ]

        for item in courses:
            code = norm(item.get("code", ""))
            if code in seen:
                errors.append(f"{item.get('code')} is scheduled more than once.")
            seen.add(code)

            if item.get("type") != "Improvement D":
                missing = {
                    norm(x) for x in item.get("prereq", [])
                } - passed
                if missing:
                    errors.append(
                        f"{term.get('term_name')}: {item.get('code')} is before prerequisite(s) "
                        + ", ".join(sorted(missing))
                    )
                else:
                    base_passed_hours = float(
                        st.session_state.get("auto_plan_base_header", {}).get("passed_hours", 0)
                    )
                    if term_index == 0:
                        passed_hours_before_term = base_passed_hours
                    elif term_results and term_index - 1 < len(term_results):
                        passed_hours_before_term = float(
                            term_results[term_index - 1].get(
                                "new_passed_hours",
                                base_passed_hours,
                            )
                        )
                    else:
                        passed_hours_before_term = base_passed_hours

                    if not _training_hours_rule_met(
                        item,
                        passed,
                        passed_hours_before_term,
                        int(st.session_state.get("training1_required_hours", 65)),
                        int(st.session_state.get("training2_required_hours", 101)),
                    ):
                        training_reason = _training_rule_diagnostic(
                            item,
                            passed,
                            passed_hours_before_term,
                            IS_AR,
                            int(st.session_state.get("training1_required_hours", 65)),
                            int(st.session_state.get("training2_required_hours", 101)),
                        )
                        errors.append(
                            f"{term.get('term_name')}: {training_reason}"
                        )

        # Courses become prerequisites only after the term is completed.
        for item in courses:
            if item.get("type") != "Improvement D":
                passed.add(norm(item.get("code", "")))

    required_unscheduled = [
        item for item in unscheduled
        if _auto_base_type(item) != "Improvement D"
    ]
    optional_unscheduled = [
        item for item in unscheduled
        if _auto_base_type(item) == "Improvement D"
    ]

    if required_unscheduled:
        errors.append(
            "Required courses are still unscheduled: "
            + ", ".join(str(item.get("code", "")) for item in required_unscheduled)
        )
    if optional_unscheduled:
        warnings.append(
            "Optional D improvements outside the plan: "
            + ", ".join(str(item.get("code", "")) for item in optional_unscheduled)
        )

    return errors, warnings


def _auto_apply_training_placements(training1_term: str, training2_term: str):
    draft = st.session_state.get("auto_plan_draft", [])
    term_index_by_name = {
        term.get("term_name"): index for index, term in enumerate(draft)
    }

    changed = False
    if training1_term in term_index_by_name:
        changed = _auto_move_course_to_term("MEC 200", term_index_by_name[training1_term]) or changed
    if training2_term in term_index_by_name:
        # Re-read the draft because moving Training 1 may resequence it.
        refreshed = st.session_state.get("auto_plan_draft", [])
        term_index_by_name = {
            term.get("term_name"): index for index, term in enumerate(refreshed)
        }
        if training2_term in term_index_by_name:
            changed = _auto_move_course_to_term("MEC 300", term_index_by_name[training2_term]) or changed
    return changed




def _auto_refresh_term_metadata(draft: List[Dict]) -> List[Dict]:
    """
    Refresh capacities and off-term labels without collapsing chronological gaps.
    Empty terms stay available so a removed course can be placed in Summer or
    in the same semester of the following academic year.
    """
    refreshed = []
    for term in draft:
        copied = dict(term)
        copied["courses"] = [
            _auto_adjust_item_for_term(dict(item), copied.get("term_type", "Fall"))
            for item in term.get("courses", [])
        ]
        copied["locked"] = bool(term.get("locked", False))
        refreshed.append(copied)

    nonempty_indexes = [
        index for index, term in enumerate(refreshed)
        if term.get("courses")
    ]
    last_nonempty = nonempty_indexes[-1] if nonempty_indexes else -1

    starting_cgpa = float(
        st.session_state.get("auto_plan_base_header", {}).get("cgpa", 0)
    )
    regular_capacity = regular_load_limit_for_cgpa(starting_cgpa)

    for index, term in enumerate(refreshed):
        is_final = index == last_nonempty and last_nonempty >= 0
        term_type = term.get("term_type", "Fall")
        term["is_final_term"] = is_final
        term["capacity"] = (
            (12 if term_type == "Summer" else 22)
            if is_final
            else (9 if term_type == "Summer" else regular_capacity)
        )

    return refreshed


def _auto_term_position_for_code(draft: List[Dict], code: str):
    ncode = norm(code)
    for term_index, term in enumerate(draft):
        for item in term.get("courses", []):
            if norm(item.get("code", "")) == ncode:
                return term_index
    return None


def _auto_locked_course_codes(draft: List[Dict]) -> Set[str]:
    return {
        norm(item.get("code", ""))
        for term in draft
        if term.get("locked", False)
        for item in term.get("courses", [])
    }


def _auto_available_codes_for_term(
    draft: List[Dict],
    unscheduled: List[Dict],
    target_index: int,
) -> List[str]:
    """
    Courses in earlier reviewed terms never appear in later choices.
    The advisor can still pull a course forward from a later term.
    """
    options = []
    seen = set()
    locked_codes = _auto_locked_course_codes(draft)

    for item in unscheduled:
        code = norm(item.get("code", ""))
        if code and code not in seen and code not in locked_codes:
            options.append(item.get("code"))
            seen.add(code)

    for source_index, term in enumerate(draft):
        if source_index <= target_index:
            continue
        for item in term.get("courses", []):
            code = norm(item.get("code", ""))
            if code and code not in seen and code not in locked_codes:
                options.append(item.get("code"))
                seen.add(code)

    return options


def _auto_next_summer(term_type: str, academic_year_start: int):
    next_type, next_year = _next_academic_term(term_type, academic_year_start)
    for _ in range(5):
        if next_type == "Summer":
            return next_type, next_year
        next_type, next_year = _next_academic_term(next_type, next_year)
    return "Summer", academic_year_start + 1


def _auto_destination_options(
    draft: List[Dict],
    source_index: int,
    item: Dict,
) -> List[Dict]:
    """
    Offer the next Summer, the same semester next academic year,
    and all already-existing future terms.
    """
    if source_index < 0 or source_index >= len(draft):
        return []

    source = draft[source_index]
    source_type = source.get("term_type", "Fall")
    source_year = int(source.get("academic_year_start", datetime.now().year))

    next_summer_type, next_summer_year = _auto_next_summer(source_type, source_year)
    next_summer_name = _academic_term_label(next_summer_year, next_summer_type)

    same_next_year_name = _academic_term_label(source_year + 1, source_type)

    choices = []
    used = set()

    def add_choice(term_name, label, recommended=False):
        if term_name and term_name != source.get("term_name") and term_name not in used:
            choices.append({
                "term_name": term_name,
                "label": label,
                "recommended": recommended,
            })
            used.add(term_name)

    add_choice(
        next_summer_name,
        (
            f"Next Summer — {next_summer_name}"
            if not IS_AR else
            f"الصيفي القادم — {next_summer_name}"
        ),
        True,
    )
    add_choice(
        same_next_year_name,
        (
            f"Same Semester Next Year — {same_next_year_name}"
            if not IS_AR else
            f"نفس الترم في السنة التالية — {same_next_year_name}"
        ),
        True,
    )

    for index, term in enumerate(draft):
        if index <= source_index:
            continue
        add_choice(
            term.get("term_name"),
            (
                f"Existing Term — {term.get('term_name')}"
                if not IS_AR else
                f"ترم موجود — {term.get('term_name')}"
            ),
        )

    return choices


def _auto_append_until_term(draft: List[Dict], target_term_name: str) -> List[Dict]:
    """Append sequential empty terms until the requested destination exists."""
    if any(term.get("term_name") == target_term_name for term in draft):
        return draft

    if draft:
        last = draft[-1]
        term_type = last.get("term_type", "Fall")
        academic_year = int(last.get("academic_year_start", datetime.now().year))
    else:
        term_type = st.session_state.get("auto_start_term", "Fall")
        academic_year = int(st.session_state.get("auto_year_start", datetime.now().year))
        draft.append({
            "term_type": term_type,
            "term_name": _academic_term_label(academic_year, term_type),
            "academic_year_start": academic_year,
            "capacity": 0,
            "is_final_term": False,
            "courses": [],
            "locked": False,
        })

    safety = 0
    while not any(term.get("term_name") == target_term_name for term in draft):
        safety += 1
        if safety > 24:
            break
        term_type, academic_year = _next_academic_term(term_type, academic_year)
        draft.append({
            "term_type": term_type,
            "term_name": _academic_term_label(academic_year, term_type),
            "academic_year_start": academic_year,
            "capacity": 0,
            "is_final_term": False,
            "courses": [],
            "locked": False,
        })

    return draft


def _auto_move_course_to_named_term(
    course_code: str,
    target_term_name: str,
):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]
    unscheduled = [
        dict(item) for item in st.session_state.get("auto_unscheduled_courses", [])
    ]

    item = _auto_find_item(draft, unscheduled, course_code)
    if item is None:
        return False

    # A reviewed term must be explicitly unlocked before one of its courses moves.
    source_index = _auto_term_position_for_code(draft, course_code)
    if (
        source_index is not None
        and draft[source_index].get("locked", False)
        and draft[source_index].get("term_name") != target_term_name
    ):
        return False

    _auto_remove_code_everywhere(draft, unscheduled, course_code)
    draft = _auto_append_until_term(draft, target_term_name)

    target_index = next(
        (
            index for index, term in enumerate(draft)
            if term.get("term_name") == target_term_name
        ),
        None,
    )
    if target_index is None:
        return False

    draft[target_index]["courses"].append(
        _auto_adjust_item_for_term(item, draft[target_index].get("term_type", "Fall"))
    )

    st.session_state["auto_plan_draft"] = _auto_refresh_term_metadata(draft)
    st.session_state["auto_unscheduled_courses"] = unscheduled
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True


def _auto_set_term_lock(term_index: int, locked: bool):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]

    if term_index < 0 or term_index >= len(draft):
        return False

    draft[term_index]["locked"] = bool(locked)
    st.session_state["pending_course_relocation"] = None
    st.session_state["auto_plan_draft"] = _auto_refresh_term_metadata(draft)
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True


def _auto_delete_empty_term(term_index: int):
    draft = [dict(term) for term in st.session_state.get("auto_plan_draft", [])]
    for term in draft:
        term["courses"] = [dict(item) for item in term.get("courses", [])]

    if term_index < 0 or term_index >= len(draft):
        return False, "Invalid term."
    if draft[term_index].get("courses"):
        return (
            False,
            (
                "Move the courses first, then delete the empty term."
                if not IS_AR else
                "انقل مواد الترم أولًا، وبعد ما يبقى فاضي احذفه."
            ),
        )
    if draft[term_index].get("locked", False):
        return (
            False,
            (
                "Unlock the term before deleting it."
                if not IS_AR else
                "افتح تعديل الترم أولًا قبل حذفه."
            ),
        )

    del draft[term_index]

    # Empty-term deletion is allowed to compact the displayed plan.
    start_term = st.session_state.get("auto_start_term", "Fall")
    start_year = int(st.session_state.get("auto_year_start", datetime.now().year))
    compact = _auto_resequence_terms(draft, start_term, start_year)
    for term in compact:
        term["locked"] = bool(term.get("locked", False))

    st.session_state["auto_plan_draft"] = _auto_refresh_term_metadata(compact)
    st.session_state["auto_edit_revision"] = int(
        st.session_state.get("auto_edit_revision", 0)
    ) + 1
    return True, ""


def _auto_existing_term_names(draft: List[Dict]) -> List[str]:
    return [term.get("term_name") for term in draft if term.get("term_name")]



def automatic_term_results(base_header: Dict, draft: List[Dict], grade_values: Dict[str, str]):
    """Calculate all automatic terms sequentially using advisor-entered grades."""
    running_header = dict(base_header)
    results = []

    calculation_terms = [term for term in draft if term.get("courses")]
    for term_index, term in enumerate(calculation_terms):
        cgpa_before_term = float(running_header.get("cgpa", 0))
        allowed_regular_hours_before = regular_load_limit_for_cgpa(
            cgpa_before_term
        )
        new_codes, offterm_codes = [], []
        retake_rows, improvement_rows = [], []
        expected = {}

        for course_index, item in enumerate(term.get("courses", [])):
            code = item.get("code", "")
            item_type = item.get("type", "New / Remaining")
            widget_key = item.get("grade_key", f"AUTO::{term_index}::{course_index}")
            grade = grade_values.get(widget_key, "Select")

            if item_type == "Retake Failed":
                expected[f"RET::{code}"] = grade
                retake_rows.append({
                    "code": code,
                    "name": item.get("name", ""),
                    "hours": item.get("hours", 0),
                    "effective_grade": item.get("current_grade", "F"),
                    "latest_grade": item.get("current_grade", "F"),
                    "attempts_count": int(item.get("attempts_count", 1) or 1),
                    "max_allowed_grade": item.get(
                        "max_allowed_grade",
                        retake_max_allowed_grade(item.get("attempts_count", 1)),
                    ),
                })
            elif item_type == "Improvement D":
                expected[f"IMP::{code}"] = grade
                improvement_rows.append({
                    "code": code,
                    "name": item.get("name", ""),
                    "hours": item.get("hours", 0),
                    "current_grade": "D",
                    "current_points": item.get("current_points", 1.0),
                })
            elif item_type == "Off-Term Graduation Exception":
                expected[f"OFF::{code}"] = grade
                offterm_codes.append(code)
            else:
                expected[f"NEW::{code}"] = grade
                new_codes.append(code)

        result = compute_one_term(
            running_header,
            new_codes,
            pd.DataFrame(retake_rows),
            pd.DataFrame(improvement_rows),
            expected,
            offterm_codes,
        )
        if not result["plan_df"].empty:
            result["plan_df"]["planned_term"] = term.get("term_name", term.get("term_type", ""))
            result["plan_df"]["automatic_plan"] = "Yes"

            for item in term.get("courses", []):
                if not item.get("is_list_ab_replacement"):
                    continue
                code_mask = result["plan_df"]["course"].astype(str).apply(norm).eq(
                    norm(item.get("code", ""))
                )
                result["plan_df"].loc[code_mask, "name"] = item.get(
                    "name",
                    list_replacement_course_name(
                        item.get("code", ""),
                        item.get("replacement_for", ""),
                        False,
                    ),
                )
                result["plan_df"].loc[code_mask, "effect"] = (
                    "Alternative course from the same List A/B; full grade scale from A+"
                )
                result["plan_df"].loc[code_mask, "replacement_for"] = item.get(
                    "replacement_for",
                    "",
                )

        grades_complete = all(
            str(grade_values.get(item.get("grade_key"), "Select")) != "Select"
            for item in term.get("courses", [])
        )

        record = {
            "term_name": term.get("term_name", term.get("term_type", "")),
            "term_type": term.get("term_type", ""),
            "cgpa_before_term": cgpa_before_term,
            "allowed_regular_hours_before": allowed_regular_hours_before,
            "grades_complete": grades_complete,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "plan_df": result["plan_df"],
            "term_registered_hours": result["term_registered_hours"],
            "term_sgpa": result["term_sgpa"],
            "new_passed_hours": result["new_passed_hours"],
            "new_gpa_hours": result["new_gpa_hours"],
            "new_total_points": result["new_total_points"],
            "new_cgpa": result["new_cgpa"],
            "term_grade": gpa_grade_description(result["term_sgpa"], False),
            "cumulative_grade": gpa_grade_description(result["new_cgpa"], False),
            "next_regular_load": regular_load_limit_for_cgpa(result["new_cgpa"]),
            "next_regular_load_description": registration_load_description(
                result["new_cgpa"],
                False,
            ),
            "auto_generated": True,
        }
        results.append(record)
        running_header = {
            **running_header,
            "passed_hours": result["new_passed_hours"],
            "gpa_hours": result["new_gpa_hours"],
            "total_points": result["new_total_points"],
            "cgpa": result["new_cgpa"],
        }

    return results


def _auto_apply_dynamic_expected_loads(
    draft: List[Dict],
    base_header: Dict,
):
    """
    Update every regular-term capacity from the expected CGPA after the
    preceding completed term.

    Example:
    Starting CGPA allows 12 hours. If the expected result after Term 1 raises
    CGPA above 1.00, Term 2 immediately opens to 15 hours.
    """
    refreshed = [dict(term) for term in draft]
    for term in refreshed:
        term["courses"] = [
            dict(item) for item in term.get("courses", [])
        ]

    preview_grades = {
        item.get("grade_key"): st.session_state.get(
            item.get("grade_key"),
            "Select",
        )
        for term in refreshed
        for item in term.get("courses", [])
        if item.get("grade_key")
    }

    preview_records = automatic_term_results(
        base_header,
        refreshed,
        preview_grades,
    )

    running_cgpa = float(base_header.get("cgpa", 0))
    completed_prefix = True
    result_index = 0
    last_nonempty_index = max(
        (
            index for index, term in enumerate(refreshed)
            if term.get("courses")
        ),
        default=-1,
    )
    contexts = []

    for term_index, term in enumerate(refreshed):
        term_type = term.get("term_type", "Fall")
        is_final = term_index == last_nonempty_index and last_nonempty_index >= 0

        cgpa_before = running_cgpa
        normal_capacity = (
            9
            if term_type == "Summer"
            else regular_load_limit_for_cgpa(cgpa_before)
        )
        capacity = (
            (12 if is_final else 9)
            if term_type == "Summer"
            else (22 if is_final else normal_capacity)
        )

        record = None
        grades_complete = False
        if term.get("courses") and result_index < len(preview_records):
            record = preview_records[result_index]
            grades_complete = bool(record.get("grades_complete", False))
            result_index += 1

        prediction_reliable = bool(completed_prefix and grades_complete)
        expected_after = None
        next_load = None

        if record is not None and prediction_reliable:
            expected_after = float(record.get("new_cgpa", cgpa_before))
            next_load = regular_load_limit_for_cgpa(expected_after)
            running_cgpa = expected_after
        elif term.get("courses"):
            completed_prefix = False

        term["is_final_term"] = is_final
        term["capacity"] = int(capacity)
        term["cgpa_before_term"] = float(cgpa_before)
        term["normal_regular_capacity"] = int(normal_capacity)
        term["expected_cgpa_after_term"] = expected_after
        term["next_regular_load"] = next_load
        term["load_prediction_reliable"] = prediction_reliable

        contexts.append({
            "term_name": term.get("term_name", ""),
            "term_type": term_type,
            "cgpa_before_term": cgpa_before,
            "capacity": int(capacity),
            "normal_regular_capacity": int(normal_capacity),
            "expected_cgpa_after_term": expected_after,
            "next_regular_load": next_load,
            "prediction_reliable": prediction_reliable,
        })

    return refreshed, contexts


# =========================================================
# Robust Session State Initialization
# =========================================================
SESSION_DEFAULTS = {
    "parsed": None,
    "terms": [],
    "corona_selected_keys": set(),
    "planned_passed": set(),
    "planned_improved_d": set(),
    "planned_scheduled": set(),
    "planned_failed": set(),
    "newly_unlocked": [],
    "editing_term_number": None,
    "plan_offterm": [],
    "pending_term_edit": None,
    "auto_plan_draft": [],
    "auto_plan_notes": [],
    "auto_plan_version": 0,
    "auto_unscheduled_courses": [],
    "auto_edit_revision": 0,
    "auto_choose_training_manually": True,
    "auto_saved_notice": "",
    "local_settings_loaded": False,
    "saved_advisor_name": "",
    "saved_student_names": {},
    "training1_required_hours": 65,
    "training2_required_hours": 101,
    "pending_course_relocation": None,
    "elective_replacement_choices_by_student": {},
    "recovery_plan_records": [],
    "recovery_plan_notes": [],
    "recovery_plan_draft": [],
    "recovery_unscheduled_courses": [],
    "recovery_base_header": {},
    "recovery_editor_revision": 0,
}

for _key, _default in SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        if isinstance(_default, set):
            st.session_state[_key] = set()
        elif isinstance(_default, list):
            st.session_state[_key] = []
        elif isinstance(_default, dict):
            st.session_state[_key] = {}
        else:
            st.session_state[_key] = _default


if not st.session_state.get("local_settings_loaded", False):
    _saved_settings = load_local_settings()
    st.session_state["saved_advisor_name"] = _saved_settings.get("advisor_name", "")
    st.session_state["saved_student_names"] = _saved_settings.get("student_names", {})
    st.session_state["training1_required_hours"] = int(
        _saved_settings.get("training1_required_hours", 65)
    )
    st.session_state["training2_required_hours"] = int(
        _saved_settings.get("training2_required_hours", 101)
    )
    st.session_state["local_settings_loaded"] = True

# =========================================================
# Session
# =========================================================

if "parsed" not in st.session_state:
    st.session_state.parsed = None
if "terms" not in st.session_state:
    st.session_state.terms = []
if "corona_selected_keys" not in st.session_state:
    st.session_state.corona_selected_keys = set()
if "planned_passed" not in st.session_state:
    st.session_state.planned_passed = set()
if "planned_improved_d" not in st.session_state:
    st.session_state.planned_improved_d = set()
if "planned_scheduled" not in st.session_state:
    st.session_state.planned_scheduled = set()
if "planned_failed" not in st.session_state:
    st.session_state.planned_failed = set()
if "newly_unlocked" not in st.session_state:
    st.session_state.newly_unlocked = []


# =========================================================
# Sidebar
# =========================================================

st.sidebar.markdown(
    f"<div style='text-align:center;margin-bottom:2px'>"
    f"<img src='data:image/png;base64,{base64.b64encode(UNIVERSITY_LOGO_BYTES).decode('ascii')}' "
    f"style='width:82px;max-width:82px;opacity:.92'>"
    f"</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"<div style='text-align:center;font-weight:800;font-size:18px;"
    f"color:#0B5FA5;line-height:1.25'>{UNIVERSITY_NAME}</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"<div style='text-align:center;font-weight:700;font-size:15px;"
    f"color:#F28C00;margin-top:4px'>{PROGRAM_BRAND}</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"""
    <div style="
        margin:12px 4px 4px;
        padding:10px 12px;
        background:#FFFFFF;
        border:1px solid #D7E0EA;
        border-radius:12px;
        text-align:center;
        box-shadow:0 3px 10px rgba(31,78,120,.06);
    ">
        <div style="font-size:11px;color:#64748B;letter-spacing:.3px">
            DESIGNED &amp; DEVELOPED BY
        </div>
        <div style="font-size:15px;font-weight:900;color:#1F4E78;margin-top:3px">
            {APP_DEVELOPER}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.divider()
st.sidebar.title("Graduation Planner")
lang = st.sidebar.radio("Language", ["English", "العربية"], horizontal=True)
IS_AR = lang == "العربية"

TXT = {
    "title": "مخطط التخرج" if IS_AR else "Graduation Planner",
    "caption": "أداة للمرشد: حلّل الطالب، اختار المواد يدويًا، أدخل التوقعات، واحسب المعدل ترم بترم." if IS_AR else "Advisor tool: analyze the student, choose courses manually, enter expected grades, and calculate CGPA term by term.",
    "upload": "رفع ملف History PDF" if IS_AR else "Upload History PDF",
    "analyze": "تحليل الملف" if IS_AR else "Analyze PDF",
    "reset": "إعادة ضبط الخطة" if IS_AR else "Reset Planner",
    "debug": "عرض النص المستخرج" if IS_AR else "Show extracted text debug",
    "tab_all_courses": "كل مواد القسم" if IS_AR else "All Curriculum",
    "tab_history": "تاريخ الطالب" if IS_AR else "Student History",
    "tab_failed": "مواد الرسوب و D" if IS_AR else "Failed & D Courses",
    "tab_auto": "الخطة التلقائية" if IS_AR else "Automatic Plan",
    "tab_recovery": "خطة الوصول إلى 2.00" if IS_AR else "CGPA Recovery to 2.00",
    "tab_plan": "بناء الخطة والحساب" if IS_AR else "Plan & Calculate",
    "tab_report": "تقرير خطة التخرج" if IS_AR else "Graduation Report",
    "student_summary": "ملخص الطالب" if IS_AR else "Student Summary",
    "course_code": "كود المادة" if IS_AR else "Code",
    "course_name": "اسم المادة" if IS_AR else "Course Name",
    "requirement": "نوع المتطلب" if IS_AR else "Requirement",
    "level": "المستوى" if IS_AR else "Level",
    "semester": "الترم" if IS_AR else "Semester",
    "hours": "ساعات" if IS_AR else "Hours",
    "grade": "التقدير" if IS_AR else "Grade",
    "term": "الترم" if IS_AR else "Term",
    "failed_title": "مواد شايلها / إعادة" if IS_AR else "Failed / Retake Courses",
    "d_title": "مواد D فقط للتحسين" if IS_AR else "D Grade Improvement Only",
    "build_term": "بناء ترم واحد يدويًا" if IS_AR else "Build One Term Manually",
    "choose_term": "اختار الترم" if IS_AR else "Choose term",
    "new_courses": "مواد جديدة / متبقية" if IS_AR else "New / Remaining Courses",
    "retake_courses": "مواد إعادة / شايلها" if IS_AR else "Failed / Retake Courses",
    "improve_courses": "مواد تحسين D" if IS_AR else "D Improvement Courses",
    "expected_grades": "التقديرات المتوقعة" if IS_AR else "Expected Grades",
    "calculate": "الحساب" if IS_AR else "Calculate",
    "print_report": "تحميل تقرير HTML للطباعة" if IS_AR else "Download Printable HTML Report",
    "excel_report": "تحميل Excel" if IS_AR else "Download Excel Report",
    "a4_note": "التقرير HTML مضبوط للطباعة A4. افتحه من المتصفح ثم Ctrl+P." if IS_AR else "The HTML report is A4 print-friendly. Open it in a browser then press Ctrl+P.",
}

uploaded = st.sidebar.file_uploader(TXT["upload"], type=["pdf"])
if st.sidebar.button(TXT["analyze"], use_container_width=True):
    if not uploaded:
        st.sidebar.warning("Upload a PDF first.")
    else:
        try:
            text = extract_pdf_text(uploaded)
            header = parse_header(text)
            attempts = parse_courses(text)
            best = best_attempts(attempts)
            st.session_state.parsed = {
                "text": text,
                "header": header,
                "attempts": attempts,
                "best": best,
            }
            st.session_state.terms = []
            st.session_state.corona_selected_keys = set()
            st.session_state.planned_passed = set()
            st.session_state.planned_improved_d = set()
            st.session_state.planned_scheduled = set()
            st.session_state.planned_failed = set()
            clear_auto_plan_state()
            st.session_state["recovery_plan_records"] = []
            st.session_state["recovery_plan_notes"] = []
            st.session_state["recovery_plan_draft"] = []
            st.session_state["recovery_unscheduled_courses"] = []
            st.session_state["recovery_base_header"] = {}
            st.session_state["recovery_editor_revision"] = 0
            for key in ["plan_new", "plan_retakes", "plan_improve", "plan_offterm", "plan_term", "allow_offterm_exception", "pending_term_edit"]:
                st.session_state.pop(key, None)
            st.sidebar.success("PDF analyzed successfully ✅")
        except Exception as e:
            st.sidebar.error(f"PDF analysis failed: {e}")

show_debug = st.sidebar.checkbox(TXT["debug"])
if st.sidebar.button(TXT["reset"], use_container_width=True):
    st.session_state.terms = []
    st.session_state.corona_selected_keys = set()
    st.session_state.planned_passed = set()
    st.session_state.planned_improved_d = set()
    st.session_state.planned_scheduled = set()
    st.session_state.planned_failed = set()
    clear_auto_plan_state()
    st.session_state["recovery_plan_records"] = []
    st.session_state["recovery_plan_notes"] = []
    st.session_state["recovery_plan_draft"] = []
    st.session_state["recovery_unscheduled_courses"] = []
    st.session_state["recovery_base_header"] = {}
    st.session_state["recovery_editor_revision"] = 0
    for key in ["plan_new", "plan_retakes", "plan_improve", "plan_offterm", "plan_term", "allow_offterm_exception", "pending_term_edit"]:
        st.session_state.pop(key, None)


# =========================================================
# Main
# =========================================================

brand_col1, brand_col2 = st.columns([1, 5], vertical_alignment="center")
with brand_col1:
    st.markdown(
        f"<div style='text-align:center'>"
        f"<img src='data:image/png;base64,{base64.b64encode(UNIVERSITY_LOGO_BYTES).decode('ascii')}' "
        f"style='width:88px;max-width:88px;opacity:.92'>"
        f"</div>",
        unsafe_allow_html=True,
    )
with brand_col2:
    st.markdown(
        f"<h1 style='margin-bottom:2px;color:#0B5FA5'>{UNIVERSITY_NAME}</h1>"
        f"<h3 style='margin-top:0;color:#F28C00'>{PROGRAM_BRAND}</h3>",
        unsafe_allow_html=True,
    )
    st.caption(TXT["caption"])

st.markdown(
    f"""
    <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:8px 0 16px'>
      <div style='background:white;border:1px solid #d8e1ea;border-radius:10px;padding:9px'><b>1</b> — {'رفع السجل' if IS_AR else 'Upload History'}</div>
      <div style='background:white;border:1px solid #d8e1ea;border-radius:10px;padding:9px'><b>2</b> — {'مراجعة البيانات' if IS_AR else 'Review Data'}</div>
      <div style='background:#eaf4ff;border:1px solid #0B5FA5;border-radius:10px;padding:9px'><b>3</b> — {'بناء الخطة' if IS_AR else 'Build Plan'}</div>
      <div style='background:white;border:1px solid #d8e1ea;border-radius:10px;padding:9px'><b>4</b> — {'مراجعة الحساب' if IS_AR else 'Review Calculation'}</div>
      <div style='background:white;border:1px solid #d8e1ea;border-radius:10px;padding:9px'><b>5</b> — {'تحميل التقرير' if IS_AR else 'Download Report'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

if st.session_state.parsed is None:
    st.info("ارفع History PDF من الشمال واضغط Analyze PDF." if IS_AR else "Upload a History PDF from the sidebar and click Analyze PDF.")
    st.stop()

data = st.session_state.parsed
text = data["text"]
header = dict(data["header"])
header["program"] = PROGRAM_BRAND
attempts = data["attempts"]
best = data["best"]

student_id_for_settings = str(header.get("student_id", "")).strip()
saved_student_names = dict(st.session_state.get("saved_student_names", {}))
default_student_name = (
    saved_student_names.get(student_id_for_settings, "")
    or clean_extracted_student_name(header.get("student_name", ""))
)

with st.container(border=True):
    st.subheader(
        "بيانات الطالب والتقرير"
        if IS_AR else
        "Student and Report Details"
    )
    st.caption(
        (
            "اكتب اسم الطالب واسم المرشد هنا قبل حفظ أو طباعة الخطة. "
            "اسم المرشد يتم حفظه ويظهر تلقائيًا مع الطلاب التاليين."
        )
        if IS_AR else
        (
            "Enter the student and advisor names here before saving or printing. "
            "The advisor name is saved and reused for future students."
        )
    )

    identity_col1, identity_col2 = st.columns(2)

    with identity_col1:
        corrected_student_name = st.text_input(
            "اسم الطالب الصحيح" if IS_AR else "Correct Student Name",
            value=default_student_name,
            key=f"global_student_name_{student_id_for_settings}",
            help=(
                "اكتب الاسم يدويًا إذا كان الاسم المستخرج من الـPDF غير واضح."
                if IS_AR else
                "Type the name manually when the PDF-extracted name is unreadable."
            ),
        )

    with identity_col2:
        advisor_name_global = st.text_input(
            "اسم المشرف / المرشد الأكاديمي" if IS_AR else "Supervisor / Academic Advisor Name",
            value=st.session_state.get("saved_advisor_name", ""),
            key="global_advisor_name",
        )

    with st.expander(
        "إعدادات التدريب"
        if IS_AR else
        "Training Settings",
        expanded=False,
    ):
        st.caption(
            (
                "قاعدة التدريب تعتمد على إجمالي الساعات المجتازة، "
                "وليس إكمال كل مواد المستوى."
            )
            if IS_AR else
            (
                "Training eligibility is based on total passed hours, "
                "not completing every course in a level."
            )
        )

        training_col1, training_col2 = st.columns(2)

        with training_col1:
            training1_required_hours = st.number_input(
                "الساعات المطلوبة لتدريب 1"
                if IS_AR else
                "Passed Hours Required for Training 1",
                min_value=0,
                max_value=160,
                value=int(st.session_state.get("training1_required_hours", 65)),
                step=1,
                key="training1_hours_setting",
            )

        with training_col2:
            training2_required_hours = st.number_input(
                "الساعات المطلوبة لتدريب 2"
                if IS_AR else
                "Passed Hours Required for Training 2",
                min_value=0,
                max_value=160,
                value=int(st.session_state.get("training2_required_hours", 101)),
                step=1,
                key="training2_hours_setting",
            )

    if st.button(
        "حفظ اسم الطالب والمشرف"
        if IS_AR else
        "Save Student and Advisor Details",
        use_container_width=True,
        type="primary",
        key="save_identity_settings",
    ):
        if student_id_for_settings and corrected_student_name.strip():
            saved_student_names[student_id_for_settings] = corrected_student_name.strip()

        st.session_state["saved_student_names"] = saved_student_names
        st.session_state["saved_advisor_name"] = advisor_name_global.strip()
        st.session_state["training1_required_hours"] = int(training1_required_hours)
        st.session_state["training2_required_hours"] = int(training2_required_hours)

        try:
            save_local_settings(
                advisor_name_global.strip(),
                saved_student_names,
                int(training1_required_hours),
                int(training2_required_hours),
            )
            st.success(
                (
                    "تم حفظ اسم الطالب واسم المرشد. اسم المرشد سيظهر تلقائيًا "
                    "مع أي طالب جديد."
                )
                if IS_AR else
                (
                    "Student and advisor details were saved. The advisor name "
                    "will be reused for future students."
                )
            )
        except Exception as settings_error:
            st.error(
                (
                    "تعذر حفظ الإعدادات محليًا: "
                    if IS_AR else
                    "Could not save settings locally: "
                )
                + str(settings_error)
            )

header["student_name"] = corrected_student_name.strip()
advisor_name_global = advisor_name_global.strip()

if not header["student_name"]:
    st.warning(
        "اكتب اسم الطالب الصحيح قبل تحميل أو طباعة التقرير."
        if IS_AR else
        "Enter the correct student name before downloading or printing the report."
    )


if show_debug:
    st.text_area("Extracted PDF Text", text[:15000], height=320)

# Corona PASS adjustment: graduation hours stay unchanged; only GPA denominator changes.
corona_candidates = corona_pass_candidates(attempts)
selected_corona = corona_candidates[
    corona_candidates.apply(
        lambda r: f"{r['term']}::{r['ncode']}" in st.session_state.corona_selected_keys, axis=1
    )
].copy() if not corona_candidates.empty else pd.DataFrame()
corona_excluded_hours = float(selected_corona["hours"].sum()) if not selected_corona.empty else 0.0
base_total_points = float(header.get("total_points", 0) or 0)
base_gpa_hours = float(header.get("gpa_hours_from_tpoints", 0) or 0)

# Corona PASS hours are excluded from the GPA denominator only if the advisor
# explicitly marks them as Corona PASS. This is applied after the T.Points/CGPA
# denominator is reconstructed.
if base_gpa_hours <= 0:
    base_gpa_hours = attempted_gpa_hours_from_history(
        best,
        corona_excluded_hours,
    )
else:
    base_gpa_hours = max(0.0, base_gpa_hours - corona_excluded_hours)

base_corrected_cgpa = corrected_cgpa(base_total_points, base_gpa_hours)

# Use last saved term state as current starting point
current_header = dict(header)
current_header["gpa_hours"] = base_gpa_hours
current_header["total_points"] = base_total_points
current_header["cgpa"] = base_corrected_cgpa
if st.session_state.terms:
    last = st.session_state.terms[-1]
    current_header["passed_hours"] = last["new_passed_hours"]
    current_header["gpa_hours"] = last.get("new_gpa_hours", last["new_passed_hours"])
    current_header["total_points"] = last["new_total_points"]
    current_header["cgpa"] = last["new_cgpa"]

# Advisor override for Humanities List A/B completion.
# Some transcripts show the real Humanities course code/name instead of GENXXX placeholders.
detected_humanities_completed = humanities_completed_slots(
    best,
    st.session_state.planned_passed,
)
with st.expander(
    "حالة مواد الجامعة List A / List B"
    if IS_AR else
    "University Humanities List A/B Status",
    expanded=False,
):
    st.caption(
        (
            "الاختيار هنا معناه أن خانة الليست مكتملة ولن تظهر في المواد المتبقية. "
            "إزالة العلامة معناها أن الخانة ناقصة ويجب أن تظهر في الخطة."
        )
        if IS_AR else
        (
            "Checked means this list slot is completed and will not appear as remaining. "
            "Unchecked means it is still required and must appear in the plan."
        )
    )

    h_cols = st.columns(3)
    manual_humanities = set()
    manual_incomplete = set()

    for h_col, h_code, h_label in zip(
        h_cols,
        ["GENXXX-A", "GENXXX-B1", "GENXXX-B2"],
        ["List A", "List B — 1", "List B — 2"],
    ):
        with h_col:
            h_norm = norm(h_code)
            detected = h_norm in detected_humanities_completed
            checked = st.checkbox(
                f"{h_label} مكتملة" if IS_AR else f"{h_label} completed",
                value=detected,
                key=f"manual_completed_{h_norm}",
                help=(
                    "شيل العلامة لو الخانة دي ناقصة وعايزها تظهر في الخطة."
                    if IS_AR else
                    "Uncheck this if the slot is missing and you want it to appear in the plan."
                ),
            )

            detected_grade = humanities_slot_grade(best, h_code)
            if detected_grade:
                st.caption(
                    (
                        f"تم رصد تقدير: {detected_grade}"
                        if IS_AR else
                        f"Detected grade: {detected_grade}"
                    )
                )

            if checked:
                manual_humanities.add(h_norm)
            else:
                manual_incomplete.add(h_norm)

    # Make the override immediate:
    # completed slots are added to planned_passed; incomplete slots are removed
    # from planned_passed and planned_scheduled so they appear again below.
    for h_code in ["GENXXX-A", "GENXXX-B1", "GENXXX-B2"]:
        h_norm = norm(h_code)
        if h_norm in manual_humanities:
            st.session_state.planned_passed.add(h_code)
            st.session_state.planned_failed.discard(h_code)
        else:
            st.session_state.planned_passed.discard(h_code)
            st.session_state.planned_scheduled.discard(h_code)
            st.session_state.planned_failed.discard(h_code)

    st.session_state["humanities_manual_completed"] = manual_humanities
    st.session_state["humanities_manual_incomplete"] = manual_incomplete

    st.caption(
        (
            "ملاحظة: GEN401 Marketing Skills محسوبة كـ List A، ولو الطالب عوضها بمادة ناجحة من نفس القائمة فلن تظهر كإعادة. "
            "لو خانة ناقصة ومش ظاهرة، شيل العلامة من الخانة ثم اضغط Refresh أو Analyze PDF."
            if IS_AR else
            "Note: GEN401 Marketing Skills is treated as List A. If a missing slot is not appearing, uncheck it then refresh or analyze the PDF again."
        )
    )

grad = graduation_numbers(current_header)
rem_df = remaining_courses(
    best,
    st.session_state.planned_passed,
    st.session_state.planned_scheduled,
)
retake_all_raw = failed_retake_courses(
    attempts,
    best,
    st.session_state.planned_passed,
    st.session_state.planned_failed,
)
if not retake_all_raw.empty:
    hidden_codes = {
        norm(x) for x in st.session_state.planned_scheduled
        if norm(x) not in {norm(y) for y in st.session_state.planned_failed}
    }
    retake_all_raw = retake_all_raw[
        ~retake_all_raw["code"].astype(str).apply(norm).isin(hidden_codes)
    ].copy()

student_id_key = str(header.get("student_id", "")).strip() or "unknown_student"
all_replacement_choices = dict(
    st.session_state.get("elective_replacement_choices_by_student", {})
)
student_replacement_choices = dict(
    all_replacement_choices.get(student_id_key, {})
)

replacement_failed_norms = {
    norm(code)
    for code, target in student_replacement_choices.items()
    if target in HUMANITIES_REPLACEMENT_OPTIONS
}

retake_all = retake_all_raw.copy()
if not retake_all.empty and replacement_failed_norms:
    retake_all = retake_all[
        ~retake_all["code"].astype(str).apply(norm).isin(replacement_failed_norms)
    ].copy()

replacement_target_to_failed = {
    norm(target): failed_code
    for failed_code, target in student_replacement_choices.items()
    if target in HUMANITIES_REPLACEMENT_OPTIONS
}

withdrawn_all = withdrawn_courses(attempts, best)
completed_humanities_slots = humanities_completed_slots(
    best,
    st.session_state.get("planned_passed", set()),
)

d_all = d_grade_courses(best)
if not d_all.empty:
    d_all = d_all[
        ~d_all["code"].astype(str).apply(norm).isin({norm(x) for x in st.session_state.planned_improved_d})
    ].copy()


# =========================================================
# Main Tabs Layout
# =========================================================

tab_curr, tab_hist, tab_failed, tab_auto, tab_recovery, tab_plan, tab_report = st.tabs([
    TXT["tab_all_courses"],
    TXT["tab_history"],
    TXT["tab_failed"],
    TXT["tab_auto"],
    TXT["tab_recovery"],
    TXT["tab_plan"],
    TXT["tab_report"],
])

with tab_curr:
    print_current_page("طباعة الصفحة" if IS_AR else "Print This Tab")
    st.header(TXT["tab_all_courses"])
    st.caption("All curriculum requirements grouped by level and semester." if not IS_AR else "كل متطلبات اللائحة مقسمة حسب المستوى والترم.")
    cur = curriculum_df()
    lvl_filter = st.selectbox(TXT["level"], ["All"] + sorted(cur["level"].unique().tolist()), key="cur_lvl")
    sem_filter = st.selectbox(TXT["semester"], ["All"] + ["Fall", "Spring", "Summer"], key="cur_sem")
    view = cur.copy()
    if lvl_filter != "All":
        view = view[view["level"] == lvl_filter]
    if sem_filter != "All":
        view = view[view["semester"] == sem_filter]
    st.info(
        (
            "أي صف لونه أزرق معناه إن المادة دي بتفتح مادة أو أكثر بعدها."
            if IS_AR else
            "A blue row means that course unlocks one or more later courses."
        )
    )
    curriculum_view = view[
        [
            "level", "semester", "code", "name", "hours",
            "requirement_type", "prerequisite", "unlocks_next",
        ]
    ].copy()
    st.dataframe(
        curriculum_view.style.apply(
            highlight_unlocking_course_rows,
            axis=1,
        ),
        use_container_width=True,
    )

with tab_hist:
    print_current_page("طباعة الصفحة" if IS_AR else "Print This Tab")
    st.header(TXT["student_summary"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Student ID" if not IS_AR else "كود الطالب", header.get("student_id", ""))
    c2.metric("Current CGPA" if not IS_AR else "المعدل الحالي", f'{current_header.get("cgpa", 0):.3f}')
    c3.metric("Passed Hours" if not IS_AR else "الساعات المجتازة", f'{current_header.get("passed_hours", 0):.0f} / 160')
    c4.metric("Remaining Hours" if not IS_AR else "الساعات المتبقية", f'{grad["remaining_hours"]:.0f}')

    with st.expander(
        "طريقة حساب المعدل في البرنامج"
        if IS_AR else
        "GPA Calculation Audit",
        expanded=False,
    ):
        tpoints_now = float(current_header.get("total_points", 0) or 0)
        gpa_hours_now = float(current_header.get("gpa_hours", 0) or 0)
        cgpa_now = corrected_cgpa(tpoints_now, gpa_hours_now)
        st.markdown(
            (
                f"""
                **القانون المستخدم:**  
                CGPA = T.Points ÷ T.Hours  

                **القيم المستخدمة حاليًا:**  
                - T.Points = `{tpoints_now:.3f}`  
                - T.Hours = `{gpa_hours_now:.3f}`  
                - CGPA = `{tpoints_now:.3f} ÷ {gpa_hours_now:.3f} = {cgpa_now:.3f}`  

                **ملاحظات الحساب:**  
                - Total Registered Hours لا يستخدم كمقام للمعدل.  
                - المادة الراسب فيها F موجودة في المقام مرة واحدة فقط.  
                - عند النجاح في الإعادة، نضيف نقاط التقدير الجديد ولا نكرر الساعات.  
                - W لا تدخل في المقام ولا البسط.  
                """
            )
            if IS_AR else
            f"""
            **Formula used:**  
            CGPA = T.Points ÷ T.Hours  

            **Current values:**  
            - T.Points = `{tpoints_now:.3f}`  
            - T.Hours = `{gpa_hours_now:.3f}`  
            - CGPA = `{tpoints_now:.3f} ÷ {gpa_hours_now:.3f} = {cgpa_now:.3f}`  

            **Rules:**  
            - Total Registered Hours is not used as the CGPA denominator.  
            - A failed F course is counted in the denominator only once.  
            - A passed retake adds the new grade points without repeating hours.  
            - W has no numerator or denominator effect.
            """
        )

        if not attempts.empty:
            audit_df = attempts.copy()
            audit_df["attempt_points"] = audit_df["points"] * audit_df["hours"]
            audit_df["gpa_effect"] = audit_df["grade"].apply(
                lambda g: (
                    "No effect — W/PASS/FAIL"
                    if str(g).upper() in {"W", "PASS", "FAIL"}
                    else "GPA-bearing attempt"
                )
            )
            st.dataframe(
                audit_df[
                    [
                        "term", "code", "name", "grade",
                        "hours", "points", "attempt_points",
                        "passed", "gpa_effect",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Total Points" if not IS_AR else "إجمالي النقاط", f'{current_header.get("total_points", 0):.1f}')
    c6.metric("GPA Hours" if not IS_AR else "ساعات المعدل", f'{current_header.get("gpa_hours", 0):.0f}')
    points_source = header.get("points_source", "CGPA × Passed Hours")
    st.caption(
        f"Points source: {points_source}. Current points are validated against CGPA × passed hours."
        if not IS_AR else
        f"مصدر النقاط: {points_source}. يتم مراجعة النقاط باستخدام المعدل × الساعات المجتازة."
    )
    c7.metric("Points Gap to 2.00" if not IS_AR else "فرق النقاط للوصول 2.00", f'{grad["points_gap"]:.1f}')
    c8.metric("Academic Status" if not IS_AR else "الحالة الأكاديمية", infer_status(current_header.get("cgpa", 0)))

    if current_header.get("cgpa", 0) < 2:
        st.warning(
            "Target is only to reach CGPA 2.00 for graduation. Do not over-improve unless needed."
            if not IS_AR else
            "الهدف هو الوصول إلى CGPA 2.00 فقط للتخرج. لا تضف تحسينات زيادة إلا عند الحاجة."
        )
    else:
        st.success(
            "Student is already above 2.00. Focus on remaining requirements only."
            if not IS_AR else
            "الطالب بالفعل فوق 2.00. ركز على استكمال المتطلبات فقط."
        )

    st.subheader("Corona PASS Adjustment" if not IS_AR else "استبعاد مواد كورونا PASS")
    st.caption(
        "Select only positive-hour PASS courses taken during a Corona semester."
        if not IS_AR else
        "اختار فقط مواد PASS ذات الساعات الفعلية التي أخذها الطالب في ترم كورونا."
    )
    if corona_candidates.empty:
        st.info("No positive-hour PASS courses found." if not IS_AR else "لا توجد مواد PASS بساعات فعلية.")
    else:
        corona_view = corona_candidates.copy()
        corona_view["selector"] = corona_view.apply(lambda r: f"{r['term']}::{r['ncode']}", axis=1)
        options = corona_view["selector"].tolist()
        label_map = {r["selector"]: f"{r['term']} — {r['code']} — {r['name']} — {int(r['hours'])} hrs" for _, r in corona_view.iterrows()}
        selected = st.multiselect(
            "Corona PASS Courses" if not IS_AR else "مواد كورونا PASS",
            options,
            default=[x for x in st.session_state.corona_selected_keys if x in options],
            format_func=lambda x: label_map.get(x, x),
            key="corona_selector"
        )
        st.session_state.corona_selected_keys = set(selected)
        excluded = float(corona_view[corona_view["selector"].isin(selected)]["hours"].sum())
        gpa_hours_display = calculate_gpa_hours(header.get("passed_hours", 0), excluded)
        cgpa_display = corrected_cgpa(header.get("total_points", 0), gpa_hours_display)
        q1, q2, q3 = st.columns(3)
        q1.metric("Corona Excluded Hours" if not IS_AR else "ساعات كورونا المستبعدة", f"{excluded:.0f}")
        q2.metric("GPA Calculation Hours" if not IS_AR else "ساعات حساب المعدل", f"{gpa_hours_display:.0f}")
        q3.metric("Corrected CGPA" if not IS_AR else "المعدل بعد الاستبعاد", f"{cgpa_display:.3f}")
        st.info(
            "Graduation hours stay unchanged. Corona PASS hours are removed only from the CGPA denominator."
            if not IS_AR else
            "ساعات التخرج لا تتغير. ساعات كورونا PASS تُستبعد فقط من مقام حساب المعدل."
        )

    st.subheader("All History Attempts" if not IS_AR else "كل محاولات الطالب")
    st.dataframe(attempts[["term", "code", "name", "grade", "hours", "points", "passed"]], use_container_width=True)

    st.subheader("Best Attempt / Current Course Status" if not IS_AR else "أفضل محاولة / الوضع الحالي للمواد")
    st.dataframe(best[["term", "code", "name", "grade", "hours", "points", "passed"]], use_container_width=True)

with tab_failed:
    print_current_page("طباعة الصفحة" if IS_AR else "Print This Tab")
    st.header(TXT["failed_title"])

    if not withdrawn_all.empty:
        st.subheader(
            "المواد المنسحب منها W"
            if IS_AR else
            "Withdrawn Courses (W)"
        )
        st.info(
            (
                "تقدير W يعني انسحاب وليس رسوبًا. المادة لا تدخل في ساعات المعدل "
                "ولا عدد مرات الرسوب، وتظهر عند تسجيلها مرة أخرى كمادة جديدة "
                "بدون حد B+ أو C+."
            )
            if IS_AR else
            (
                "W means withdrawn, not failed. It does not count in GPA hours "
                "or failed attempts, and it is registered again as a normal new "
                "course without a B+/C retake cap."
            )
        )
        withdrawn_view = withdrawn_all.copy()
        withdrawn_view["status"] = (
            "منسحب — تُسجل كمادة جديدة"
            if IS_AR else
            "Withdrawn — register as new"
        )
        st.dataframe(
            withdrawn_view,
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        (
            "قاعدة الإعادة: لو الطالب هيعيد نفس المادة، فأقصى تقدير B+ بعد أول رسوب، "
            "وC+ لو رسب فيها أكثر من مرة. أما لو المادة من List A أو List B "
            "وسجّل مادة مختلفة من نفس القائمة، فهي مادة جديدة وتقديرها يبدأ من A+."
        )
        if IS_AR else
        (
            "Retake rule: repeating the same failed course is capped at B+ after one failure "
            "and C+ after more than one failure. If a failed List A/B elective is replaced "
            "with a different course from the same list, it is treated as a new course with "
            "the full grade scale starting at A+."
        )
    )
    st.caption(
        "حدد طريقة التعامل مع كل مادة راسب فيها الطالب."
        if IS_AR else
        "Choose how each failed course will be handled."
    )

    if retake_all_raw.empty:
        st.success(
            "لا توجد مواد رسوب غير مجتازة."
            if IS_AR else
            "No failed retake courses found."
        )
    else:
        retake_display = add_course_display_columns(retake_all_raw)
        cols = [
            "course_display", "requirement_type", "unlocks_next",
            "elective_list", "effective_grade", "latest_grade",
            "hours", "attempts_count", "max_allowed_grade",
            "last_term", "retake_reason",
        ]
        existing = [c for c in cols if c in retake_display.columns]
        st.dataframe(retake_display[existing], use_container_width=True)

        st.subheader(
            "استبدال مواد List A / List B"
            if IS_AR else
            "List A / List B Course Replacement"
        )
        st.caption(
            (
                "استخدم الاستبدال فقط لو المادة الراسب فيها الطالب أصلًا من List A أو List B. "
                "اختيار مادة بديلة يلغي إعادة نفس المادة من الخطة، والمادة البديلة يكون "
                "متاحًا لها A+."
            )
            if IS_AR else
            (
                "Use replacement only when the failed course originally belongs to List A or List B. "
                "The failed course will be removed from retakes, and the alternative course will allow A+."
            )
        )

        replacement_options = [
            "RETAKE_SAME",
            "GENXXX-A",
            "GENXXX-B1",
            "GENXXX-B2",
        ]

        replacement_labels = {
            "RETAKE_SAME": (
                "إعادة نفس المادة — يطبق حد B+ / C+"
                if IS_AR else
                "Retake the same course — B+ / C+ cap applies"
            ),
            "GENXXX-A": humanities_replacement_label("GENXXX-A", IS_AR) + (
                " — التقدير من A+"
                if IS_AR else
                " — full scale from A+"
            ),
            "GENXXX-B1": humanities_replacement_label("GENXXX-B1", IS_AR) + (
                " — التقدير من A+"
                if IS_AR else
                " — full scale from A+"
            ),
            "GENXXX-B2": humanities_replacement_label("GENXXX-B2", IS_AR) + (
                " — التقدير من A+"
                if IS_AR else
                " — full scale from A+"
            ),
        }

        proposed_choices = {}
        for _, failed_row in retake_all_raw.iterrows():
            failed_code = str(failed_row.get("code", ""))
            current_target = student_replacement_choices.get(
                failed_code,
                "RETAKE_SAME",
            )
            if current_target not in replacement_options:
                current_target = "RETAKE_SAME"

            selected_action = st.selectbox(
                (
                    f"{failed_code} — {failed_row.get('name', '')}"
                ),
                replacement_options,
                index=replacement_options.index(current_target),
                format_func=lambda value: replacement_labels.get(value, value),
                key=f"list_ab_replacement_{student_id_key}_{norm(failed_code)}",
            )
            proposed_choices[failed_code] = selected_action

        if st.button(
            "تطبيق اختيارات الإعادة والاستبدال"
            if IS_AR else
            "Apply Retake and Replacement Choices",
            type="primary",
            use_container_width=True,
            key=f"apply_list_ab_replacements_{student_id_key}",
        ):
            chosen_targets = [
                target
                for target in proposed_choices.values()
                if target in HUMANITIES_REPLACEMENT_OPTIONS
            ]
            duplicate_targets = {
                target for target in chosen_targets
                if chosen_targets.count(target) > 1
            }

            if duplicate_targets:
                duplicate_text = ", ".join(
                    humanities_replacement_label(code, IS_AR)
                    for code in sorted(duplicate_targets)
                )
                st.error(
                    (
                        f"لا يمكن استخدام نفس خانة القائمة كبديل لأكثر من مادة: {duplicate_text}"
                    )
                    if IS_AR else
                    f"The same list slot cannot replace more than one failed course: {duplicate_text}"
                )
            else:
                saved_choices = {
                    code: target
                    for code, target in proposed_choices.items()
                    if target in HUMANITIES_REPLACEMENT_OPTIONS
                }
                all_replacement_choices[student_id_key] = saved_choices
                st.session_state[
                    "elective_replacement_choices_by_student"
                ] = all_replacement_choices

                # A generated draft may still contain the old retake, so clear it.
                clear_auto_plan_state()
                st.success(
                    "تم تطبيق الاختيارات. أنشئ الخطة التلقائية من جديد."
                    if IS_AR else
                    "Choices applied. Generate the automatic plan again."
                )
                st.rerun()

    st.header(TXT["d_title"])
    st.caption("D only. D+ is not included." if not IS_AR else "مواد D فقط. D+ غير مدرجة.")
    if d_all.empty:
        st.success("No D grade courses found." if not IS_AR else "لا توجد مواد D.")
    else:
        d_display = add_course_display_columns(d_all)
        cols = ["course_display", "requirement_type", "unlocks_next", "current_grade", "hours", "current_points", "term"]
        existing = [c for c in cols if c in d_display.columns]
        st.dataframe(d_display[existing], use_container_width=True)

with tab_auto:
    st.header("Automatic Graduation Plan" if not IS_AR else "إنشاء خطة التخرج تلقائيًا")
    st.caption(
        "The planner distributes remaining requirements by prerequisites and course offering. You enter every expected grade, then save and print the full plan."
        if not IS_AR else
        "البرنامج يوزع المواد المتبقية تلقائيًا حسب المتطلبات السابقة وموعد طرح المادة، ثم تدخل التقدير المتوقع لكل مادة وتحفظ وتطبع الخطة كاملة."
    )

    st.info(
        (
            "Regular load is recalculated after every term: 12 hours for CGPA 0.00–1.00, "
            "15 hours above 1.00 through 1.50, and 19 hours above 1.50. "
            "Summer allows 12 hours; the final regular term may reach 22 hours."
        )
        if not IS_AR else
        (
            "الحمل في الترم العادي يُعاد حسابه بعد كل ترم: 12 ساعة للمعدل من 0.00 إلى 1.00، "
            "و15 ساعة إذا أصبح أكبر من 1.00 وحتى 1.50، و19 ساعة إذا أصبح أكبر من 1.50. "
            "الصيفي حتى 12 ساعة، وآخر ترم عادي قد يصل إلى 22 ساعة."
        )
    )

    a1, a2, a3 = st.columns(3)
    with a1:
        auto_start_term = st.selectbox(
            "Starting Term" if not IS_AR else "بداية الخطة من ترم",
            ["Fall", "Spring", "Summer"],
            key="auto_start_term",
        )
    with a2:
        default_year = datetime.now().year
        auto_year = st.number_input(
            "Academic Year Start" if not IS_AR else "سنة بداية العام الأكاديمي",
            min_value=2020,
            max_value=2100,
            value=int(default_year),
            step=1,
            key="auto_year_start",
            help="Example: enter 2026 for 2026-2027.",
        )
    with a3:
        replace_saved_plan = st.checkbox(
            "Replace current saved plan" if not IS_AR else "استبدال الخطة المحفوظة الحالية",
            value=True,
            key="auto_replace_saved",
        )

    choose_training_manually = st.checkbox(
        "Ask me where to place Training 1 and Training 2 after generating the plan"
        if not IS_AR else
        "اسألني أضع تدريب 1 وتدريب 2 في أي ترم بعد إنشاء الخطة",
        value=True,
        key="auto_choose_training_manually",
        help=(
            "The advisor will select the exact generated term for each training course."
            if not IS_AR else
            "بعد إنشاء الخطة سيختار المرشد الترم المحدد لكل مادة تدريب."
        ),
    )

    if student_replacement_choices:
        replacement_summary = [
            (
                f"{failed_code} → {humanities_replacement_label(target_code, IS_AR)}"
            )
            for failed_code, target_code in student_replacement_choices.items()
        ]
        st.success(
            (
                "بدائل List A/B المطبقة: " + " | ".join(replacement_summary)
            )
            if IS_AR else
            (
                "Applied List A/B replacements: " + " | ".join(replacement_summary)
            )
        )

    improvement_options = d_all["code"].tolist() if not d_all.empty else []
    selected_auto_improvements = st.multiselect(
        "Optional D improvements" if not IS_AR else "مواد D اختيارية للتحسين عند الحاجة",
        improvement_options,
        format_func=lambda x: course_label(x, d_all),
        key="auto_selected_improvements",
        help=(
            "These courses count in the semester load but add only the grade-point difference."
            if not IS_AR else
            "هذه المواد تُحسب ضمن حمل الترم، لكنها تضيف فرق النقاط فقط ولا تضيف ساعات نجاح جديدة."
        ),
    )

    if st.button(
        "Generate Automatic Graduation Plan" if not IS_AR else "إنشاء خطة التخرج تلقائيًا",
        type="primary",
        use_container_width=True,
        key="generate_auto_plan",
    ):
        clear_auto_plan_state()

        if replace_saved_plan:
            generator_extra_passed = set()
            generator_scheduled = set()
            generator_failed = set()
            generator_header = dict(header)
            generator_header["gpa_hours"] = base_gpa_hours
            generator_header["cgpa"] = base_corrected_cgpa
        else:
            generator_extra_passed = set(st.session_state.planned_passed)
            generator_scheduled = set(st.session_state.planned_scheduled)
            generator_failed = set(st.session_state.planned_failed)
            generator_header = dict(current_header)

        draft, notes = generate_automatic_plan(
            best,
            attempts,
            generator_extra_passed,
            generator_scheduled,
            generator_failed,
            selected_auto_improvements,
            auto_start_term,
            int(auto_year),
            float(generator_header.get("cgpa", 0)),
            float(generator_header.get("passed_hours", 0)),
            student_replacement_choices,
        )

        version = int(st.session_state.get("auto_plan_version", 0))
        for ti, term in enumerate(draft):
            for ci, item in enumerate(term.get("courses", [])):
                prefix = {
                    "Retake Failed": "RET",
                    "Improvement D": "IMP",
                    "Off-Term Graduation Exception": "OFF",
                }.get(item.get("type"), "NEW")
                item["grade_key"] = f"auto_grade_{version}_{ti}_{ci}_{prefix}_{norm(item.get('code',''))}"

        draft = _auto_resequence_terms(draft, auto_start_term, int(auto_year))
        st.session_state["auto_plan_draft"] = draft
        st.session_state["auto_unscheduled_courses"] = []
        st.session_state["auto_plan_notes"] = notes
        st.session_state["auto_plan_base_header"] = generator_header
        st.session_state["auto_plan_replace_saved"] = replace_saved_plan
        st.rerun()

    draft = st.session_state.get("auto_plan_draft", [])
    notes = st.session_state.get("auto_plan_notes", [])

    if notes:
        for note in notes:
            st.warning(note)

    if draft:
        st.success(
            f"Automatic plan generated: {len(draft)} terms."
            if not IS_AR else
            f"تم إنشاء الخطة تلقائيًا: {len(draft)} ترم."
        )

        total_planned_hours = sum(
            int(item.get("hours", 0))
            for term in draft
            for item in term.get("courses", [])
        )
        p1, p2, p3 = st.columns(3)
        p1.metric("Number of Terms" if not IS_AR else "عدد الترمات", len(draft))
        p2.metric("Planned Registered Hours" if not IS_AR else "إجمالي الساعات المخططة", total_planned_hours)
        p3.metric(
            "Starting CGPA" if not IS_AR else "المعدل في بداية الخطة",
            f'{st.session_state.get("auto_plan_base_header", current_header).get("cgpa", 0):.3f}',
        )

        bulk_grade = st.selectbox(
            "Default expected grade" if not IS_AR else "تقدير افتراضي لجميع المواد",
            GRADE_OPTIONS,
            key="auto_bulk_grade",
        )
        if st.button(
            "Apply to all unfilled grades" if not IS_AR else "تطبيقه على كل التقديرات الفارغة",
            use_container_width=True,
            key="apply_auto_bulk_grade",
        ):
            if bulk_grade != "Select":
                for term in draft:
                    for item in term.get("courses", []):
                        key = item.get("grade_key")
                        if key and st.session_state.get(key, "Select") == "Select":
                            # Improvement is capped at B+.
                            if (
                                item.get("type") == "Improvement D"
                                and point_of_grade(bulk_grade) > point_of_grade("B+")
                            ):
                                st.session_state[key] = "B+"
                            elif item.get("type") == "Retake Failed":
                                st.session_state[key] = cap_retake_grade(
                                    bulk_grade,
                                    item.get("attempts_count", 1),
                                )
                            else:
                                st.session_state[key] = bulk_grade
                st.rerun()

        # -------------------------------------------------
        # Training placement
        # -------------------------------------------------
        draft = st.session_state.get("auto_plan_draft", [])
        unscheduled_courses = st.session_state.get("auto_unscheduled_courses", [])
        editor_revision = int(st.session_state.get("auto_edit_revision", 0))

        training_codes_in_plan = {
            norm(item.get("code", ""))
            for term in draft
            for item in term.get("courses", [])
        }.union({
            norm(item.get("code", ""))
            for item in unscheduled_courses
        })

        if st.session_state.get("auto_choose_training_manually", True) and (
            "MEC200" in training_codes_in_plan or "MEC300" in training_codes_in_plan
        ):
            st.subheader(
                "Choose Training Terms"
                if not IS_AR else
                "حدد الترم المناسب للتدريب"
            )
            st.caption(
                "Training can be moved to any generated term. The program will validate Training 1 before Training 2."
                if not IS_AR else
                "يمكن نقل التدريب لأي ترم في الخطة، وسيتم التأكد أن تدريب 1 يسبق تدريب 2."
            )

            term_names = [term.get("term_name") for term in draft]
            tcol1, tcol2, tcol3 = st.columns([2, 2, 1])

            current_t1 = _auto_course_location("MEC 200", draft, unscheduled_courses)
            current_t2 = _auto_course_location("MEC 300", draft, unscheduled_courses)

            with tcol1:
                training1_term = st.selectbox(
                    "Training 1 Term" if not IS_AR else "ترم تدريب 1",
                    term_names,
                    index=term_names.index(current_t1) if current_t1 in term_names else 0,
                    key=f"auto_training1_{editor_revision}",
                )
            with tcol2:
                training2_term = st.selectbox(
                    "Training 2 Term" if not IS_AR else "ترم تدريب 2",
                    term_names,
                    index=term_names.index(current_t2) if current_t2 in term_names else min(1, len(term_names) - 1),
                    key=f"auto_training2_{editor_revision}",
                )
            with tcol3:
                st.write("")
                st.write("")
                if st.button(
                    "Apply" if not IS_AR else "تطبيق",
                    key=f"apply_training_terms_{editor_revision}",
                    use_container_width=True,
                ):
                    _auto_apply_training_placements(training1_term, training2_term)
                    st.rerun()

        # -------------------------------------------------
        # Guided and flexible term editor
        # -------------------------------------------------
        st.subheader(
            "Review the Plan Term by Term"
            if not IS_AR else
            "راجع الخطة ترم بترم"
        )
        st.info(
            (
                "Approve each term after reviewing it. Approved-term courses disappear "
                "from later choices. When moving a course, choose its destination directly "
                "inside the same term box without scrolling."
            )
            if not IS_AR else
            (
                "بعد مراجعة كل ترم اضغط اعتماد توزيع الترم. مواد الترم المعتمد تختفي "
                "من اختيارات الترمات التالية. وعند نقل مادة هتختار الترم الجديد "
                "في نفس خانة الترم من غير ما تطلع لفوق."
            )
        )

        draft = st.session_state.get("auto_plan_draft", [])
        unscheduled_courses = st.session_state.get("auto_unscheduled_courses", [])
        editor_revision = int(st.session_state.get("auto_edit_revision", 0))

        # Any old unscheduled course is shown first and must be placed immediately.
        if unscheduled_courses:
            st.warning(
                "Place these courses before completing the plan."
                if not IS_AR else
                "وزّع المواد دي أولًا قبل استكمال الخطة."
            )
            for ui, item in enumerate(list(unscheduled_courses), start=1):
                existing_names = _auto_existing_term_names(draft)
                preferred_names = [
                    term.get("term_name")
                    for term in draft
                    if term.get("term_type") in {
                        item.get("semester", ""),
                        "Summer",
                    }
                ]
                destination_names = list(dict.fromkeys(preferred_names + existing_names))
                if not destination_names:
                    continue

                place_c1, place_c2, place_c3 = st.columns([3, 3, 1])
                with place_c1:
                    st.write(
                        f"**{item.get('code')} — {item.get('name', '')}** "
                        f"({item.get('hours', 0)} hrs)"
                    )
                with place_c2:
                    place_destination = st.selectbox(
                        "Destination" if not IS_AR else "الترم المقترح",
                        destination_names,
                        key=f"place_unscheduled_destination_{editor_revision}_{ui}",
                    )
                with place_c3:
                    st.write("")
                    if st.button(
                        "Place" if not IS_AR else "توزيع",
                        key=f"place_unscheduled_btn_{editor_revision}_{ui}",
                        use_container_width=True,
                    ):
                        _auto_move_course_to_named_term(
                            item.get("code"),
                            place_destination,
                        )
                        st.rerun()

        grade_values = {}

        draft, dynamic_load_contexts = _auto_apply_dynamic_expected_loads(
            draft,
            st.session_state.get("auto_plan_base_header", current_header),
        )
        st.session_state["auto_plan_draft"] = draft

        for ti, term in enumerate(draft, start=1):
            term_index = ti - 1
            term_hours = sum(
                int(item.get("hours", 0))
                for item in term.get("courses", [])
            )
            capacity = int(term.get("capacity", 0))
            is_locked = bool(term.get("locked", False))
            final_badge = (
                " — Final Term"
                if term.get("is_final_term") and not IS_AR
                else (" — آخر ترم" if term.get("is_final_term") else "")
            )
            lock_badge = (
                " ✅ Reviewed"
                if is_locked and not IS_AR
                else (" ✅ تم اعتماد التوزيع" if is_locked else "")
            )

            cgpa_before_term = float(
                term.get(
                    "cgpa_before_term",
                    st.session_state.get(
                        "auto_plan_base_header",
                        current_header,
                    ).get("cgpa", 0),
                )
            )

            with st.expander(
                f"Term {ti}: {term.get('term_name')} — "
                f"{term_hours}/{capacity} hrs — "
                f"CGPA before {cgpa_before_term:.3f}"
                f"{final_badge}{lock_badge}",
                expanded=True,
            ):
                display_rows = []
                for item in term.get("courses", []):
                    display_rows.append({
                        "Code" if not IS_AR else "الكود": item.get("code"),
                        "Course" if not IS_AR else "المادة": item.get("name"),
                        "Type" if not IS_AR else "النوع": item.get("type"),
                        "Original Semester" if not IS_AR else "الترم الأصلي": item.get("semester"),
                        "Hours" if not IS_AR else "الساعات": item.get("hours"),
                        "Unlocks Next" if not IS_AR else "تفتح بعد كده": item.get("unlocks_next", ""),
                    })
                st.dataframe(
                    pd.DataFrame(display_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                load_c1, load_c2, load_c3 = st.columns(3)
                load_c1.metric(
                    "CGPA Before Term"
                    if not IS_AR else
                    "المعدل قبل الترم",
                    f"{cgpa_before_term:.3f}",
                )
                load_c2.metric(
                    "Allowed Hours This Term"
                    if not IS_AR else
                    "الساعات المسموحة في الترم",
                    capacity,
                )

                if term.get("load_prediction_reliable"):
                    expected_after = float(
                        term.get("expected_cgpa_after_term", 0)
                    )
                    next_load = int(term.get("next_regular_load", 0))
                    load_c3.metric(
                        "Next Regular-Term Load"
                        if not IS_AR else
                        "الساعات المسموحة في الترم العادي التالي",
                        next_load,
                        delta=(
                            f"CGPA {expected_after:.3f}"
                            if not IS_AR else
                            f"المعدل {expected_after:.3f}"
                        ),
                    )
                    st.success(
                        (
                            f"After this term: expected CGPA {expected_after:.3f}; "
                            f"the next regular-semester load becomes {next_load} hours."
                        )
                        if not IS_AR else
                        (
                            f"بعد هذا الترم: المعدل المتوقع {expected_after:.3f}، "
                            f"وبالتالي حمل الترم العادي التالي يصبح {next_load} ساعة."
                        )
                    )
                else:
                    load_c3.metric(
                        "Next Regular-Term Load"
                        if not IS_AR else
                        "الساعات المسموحة في الترم العادي التالي",
                        "Pending" if not IS_AR else "بعد إدخال التقديرات",
                    )
                    st.caption(
                        (
                            "Enter all expected grades in this term to calculate "
                            "the next regular-semester load."
                        )
                        if not IS_AR else
                        (
                            "أدخل كل تقديرات هذا الترم ليحسب البرنامج عدد الساعات "
                            "المسموحة في الترم العادي التالي."
                        )
                    )

                lock_col1, lock_col2 = st.columns([1, 3])
                with lock_col1:
                    if is_locked:
                        if st.button(
                            "Unlock Term"
                            if not IS_AR else
                            "فتح تعديل الترم",
                            key=f"unlock_auto_term_{editor_revision}_{ti}",
                            use_container_width=True,
                        ):
                            _auto_set_term_lock(term_index, False)
                            st.rerun()
                    else:
                        if st.button(
                            "Approve Term Distribution"
                            if not IS_AR else
                            "اعتماد توزيع الترم",
                            key=f"lock_auto_term_{editor_revision}_{ti}",
                            use_container_width=True,
                        ):
                            _auto_set_term_lock(term_index, True)
                            st.rerun()
                with lock_col2:
                    st.caption(
                        (
                            "Approved courses are removed from all later course choices."
                            if not IS_AR else
                            "بعد الاعتماد مواد الترم لن تظهر في اختيارات الترمات التالية."
                        )
                        if is_locked
                        else (
                            "Review additions and moves, then approve this term."
                            if not IS_AR else
                            "راجع الإضافات والنقل ثم اعتمد توزيع الترم."
                        )
                    )

                if not is_locked:
                    action_col1, action_col2 = st.columns(2)

                    with action_col1:
                        available_codes = _auto_available_codes_for_term(
                            draft,
                            unscheduled_courses,
                            term_index,
                        )
                        add_code = st.selectbox(
                            "+ Pull Course from a Later Term"
                            if not IS_AR else
                            "+ سحب مادة من ترم لاحق إلى هذا الترم",
                            [""] + available_codes,
                            format_func=lambda code: (
                                "Select course"
                                if not code and not IS_AR else
                                (
                                    "اختر المادة"
                                    if not code else
                                    _auto_editor_option_label(
                                        code,
                                        draft,
                                        unscheduled_courses,
                                    )
                                )
                            ),
                            key=f"auto_add_course_{editor_revision}_{ti}",
                        )
                        if st.button(
                            "Move Here"
                            if not IS_AR else
                            "نقل إلى هذا الترم",
                            key=f"auto_add_course_btn_{editor_revision}_{ti}",
                            use_container_width=True,
                            disabled=not bool(add_code),
                        ):
                            _auto_move_course_to_term(add_code, term_index)
                            st.rerun()

                    with action_col2:
                        current_codes = [
                            item.get("code")
                            for item in term.get("courses", [])
                        ]

                        move_code = st.selectbox(
                            "شيل أو انقل مادة من الترم"
                            if IS_AR else
                            "Remove or Move a Course",
                            [""] + current_codes,
                            format_func=lambda code: (
                                "اختر المادة"
                                if not code and IS_AR else
                                (
                                    "Select course"
                                    if not code else course_label(code)
                                )
                            ),
                            key=f"auto_move_future_course_{editor_revision}_{ti}",
                        )

                        selected_item = (
                            _auto_find_item(
                                draft,
                                unscheduled_courses,
                                move_code,
                            )
                            if move_code else None
                        )

                        destination_choices = (
                            _auto_destination_options(
                                draft,
                                term_index,
                                selected_item,
                            )
                            if selected_item else []
                        )
                        destination_names = [
                            choice["term_name"]
                            for choice in destination_choices
                        ]
                        destination_labels = {
                            choice["term_name"]: choice["label"]
                            for choice in destination_choices
                        }

                        destination = st.selectbox(
                            "اختار الترم الجديد للمادة"
                            if IS_AR else
                            "Choose the New Term",
                            destination_names or [""],
                            format_func=lambda name: (
                                destination_labels.get(name, name)
                                if name else
                                (
                                    "اختر الترم"
                                    if IS_AR else
                                    "Select destination"
                                )
                            ),
                            key=f"inline_destination_{editor_revision}_{ti}",
                            disabled=not bool(move_code),
                        )

                        if st.button(
                            "نقل المادة للترم المختار"
                            if IS_AR else
                            "Move Course to Selected Term",
                            key=f"inline_move_course_btn_{editor_revision}_{ti}",
                            use_container_width=True,
                            type="primary",
                            disabled=not bool(move_code and destination),
                        ):
                            moved = _auto_move_course_to_named_term(
                                move_code,
                                destination,
                            )
                            if moved:
                                st.session_state["pending_course_relocation"] = None
                                st.rerun()
                            else:
                                st.error(
                                    "تعذر نقل المادة. افتح تعديل الترم وحاول مرة أخرى."
                                    if IS_AR else
                                    "The course could not be moved. Unlock the term and try again."
                                )

                    manage_col1, manage_col2 = st.columns(2)
                    with manage_col1:
                        if ti > 1 and st.button(
                            "Merge This Term into Previous"
                            if not IS_AR else
                            "دمج هذا الترم مع الترم السابق",
                            key=f"auto_merge_term_{editor_revision}_{ti}",
                            use_container_width=True,
                        ):
                            merged, message = _auto_merge_with_previous(term_index)
                            if merged:
                                st.rerun()
                            else:
                                st.error(message)

                    with manage_col2:
                        delete_disabled = bool(term.get("courses"))
                        if st.button(
                            "Delete Empty Term"
                            if not IS_AR else
                            "حذف الترم الفارغ",
                            key=f"auto_delete_term_{editor_revision}_{ti}",
                            use_container_width=True,
                            disabled=delete_disabled,
                        ):
                            deleted, message = _auto_delete_empty_term(term_index)
                            if deleted:
                                st.rerun()
                            else:
                                st.error(message)
                        if delete_disabled:
                            st.caption(
                                "Move its courses first; no course will be left at the end."
                                if not IS_AR else
                                "انقل مواده أولًا؛ لن يتم ترك أي مادة معلقة في آخر الخطة."
                            )

                    if term.get("term_type") == "Summer":
                        st.caption(
                            (
                                "Summer is flexible: pull any course that the department "
                                "officially opens, subject to prerequisites and the 12-hour Summer limit."
                            )
                            if not IS_AR else
                            (
                                "الصيفي مرن: اسحب أي مادة فتحها القسم رسميًا، "
                                "مع مراعاة المتطلبات السابقة وحد الصيفي 12 ساعة."
                            )
                        )

                grade_cols = st.columns(2)
                for ci, item in enumerate(term.get("courses", [])):
                    options = GRADE_OPTIONS
                    label = f"{item.get('code')} — {item.get('name')}"

                    if item.get("type") == "Improvement D":
                        options = [
                            "Select", "B+", "B", "B-", "C+",
                            "C", "C-", "D+", "D", "F",
                        ]
                        label += (
                            " — أقصى تحسين B+"
                            if IS_AR else
                            " — Max B+"
                        )

                    elif item.get("type") == "Retake Failed":
                        attempts_count = int(item.get("attempts_count", 1) or 1)
                        max_grade = retake_max_allowed_grade(attempts_count)
                        options = retake_grade_options(attempts_count)
                        label += (
                            f" — مرات الرسوب {attempts_count} — أقصى تقدير {max_grade}"
                            if IS_AR else
                            f" — Failed attempts {attempts_count} — Max {max_grade}"
                        )

                    elif item.get("is_list_ab_replacement"):
                        options = GRADE_OPTIONS
                        replacement_for = item.get("replacement_for", "")
                        label += (
                            f" — بديل من نفس القائمة بدل {replacement_for} — التقدير من A+"
                            if IS_AR else
                            f" — Same-list alternative replacing {replacement_for} — full scale from A+"
                        )

                    current_widget_grade = st.session_state.get(
                        item["grade_key"],
                        "Select",
                    )
                    if current_widget_grade not in options:
                        st.session_state[item["grade_key"]] = (
                            cap_retake_grade(
                                current_widget_grade,
                                item.get("attempts_count", 1),
                            )
                            if item.get("type") == "Retake Failed"
                            else "B+"
                        )

                    with grade_cols[ci % 2]:
                        grade_values[item["grade_key"]] = st.selectbox(
                            label,
                            options,
                            key=item["grade_key"],
                        )

        add_term_col, compact_col = st.columns(2)
        with add_term_col:
            if st.button(
                "+ Add Another Term"
                if not IS_AR else
                "+ إضافة ترم جديد",
                key=f"auto_add_new_term_{editor_revision}",
                use_container_width=True,
            ):
                _auto_add_next_term()
                st.rerun()

        with compact_col:
            st.caption(
                (
                    "To reduce the number of terms, pull courses into earlier terms or merge "
                    "two unlocked terms while staying within the allowed load."
                )
                if not IS_AR else
                (
                    "لتقليل عدد الترمات اسحب المواد للترمات السابقة أو ادمج ترمين "
                    "غير معتمدين مع الالتزام بعدد الساعات."
                )
            )

        draft = st.session_state.get("auto_plan_draft", [])
        unscheduled_courses = st.session_state.get("auto_unscheduled_courses", [])

        auto_records = automatic_term_results(
            st.session_state.get("auto_plan_base_header", current_header),
            draft,
            grade_values,
        )

        validation_errors, validation_warnings = _auto_validation(
            draft,
            unscheduled_courses,
            best,
            (
                set()
                if st.session_state.get("auto_plan_replace_saved", True)
                else set(st.session_state.planned_passed)
            ),
            auto_records,
        )

        for warning in validation_warnings:
            st.warning(warning)
        for error in validation_errors:
            st.error(error)

        missing_auto_grades = any(value == "Select" for value in grade_values.values())
        failing_required = []
        for term in draft:
            for item in term.get("courses", []):
                grade = grade_values.get(item.get("grade_key"), "Select")
                if item.get("type") != "Improvement D" and grade not in PASSING and grade != "Select":
                    failing_required.append(item.get("code"))

        if auto_records:
            st.subheader("Automatic Plan Calculation" if not IS_AR else "حساب الخطة التلقائية")
            auto_summary = pd.DataFrame([
                {
                    "Term" if not IS_AR else "الترم": record["term_name"],
                    "Hours" if not IS_AR else "الساعات": record["term_registered_hours"],
                    "SGPA": round(record["term_sgpa"], 3),
                    "Term Grade" if not IS_AR else "تقدير الترم": gpa_grade_description(record["term_sgpa"], IS_AR),
                    "Passed Hours After" if not IS_AR else "الساعات بعد الترم": round(record["new_passed_hours"], 0),
                    "CGPA After" if not IS_AR else "المعدل بعد الترم": round(record["new_cgpa"], 3),
                    "Cumulative Grade" if not IS_AR else "التقدير التراكمي": gpa_grade_description(record["new_cgpa"], IS_AR),
                    "Next Regular Load" if not IS_AR else "ساعات الترم العادي التالي": regular_load_limit_for_cgpa(record["new_cgpa"]),
                }
                for record in auto_records
            ])
            st.dataframe(auto_summary, use_container_width=True)
            st.caption(
                (
                    "The next-term load is calculated from the CGPA after each term. "
                    "For example, a student may start with 12 hours and move to 15 hours "
                    "after raising the CGPA above 1.00."
                )
                if not IS_AR else
                (
                    "ساعات الترم التالي تُحسب من المعدل بعد كل ترم؛ لذلك قد يبدأ الطالب "
                    "بـ12 ساعة، ثم يصبح مسموحًا له 15 ساعة بمجرد ارتفاع المعدل فوق 1.00."
                )
            )

            final_record = auto_records[-1]
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Final Expected CGPA" if not IS_AR else "المعدل النهائي المتوقع", f'{final_record["new_cgpa"]:.3f}')
            f2.metric("Final Cumulative Grade" if not IS_AR else "التقدير التراكمي النهائي", gpa_grade_description(final_record["new_cgpa"], IS_AR))
            f3.metric("Final Passed Hours" if not IS_AR else "الساعات النهائية", f'{final_record["new_passed_hours"]:.0f}')
            f4.metric("Number of Terms" if not IS_AR else "عدد الترمات", len(auto_records))

            if final_record["new_passed_hours"] >= 160 and final_record["new_cgpa"] >= 2:
                st.success("The expected plan meets the graduation hours and CGPA requirements." if not IS_AR else "الخطة المتوقعة تحقق شرط الساعات والمعدل للتخرج.")
            elif not missing_auto_grades:
                st.warning(_report_status(final_record["new_cgpa"], final_record["new_passed_hours"], IS_AR))

        st.subheader(
            "Training Progress"
            if not IS_AR else
            "متابعة التدريب"
        )
        for message_type, message_text in _live_training_messages(
            best,
            draft,
            grade_values,
            IS_AR,
        ):
            if message_type == "success":
                st.success(message_text)
            elif message_type == "warning":
                st.warning(message_text)
            else:
                st.info(message_text)

        if failing_required:
            st.error(
                ("The automatic prerequisite chain assumes passing grades. Change F for: " if not IS_AR else "الخطة التلقائية تفترض النجاح حتى تفتح المواد التالية. غيّر تقدير F للمواد: ")
                + ", ".join(failing_required)
            )

        save_auto_disabled = (
            missing_auto_grades
            or bool(failing_required)
            or bool(validation_errors)
            or not auto_records
        )

        replace_saved = st.session_state.get("auto_plan_replace_saved", True)
        prospective_terms = (
            list(auto_records)
            if replace_saved
            else list(st.session_state.terms) + list(auto_records)
        )

        auto_report_header = dict(header)
        auto_report_header["corona_excluded_hours"] = corona_excluded_hours
        auto_report_header["gpa_hours"] = current_header.get("gpa_hours", base_gpa_hours)
        auto_report_header["training1_completed_before_plan"] = "MEC200" in passed_codes(best)
        auto_report_header["training2_completed_before_plan"] = "MEC300" in passed_codes(best)
        auto_report_header["training1_required_hours"] = int(training1_required_hours)
        auto_report_header["training2_required_hours"] = int(training2_required_hours)
        auto_training2_reason = _saved_training2_rule_diagnostic(
            auto_report_header,
            best,
            prospective_terms,
            IS_AR,
        )
        auto_report_header["training2_rule_valid"] = not bool(auto_training2_reason)
        auto_report_header["training2_rule_reason"] = auto_training2_reason

        auto_expected_grad_term = (
            prospective_terms[-1].get("term_name", "")
            if prospective_terms else ""
        )
        auto_advisor_name = advisor_name_global
        st.caption(
            (
                f"Academic Advisor in report: {auto_advisor_name or 'Not entered'}"
                if not IS_AR else
                f"المرشد الأكاديمي في التقرير: {auto_advisor_name or 'لم يتم إدخاله'}"
            )
        )

        auto_pdf_bytes = build_pdf_report(
            auto_report_header,
            prospective_terms,
            auto_advisor_name,
            auto_expected_grad_term,
            IS_AR,
            UNIVERSITY_LOGO_BYTES,
        )
        auto_excel_bytes = build_excel_report(
            auto_report_header,
            attempts,
            best,
            prospective_terms,
            None,
            IS_AR,
            auto_advisor_name,
            auto_expected_grad_term,
            UNIVERSITY_LOGO_BYTES,
        )
        auto_print_html = build_graduation_report_html(
            auto_report_header,
            prospective_terms,
            auto_advisor_name,
            auto_expected_grad_term,
            IS_AR,
            UNIVERSITY_LOGO_BYTES,
        )

        if st.session_state.get("auto_saved_notice"):
            st.success(st.session_state.pop("auto_saved_notice"))

        st.subheader(
            "Save, Download and Print"
            if not IS_AR else
            "الحفظ والتحميل والطباعة"
        )

        override_confirm = st.checkbox(
            (
                "Advisor override: allow saving and printing despite academic "
                "validation errors. Hour and course-count overloads are warnings only."
            )
            if not IS_AR else
            (
                "تجاوز بموافقة المرشد: السماح بالحفظ والطباعة رغم أخطاء المراجعة. "
                "زيادة الساعات أو عدد المواد تظهر كتحذير فقط."
            ),
            key="auto_advisor_override",
        )

        action1, action2, action3, action4 = st.columns(4)

        with action1:
            if st.button(
                "Save Plan"
                if not IS_AR else
                "حفظ الخطة",
                disabled=save_auto_disabled,
                type="primary",
                use_container_width=True,
                key="save_auto_plan",
            ):
                _save_automatic_records(auto_records, replace_saved)
                st.rerun()

        with action2:
            st.download_button(
                "Save & Download PDF"
                if not IS_AR else
                "حفظ وتحميل PDF",
                data=auto_pdf_bytes,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "pdf",
                    IS_AR,
                ),
                mime="application/pdf",
                disabled=save_auto_disabled,
                use_container_width=True,
                on_click=_save_automatic_records,
                args=(auto_records, replace_saved),
                key="save_download_auto_pdf",
            )

        with action3:
            st.download_button(
                "Save & Download Excel"
                if not IS_AR else
                "حفظ وتحميل Excel",
                data=auto_excel_bytes,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "xlsx",
                    IS_AR,
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=save_auto_disabled,
                use_container_width=True,
                on_click=_save_automatic_records,
                args=(auto_records, replace_saved),
                key="save_download_auto_excel",
            )

        with action4:
            override_disabled = (
                missing_auto_grades
                or not auto_records
                or not override_confirm
            )
            st.download_button(
                "Save & Print PDF Anyway"
                if not IS_AR else
                "حفظ وطباعة PDF بأي حال",
                data=auto_pdf_bytes,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "pdf",
                    IS_AR,
                    "Advisor Override" if not IS_AR else "تجاوز بموافقة المرشد",
                ),
                mime="application/pdf",
                disabled=override_disabled,
                use_container_width=True,
                on_click=_save_automatic_records,
                args=(auto_records, replace_saved),
                key="save_print_anyway_pdf",
            )

        if not save_auto_disabled or override_confirm:
            render_print_report_button(
                auto_print_html,
                "Print Current Plan"
                if not IS_AR else
                "طباعة الخطة الحالية مباشرة",
            )
    else:
        st.info("Choose the starting term and generate the automatic plan." if not IS_AR else "اختار ترم البداية واضغط إنشاء خطة التخرج تلقائيًا.")


apply_pending_term_edit()


with tab_recovery:
    st.header(
        "خطة رفع المعدل التراكمي إلى 2.00"
        if IS_AR else
        "CGPA Recovery Plan to 2.00"
    )
    st.caption(
        (
            "الخطة دي بتبني ترم ورا ترم وتتوقف أول ما المعدل المتوقع يوصل 2.00. "
            "الأولوية تكون لتحسين D، مواد الرسوب، والمواد الجديدة المهمة اللي تفتح "
            "مواد بعدها. وكمان تقدر تستخدم مادة مختلفة من List A أو List B "
            "بدل المادة القديمة، ويكون تقديرها متاح من A+."
        )
        if IS_AR else
        (
            "This plan stops as soon as the expected CGPA reaches the target. "
            "It can use failed courses, D improvements, new prerequisite-opening "
            "courses, and List A/B alternatives with the full scale from A+."
        )
    )

    current_recovery_cgpa = float(current_header.get("cgpa", 0) or 0)
    target_col1, target_col2, target_col3 = st.columns(3)

    with target_col1:
        recovery_target = st.number_input(
            "المعدل المستهدف"
            if IS_AR else
            "Target CGPA",
            min_value=2.0,
            max_value=4.0,
            value=2.0,
            step=0.05,
            key="recovery_target_cgpa",
        )

    with target_col2:
        recovery_start_term = st.selectbox(
            "بداية الخطة من ترم"
            if IS_AR else
            "Starting Term",
            ["Fall", "Spring", "Summer"],
            key="recovery_start_term",
        )

    with target_col3:
        recovery_start_year = st.number_input(
            "سنة بداية العام الأكاديمي"
            if IS_AR else
            "Academic Year Start",
            min_value=2020,
            max_value=2100,
            value=int(datetime.now().year),
            step=1,
            key="recovery_start_year",
        )

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric(
        "المعدل الحالي"
        if IS_AR else
        "Current CGPA",
        f"{current_recovery_cgpa:.3f}",
    )
    rc2.metric(
        "فرق المعدل"
        if IS_AR else
        "CGPA Gap",
        f"{max(0.0, recovery_target-current_recovery_cgpa):.3f}",
    )
    rc3.metric(
        "الساعات المسموحة حاليًا"
        if IS_AR else
        "Current Regular Load",
        regular_load_limit_for_cgpa(current_recovery_cgpa),
    )

    st.subheader(
        "طريقة بناء الخطة" if IS_AR else "Plan Method"
    )
    recovery_plan_method = st.radio(
        "اختر طريقة الخطة" if IS_AR else "Choose Plan Method",
        ["balanced", "fastest"],
        format_func=lambda value: (
            "خطة متوازنة مع استكمال التخرج"
            if value == "balanced" and IS_AR else
            "Balanced Plan with Graduation Completion"
            if value == "balanced" else
            "أسرع طريق للوصول إلى 2.00"
            if IS_AR else
            "Fastest Route to CGPA 2.00"
        ),
        horizontal=True,
        key="recovery_plan_method",
    )
    st.caption(
        (
            "الخطة المتوازنة تعطي أولوية لمواد الرسوب والمتطلبات والمواد التي تفتح مواد لاحقة. "
            "الخطة الأسرع تركز على أكبر تحسن متوقع في المعدل."
        ) if IS_AR else (
            "The balanced plan prioritizes failed requirements, prerequisites, and courses that unlock later courses. "
            "The fastest plan prioritizes the largest CGPA gain."
        )
    )

    st.subheader(
        "مصادر رفع المعدل"
        if IS_AR else
        "Recovery Sources"
    )

    source_col1, source_col2, source_col3 = st.columns(3)
    with source_col1:
        recovery_include_retakes = st.checkbox(
            "إدخال مواد الرسوب"
            if IS_AR else
            "Include Failed Retakes",
            value=True,
            key="recovery_include_retakes",
        )
        recovery_retake_grade = st.selectbox(
            "التقدير المتوقع في الإعادة"
            if IS_AR else
            "Expected Retake Grade",
            ["B+", "B", "B-", "C+", "C", "C-", "D+", "D"],
            index=0,
            key="recovery_retake_grade",
            help=(
                "البرنامج هيطبق تلقائيًا الحد B+ لأول رسوب، وC عند الرسوب مرتين أو أكثر."
                if IS_AR else
                "The B+/C retake cap is enforced automatically."
            ),
        )

    with source_col2:
        recovery_include_improvements = st.checkbox(
            "إدخال تحسين مواد D"
            if IS_AR else
            "Include D Improvements",
            value=True,
            key="recovery_include_improvements",
        )
        recovery_improvement_grade = st.selectbox(
            "التقدير المتوقع في التحسين"
            if IS_AR else
            "Expected Improvement Grade",
            ["B+", "B", "B-", "C+", "C", "C-", "D+"],
            index=0,
            key="recovery_improvement_grade",
        )

    with source_col3:
        recovery_include_new = st.checkbox(
            "السماح بمواد جديدة"
            if IS_AR else
            "Allow New Courses",
            value=True,
            key="recovery_include_new",
        )
        recovery_new_grade = st.selectbox(
            "التقدير المتوقع في المواد الجديدة"
            if IS_AR else
            "Expected New-Course Grade",
            ["A+", "A", "A-", "B+", "B", "B-", "C+", "C"],
            index=3,
            key="recovery_new_grade",
        )

    recovery_remaining_df = remaining_courses(
        best,
        st.session_state.planned_passed,
        st.session_state.planned_scheduled,
    )

    preferred_new_options = []
    preferred_new_labels = {}
    if not recovery_remaining_df.empty:
        for _, recovery_row in recovery_remaining_df.iterrows():
            code = str(recovery_row.get("code", ""))
            unlocks = str(recovery_row.get("unlocks_next", ""))
            label = (
                f"{code} — {recovery_row.get('name', '')} "
                f"({recovery_row.get('hours', 0)} hrs)"
            )
            if unlocks:
                label += (
                    f" — تفتح: {unlocks}"
                    if IS_AR else
                    f" — Unlocks: {unlocks}"
                )
            preferred_new_options.append(code)
            preferred_new_labels[code] = label

    recovery_preferred_new = st.multiselect(
        "مواد جديدة عايز تديها أولوية لأنها تفتح مواد بعدها"
        if IS_AR else
        "Prioritize New Courses That Unlock Later Courses",
        preferred_new_options,
        format_func=lambda code: preferred_new_labels.get(code, code),
        key="recovery_preferred_new_courses",
        disabled=not recovery_include_new,
    )

    render_course_dependency_panel(
        recovery_preferred_new,
        (
            "معاينة المواد الجديدة ومسار المواد التي ستفتحها"
            if IS_AR else
            "Preview New Courses and Their Unlock Chain"
        ),
        IS_AR,
        recovery_remaining_df,
        compact=False,
    )

    st.subheader(
        "بدائل List A وList B"
        if IS_AR else
        "List A and List B Alternatives"
    )

    recovery_allow_list_ab_alternatives = st.checkbox(
        "السماح ببدائل List A/B الاختيارية"
        if IS_AR else
        "Allow Optional List A/B Alternatives",
        value=False,
        key="recovery_allow_list_ab_alternatives",
        help=(
            "خليها مقفولة لو الطالب خلّص ساعات List A/B ومش عايز البرنامج يضيف مواد إنسانية تانية."
            if IS_AR else
            "Keep this off when the student already completed List A/B hours and no extra humanities alternatives are needed."
        ),
    )
    st.info(
        (
            "لو الطالب رسب أو عايز يبدل مادة من List A أو List B بمادة مختلفة "
            "من نفس القائمة، المادة الجديدة بتاخد تقدير من A+ ومش بتتطبق عليها "
            "حدود الإعادة B+ أو C+. ولو ساعات الخانة محسوبة قبل كده، يتحسب فرق النقاط فقط."
        )
        if IS_AR else
        (
            "A different course from the same List A/B uses the full grade scale "
            "from A+ and is not capped at B+/C+. If the slot hours are already "
            "in the GPA denominator, only the point difference is counted."
        )
    )

    list_alt_points_only = st.checkbox(
        "احتساب فرق النقاط فقط وعدم تكرار الساعات"
        if IS_AR else
        "Count Point Difference Only — Do Not Repeat Passed Hours",
        value=True,
        key="recovery_list_alt_points_only",
    )

    list_alt_configs = []
    alt_slots = [
        ("GENXXX-A", "List A"),
        ("GENXXX-B1", "List B — 1"),
        ("GENXXX-B2", "List B — 2"),
    ]
    current_grade_options = [
        "Not completed",
        "A+", "A", "A-", "B+", "B", "B-",
        "C+", "C", "C-", "D+", "D", "F",
    ]
    expected_alt_options = [
        "A+", "A", "A-", "B+", "B", "B-",
        "C+", "C", "C-", "D+", "D",
    ]

    for slot_code, slot_label in alt_slots:
        detected_grade = humanities_slot_grade(best, slot_code)
        if not detected_grade:
            detected_grade = _best_grade_for_exact_code(best, slot_code)
        default_current = (
            detected_grade
            if detected_grade in current_grade_options
            else "Not completed"
        )

        with st.expander(
            (
                f"بديل {slot_label}"
                if IS_AR else
                f"{slot_label} Alternative"
            ),
            expanded=False,
        ):
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                enabled = st.checkbox(
                    "استخدام مادة بديلة"
                    if IS_AR else
                    "Use Alternative Course",
                    value=False,
                    key=f"recovery_alt_enabled_{norm(slot_code)}",
                )
            with ac2:
                current_grade = st.selectbox(
                    "التقدير الحالي للمادة القديمة"
                    if IS_AR else
                    "Current Grade of Old Course",
                    current_grade_options,
                    index=current_grade_options.index(default_current),
                    key=f"recovery_alt_current_{norm(slot_code)}",
                    disabled=(not enabled or not recovery_allow_list_ab_alternatives),
                )
            with ac3:
                expected_grade = st.selectbox(
                    "التقدير المتوقع للمادة البديلة"
                    if IS_AR else
                    "Expected Alternative Grade",
                    expected_alt_options,
                    index=0,
                    key=f"recovery_alt_expected_{norm(slot_code)}",
                    disabled=(not enabled or not recovery_allow_list_ab_alternatives),
                )

            list_alt_configs.append({
                "enabled": (recovery_allow_list_ab_alternatives and enabled and current_grade != "Not completed"),
                "slot_code": slot_code,
                "current_grade": current_grade,
                "expected_grade": expected_grade,
            })

    max_recovery_terms = st.slider(
        "أقصى عدد ترمات في خطة رفع المعدل"
        if IS_AR else
        "Maximum Recovery Terms",
        min_value=1,
        max_value=15,
        value=8,
        key="recovery_max_terms",
    )

    if st.button(
        "إنشاء خطة الوصول إلى 2.00"
        if IS_AR else
        "Generate Recovery Plan",
        type="primary",
        use_container_width=True,
        key="generate_recovery_plan",
    ):
        excluded_retake_codes = set(student_replacement_choices.keys())

        generated_recovery, recovery_notes = generate_cgpa_recovery_plan(
            header=current_header,
            best=best,
            attempts=attempts,
            extra_passed=set(st.session_state.planned_passed),
            planned_scheduled=set(st.session_state.planned_scheduled),
            planned_failed=set(st.session_state.planned_failed),
            planned_improved_d=set(
                st.session_state.planned_improved_d
            ),
            start_term=recovery_start_term,
            academic_year_start=int(recovery_start_year),
            target_cgpa=float(recovery_target),
            include_retakes=bool(recovery_include_retakes),
            include_improvements=bool(
                recovery_include_improvements
            ),
            include_new_courses=bool(recovery_include_new),
            expected_retake_grade=recovery_retake_grade,
            expected_improvement_grade=recovery_improvement_grade,
            expected_new_grade=recovery_new_grade,
            preferred_new_codes=recovery_preferred_new,
            excluded_retake_codes=excluded_retake_codes,
            list_alternative_configs=list_alt_configs,
            list_alternative_points_only=bool(
                list_alt_points_only
            ),
            max_terms=int(max_recovery_terms),
        )

        candidate_pool = _build_recovery_candidates(
            best=best,
            attempts=attempts,
            extra_passed=set(st.session_state.planned_passed),
            planned_scheduled=set(st.session_state.planned_scheduled),
            planned_failed=set(st.session_state.planned_failed),
            planned_improved_d=set(st.session_state.planned_improved_d),
            include_retakes=bool(recovery_include_retakes),
            include_improvements=bool(recovery_include_improvements),
            include_new_courses=bool(recovery_include_new),
            expected_retake_grade=recovery_retake_grade,
            expected_improvement_grade=recovery_improvement_grade,
            expected_new_grade=recovery_new_grade,
            preferred_new_codes=recovery_preferred_new,
            excluded_retake_codes=excluded_retake_codes,
            list_alternative_configs=list_alt_configs,
            list_alternative_points_only=bool(list_alt_points_only),
        )
        recovery_draft, recovery_unscheduled = _recovery_build_editor(
            generated_recovery, candidate_pool
        )

        st.session_state["recovery_plan_records"] = generated_recovery
        st.session_state["recovery_plan_notes"] = recovery_notes
        st.session_state["recovery_plan_draft"] = recovery_draft
        st.session_state["recovery_unscheduled_courses"] = recovery_unscheduled
        st.session_state["recovery_base_header"] = dict(current_header)
        st.session_state["recovery_editor_revision"] = int(
            st.session_state.get("recovery_editor_revision", 0)
        ) + 1
        st.rerun()

    recovery_draft = st.session_state.get("recovery_plan_draft", [])
    recovery_unscheduled = st.session_state.get(
        "recovery_unscheduled_courses", []
    )
    recovery_base_header = st.session_state.get(
        "recovery_base_header", current_header
    )

    if recovery_draft:
        cleaned_recovery_draft = _clean_draft_from_already_passed_courses(
            recovery_draft,
            best,
        )
        if cleaned_recovery_draft != recovery_draft:
            st.session_state["recovery_plan_draft"] = cleaned_recovery_draft
            recovery_draft = cleaned_recovery_draft

        recovery_records, recovery_notes = calculate_recovery_editor_plan(
            recovery_base_header,
            recovery_draft,
            best,
            float(recovery_target),
        )
        st.session_state["recovery_plan_records"] = recovery_records
    else:
        recovery_records = st.session_state.get(
            "recovery_plan_records", []
        )
        recovery_notes = st.session_state.get(
            "recovery_plan_notes", []
        )

    for recovery_note in recovery_notes:
        if "Target reached" in recovery_note:
            st.success(
                recovery_note
                if not IS_AR else
                recovery_note.replace(
                    "Target reached:",
                    "تم الوصول للهدف:",
                )
            )
        else:
            st.warning(recovery_note)

    if recovery_records:
        st.subheader(
            "نتيجة خطة رفع المعدل"
            if IS_AR else
            "Recovery Plan Result"
        )

        recovery_summary = pd.DataFrame([
            {
                "الترم" if IS_AR else "Term":
                    record.get("term_name", ""),
                "الساعات" if IS_AR else "Hours":
                    record.get("term_registered_hours", 0),
                "SGPA":
                    round(record.get("term_sgpa", 0), 3),
                "تقدير الترم" if IS_AR else "Term Grade":
                    gpa_grade_description(
                        record.get("term_sgpa", 0),
                        IS_AR,
                    ),
                "CGPA بعد الترم" if IS_AR else "CGPA After":
                    round(record.get("new_cgpa", 0), 3),
                "التقدير التراكمي" if IS_AR else "Cumulative Grade":
                    gpa_grade_description(
                        record.get("new_cgpa", 0),
                        IS_AR,
                    ),
                "ساعات الترم التالي" if IS_AR else "Next Regular Load":
                    regular_load_limit_for_cgpa(
                        record.get("new_cgpa", 0)
                    ),
            }
            for record in recovery_records
        ])
        st.dataframe(
            recovery_summary,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(
            "تعديل مواد الترمات"
            if IS_AR else
            "Edit Recovery Terms"
        )
        st.info(
            (
                "من داخل كل ترم تقدر تضيف مادة، تنقل مادة لأي ترم تاني، "
                "أو تشيلها وترجعها لقائمة المواد غير المجدولة. "
                "الحساب بيتحدث تلقائيًا بعد كل تعديل."
            )
            if IS_AR else
            (
                "Inside each term, add an unscheduled course, move a course "
                "to any other term, or return it to the unscheduled pool. "
                "Calculations update after every edit."
            )
        )

        if recovery_unscheduled:
            with st.expander(
                (
                    f"المواد غير المجدولة ({len(recovery_unscheduled)})"
                    if IS_AR else
                    f"Unscheduled Courses ({len(recovery_unscheduled)})"
                ),
                expanded=False,
            ):
                st.dataframe(
                    pd.DataFrame([
                        {
                            "الكود" if IS_AR else "Code": item.get("code", ""),
                            "المادة" if IS_AR else "Course": item.get("name", ""),
                            "النوع" if IS_AR else "Type": item.get("type", ""),
                            "الساعات" if IS_AR else "Hours": item.get("hours", 0),
                            "التقدير" if IS_AR else "Grade": item.get("expected_grade", ""),
                            "تفتح" if IS_AR else "Unlocks": item.get("unlocks_next", ""),
                        }
                        for item in recovery_unscheduled
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )

        revision = int(
            st.session_state.get("recovery_editor_revision", 0)
        )
        recovery_draft_local = st.session_state.get(
            "recovery_plan_draft", []
        )

        for recovery_index, term in enumerate(
            recovery_draft_local, start=1
        ):
            term_index = recovery_index - 1
            matching = next(
                (
                    r for r in recovery_records
                    if r.get("term_name") == term.get("term_name")
                ),
                {},
            )
            hours = sum(
                int(i.get("hours", 0) or 0)
                for i in term.get("courses", [])
            )
            allowed = int(
                matching.get(
                    "allowed_hours",
                    12 if term.get("term_type") == "Summer"
                    else regular_load_limit_for_cgpa(
                        matching.get(
                            "cgpa_before_term",
                            current_recovery_cgpa,
                        )
                    ),
                )
            )

            with st.expander(
                (
                    f"الترم {recovery_index}: {term.get('term_name','')} "
                    f"— {hours}/{allowed} ساعة"
                )
                if IS_AR else
                (
                    f"Term {recovery_index}: {term.get('term_name','')} "
                    f"— {hours}/{allowed} hours"
                ),
                expanded=True,
            ):
                if term.get("courses"):
                    course_items = list(term.get("courses", []))
                    for card_start in range(0, len(course_items), 2):
                        card_columns = st.columns(2)
                        for offset, item in enumerate(course_items[card_start:card_start + 2]):
                            item_type = str(item.get("type", ""))
                            palette = {
                                "Retake Failed": ("#FFF0F0", "#D96C6C"),
                                "Improvement D": ("#FFF7D6", "#D5B447"),
                                "List A/B Alternative Improvement": ("#F4EEFF", "#9873C9"),
                            }.get(item_type, ("#EAF4FF", "#6EA9D8"))
                            with card_columns[offset]:
                                st.markdown(
                                    f"""
                                    <div style='background:{palette[0]};border:1px solid {palette[1]};border-radius:12px;padding:11px;min-height:145px'>
                                      <div style='font-weight:800'>{html_lib.escape(str(item.get('code','')))} — {html_lib.escape(str(item.get('name','')))}</div>
                                      <div style='font-size:12px;color:#475467;margin-top:6px;line-height:1.6'>
                                        {'النوع' if IS_AR else 'Type'}: <b>{html_lib.escape(str(item_type))}</b><br>
                                        {'الساعات' if IS_AR else 'Hours'}: <b>{item.get('hours',0)}</b><br>
                                        {'التقدير المتوقع' if IS_AR else 'Expected Grade'}: <b>{html_lib.escape(str(item.get('expected_grade','')))}</b><br>
                                        {'تفتح' if IS_AR else 'Unlocks'}: <b>{html_lib.escape(str(item.get('unlocks_next','') or '-'))}</b>
                                      </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                    grade_changed = False
                    grade_cols = st.columns(2)
                    for item_index, item in enumerate(term.get("courses", [])):
                        options = _recovery_grade_options(item)
                        current_grade = str(item.get("expected_grade", "Select"))
                        if current_grade not in options:
                            current_grade = (
                                cap_retake_grade(
                                    current_grade,
                                    item.get("attempts_count", 1),
                                )
                                if item.get("type") == "Retake Failed"
                                else "Select"
                            )
                        with grade_cols[item_index % 2]:
                            new_grade = st.selectbox(
                                _recovery_item_label(item, IS_AR),
                                options,
                                index=options.index(current_grade),
                                key=(
                                    f"rec_grade_{revision}_"
                                    f"term_{term_index}_"
                                    f"item_{item_index}_"
                                    f"{norm(item.get('code',''))}"
                                ),
                            )
                        if new_grade != item.get("expected_grade"):
                            item["expected_grade"] = new_grade
                            grade_changed = True

                    if grade_changed:
                        st.session_state[
                            "recovery_plan_draft"
                        ] = recovery_draft_local
                        st.rerun()

                add_col, move_col = st.columns(2)

                with add_col:
                    unscheduled_now = st.session_state.get(
                        "recovery_unscheduled_courses", []
                    )
                    unscheduled_codes = [
                        i.get("code", "") for i in unscheduled_now
                    ]
                    unscheduled_map = {
                        norm(i.get("code", "")): i
                        for i in unscheduled_now
                    }

                    add_code = st.selectbox(
                        "إضافة مادة لهذا الترم"
                        if IS_AR else
                        "Add a Course to This Term",
                        [""] + unscheduled_codes,
                        format_func=lambda code: (
                            "اختر المادة" if not code and IS_AR
                            else "Select course" if not code
                            else _recovery_item_label(
                                unscheduled_map.get(
                                    norm(code), {"code": code}
                                ),
                                IS_AR,
                            )
                        ),
                        key=f"rec_add_{revision}_{term_index}",
                    )
                    if st.button(
                        "إضافة المادة هنا"
                        if IS_AR else
                        "Add Course Here",
                        disabled=not bool(add_code),
                        use_container_width=True,
                        key=f"rec_add_btn_{revision}_{term_index}",
                    ):
                        if _recovery_move_course(
                            add_code, target_index=term_index
                        ):
                            st.rerun()

                with move_col:
                    current_codes = [
                        i.get("code", "") for i in term.get("courses", [])
                    ]
                    current_map = {
                        norm(i.get("code", "")): i
                        for i in term.get("courses", [])
                    }

                    move_code = st.selectbox(
                        "مادة للنقل أو الإزالة"
                        if IS_AR else
                        "Course to Move or Remove",
                        [""] + current_codes,
                        format_func=lambda code: (
                            "اختر المادة" if not code and IS_AR
                            else "Select course" if not code
                            else _recovery_item_label(
                                current_map.get(
                                    norm(code), {"code": code}
                                ),
                                IS_AR,
                            )
                        ),
                        key=f"rec_move_{revision}_{term_index}",
                    )
                    destinations = [
                        i for i in range(len(recovery_draft_local))
                        if i != term_index
                    ]
                    destination = st.selectbox(
                        "الترم الجديد"
                        if IS_AR else
                        "New Destination",
                        [-1] + destinations,
                        format_func=lambda i: (
                            "اختر الترم" if i == -1 and IS_AR
                            else "Select term" if i == -1
                            else recovery_draft_local[i].get(
                                "term_name", ""
                            )
                        ),
                        disabled=not bool(move_code),
                        key=f"rec_dest_{revision}_{term_index}",
                    )

                    move_btn, remove_btn = st.columns(2)
                    with move_btn:
                        if st.button(
                            "نقل للمختار"
                            if IS_AR else
                            "Move",
                            disabled=(
                                not bool(move_code)
                                or destination == -1
                            ),
                            use_container_width=True,
                            key=f"rec_move_btn_{revision}_{term_index}",
                        ):
                            if _recovery_move_course(
                                move_code,
                                target_index=destination,
                            ):
                                st.rerun()

                    with remove_btn:
                        if st.button(
                            "إزالة من الترم"
                            if IS_AR else
                            "Remove",
                            disabled=not bool(move_code),
                            use_container_width=True,
                            key=f"rec_remove_btn_{revision}_{term_index}",
                        ):
                            if _recovery_move_course(
                                move_code,
                                unschedule=True,
                            ):
                                st.rerun()

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("SGPA", f"{matching.get('term_sgpa',0):.3f}")
                m2.metric(
                    "تقدير الترم" if IS_AR else "Term Grade",
                    gpa_grade_description(
                        matching.get("term_sgpa", 0), IS_AR
                    ),
                )
                m3.metric(
                    "CGPA بعد الترم" if IS_AR else "CGPA After",
                    f"{matching.get('new_cgpa',0):.3f}",
                )
                m4.metric(
                    "الساعات المسموحة بعده"
                    if IS_AR else
                    "Next Regular Load",
                    regular_load_limit_for_cgpa(
                        matching.get(
                            "new_cgpa",
                            current_recovery_cgpa,
                        )
                    ),
                )

                if st.button(
                    "حذف الترم بالكامل"
                    if IS_AR else
                    "Delete This Term",
                    use_container_width=True,
                    key=f"rec_delete_{revision}_{term_index}",
                    help=(
                        "سيتم نقل مواد الترم إلى المواد غير المجدولة."
                        if IS_AR else
                        "The term courses will be moved back to unscheduled courses."
                    ),
                ):
                    if _recovery_delete_term(term_index):
                        st.rerun()

        if st.button(
            "+ إضافة ترم جديد"
            if IS_AR else
            "+ Add Another Term",
            use_container_width=True,
            key=f"rec_add_term_{revision}",
        ):
            _recovery_add_term()
            st.rerun()

        final_recovery = recovery_records[-1]
        if final_recovery.get("new_cgpa", 0) >= recovery_target:
            st.success(
                (
                    f"الخطة توصل الطالب إلى معدل "
                    f"{final_recovery.get('new_cgpa', 0):.3f} "
                    f"بعد {len(recovery_records)} ترم."
                )
                if IS_AR else
                (
                    f"The plan reaches CGPA "
                    f"{final_recovery.get('new_cgpa', 0):.3f} "
                    f"after {len(recovery_records)} term(s)."
                )
            )
        else:
            st.warning(
                (
                    f"الخطة الحالية توصل إلى "
                    f"{final_recovery.get('new_cgpa', 0):.3f} فقط. "
                    "زود مواد جديدة أو بدائل List A/B أو ارفع التقديرات المتوقعة."
                )
                if IS_AR else
                (
                    f"The current plan reaches only "
                    f"{final_recovery.get('new_cgpa', 0):.3f}. "
                    "Add new courses, List A/B alternatives, or higher expected grades."
                )
            )

        replace_main_plan = st.checkbox(
            "استبدال الخطة الرئيسية الحالية بخطة رفع المعدل"
            if IS_AR else
            "Replace the Current Main Plan with the Recovery Plan",
            value=not bool(st.session_state.terms),
            key="replace_main_with_recovery",
        )

        recovery_prospective_terms = (
            list(recovery_records)
            if replace_main_plan
            else list(st.session_state.terms) + list(recovery_records)
        )

        recovery_report_header = dict(header)
        recovery_report_header["gpa_hours"] = current_header.get(
            "gpa_hours",
            current_header.get("passed_hours", 0),
        )
        recovery_report_header["recovery_target_cgpa"] = recovery_target

        recovery_expected_term = recovery_records[-1].get(
            "term_name",
            "",
        )

        recovery_pdf = build_pdf_report(
            recovery_report_header,
            recovery_prospective_terms,
            advisor_name_global,
            recovery_expected_term,
            IS_AR,
            UNIVERSITY_LOGO_BYTES,
        )
        recovery_excel = build_excel_report(
            recovery_report_header,
            attempts,
            best,
            recovery_prospective_terms,
            None,
            IS_AR,
            advisor_name_global,
            recovery_expected_term,
            UNIVERSITY_LOGO_BYTES,
        )

        recovery_action1, recovery_action2, recovery_action3 = st.columns(3)

        with recovery_action1:
            if st.button(
                "اعتمادها كخطة رئيسية"
                if IS_AR else
                "Use as Main Plan",
                type="primary",
                use_container_width=True,
                key="save_recovery_as_main",
            ):
                if replace_main_plan:
                    st.session_state.terms = list(recovery_records)
                else:
                    st.session_state.terms.extend(
                        list(recovery_records)
                    )
                apply_rebuilt_state(st.session_state.terms)
                st.success(
                    "تم اعتماد خطة رفع المعدل."
                    if IS_AR else
                    "Recovery plan saved as the main plan."
                )
                st.rerun()

        with recovery_action2:
            st.download_button(
                "تحميل خطة رفع المعدل PDF"
                if IS_AR else
                "Download Recovery PDF",
                data=recovery_pdf,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "pdf",
                    IS_AR,
                    "خطة رفع المعدل إلى 2"
                    if IS_AR else
                    "CGPA Recovery to 2",
                ),
                mime="application/pdf",
                use_container_width=True,
                key="download_recovery_pdf",
            )

        with recovery_action3:
            st.download_button(
                "تحميل خطة رفع المعدل Excel"
                if IS_AR else
                "Download Recovery Excel",
                data=recovery_excel,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "xlsx",
                    IS_AR,
                    "خطة رفع المعدل إلى 2"
                    if IS_AR else
                    "CGPA Recovery to 2",
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="download_recovery_excel",
            )



with tab_plan:
    print_current_page("طباعة الصفحة" if IS_AR else "Print This Tab")
    if st.session_state.newly_unlocked:
        st.success("Newly Unlocked Courses" if not IS_AR else "مواد اتفتحت بعد الترم السابق")
        unlocked_rows = []
        for code in st.session_state.newly_unlocked:
            c = course_obj_by_code(code)
            unlocked_rows.append({
                "Code" if not IS_AR else "الكود": code,
                "Course Name" if not IS_AR else "اسم المادة": c.name if c else code,
                "Semester" if not IS_AR else "الترم": c.semester if c else "",
                "Hours" if not IS_AR else "الساعات": c.hours if c else "",
                "Unlocks Next" if not IS_AR else "تفتح بعد كده": unlocks_text(code),
            })
        st.dataframe(pd.DataFrame(unlocked_rows), use_container_width=True)

    edit_term_number = st.session_state.get("editing_term_number")
    if edit_term_number:
        st.warning(
            (
                f"Editing saved term {edit_term_number}. Saving will replace it. "
                "Later terms were removed because they depended on this term."
            )
            if not IS_AR else
            (
                f"أنت تعدل الترم المحفوظ رقم {edit_term_number}. عند الحفظ سيتم استبداله، "
                "وتم حذف الترمات التالية لأنها مبنية عليه."
            )
        )

    st.header(TXT["build_term"])
    term_name = st.selectbox(TXT["choose_term"], ["Fall", "Spring", "Summer"], key="plan_term")
    st.caption("Choose courses manually. This tool calculates only; registration is still done on the university system." if not IS_AR else "اختر المواد بنفسك. البرنامج يحسب فقط، والتسجيل يتم على سيستم الجامعة.")
    st.caption(
        "→ shows the direct course(s) unlocked after passing this course."
        if not IS_AR else
        "العلامة → توضح المواد التي تفتح مباشرة بعد النجاح في هذه المادة."
    )

    st.info(
        "Planning target: reach CGPA 2.00 for graduation, not the highest possible CGPA."
        if not IS_AR else
        "هدف الخطة: الوصول إلى CGPA 2.00 للتخرج فقط، وليس رفع المعدل لأعلى رقم ممكن."
    )

    all_available_remaining = rem_df[rem_df["status"] == "available"].copy()
    available_remaining = all_available_remaining.copy()

    if term_name in ["Fall", "Spring"]:
        available_remaining = available_remaining[available_remaining["semester"] == term_name]
    else:
        st.info(
            "Summer: manually choose the courses opened by the department."
            if not IS_AR else
            "Summer: اختار المواد المفتوحة صيفي يدويًا من المواد المتبقية المتاحة."
        )

    offterm_selected = []
    offterm_available = pd.DataFrame(columns=all_available_remaining.columns)

    if term_name in ["Fall", "Spring"]:
        opposite_term = "Spring" if term_name == "Fall" else "Fall"
        allow_offterm = st.checkbox(
            f"+ Add {opposite_term} Course as Graduation Exception"
            if not IS_AR else
            f"+ إضافة مادة من ترم {'الربيع' if opposite_term == 'Spring' else 'الخريف'} كاستثناء لطالب خريج",
            key="allow_offterm_exception",
            help=(
                "Use only when the department opens an off-term course for a graduating student."
                if not IS_AR else
                "يُستخدم فقط عندما يفتح القسم مادة من ترم آخر لطالب خريج."
            ),
        )

        if allow_offterm:
            st.warning(
                "Advisor confirmation required: the course must be officially opened as a graduation exception."
                if not IS_AR else
                "يتطلب تأكيد المرشد: يجب أن تكون المادة مفتوحة رسميًا كاستثناء لطالب خريج."
            )

            offterm_available = all_available_remaining[
                all_available_remaining["semester"] == opposite_term
            ].copy()

            previous_offterm = set(st.session_state.get("plan_offterm", []))
            offterm_options = offterm_available["code"].tolist() if not offterm_available.empty else []

            offterm_selected = st.multiselect(
                "+ Off-Term Graduation Exception"
                if not IS_AR else
                "+ مادة من ترم آخر لطالب خريج",
                offterm_options,
                default=[x for x in previous_offterm if x in offterm_options],
                key="plan_offterm",
                format_func=lambda x: course_label(x, offterm_available),
                help=(
                    "Only remaining courses with completed prerequisites are shown."
                    if not IS_AR else
                    "تظهر فقط المواد المتبقية التي اكتملت متطلباتها السابقة."
                ),
            )
        else:
            st.session_state["plan_offterm"] = []

    base_new_options = available_remaining["code"].tolist() if not available_remaining.empty else []
    base_retake_options = retake_all["code"].tolist() if not retake_all.empty else []
    base_d_options = d_all["code"].tolist() if not d_all.empty else []

    previous_new = set(st.session_state.get("plan_new", []))
    previous_retakes = set(st.session_state.get("plan_retakes", []))
    previous_improve = set(st.session_state.get("plan_improve", []))
    previous_offterm = set(st.session_state.get("plan_offterm", []))

    # A course selected in one box is hidden from the other two boxes.
    available_new_options = [
        x for x in base_new_options
        if x not in previous_retakes
        and x not in previous_improve
        and x not in previous_offterm
    ]
    retake_options = [
        x for x in base_retake_options
        if x not in previous_new
        and x not in previous_improve
        and x not in previous_offterm
    ]
    d_options = [
        x for x in base_d_options
        if x not in previous_new
        and x not in previous_retakes
        and x not in previous_offterm
    ]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        selected_new = st.multiselect(
            TXT["new_courses"],
            available_new_options,
            default=[x for x in previous_new if x in available_new_options],
            key="plan_new",
            format_func=lambda x: course_label(x, available_remaining),
            help="New/remaining courses. A selected course is hidden from the other boxes.",
        )
    with col_b:
        selected_retakes = st.multiselect(
            TXT["retake_courses"],
            retake_options,
            default=[x for x in previous_retakes if x in retake_options],
            key="plan_retakes",
            format_func=lambda x: course_label(x, retake_all),
            help="Failed courses only. A selected course is hidden from the other boxes.",
        )
    with col_c:
        selected_d_improve = st.multiselect(
            TXT["improve_courses"],
            d_options,
            default=[x for x in previous_improve if x in d_options],
            key="plan_improve",
            format_func=lambda x: course_label(x, d_all),
            help="D improvement only. A selected course is hidden from the other boxes.",
        )

    if previous_new or previous_retakes or previous_improve or previous_offterm:
        st.caption(
            "A selected course is automatically removed from the other selection lists."
            if not IS_AR else
            "أي مادة يتم اختيارها في خانة تختفي تلقائيًا من الخانتين الأخريين."
        )

    selected_visual_codes = list(dict.fromkeys(
        list(selected_new)
        + list(selected_retakes)
        + list(selected_d_improve)
        + list(offterm_selected)
    ))
    selected_visual_source = pd.concat(
        [
            available_remaining,
            retake_all,
            d_all,
            offterm_available,
        ],
        ignore_index=True,
        sort=False,
    )
    render_course_dependency_panel(
        selected_visual_codes,
        (
            "تفاصيل المواد المختارة والمواد التي تفتحها"
            if IS_AR else
            "Selected Course Details and Unlock Map"
        ),
        IS_AR,
        selected_visual_source,
        compact=False,
    )

    selected_retake_df = retake_all[retake_all["code"].isin(selected_retakes)].copy() if not retake_all.empty else pd.DataFrame()
    selected_d_df = d_all[d_all["code"].isin(selected_d_improve)].copy() if not d_all.empty else pd.DataFrame()

    st.subheader(TXT["expected_grades"])
    st.caption("Choose a realistic expected grade. Leave Select if you do not want to calculate yet." if not IS_AR else "اختار تقدير واقعي. سيبها Select لو لسه مش عايز تحسب.")

    expected = {}

    if selected_new:
        st.markdown("**" + TXT["new_courses"] + "**")
        for code in selected_new:
            c = course_obj_by_code(code)
            label = f"{code} — {c.name if c else ''}"
            replaced_failed_code = replacement_target_to_failed.get(norm(code))
            if replaced_failed_code:
                label += (
                    f" — بديل من نفس القائمة بدل {replaced_failed_code} — التقدير من A+"
                    if IS_AR else
                    f" — Same-list alternative replacing {replaced_failed_code} — full scale from A+"
                )
            expected[f"NEW::{code}"] = st.selectbox(
                label,
                GRADE_OPTIONS,
                key=f"new_{code}",
            )

    if offterm_selected:
        st.markdown(
            "**Off-Term Graduation Exception**"
            if not IS_AR else
            "**مواد من ترم آخر كاستثناء لطالب خريج**"
        )
        for code in offterm_selected:
            c = course_obj_by_code(code)
            label = (
                f"{code} — {c.name if c else ''} — Graduation Exception"
                if not IS_AR else
                f"{code} — {c.name if c else ''} — استثناء طالب خريج"
            )
            expected[f"OFF::{code}"] = st.selectbox(
                label,
                GRADE_OPTIONS,
                key=f"off_{code}",
            )

    if not selected_retake_df.empty:
        st.markdown("**" + TXT["retake_courses"] + "**")
        for _, r in selected_retake_df.iterrows():
            attempts_count = int(r.get("attempts_count", 1) or 1)
            max_grade = retake_max_allowed_grade(attempts_count)
            options = retake_grade_options(attempts_count)
            widget_key = f"ret_{r['code']}"

            old_value = st.session_state.get(widget_key, "Select")
            if old_value not in options:
                st.session_state[widget_key] = cap_retake_grade(
                    old_value,
                    attempts_count,
                )

            label = (
                f"{r['code']} — {r['name']} — "
                f"مرات الرسوب: {attempts_count} — أقصى تقدير: {max_grade}"
                if IS_AR else
                f"{r['code']} — {r['name']} — "
                f"Failed attempts: {attempts_count} — Maximum grade: {max_grade}"
            )
            expected[f"RET::{r['code']}"] = st.selectbox(
                label,
                options,
                key=widget_key,
            )

    if not selected_d_df.empty:
        st.markdown("**" + TXT["improve_courses"] + "**")
        for _, r in selected_d_df.iterrows():
            label = f"{r['code']} — current D — {r['name']}"
            expected[f"IMP::{r['code']}"] = st.selectbox(label, GRADE_OPTIONS, key=f"imp_{r['code']}")

    # =========================================================
    # Step 4 - Calculate
    # =========================================================

    st.header(TXT["calculate"])

    missing_grade = any(v == "Select" for v in expected.values()) if expected else False
    if missing_grade:
        st.warning("في مواد مختارة بدون Expected Grade. الحساب هيعتبرها 0 لو حسبت الآن، فالأفضل تختار التقديرات الأول.")

    result = compute_one_term(
        current_header,
        selected_new,
        selected_retake_df,
        selected_d_df,
        expected,
        offterm_selected,
    )

    if not result["plan_df"].empty:
        for target_norm, failed_code in replacement_target_to_failed.items():
            code_mask = result["plan_df"]["course"].astype(str).apply(norm).eq(
                target_norm
            )
            target_code = next(
                (
                    code for code in HUMANITIES_REPLACEMENT_OPTIONS
                    if norm(code) == target_norm
                ),
                target_norm,
            )
            result["plan_df"].loc[code_mask, "name"] = (
                list_replacement_course_name(
                    target_code,
                    failed_code,
                    IS_AR,
                )
            )
            result["plan_df"].loc[code_mask, "effect"] = (
                "مادة بديلة من نفس List A/B — التقدير متاح من A+"
                if IS_AR else
                "Alternative course from the same List A/B — full grade scale from A+"
            )
            result["plan_df"].loc[code_mask, "replacement_for"] = failed_code

        st.dataframe(result["plan_df"], use_container_width=True)
    else:
        st.info("لم يتم اختيار مواد في هذا الترم بعد.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Term Registered Hours" if not IS_AR else "ساعات الترم المسجلة", f'{result["term_registered_hours"]:.0f}')
    m2.metric("Expected Term SGPA" if not IS_AR else "معدل الترم المتوقع SGPA", f'{result["term_sgpa"]:.3f}')
    m3.metric("Passed Hours After This Term" if not IS_AR else "الساعات المجتازة بعد الترم", f'{result["new_passed_hours"]:.0f}')
    m4.metric(
        "CGPA After This Term" if not IS_AR else "المعدل التراكمي بعد الترم CGPA",
        f'{result["new_cgpa"]:.3f}',
        delta=f'{result["new_cgpa"] - current_header.get("cgpa", 0):+.3f}'
    )

    grade_m1, grade_m2, grade_m3 = st.columns(3)
    grade_m1.metric(
        "Expected Term Grade" if not IS_AR else "تقدير الترم المتوقع",
        gpa_grade_description(result["term_sgpa"], IS_AR),
    )
    grade_m2.metric(
        "Cumulative Grade After Term" if not IS_AR else "التقدير التراكمي بعد الترم",
        gpa_grade_description(result["new_cgpa"], IS_AR),
    )
    grade_m3.metric(
        "Next Regular-Term Load"
        if not IS_AR else
        "الساعات المسموحة في الترم العادي التالي",
        regular_load_limit_for_cgpa(result["new_cgpa"]),
        delta=f'CGPA {result["new_cgpa"]:.3f}',
    )

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Current CGPA Before Term" if not IS_AR else "المعدل قبل الترم", f'{current_header.get("cgpa", 0):.3f}')
    m6.metric("Added Course Points" if not IS_AR else "نقاط المواد المضافة", f'{result["added_points"]:.1f}')
    m7.metric("Improvement Gain" if not IS_AR else "فرق نقاط التحسين", f'{result["improvement_gain"]:.1f}')
    m8.metric("Total Points After Term" if not IS_AR else "إجمالي النقاط بعد الترم", f'{result["new_total_points"]:.1f}')

    overall_status = cumulative_status(result["new_cgpa"], result["new_passed_hours"])
    if IS_AR:
        if result["new_passed_hours"] >= 160 and result["new_cgpa"] >= 2:
            overall_status = "مستوفي شرط الساعات والمعدل للتخرج"
        elif result["new_cgpa"] >= 2:
            overall_status = "وصل لمعدل 2.00؛ راجع المتطلبات والساعات المتبقية"
        else:
            overall_status = f'أقل من معدل التخرج 2.00 بمقدار {max(0.0, 2.0 - result["new_cgpa"]):.3f}'

    st.subheader("Overall Result After This Term" if not IS_AR else "النتيجة الكلية بعد هذا الترم")
    st.info(
        f'Expected cumulative GPA after completing the selected courses: {result["new_cgpa"]:.3f}. {overall_status}.'
        if not IS_AR else
        f'المعدل التراكمي المتوقع بعد إنهاء المواد المختارة: {result["new_cgpa"]:.3f}. {overall_status}.'
    )

    if result["new_passed_hours"] >= 160 and result["new_cgpa"] >= 2:
        st.success("الخطة المتوقعة تحقق شرط التخرج مبدئيًا: 160 ساعة و CGPA ≥ 2.00.")
    elif result["new_cgpa"] >= 2:
        st.info("المعدل وصل 2.00 أو أكثر، لكن راجع الساعات والمتطلبات المتبقية.")
    else:
        st.warning("لسه الطالب أقل من 2.00 أو محتاج ساعات/مواد إضافية. أضف ترم جديد وكرر.")

    save_disabled = result["plan_df"].empty or missing_grade
    next_semester_preview = "Fall" if term_name == "Summer" else ("Spring" if term_name == "Fall" else "Fall")
    available_before_save = available_course_codes_for_term(
        best,
        st.session_state.planned_passed,
        st.session_state.planned_scheduled,
        next_semester_preview,
    )

    if st.button(
        "Save This Term and Continue" if not IS_AR else "حفظ الترم والانتقال للترم التالي",
        disabled=save_disabled,
        use_container_width=True
    ):
        term_record = {
            "term_name": term_name,
            "term_type": term_name,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "plan_df": result["plan_df"],
            "term_registered_hours": result["term_registered_hours"],
            "term_sgpa": result["term_sgpa"],
            "new_passed_hours": result["new_passed_hours"],
            "new_gpa_hours": result["new_gpa_hours"],
            "new_total_points": result["new_total_points"],
            "new_cgpa": result["new_cgpa"],
            "term_grade": gpa_grade_description(result["term_sgpa"], False),
            "cumulative_grade": gpa_grade_description(result["new_cgpa"], False),
        }
        st.session_state.terms.append(term_record)
        st.session_state["editing_term_number"] = None

        # Update academic state for the next term.
        for _, row in result["plan_df"].iterrows():
            expected_grade = str(row.get("expected_grade", ""))
            course_code = str(row.get("course", ""))
            course_type = str(row.get("type", ""))

            # Once assigned to a saved term, remove it from its original selection list.
            st.session_state.planned_scheduled.add(course_code)

            if expected_grade in PASSING:
                st.session_state.planned_failed.discard(course_code)

                if course_type in ["New / Remaining", "Withdrawn / New", "Off-Term Graduation Exception", "Retake Failed"]:
                    st.session_state.planned_passed.add(course_code)
                elif course_type == "Improvement D" and point_of_grade(expected_grade) > point_of_grade("D"):
                    st.session_state.planned_improved_d.add(course_code)
            else:
                # Expected F appears only in the next term's Retake list.
                st.session_state.planned_failed.add(course_code)

        # Clear current selections so the next term starts clean.
        for key in ["plan_new", "plan_retakes", "plan_improve", "plan_offterm"]:
            st.session_state.pop(key, None)

        available_after_save = available_course_codes_for_term(
            best,
            st.session_state.planned_passed,
            st.session_state.planned_scheduled,
            next_semester_preview,
        )
        st.session_state.newly_unlocked = sorted(list(available_after_save - available_before_save))

        st.success(
            "Term saved. Course lists were updated for the next term."
            if not IS_AR else
            "تم حفظ الترم وتحديث قوائم المواد للترم التالي."
        )
        st.rerun()

# =========================================================
# Saved terms
# =========================================================

with tab_plan:
    st.header("Saved Term Plan" if not IS_AR else "الخطة المحفوظة")

    if not st.session_state.terms:
        st.info("No saved terms yet." if not IS_AR else "لا توجد ترمات محفوظة بعد.")
    else:
        summary_rows = []
        for i, term in enumerate(st.session_state.terms, start=1):
            summary_rows.append({
                "No.": i,
                "Term": term["term_name"],
                "Saved Date": term.get("saved_date", ""),
                "Term Hours": term["term_registered_hours"],
                "SGPA": round(term["term_sgpa"], 3),
                "Term Grade": gpa_grade_description(term["term_sgpa"], IS_AR),
                "Passed Hours After": round(term["new_passed_hours"], 0),
                "Total Points After": round(term["new_total_points"], 1),
                "CGPA After": round(term["new_cgpa"], 3),
                "Cumulative Grade": gpa_grade_description(term["new_cgpa"], IS_AR),
                "Next Regular Load": regular_load_limit_for_cgpa(term["new_cgpa"]),
            })

            with st.expander(f"Term {i}: {term['term_name']}"):
                st.dataframe(term["plan_df"], use_container_width=True)

                edit_col, delete_col = st.columns(2)

                with edit_col:
                    if st.button(
                        "Edit This Term" if not IS_AR else "تعديل هذا الترم",
                        key=f"edit_term_{i}",
                        use_container_width=True,
                    ):
                        load_term_for_edit(term, i - 1)
                        st.rerun()

                with delete_col:
                    if st.button(
                        "Delete This Term" if not IS_AR else "حذف هذا الترم",
                        key=f"delete_term_{i}",
                        use_container_width=True,
                    ):
                        # Delete this term and all following terms because later CGPA values depend on it.
                        st.session_state.terms = st.session_state.terms[:i - 1]
                        apply_rebuilt_state(st.session_state.terms)
                        st.session_state.newly_unlocked = []
                        st.session_state["editing_term_number"] = None

                        for key in ["plan_new", "plan_retakes", "plan_improve", "plan_offterm"]:
                            st.session_state.pop(key, None)

                        st.warning(
                            "The selected term and all later dependent terms were deleted."
                            if not IS_AR else
                            "تم حذف الترم المحدد وكل الترمات التالية لأنها مبنية عليه."
                        )
                        st.rerun()

        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(summary_df, use_container_width=True)

with tab_report:
    st.header("Graduation Plan Report" if not IS_AR else "تقرير خطة التخرج")
    st.caption(
        "Review the complete plan, then download a formal PDF or Excel report."
        if not IS_AR else
        "راجع الخطة كاملة ثم حمّل تقرير رسمي PDF أو Excel."
    )

    if not st.session_state.terms:
        st.info("Save at least one term before generating the report." if not IS_AR else "احفظ ترم واحد على الأقل قبل إنشاء التقرير.")
    else:
        r1, r2 = st.columns(2)
        with r1:
            advisor_name = advisor_name_global
            st.text_input(
                "Academic Advisor Name" if not IS_AR else "اسم المرشد الأكاديمي",
                value=advisor_name,
                disabled=True,
                key="report_advisor_display",
                help=(
                    "Change and save the advisor name from Report Identity in the sidebar."
                    if not IS_AR else
                    "غيّر اسم المرشد واحفظه من بيانات التقرير في القائمة الجانبية."
                ),
            )
        with r2:
            expected_grad_term = st.text_input(
                "Expected Graduation Term"
                if not IS_AR else
                "الترم المتوقع للتخرج",
                key="report_grad_term",
            )
        st.info(
            (
                "Delta University branding and logo are included automatically in every report."
                if not IS_AR else
                "اسم جامعة الدلتا وشعارها مضافان تلقائيًا في كل تقرير."
            )
        )
        logo_file = st.file_uploader(
            "Optional replacement logo"
            if not IS_AR else
            "شعار بديل اختياري",
            type=["png", "jpg", "jpeg"],
            key="report_logo",
        )
        logo_bytes = (
            logo_file.getvalue()
            if logo_file else
            UNIVERSITY_LOGO_BYTES
        )

        report_header = dict(header)
        report_header["corona_excluded_hours"] = corona_excluded_hours
        report_header["gpa_hours"] = current_header.get("gpa_hours", base_gpa_hours)
        report_header["training1_completed_before_plan"] = "MEC200" in passed_codes(best)
        report_header["training2_completed_before_plan"] = "MEC300" in passed_codes(best)
        report_header["training1_required_hours"] = int(training1_required_hours)
        report_header["training2_required_hours"] = int(training2_required_hours)
        report_training2_reason = _saved_training2_rule_diagnostic(
            report_header,
            best,
            st.session_state.terms,
            IS_AR,
        )
        report_header["training2_rule_valid"] = not bool(report_training2_reason)
        report_header["training2_rule_reason"] = report_training2_reason
        report_html = build_graduation_report_html(
            report_header,
            st.session_state.terms,
            advisor_name,
            expected_grad_term,
            IS_AR,
            logo_bytes,
        )

        st.subheader("Report Preview" if not IS_AR else "معاينة التقرير")
        components.html(report_html, height=950, scrolling=True)

        d1, d2, d3 = st.columns(3)
        with d1:
            try:
                pdf_bytes = build_pdf_report(
                    report_header,
                    st.session_state.terms,
                    advisor_name,
                    expected_grad_term,
                    IS_AR,
                    logo_bytes,
                )
                st.download_button(
                    "Download PDF Report" if not IS_AR else "تحميل تقرير PDF",
                    data=pdf_bytes,
                    file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "pdf",
                    IS_AR,
                ),
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as pdf_error:
                st.error(("PDF generation failed: " if not IS_AR else "تعذر إنشاء PDF: ") + str(pdf_error))
        with d2:
            excel_bytes = build_excel_report(
                report_header,
                attempts,
                best,
                st.session_state.terms,
                None,
                IS_AR,
                advisor_name,
                expected_grad_term,
                logo_bytes,
            )
            st.download_button(
                "Download Excel Report" if not IS_AR else "تحميل تقرير Excel",
                data=excel_bytes,
                file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "xlsx",
                    IS_AR,
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with d3:
            render_print_report_button(
                report_html,
                "Print Report Now"
                if not IS_AR else
                "طباعة التقرير الآن",
            )

        st.download_button(
            "Download Print-ready HTML" if not IS_AR else "تحميل نسخة HTML للطباعة",
            data=report_html.encode("utf-8"),
            file_name=safe_student_report_filename(
                    header.get("student_name", ""),
                    header.get("student_id", ""),
                    "html",
                    IS_AR,
                ),
            mime="text/html",
            use_container_width=True,
        )


st.divider()
st.markdown(
    f"<div style='text-align:center;color:#667085;font-size:12px'>"
    f"<b style='color:#0B5FA5'>{UNIVERSITY_NAME}</b>"
    f" &nbsp;•&nbsp; "
    f"<b style='color:#F28C00'>{PROGRAM_BRAND}</b>"
    f"</div>",
    unsafe_allow_html=True,
)


st.markdown(
    f"""
    <div style="
        margin-top:28px;
        padding:10px 14px;
        border-top:1px solid #D7E0EA;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        color:#64748B;
        font-size:12px;
    ">
        <span>Graduation Planner</span>
        <span>Designed &amp; Developed by
            <strong style="color:#1F4E78">{APP_DEVELOPER}</strong>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
