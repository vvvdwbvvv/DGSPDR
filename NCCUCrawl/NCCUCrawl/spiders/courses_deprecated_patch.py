import json
import scrapy
import sqlite3
from typing import Set, Dict, List
from .courses_deprecated import CoursesLegacySpider
from NCCUCrawl.items import CourseLegacyItem


class DatabaseComparator:
    def __init__(self, db_path="data.db"):
        self.conn = sqlite3.connect(db_path)
        self.existing_courses: Set[str] = set()
        self.load_existing_courses()

    def load_existing_courses(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM course_legacy")
            rows = cursor.fetchall()

            for row in rows:
                if row[0]:
                    self.existing_courses.add(row[0])

            print(f"Loaded {len(self.existing_courses)} existing courses from database")

        except Exception as e:
            print(f"Error loading from database: {e}")
            raise
        finally:
            self.conn.close()

    def is_course_exists(self, course_id: str) -> bool:
        return course_id in self.existing_courses

    def get_missing_courses_for_category(
        self, semester: str, dp1: str, dp2: str, dp3: str, api_courses: List[Dict]
    ) -> List[Dict]:
        missing_courses = []

        for course in api_courses:
            course_id = f"{semester}{course['subNum']}"

            if not self.is_course_exists(course_id):
                course["_missing_reason"] = "not_in_db"
                course["_full_course_id"] = course_id
                missing_courses.append(course)

        return missing_courses


class SmartCoursesSpider(CoursesLegacySpider):
    name = "smart_courses"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger.info("Using database comparator")
        self.comparator = DatabaseComparator()

        self.api_request_count = 0
        self.api_limit = 500
        self.total_existing_courses = 0
        self.total_missing_courses = 0
        self.total_processed_courses = 0
        self.total_saved_courses = 0

    def parse_course_list(self, response, semester, dp1, dp2, dp3):
        try:
            courses = json.loads(response.text)
            self.total_processed_courses += len(courses)

            missing_courses = self.comparator.get_missing_courses_for_category(
                semester, dp1, dp2, dp3, courses
            )

            existing_count = len(courses) - len(missing_courses)
            self.total_existing_courses += existing_count
            self.total_missing_courses += len(missing_courses)

            category_key = f"{dp1}-{dp2}-{dp3}"

            if missing_courses:
                self.logger.info(
                    f"Category {category_key}: Total {len(courses)}, "
                    f"Existing {existing_count}, Missing {len(missing_courses)}"
                )

                unit_key = f"{dp1}-{dp2}-{dp3}"
                unit_info = self.unit_mapping.get(unit_key, {})

                for c in missing_courses:
                    if self.api_request_count >= self.api_limit:
                        self.logger.warning("API limit reached")
                        return

                    item = self.create_course_item(
                        c, semester, unit_info, dp1, dp2, dp3
                    )
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
                        },
                        dont_filter=True,
                    )

                    self.logger.debug(f"Creating item for missing course: {course_id}")
                    self.total_saved_courses += 1
                    self.api_request_count += 1

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
        except Exception as e:
            self.logger.error(f"Error processing course list: {e}")

    def create_complete_course_legacy_item(
        self, course_data, semester, unit_info, dp1, dp2, dp3
    ):
        item = CourseLegacyItem()

        # 主要識別欄位
        course_id = f"{semester}{course_data['subNum']}"
        item["id"] = course_id

        # 學期資訊
        item["y"] = semester[:3]  # 年度 (114)
        item["s"] = semester[3:]  # 學期 (1)
        item["subNum"] = course_data.get("subNum", "")

        # 課程基本資訊
        item["name"] = course_data.get("subNam", "")
        item["nameEn"] = course_data.get("subNamEn", "")
        item["teacher"] = course_data.get("teaNam", "")
        item["teacherEn"] = course_data.get("teaNamEn", "")

        # 課程類別與時間
        lmt_kind = course_data.get("lmtKind", "")
        item["kind"] = self.convert_kind_to_int(
            course_data.get("subKind", ""), lmt_kind
        )
        item["time"] = course_data.get("subTime", "")
        item["timeEn"] = course_data.get("subTimeEn", "")

        # 語言與限制
        item["lmtKind"] = course_data.get("lmtKind", "")
        item["lmtKindEn"] = course_data.get("lmtKindEn", "")
        item["core"] = 1 if course_data.get("core", "") == "是" else 0
        item["lang"] = course_data.get("langTpe", "")
        item["langEn"] = course_data.get("langTpeEn", "")
        item["semQty"] = course_data.get("smtQty", "")

        # 教室資訊
        item["classroom"] = course_data.get("subClassroom", "")
        item["classroomId"] = course_data.get("subClassroomId", "")

        # 單位資訊
        item["unit"] = course_data.get("subGde", "")
        item["unitEn"] = course_data.get("subGdeEn", "")
        item["dp1"] = dp1
        item["dp2"] = dp2
        item["dp3"] = dp3

        # 學分
        item["point"] = float(course_data.get("subPoint", 0))

        # URL 相關 (設為預設值)
        item["subRemainUrl"] = course_data.get("subRemainUrl", "")
        item["subSetUrl"] = course_data.get("subSetUrl", "")
        item["subUnitRuleUrl"] = course_data.get("subUnitRuleUrl", "")
        item["teaExpUrl"] = course_data.get("teaExpUrl", "")
        item["teaSchmUrl"] = course_data.get("teaSchmUrl", "")

        # 其他資訊
        item["tranTpe"] = course_data.get("tranTpe", "")
        item["tranTpeEn"] = course_data.get("tranTpeEn", "")
        item["info"] = course_data.get("info", "")
        item["infoEn"] = course_data.get("infoEn", "")
        item["note"] = course_data.get("note", "")
        item["noteEn"] = course_data.get("noteEn", "")
        item["syllabus"] = ""
        item["objective"] = ""

        return item

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

    def closed(self, reason):
        self.logger.info("=== Smart Courses Spider Statistics ===")
        self.logger.info(
            f"Database existing courses: {len(self.comparator.existing_courses)}"
        )
        self.logger.info(f"Total processed courses: {self.total_processed_courses}")
        self.logger.info(f"Found existing courses: {self.total_existing_courses}")
        self.logger.info(f"Found missing courses: {self.total_missing_courses}")
        self.logger.info(f"Created items: {self.total_saved_courses}")
        self.logger.info(
            f"API requests made: {self.api_request_count}/{self.api_limit}"
        )

        if self.total_missing_courses > 0:
            creation_rate = (
                self.total_saved_courses / self.total_missing_courses
            ) * 100
            self.logger.info(f"Item creation rate: {creation_rate:.1f}%")

        if (self.total_existing_courses + self.total_missing_courses) > 0:
            efficiency = (
                self.total_existing_courses
                / (self.total_existing_courses + self.total_missing_courses)
            ) * 100
            self.logger.info(f"Duplicate avoidance efficiency: {efficiency:.1f}%")

        self.logger.info("=== Final Recommendation ===")
        if self.total_saved_courses > 0:
            self.logger.info(f"✅ Created {self.total_saved_courses} CourseLegacyItems")
        else:
            self.logger.warning("❌ No items were created")
