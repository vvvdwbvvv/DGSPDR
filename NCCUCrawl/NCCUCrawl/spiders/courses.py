import json
import scrapy
from NCCUCrawl.items import CourseItem


class CoursesSpider(scrapy.Spider):
    name = "courses"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.1,
    }

    def start_requests(self):
        # 先抓 unit.json
        yield scrapy.Request(
            url="https://qrysub.nccu.edu.tw/assets/api/unit.json",
            callback=self.parse_units,
        )

    def parse_units(self, response):
        units = json.loads(response.text)
        categories = [
            (l1["utCodL1"], l2["utCodL2"], l3["utCodL3"])
            for l1 in units
            if l1["utCodL1"] != "0"
            for l2 in l1["utL2"]
            if l2["utCodL2"] != "0"
            for l3 in l2["utL3"]
            if l3["utCodL3"] != "0"
        ]

        semesters = ["1141"]

        for sem in semesters:
            for dp1, dp2, dp3 in categories:
                url = (
                    "https://es.nccu.edu.tw/course/zh-TW/"
                    f":sem={sem}%20:dp1={dp1}%20:dp2={dp2}%20:dp3={dp3}"  # ex: https://es.nccu.edu.tw/course/zh-TW/:sem=1131%20:dp1=01%20:dp2=A1%20:dp3=105%20/
                )
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_course_list,
                    cb_kwargs={"semester": sem},
                )

    def parse_course_list(self, response, semester):
        courses = json.loads(response.text)
        for c in courses:
            item = CourseItem(
                id=f"{semester}{c['subNum']}",
                year=semester[:3],
                semester=semester[3],
                sub_num=c["subNum"],
                name=c["subNam"],
                name_en=c.get("subNamEn", ""),
                teacher_id="",  # Will need separate processing for teaNam
                kind=c.get("subKind", ""),
                time=c.get("subTime", ""),
                lang=c.get("langTpe", ""),
                lang_en=c.get("langTpeEn", ""),
                sem_qty=c.get("smtQty", ""),
                sem_qty_en=c.get("smtQtyEn", ""),
                classroom_id=c.get("subClassroom", ""),
                unit=c.get("subGde", ""),  # subGde appears to be the department/unit
                unit_en=c.get("subGdeEn", ""),
                college=c.get("college", ""),
                degree=c.get("gdeType", ""),
                department=c.get("subGde", ""),
                credit=float(c.get("subPoint", 0)) if c.get("subPoint") else None,
                transition_type=c.get("tranTpe", ""),
                transition_type_en=c.get("tranTpeEn", ""),
                info=c.get("info", ""),
                info_en=c.get("infoEn", ""),
                note=c.get("note", ""),
                note_en=c.get("noteEn", ""),
                syllabus="",  # Not available in this API
                syllabus_en="",
                objective="",  # Not available in this API
                objective_en="",
                core=c.get("core", "") == "是",  # Convert "是"/"否" to boolean
                discipline=c.get("subGde", ""),
                last_enroll=None,  # Not available in this API
                student_limit=None,  # Not available in this API
                student_count=None,  # Not available in this API
            )
            yield item
