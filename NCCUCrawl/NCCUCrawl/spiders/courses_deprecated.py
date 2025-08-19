import json
import scrapy
from NCCUCrawl.items import CourseLegacyItem


class CoursesLegacySpider(scrapy.Spider):
    name = "courses_deprecated"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 追蹤已處理的課程，避免重複
        self.processed_courses = set()
        self.search_stats = {
            "three_level": {"categories": 0, "courses": 0, "new_courses": 0},
            "two_level": {"categories": 0, "courses": 0, "new_courses": 0},
            "one_level": {"categories": 0, "courses": 0, "new_courses": 0},
            "zero_level": {"categories": 0, "courses": 0, "new_courses": 0},
        }

    def _find_unit_info_for_two_level(self, dp1, dp2):
        """為二階層搜尋尋找對應的 unit_info"""
        for key, info in self.unit_mapping.items():
            key_parts = key.split("-")
            if len(key_parts) == 3 and key_parts[0] == dp1 and key_parts[1] == dp2:
                return info
        return {}

    def _find_unit_info_for_one_level(self, dp1):
        """為一階層搜尋尋找對應的 unit_info"""
        for key, info in self.unit_mapping.items():
            key_parts = key.split("-")
            if len(key_parts) == 3 and key_parts[0] == dp1:
                return info
        return {}

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
        semesters = self.get_semesters()
        for sem in semesters:
            yield from self.generate_hierarchical_requests(units, sem)

    def generate_hierarchical_requests(self, units, semester):
        """生成階層式搜尋請求：三階層 → 二階層 → 一階層 → 零階層"""

        # 1. 三階層搜尋 (dp1-dp2-dp3)
        three_level_categories = self.get_three_level_categories(units)
        for dp1, dp2, dp3 in three_level_categories:
            url = self.build_course_list(semester, dp1, dp2, dp3)
            yield scrapy.Request(
                url=url,
                callback=self.parse_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": dp2,
                    "dp3": dp3,
                    "search_level": "three_level",
                },
                meta={"search_level": "three_level"},
                priority=100,  # 最高優先級
            )
        # 2. 二階層搜尋 (dp1-dp2-"")
        two_level_categories = self.get_two_level_categories(units)
        for dp1, dp2 in two_level_categories:
            url = self.build_course_list(semester, dp1, dp2, "")
            yield scrapy.Request(
                url=url,
                callback=self.parse_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": dp2,
                    "dp3": "",
                    "search_level": "two_level",
                },
                meta={"search_level": "two_level"},
                priority=90,  # 第二優先級
            )
        # 3. 一階層搜尋 (dp1-""-"")
        one_level_categories = self.get_one_level_categories(units)
        for dp1 in one_level_categories:
            url = self.build_course_list(semester, dp1, "", "")
            yield scrapy.Request(
                url=url,
                callback=self.parse_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": "",
                    "dp3": "",
                    "search_level": "one_level",
                },
                meta={"search_level": "one_level"},
                priority=80,  # 第三優先級
            )

        # 4. 零階層搜尋 (""-""-"") - 全部課程
        url = self.build_course_list(semester, "", "", "")
        yield scrapy.Request(
            url=url,
            callback=self.parse_course_list,
            cb_kwargs={
                "semester": semester,
                "dp1": "",
                "dp2": "",
                "dp3": "",
                "search_level": "zero_level",
            },
            meta={"search_level": "zero_level"},
            priority=70,  # 最低優先級
        )

    def get_three_level_categories(self, units):
        """取得所有三階層分類 (dp1-dp2-dp3)"""
        categories = []
        for l1 in units:
            if l1["utCodL1"] != "0":
                for l2 in l1["utL2"]:
                    if l2["utCodL2"] != "0":
                        for l3 in l2["utL3"]:
                            if l3["utCodL3"] != "0":
                                categories.append(
                                    (l1["utCodL1"], l2["utCodL2"], l3["utCodL3"])
                                )
        return categories

    def get_two_level_categories(self, units):
        """取得所有二階層分類 (dp1-dp2)，去重複"""
        categories = set()
        for l1 in units:
            if l1["utCodL1"] != "0":
                for l2 in l1["utL2"]:
                    if l2["utCodL2"] != "0":
                        categories.add((l1["utCodL1"], l2["utCodL2"]))
        return list(categories)

    def get_one_level_categories(self, units):
        """取得所有一階層分類 (dp1)，去重複"""
        categories = set()
        for l1 in units:
            if l1["utCodL1"] != "0":
                categories.add(l1["utCodL1"])
        return list(categories)

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

    def create_course_item(self, c, semester, unit_info, dp1, dp2, dp3):
        """Create course item - can be extended by subclasses"""
        return CourseLegacyItem(
            id=f"{semester}{c['subNum']}",
            y=semester[:3],
            s=semester[3],
            subNum=c["subNum"],
            name=c["subNam"],
            nameEn=c.get("subNamEn", ""),  # from en api
            teacher=c.get("teaNam", ""),
            teacherEn=c.get("teaNamEn", ""),  # from en api
            kind=c.get("subKind", ""),
            time=c.get("subTime", ""),
            timeEn=c.get("subTimeEn", ""),  # from en api
            lmtKind=c.get("lmtKind", ""),
            lmtKindEn=c.get("lmtKindEn", ""),  # from en api
            core=c.get("core", ""),
            lang=c.get("langTpe", ""),
            langEn=c.get("langTpeEn", ""),  # from en api
            semQty=c.get("smtQty", ""),
            classroom=c.get("subClassroom", ""),
            classroomId=c.get("subClassroomId", ""),  # from en api
            unit=c.get("subGde", ""),
            unitEn=c.get("subGdeEn", ""),  # from en api
            dp1=dp1,
            dp2=dp2,
            dp3=dp3,
            point=float(c.get("subPoint", 0)) if c.get("subPoint") else None,
            subRemainUrl=c.get("subRemainUrl", ""),
            subSetUrl=c.get("subSetUrl", ""),
            subUnitRuleUrl=c.get("subUnitRuleUrl", ""),
            teaExpUrl=c.get("teaExpUrl", ""),
            teaSchmUrl=c.get("teaSchmUrl", ""),
            tranTpe=c.get("tranTpe", ""),
            tranTpeEn=c.get("tranTpeEn", ""),  # from en api
            info=c.get("info", ""),
            infoEn=c.get("infoEn", ""),  # from en api
            note=c.get("note", ""),
            noteEn=c.get("noteEn", ""),  # from en api
            syllabus="",  # In parse_syllabus
            objective="",  # In parse_syllabus
        )

    def parse_course_list(
        self, response, semester, dp1, dp2, dp3, search_level="unknown"
    ):
        courses = json.loads(response.text)
        self.search_stats[search_level]["categories"] += 1
        self.search_stats[search_level]["courses"] += len(courses)

        if dp1 and dp2 and dp3:
            category_key = f"{dp1}-{dp2}-{dp3}"
            unit_info = self.unit_mapping.get(category_key, {})
        elif dp1 and dp2:
            category_key = f"{dp1}-{dp2}-∅"
            # 尋找對應的 unit_info (可能需要從三階層對應找)
            unit_info = self._find_unit_info_for_two_level(dp1, dp2)
        elif dp1:
            category_key = f"{dp1}-∅-∅"
            unit_info = self._find_unit_info_for_one_level(dp1)
        else:
            category_key = "∅-∅-∅"
            unit_info = {}

        new_courses = []
        duplicate_count = 0

        for c in courses:
            course_id = f"{semester}{c['subNum']}"
            if course_id not in self.processed_courses:
                new_courses.append(c)
                self.processed_courses.add(course_id)
            else:
                duplicate_count += 1

        # 更新統計
        self.search_stats[search_level]["new_courses"] += len(new_courses)

        # 日誌輸出
        if new_courses or duplicate_count > 0:
            self.logger.info(
                f"[{search_level}] {category_key}: "
                f"Total={len(courses)}, New={len(new_courses)}, "
                f"Duplicates={duplicate_count}"
            )

        for c in new_courses:
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
                    "dp3": dp3,
                    "search_level": search_level,
                    "category_key": category_key,
                },
                dont_filter=True,
            )

    def _find_unit_info_for_two_level(self, dp1, dp2):
        """為二階層搜尋尋找對應的 unit_info"""
        for key, info in self.unit_mapping.items():
            key_parts = key.split("-")
            if len(key_parts) == 3 and key_parts[0] == dp1 and key_parts[1] == dp2:
                return info
        return {}

    def _find_unit_info_for_one_level(self, dp1):
        """為一階層搜尋尋找對應的 unit_info"""
        for key, info in self.unit_mapping.items():
            key_parts = key.split("-")
            if len(key_parts) == 3 and key_parts[0] == dp1:
                return info
        return {}

    def convert_kind_to_int(self, kind_str, lmt_kind_str=""):
        """Convert kind string to integer, considering lmtKind for special cases"""
        if lmt_kind_str:
            if "通識" in lmt_kind_str:
                return 4
            elif "跨領域" in lmt_kind_str:
                return 0

        kind_mapping = {
            "必修": 1,
            "選修": 2,
            "群修": 3,
        }
        return kind_mapping.get(kind_str, 0)

    def parse_course_detail_zh(self, response):
        item = response.meta["item"]
        course_id = response.meta["course_id"]

        zh_data = json.loads(response.text)
        if len(zh_data) == 1:
            zh_course = zh_data[0]
            item["teacher"] = zh_course.get("teaNam", item["teacher"])
            item["kind"] = self.convert_kind_to_int(
                zh_course.get("subKind", item["lmtKind"])
            )
            item["time"] = zh_course.get("subTime", item["time"])
            lmt_kind = zh_course.get("lmtKind", item["lmtKind"])
            item["kind"] = self.convert_kind_to_int(
                zh_course.get("subKind", ""), lmt_kind
            )
            item["core"] = 1 if zh_course.get("core", "") == "是" else 0
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
            dont_filter=True,
        )

    def parse_course_detail_en(self, response):
        item = response.meta["item"]
        course_data = response.meta["course_data"]

        en_data = json.loads(response.text)
        if len(en_data) == 1:
            en_course = en_data[0]
            item["nameEn"] = en_course.get("subNam", "")
            item["teacherEn"] = en_course.get("teaNam", "")
            item["timeEn"] = en_course.get("subTime", "")
            item["lmtKindEn"] = en_course.get("lmtKind", "")
            item["langEn"] = en_course.get("langTpe", "")
            item["classroomId"] = en_course.get("subClassroom", item["classroom"])
            item["tranTpeEn"] = en_course.get("tranTpe", "")
            item["infoEn"] = en_course.get("info", "")
            item["unitEn"] = en_course.get("subGde", "")
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

        description_title = response.css(
            "div.col-sm-7.sylview--mtop.col-p-6 h2.text-primary"
        )
        if description_title:
            descriptions = []
            # Get all siblings after the h2 title
            siblings = description_title.xpath("following-sibling::*")

            for sibling in siblings:
                # Check if we hit the stop condition (row sylview-mtop fa-border class)
                classes = sibling.css("::attr(class)").get()
                if classes and set(["row", "sylview-mtop", "fa-border"]).issubset(
                    set(classes.split())
                ):
                    break

                # Extract text content and split by newlines
                text_content = sibling.css("::text").getall()
                for text in text_content:
                    lines = [
                        line.strip()
                        for line in text.split("\n")
                        if line.strip() and line.strip() != " "
                    ]
                    descriptions.extend(lines)

            if descriptions:
                item["syllabus"] = "\n".join(descriptions)
            else:
                item["syllabus"] = response.url
        else:
            # Fallback to just storing the URL if structure is different
            syllabus_content = response.css(".sylview-section").get()
            if syllabus_content:
                item["syllabus"] = response.url

        yield from self.process_course_item(item, course_data)
