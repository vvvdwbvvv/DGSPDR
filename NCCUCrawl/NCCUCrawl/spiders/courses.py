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
        categories = self.get_categories(units)
        semesters = self.get_semesters()

        for sem in semesters:
            for dp1, dp2, dp3 in categories:
                url = self.build_course_list_url(sem, dp1, dp2, dp3)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_course_list,
                    cb_kwargs={"semester": sem, "dp1": dp1, "dp2": dp2, "dp3": dp3},
                )

    def get_categories(self, units):
        categories = []

        for l1 in units:
            if l1["utCodL1"] != "0":
                # 添加只有 dp1 的情況 (dp2="", dp3="")
                categories.append((l1["utCodL1"], "", ""))

                for l2 in l1["utL2"]:
                    if l2["utCodL2"] != "0":
                        # 添加只有 dp1, dp2 的情況 (dp3="")
                        categories.append((l1["utCodL1"], l2["utCodL2"], ""))

                        for l3 in l2["utL3"]:
                            if l3["utCodL3"] != "0":
                                # 原本的完整三層情況
                                categories.append(
                                    (l1["utCodL1"], l2["utCodL2"], l3["utCodL3"])
                                )

        return categories

    def get_semesters(self):
        return [
            "1011", "1012", "1021", "1022", "1031", "1032", "1041", "1042",
            "1051", "1052", "1061", "1062", "1071", "1072", "1081", "1082", 
            "1091", "1092", "1101", "1102", "1111", "1112", "1121", "1122",
            "1131", "1132", "1141"
        ]

    def build_course_list_url(self, sem, dp1, dp2, dp3):
        return (
            "https://es.nccu.edu.tw/course/zh-TW/"
            f":sem={sem}%20:dp1={dp1}%20:dp2={dp2}%20:dp3={dp3}"  # ex: https://es.nccu.edu.tw/course/zh-TW/:sem=1131%20:dp1=01%20:dp2=A1%20:dp3=105%20/
        )

    def process_course_item(self, item, course_data):
        yield item

    def create_course_item(self, c, semester, unit_info):
        """Create course item - can be extended by subclasses"""
        return CourseItem(
            id=f"{semester}{c['subNum']}",
            year=semester[:3],
            semester=semester[3],
            sub_num=c["subNum"],
            name=c["subNam"],
            name_en=c.get("subNamEn", ""),
            teacher_id="",
            kind=c.get("subKind", ""),
            time=c.get("subTime", ""),
            lang=c.get("langTpe", ""),
            lang_en=c.get("langTpeEn", ""),
            sem_qty=c.get("smtQty", ""),
            sem_qty_en=c.get("smtQtyEn", ""),
            classroom_id=c.get("subClassroom", ""),
            unit=unit_info.get("unit", ""),
            unit_en=unit_info.get("unit_en", ""),
            college=unit_info.get("college", ""),
            degree=c.get("gdeType", ""),
            department=unit_info.get("department", ""),
            credit=float(c.get("subPoint", 0)) if c.get("subPoint") else None,
            transition_type=c.get("tranTpe", ""),
            transition_type_en="",
            info=c.get("info", ""),
            info_en=c.get("infoEn", ""),
            note=c.get("note", ""),
            note_en=c.get("noteEn", ""),
            syllabus=c.get("teaSchmUrl", ""),
            syllabus_en="",
            objective="",
            objective_en="",
            core=c.get("core", "") == "是",
            discipline=c.get("lmtKind", ""),
            last_enroll=None,
            student_limit=None,
            student_count=None,
        )

    def parse_course_list(self, response, semester, dp1, dp2, dp3):
        courses = json.loads(response.text)
        unit_key = f"{dp1}-{dp2}-{dp3}"
        unit_info = self.unit_mapping.get(unit_key, {})

        for c in courses:
            item = self.create_course_item(c, semester, unit_info)

            # deal with syllabus url
            if c.get("teaSchmUrl"):
                yield scrapy.Request(
                    url=c["teaSchmUrl"],
                    callback=self.parse_syllabus,
                    meta={"item": item, "course_data": c},
                )
            else:
                yield from self.process_course_item(item, c)

    def parse_syllabus(self, response):
        """Parse syllabus page - can be extended by subclasses"""
        item = response.meta["item"]
        course_data = response.meta.get("course_data", {})

        # Fetch course name in English
        name_en = response.css("#CourseNameEn::text").get()
        if name_en:
            item["name_en"] = name_en.strip()

        # Fetch course objective
        objective_all = response.css(
            "body > div.container.sylview-section > div > div > div > p::text"
        ).getall()
        if objective_all:
            item["objective"] = " ".join(
                [text.strip() for text in objective_all if text.strip()]
            )

        yield from self.process_course_item(item, course_data)
