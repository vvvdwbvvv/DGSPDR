import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        # Environment variables
        self.YEAR = os.getenv("YEAR", "")
        self.SEM = os.getenv("SEM", "")
        self.USERNAME = os.getenv("USERNAME", "")
        self.PASSWORD = os.getenv("PASSWORD", "")

        # Server configuration
        self.SERVER_URL = "http://es.nccu.edu.tw/"
        self.KEY = "angu1arjjlST@2019"

        # API endpoints
        self.SEM_API = f"{self.SERVER_URL}semester/"
        self.PERSON_API = f"{self.SERVER_URL}person/"
        self.COURSE_API = f"{self.SERVER_URL}course/"
        self.TRACE_API = f"{self.SERVER_URL}tracing/"

        # Combined year-semester
        self.YEAR_SEM = f"{self.YEAR}{self.SEM}"

        # Course result semesters
        self.COURSERESULT_YEARSEM = ["1102", "1111", "1112", "1121"]

    def teacher_url(self, teacher_id: str, year_sem: str = None) -> str:
        year_sem = year_sem or self.YEAR_SEM
        return f"http://newdoc.nccu.edu.tw/teaschm/{year_sem}/statistic.jsp-tnum={teacher_id}.htm"

    def course_rate_url(self, param: str, year_sem: str = None) -> str:
        year_sem = year_sem or self.YEAR_SEM
        return f"http://newdoc.nccu.edu.tw/teaschm/{year_sem}/{param}"

    def get_rate_qry(self) -> List[str]:
        rate_qry_env = os.getenv("RATE_QRY", "")
        return rate_qry_env.split(",") if rate_qry_env else []

    def courseresult_csv(self, sem: str) -> str:
        return f"{sem}CourseResult.csv"


config = Config()
