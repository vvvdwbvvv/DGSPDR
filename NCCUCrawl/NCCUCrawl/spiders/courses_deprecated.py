import json
import scrapy
from NCCUCrawl.items import CourseLegacyItem


class CoursesSpider(scrapy.Spider):
    name = "courses_deprecated"
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
            "1011",
            "1012",
            "1021",
            "1022",
            "1031",
            "1032",
            "1041",
            "1042",
            "1051",
            "1052",
            "1061",
            "1062",
            "1071",
            "1072",
            "1081",
            "1082",
            "1091",
            "1092",
            "1101",
            "1102",
            "1111",
            "1112",
            "1121",
            "1122",
            "1131",
            "1132",
            "1141",
        ]

    # also available at https://es.nccu.edu.tw/course/zh-TW/{id}/
    def build_course_list(self, sem, dp1, dp2, dp3):
        return (
            "https://es.nccu.edu.tw/course/zh-TW/"
            f":sem={sem}%20:dp1={dp1}%20:dp2={dp2}%20:dp3={dp3}"  # ex: https://es.nccu.edu.tw/course/zh-TW/:sem=1131%20:dp1=01%20:dp2=A1%20:dp3=105%20/
        )
    def build_course_detail_url_zh(self, course_id):
        return f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/"

    def build_course_detail_url_en(self, course_id):
        return f"http://es.nccu.edu.tw/course/en/{course_id}/"

    def process_course_item(self, item, course_data):
        yield item

    def create_course_item(self, c, semester, unit_info):
        """Create course item - can be extended by subclasses"""
        return CourseLegacyItem(
            id=f"{semester}{c['subNum']}",
            y=semester[:3], 
            s=semester[3], 
            subNum=c["subNum"],
            name=c["subNam"],
            nameEn=c.get("subNamEn", ""), # from en api 
            teacher=c.get("teaNam", ""),  
            teacherEn=c.get("teaNamEn", ""),  # from en api 
            kind=c.get("subKind", ""),
            time=c.get("subTime", ""),
            timeEn=c.get("subTimeEn", ""),  # from en api 
            lmtKind=c.get("lmtKind", ""),
            lmtKindEn=c.get("lmtKindEn", ""), # from en api 
            lang=c.get("langTpe", ""),
            langEn=c.get("langTpeEn", ""), # from en api 
            semQty=c.get("smtQty", ""),
            classroom=c.get("subClassroom", ""),
            classroomId=c.get("subClassroomId", ""), # from en api 
            unit=unit_info.get("unit", ""),
            unitEn=unit_info.get("unit_en", ""), # from en api 
            dp1=c.get("dp1", ""),
            dp2=c.get("dp2", ""),
            dp3=c.get("dp3", ""),
            point=float(c.get("subPoint", 0)) if c.get("subPoint") else None,
            subRemainUrl=c.get("subRemainUrl", ""),
            subSetUrl=c.get("subSetUrl", ""),
            subUnitRuleUrl=c.get("subUnitRuleUrl", ""),
            teaExpUrl=c.get("teaExpUrl", ""),
            teaSchmUrl=c.get("teaSchmUrl", ""),
            tranTpe=c.get("tranTpe", ""),
            tranTpeEn=c.get("tranTpeEn", ""), # from en api 
            info=c.get("info", ""),
            infoEn=c.get("infoEn", ""), # from en api 
            note=c.get("note", ""),
            noteEn=c.get("noteEn", ""), # from en api 
            syllabus="",  # In parse_syllabus
            objective="",  # In parse_syllabus
        )

    def parse_course_list(self, response, semester, dp1, dp2, dp3):
        courses = json.loads(response.text)
        unit_key = f"{dp1}-{dp2}-{dp3}"
        unit_info = self.unit_mapping.get(unit_key, {})

        for c in courses:
            item = self.create_course_item(c, semester, unit_info, dp1, dp2, dp3)
            course_id = f"{semester}{c['subNum']}"

            zh_url = self.build_course_detail_url_zh(course_id)
            yield scrapy.Request(
                url=zh_url,
                callback=self.parse_course_detail_zh,
                meta={
                    "item": item, 
                    "course_data": c, 
                    "course_id": course_id,
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": dp2, 
                    "dp3": dp3
                },
                dont_filter=True
            )
    def parse_course_detail_zh(self, response):
        item = response.meta["item"]
        course_id = response.meta["course_id"]

        zh_data = json.loads(response.text)
        if len(zh_data) == 1:
            zh_course = zh_data[0]               
            item["teacher"] = zh_course.get("teaNam", item["teacher"])
            item["kind"] = zh_course.get("subKind", item["kind"])
            item["time"] = zh_course.get("subTime", item["time"])
            item["lmtKind"] = zh_course.get("lmtKind", item["lmtKind"])
            item["lang"] = zh_course.get("langTpe", item["lang"])
            item["classroom"] = zh_course.get("subClassroom", item["classroom"])
            item["tranTpe"] = zh_course.get("tranTpe", item["tranTpe"])
            item["info"] = zh_course.get("info", item["info"])
            item["note"] = zh_course.get("note", item["note"])

        en_url = self.build_course_detail_url_en(course_id)
        yield scrapy.Request(
            url=en_url,
            callback=self.parse_course_detail_en,
            meta=response.meta,
            dont_filter=True
        )

    def parse_course_detail_en(self, response):
        item = response.meta["item"]
        course_data = response.meta["course_data"]
        course_id = response.meta["course_id"]
        
        en_data = json.loads(response.text)
        if len(en_data) == 1:
            en_course = en_data[0]
            item["nameEn"] = en_course.get("subNam", "")
            item["teacherEn"] = en_course.get("teaNam", "")
            item["timeEn"] = en_course.get("subTime", "")
            item["lmtKindEn"] = en_course.get("lmtKind", "")
            item["langEn"] = en_course.get("langTpe", "")
            item["tranTpeEn"] = en_course.get("tranTpe", "")
            item["infoEn"] = en_course.get("info", "")
            item["noteEn"] = en_course.get("note", "")
        
        if course_data.get("teaSchmUrl"):
            yield scrapy.Request(
                url=course_data["teaSchmUrl"],
                callback=self.parse_syllabus,
                meta={"item": item, "course_data": course_data},
            )
        else:
            yield from self.process_course_item(item, course_data)

    def parse_syllabus(self, response):
        """Parse syllabus page - can be extended by subclasses"""
        item = response.meta["item"]
        course_data = response.meta.get("course_data", {})

        # Fetch course objective
        objective_elements = response.css(
            "body > div.container.sylview-section > div > div > div > p::text"
        ).getall()
        if objective_elements:
            item["objective"] = " ".join(
                [text.strip() for text in objective_elements if text.strip()]
            )

        syllabus_content = response.css(".sylview-section").get()
        if syllabus_content:
            item["syllabus"] = response.url

        yield from self.process_course_item(item, course_data)
