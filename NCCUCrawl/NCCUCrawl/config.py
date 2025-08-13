import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
YEAR = os.getenv("YEAR") or ""
SEM = os.getenv("SEM") or ""
USERNAME = os.getenv("USERNAME") or ""
PASSWORD = os.getenv("PASSWORD") or ""

# Server configuration
SERVER_URL = "http://es.nccu.edu.tw/"

# API endpoints
SEM_API = SERVER_URL + "semester/"
PERSON_API = SERVER_URL + "person/"
COURSE_API = SERVER_URL + "course/"
TRACE_API = SERVER_URL + "tracing/"

# Combined year-semester
YEAR_SEM = YEAR + SEM

# Course result semesters
COURSERESULT_YEARSEM = ["1102", "1111", "1112", "1121"]


def teacher_url(teacher_id: str, year_sem: str = YEAR_SEM) -> str:
    """Generate teacher statistics URL"""
    return f"http://newdoc.nccu.edu.tw/teaschm/{year_sem}/statistic.jsp-tnum={teacher_id}.htm"


def course_rate_url(param: str, year_sem: str = YEAR_SEM) -> str:
    """Generate course rate URL"""
    return f"http://newdoc.nccu.edu.tw/teaschm/{year_sem}/{param}"


def rate_qry() -> list:
    """Get rate query parameters from environment"""
    rate_qry_env = os.getenv("RATE_QRY", "")
    return rate_qry_env.split(",") if rate_qry_env else []


def courseresult_csv(sem: str) -> str:
    """Generate course result CSV filename"""
    return f"{sem}CourseResult.csv"