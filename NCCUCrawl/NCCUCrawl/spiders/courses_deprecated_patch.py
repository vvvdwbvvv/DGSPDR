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

                    course_id = f"{semester}{c['subNum']}"

                    # 直接創建完整的 CourseLegacyItem
                    item = self.create_complete_course_legacy_item(
                        c, semester, unit_info, dp1, dp2, dp3
                    )

                    self.logger.debug(f"Creating item for missing course: {course_id}")
                    self.total_saved_courses += 1

                    # 直接 yield item - 不需要額外的 API 請求
                    yield item

                    self.api_request_count += 1

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
        except Exception as e:
            self.logger.error(f"Error processing course list: {e}")

    def create_complete_course_legacy_item(
        self, course_data, semester, unit_info, dp1, dp2, dp3
    ):
        """創建完整的 CourseLegacyItem，符合 Pipeline 期待的欄位"""
        item = CourseLegacyItem()

        # 主要識別欄位
        course_id = f"{semester}{course_data['subNum']}"
        item["id"] = course_id

        # 學期資訊
        item["y"] = semester[:3]  # 年度 (114)
        item["s"] = semester[3:]  # 學期 (1)
        item["subNum"] = course_data.get("subNum", "")

        # 課程基本資訊
        item["name"] = course_data.get("subName", "未知課程")
        item["nameEn"] = course_data.get("subNameEn", "")
        item["teacher"] = course_data.get("teacher", "未知教師")
        item["teacherEn"] = course_data.get("teacherEn", "")

        # 課程類別與時間
        item["kind"] = course_data.get("subKind", "")
        item["time"] = course_data.get("subTime", "")
        item["timeEn"] = course_data.get("subTimeEn", "")

        # 語言與限制
        item["lmtKind"] = course_data.get("subLmtKind", "")
        item["lmtKindEn"] = course_data.get("subLmtKindEn", "")
        item["core"] = 1 if course_data.get("core", "") == "是" else 0
        item["lang"] = course_data.get("subLang", "")
        item["langEn"] = course_data.get("subLangEn", "")
        item["semQty"] = course_data.get("subSemQty", "")

        # 教室資訊
        item["classroom"] = course_data.get("subClassroom", "")
        item["classroomId"] = course_data.get("subClassroomId", "")

        # 單位資訊
        item["unit"] = unit_info.get("unit", "未知系所")
        item["unitEn"] = unit_info.get("unit_en", "Unknown Department")
        item["dp1"] = dp1
        item["dp2"] = dp2
        item["dp3"] = dp3

        # 學分
        item["point"] = float(course_data.get("subCredit", 0))

        # URL 相關 (設為預設值)
        item["subRemainUrl"] = ""
        item["subSetUrl"] = ""
        item["subUnitRuleUrl"] = ""
        item["teaExpUrl"] = ""
        item["teaSchmUrl"] = ""

        # 其他資訊
        item["tranTpe"] = course_data.get("subTranTpe", "")
        item["tranTpeEn"] = course_data.get("subTranTpeEn", "")
        item["info"] = course_data.get("subInfo", "")
        item["infoEn"] = course_data.get("subInfoEn", "")
        item["note"] = course_data.get("subNote", "")
        item["noteEn"] = course_data.get("subNoteEn", "")

        # 課程大綱 (預設為空，需要詳細頁面才能獲取)
        item["syllabus"] = ""
        item["objective"] = ""

        return item

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


# 測試 Pipeline 的 Spider
class TestPipelineSpider(scrapy.Spider):
    name = "test_pipeline"

    def start_requests(self):
        yield scrapy.Request(url="http://httpbin.org/get", callback=self.parse)

    def parse(self, response):
        # 創建測試用的 CourseLegacyItem
        item = CourseLegacyItem()
        item["id"] = "TEST001"
        item["y"] = "114"
        item["s"] = "1"
        item["subNum"] = "TEST001"
        item["name"] = "Test Course"
        item["nameEn"] = "Test Course English"
        item["teacher"] = "Test Teacher"
        item["teacherEn"] = "Test Teacher English"
        item["kind"] = "選修"
        item["time"] = "Mon 1-2"
        item["timeEn"] = "Mon 1-2"
        item["lmtKind"] = ""
        item["lmtKindEn"] = ""
        item["lang"] = "中文"
        item["langEn"] = "Chinese"
        item["semQty"] = "單學期科目"
        item["classroom"] = "Test Room"
        item["classroomId"] = "TR001"
        item["unit"] = "Test Department"
        item["unitEn"] = "Test Department"
        item["dp1"] = "T"
        item["dp2"] = "TE"
        item["dp3"] = "TES"
        item["point"] = 3.0
        item["subRemainUrl"] = ""
        item["subSetUrl"] = ""
        item["subUnitRuleUrl"] = ""
        item["teaExpUrl"] = ""
        item["teaSchmUrl"] = ""
        item["tranTpe"] = ""
        item["tranTpeEn"] = ""
        item["info"] = ""
        item["infoEn"] = ""
        item["note"] = ""
        item["noteEn"] = ""
        item["syllabus"] = ""
        item["objective"] = ""

        self.logger.info(f"Creating test CourseLegacyItem: {item['id']}")
        yield item
