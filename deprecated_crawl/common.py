import toml
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("USERNAME") or ""
PASSWORD = os.getenv("PASSWORD") or ""

def load_config(filepath: str = "config.toml") -> dict:
    """讀取 TOML 配置文件。

    Args:
        filepath (str): 配置文件的路徑。

    Returns:
        dict: 配置數據。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Configuration file {filepath} not found.")

    with open(filepath, 'r', encoding='utf-8') as file:
        return toml.load(file)


CONFIG = load_config("config.toml")

GENERAL = CONFIG.get("general", {})
URLS = CONFIG.get("urls", {})
RATE_QUERY = CONFIG.get("rate_query", "").split(",")
COURSERESULT_YEARSEM = CONFIG.get("course_results", {}).get("years", [])

YEAR = GENERAL.get("year", "")
SEM = GENERAL.get("sem", "")
YEAR_SEM = f"{YEAR}{SEM}"
COURSERESULT_YEARSEM = ["1102", "1111", "1112", "1121"]
KEY = "angu1arjjlST@2019"
All_SEMESTERS =[
    "1011", "1012", "1021", "1022", "1031", "1032", "1041", "1042",
    "1051", "1052", "1061", "1062", "1071", "1072", "1081", "1082",
    "1091", "1092", "1101", "1102", "1111", "1112", "1121", "1122", "1131"
]

SERVER_URL = URLS.get("server_url", "http://es.nccu.edu.tw/")
SEM_API = f"{SERVER_URL}{URLS.get('sem_api', '')}"
PERSON_API = f"{SERVER_URL}{URLS.get('person_api', '')}"
COURSE_API = f"{SERVER_URL}{URLS.get('course_api', '')}"
TRACE_API = f"{SERVER_URL}{URLS.get('trace_api', '')}"
TEACHER_SCHM_BASE_URL = URLS.get("teacher_schm_base_url", "http://newdoc.nccu.edu.tw/teaschm/")


def generate_teacher_stat_url(teacher_id: str, year_sem: str = YEAR_SEM) -> str:
    """生成教師統計頁面的 URL。

    Args:
        teacher_id (str): 教師 ID。
        year_sem (str, optional): 學年度學期標識，預設使用配置中的 YEAR + SEM。

    Returns:
        str: 統計頁面 URL。
    """
    return f"{TEACHER_SCHM_BASE_URL}{year_sem}/statistic.jsp-tnum={teacher_id}.htm"


def generate_course_rate_url(param: str, year_sem: str = YEAR_SEM) -> str:
    """生成課程評分頁面的 URL。

    Args:
        param (str): 特定參數。
        year_sem (str, optional): 學年度學期標識，預設使用配置中的 YEAR + SEM。

    Returns:
        str: 課程評分頁面 URL。
    """
    return f"{TEACHER_SCHM_BASE_URL}{year_sem}/{param}"

def courseresult_csv(sem: str) -> str:
    """生成課程結果的 CSV 文件名。

    Args:
        sem (str): 學期標識。

    Returns:
        str: 對應的 CSV 文件名。
    """
    return f"{sem}CourseResult.csv"