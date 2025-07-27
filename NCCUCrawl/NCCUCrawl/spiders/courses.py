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
        """Parse the unit.json to create a mapping of unit codes"""
        units = json.loads(response.text)

        self.unit_mapping = {}  # create mapping from unit codes to unit information
        for l1 in units:
            if l1["utCodL1"] != "0":
                for l2 in l1["utL2"]:
                    if l2["utCodL2"] != "0":
                        for l3 in l2["utL3"]:
                            if l3["utCodL3"] != "0":
                                key = f"{l1['utCodL1']}-{l2['utCodL2']}-{l3['utCodL3']}"
                                self.unit_mapping[key] = {
                                    "college": l1["utL1Text"].split(" / ")[0]
                                    if " / " in l1["utL1Text"]
                                    else l1["utL1Text"],
                                    "college_en": l1["utL1Text"].split(" / ")[1]
                                    if " / " in l1["utL1Text"]
                                    else "",
                                    "unit": l3["utL3Text"].split(" / ")[0]
                                    if " / " in l3["utL3Text"]
                                    else l3["utL3Text"],
                                    "unit_en": l3["utL3Text"].split(" / ")[1]
                                    if " / " in l3["utL3Text"]
                                    else "",
                                    "department": l3["utL3Text"].split(" / ")[0]
                                    if " / " in l3["utL3Text"]
                                    else l3["utL3Text"],
                                    "department_en": l3["utL3Text"].split(" / ")[1]
                                    if " / " in l3["utL3Text"]
                                    else "",
                                }

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
                    cb_kwargs={"semester": sem, "dp1": dp1, "dp2": dp2, "dp3": dp3},
                )

    def parse_course_list(self, response, semester, dp1, dp2, dp3):
        courses = json.loads(response.text)
        unit_key = f"{dp1}-{dp2}-{dp3}"
        unit_info = self.unit_mapping.get(unit_key, {})
        for c in courses:
            item = CourseItem(
                id=f"{semester}{c['subNum']}",
                year=semester[:3],
                semester=semester[3],
                sub_num=c["subNum"],
                name=c["subNam"],
                name_en=c.get("subNamEn", ""),  # collect in syllabus page
                teacher_id="",  # FK → teacher.id not available in this API
                kind=c.get("subKind", ""),
                time=c.get("subTime", ""),
                lang=c.get("langTpe", ""),
                lang_en=c.get("langTpeEn", ""),
                sem_qty=c.get("smtQty", ""),
                sem_qty_en=c.get("smtQtyEn", ""),
                classroom_id=c.get("subClassroom", ""),
                unit=c.get("subGde", ""),  # subGde appears to be the department/unit
                unit_en=unit_info.get("unit_en", ""),  # on unit.jsons
                college=unit_info.get("college", ""),
                degree=c.get("gdeType", ""),  # on unit.json
                department=unit_info.get("department", ""),  # on unit.json
                credit=float(c.get("subPoint", 0)) if c.get("subPoint") else None,
                transition_type=c.get("tranTpe", ""),
                transition_type_en="",
                info=c.get("info", ""),
                info_en=c.get("infoEn", ""),
                note=c.get("note", ""),
                note_en=c.get("noteEn", ""),
                syllabus=c.get("teaSchmUrl", ""),
                syllabus_en="",
                objective="",  # collect in syllabus page
                objective_en="",
                core=c.get("core", "") == "是",  # Convert "y"/"n" to boolean
                discipline=c.get("lmtKind", ""),
                last_enroll=None,  # Not available in this API
                student_limit=None,  # Not available in this API
                student_count=None,  # Not available in this API
            )
            if c.get("teaSchmUrl"):
                yield scrapy.Request(
                    url=c["teaSchmUrl"],
                    callback=self.parse_syllabus,
                    meta={"item": item},  # pass item to callback
                )
            else:
                yield item

    def parse_syllabus(self, response):
        item = response.meta["item"]

        # 從 syllabus 頁面提取額外資訊
        # 例如：課程目標、詳細說明、英文名稱等
        name_en = response.css("#CourseNameEn::text").get()
        if name_en:
            item["name_en"] = name_en.strip()

        objective_all = response.css(
            "body > div.container.sylview-section > div > div > div > p::text"
        ).getall()
        if objective_all:
            item["objective"] = " ".join(
                [text.strip() for text in objective_all if text.strip()]
            )

        yield item
