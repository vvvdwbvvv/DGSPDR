import json
import scrapy
import sqlite3
from scrapy import signals
import os
import csv
from typing import Set, Dict, List
from NCCUCrawl.items import CourseLegacyItem
from .courses_deprecated import CoursesLegacySpider


class DatabaseComparator:
    def __init__(self, db_path="data.db", csv_path="CoursesList.csv"):
        self.conn = sqlite3.connect(db_path)
        self.csv_path = csv_path
        self.existing_courses: Set[str] = set()
        self.csv_courses: Set[str] = set()
        self.load_existing_courses()
        self.load_csv_courses()

    def load_existing_courses(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT subNum FROM course_legacy")
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

    def load_csv_courses(self):
        try:
            if not os.path.exists(self.csv_path):
                print(f"CSV file not found: {self.csv_path}")
                return

            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    course_index = row.get("CourseIndex", "").strip()
                    if course_index:
                        self.csv_courses.add(course_index)

            print(f"Loaded {len(self.csv_courses)} courses from CSV file")
            target_course = "070394021"
            if target_course in self.csv_courses:
                print(f"✓ Target course {target_course} found in CSV")
            else:
                print(f"✗ Target course {target_course} NOT found in CSV")

            # 找出差異：在 CSV 但不在資料庫中的課程（應該爬取的）
            missing_in_db = self.csv_courses - self.existing_courses
            print(f"CSV courses: {len(self.csv_courses)}")
            print(f"DB courses: {len(self.existing_courses)}")
            print(f"Should crawl (in CSV but not in DB): {len(missing_in_db)}")

            if missing_in_db:
                print("Missing courses (first 10):")
                for i, course in enumerate(sorted(missing_in_db)[:10]):
                    print(f"  {i + 1:2d}. {course}")

            # 找出在資料庫但不在 CSV 中的課程（可能是舊課程）
            extra_in_db = self.existing_courses - self.csv_courses
            print(f"Extra in DB (not in current CSV): {len(extra_in_db)}")

            if extra_in_db:
                print("Extra DB courses (first 10):")
                for i, course in enumerate(sorted(extra_in_db)[:10]):
                    print(f"  {i + 1:2d}. {course}")

        except Exception as e:
            print(f"Error loading CSV file: {e}")
            self.csv_courses = set()

    def is_course_exists(self, course_subnum: str) -> bool:
        return course_subnum in self.existing_courses

    def should_crawl_course(self, course_subnum: str) -> bool:
        return (
            course_subnum in self.csv_courses
            and course_subnum not in self.existing_courses
        )

    def get_missing_courses_for_category(
        self, semester: str, dp1: str, dp2: str, dp3: str, api_courses: List[Dict]
    ) -> List[Dict]:
        missing_courses = []
        category_key = f"{dp1}-{dp2}-{dp3}"

        target_courses = [
            "070393001",
            "070393011",
            "070394001",
            "070394011",
            "070394021",
            "070395001",
            "070395011",
            "070403001",
            "070404001",
            "070406001",
        ]

        found_targets = [c for c in api_courses if c["subNum"] in target_courses]
        if found_targets:
            print(f"🎯 FOUND TARGET COURSES in {category_key}:")
            for tc in found_targets:
                print(f"   - {tc['subNum']}: {tc.get('subNam', 'N/A')}")

        for course in api_courses:
            sub_num = course["subNum"]
            course_id = f"{semester}{sub_num}"

            if sub_num in target_courses:
                print(f"🎯 FOUND TARGET COURSE {sub_num}!")
                print(f"   - Semester: {semester}")
                print(f"   - Category: {category_key}")
                print(f"   - Course name: {course.get('subNam', 'N/A')}")
                print(f"   - In CSV: {sub_num in self.csv_courses}")
                print(f"   - In DB: {self.is_course_exists(sub_num)}")
                print(f"   - Should crawl: {self.should_crawl_course(sub_num)}")

            if self.should_crawl_course(sub_num):
                course["_missing_reason"] = "in_csv_not_in_db"
                course["_full_course_id"] = course_id
                missing_courses.append(course)

        return missing_courses


class SmartCoursesSpider(CoursesLegacySpider):
    name = "smart_courses"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.logger.info("Initializing database comparator...")
            self.comparator = DatabaseComparator()
            self.logger.info(
                f"Loaded {len(self.comparator.existing_courses)} existing courses"
            )

            self.missing_courses = (
                self.comparator.csv_courses - self.comparator.existing_courses
            )
            self.remaining_missing = (
                self.missing_courses.copy()
            )  # when dp fails -> use subNum to crawl
            self.logger.info(
                f"Found {len(self.missing_courses)} missing courses to crawl"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize database comparator: {e}")
            self.comparator = None
            self.missing_courses = set()
            self.remaining_missing = set()  # when dp fails -> use subNum to crawl

        self.api_request_count = 0
        self.api_limit = 500
        self.total_existing_courses = (
            len(self.comparator.existing_courses) if self.comparator else 0
        )
        self.total_missing_courses = len(self.missing_courses)
        self.total_processed_courses = 0
        self.total_saved_courses = 0
        self.failed_requests = 0
        self.successful_detail_requests = 0
        self.redirect_count = 0

    def process_course_item(self, item, course_data):
        """Override to track actually saved items"""
        from NCCUCrawl.items import CourseLegacyItem

        self.total_saved_courses += 1
        course_id = item.get("id", "unknown")
        self.logger.debug(f"Successfully processed course: {course_id}")

        # Convert dictionary to CourseLegacyItem if needed
        if isinstance(item, dict):
            yield CourseLegacyItem(**item)
        else:
            yield item

    def handle_request_error(self, failure):
        """Handle request failures"""
        self.failed_requests += 1
        course_id = failure.request.meta.get("course_id", "unknown")
        self.logger.error(f"✗ Request failed for course {course_id}: {failure}")

    def parse_course_list(self, response, semester, dp1, dp2, dp3):
        try:
            courses = json.loads(response.text)
            self.total_processed_courses += len(courses)
            category_key = f"{dp1}-{dp2}-{dp3}"

            # DEBUG
            target_courses = [
                c
                for c in courses
                if c["subNum"]
                in ["070394021", "070394001", "070394011", "070393001", "070393011"]
            ]
            if target_courses:
                print(f"🔍 Category {category_key} contains target courses:")
                for tc in target_courses:
                    print(f"   - {tc['subNum']}: {tc.get('subNam', 'N/A')}")

            if not self.comparator:
                self.logger.warning("No database comparator available")
                return

            missing_courses = self.comparator.get_missing_courses_for_category(
                semester, dp1, dp2, dp3, courses
            )

            # 剩餘列表中移除已找到的課程
            for c in missing_courses:
                sub_num = c["subNum"]
                if sub_num in self.remaining_missing:
                    self.remaining_missing.remove(sub_num)

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
                        self.logger.warning(f"API limit reached at {self.api_limit}")
                        return

                    item = self.create_course_item(
                        c, semester, unit_info, dp1, dp2, dp3
                    )
                    course_id = f"{semester}{c['subNum']}"

                    zh_url = self.build_course_detail_url_zh(course_id)
                    self.logger.debug(
                        f"→ Requesting course detail: {course_id} from {zh_url}"
                    )

                    # Add unique identifier to prevent dupefilter issues
                    unique_url = f"{zh_url}?_spider_req={self.api_request_count}"

                    yield scrapy.Request(
                        url=unique_url,
                        callback=self.parse_course_detail_zh,
                        meta={
                            "item": item,
                            "course_data": c,
                            "course_id": course_id,
                            "semester": semester,
                            "dp1": dp1,
                            "dp2": dp2,
                            "dp3": dp3,
                            "original_url": zh_url,  # Store the original URL
                        },
                        dont_filter=True,
                        # Add error handling
                        errback=self.handle_request_error,
                    )

                    self.api_request_count += 1

                    # 每10個請求記錄一次進度
                    if self.api_request_count % 10 == 0:
                        self.logger.info(
                            f"Progress: {self.api_request_count}/{self.api_limit} requests made, "
                            f"Success rate: {self.successful_detail_requests}/{self.api_request_count}"
                        )

            else:
                self.logger.debug(
                    f"Category {category_key}: All {len(courses)} courses exist in database"
                )

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error for {category_key}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing course list for {category_key}: {e}")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)
        return spider

    def spider_idle(self):
        """當分類 API 處理完後，直接爬取剩餘的 missing courses"""
        if self.remaining_missing and self.api_request_count < self.api_limit:
            self.logger.info(
                f"Starting direct crawl for {len(self.remaining_missing)} remaining courses"
            )
            self.logger.info(
                f"Remaining courses: {sorted(list(self.remaining_missing)[:5])}"  # 顯示前5個
            )

            requests_made = 0
            requests_to_schedule = []

            for sub_num in list(self.remaining_missing):
                if self.api_request_count >= self.api_limit:
                    self.logger.warning(f"API limit reached at {self.api_limit}")
                    break

                semester = "1141"
                course_id = f"{semester}{sub_num}"

                # 建立基本項目（沒有 dp 資訊）
                item = CourseLegacyItem(
                    id=course_id,
                    subNum=sub_num,
                    y=semester[:3],  # "114" from "1141"
                    s=semester[3],  # "1" from "1141"
                    name="",  # 將從詳細頁面獲取
                    teacher="",
                    classroom="",
                    time="",
                    point=None,
                    lang="",
                    lmtKind="",
                    tranTpe="",
                    info="",
                    note="",
                    kind=0,
                    core=0,
                    nameEn="",
                    teacherEn="",
                    timeEn="",
                    lmtKindEn="",
                    langEn="",
                    classroomId="",
                    tranTpeEn="",
                    infoEn="",
                    unitEn="",
                    noteEn="",
                    dp1="",
                    dp2="",
                    dp3="",
                    unit="",
                    semQty="",
                    subRemainUrl="",
                    subSetUrl="",
                    subUnitRuleUrl="",
                    teaExpUrl="",
                    teaSchmUrl="",
                    syllabus="",
                    objective="",
                )
                zh_url = self.build_course_detail_url_zh(course_id)
                unique_url = f"{zh_url}?_direct_{self.api_request_count}"
                self.logger.info(f"→ Direct crawl: {sub_num} ({course_id})")

                course_data = {
                    "subNum": sub_num,
                    "is_direct_crawl": True,  # 標記為直接爬取
                }

                request = scrapy.Request(
                    url=unique_url,
                    callback=self.parse_course_detail_zh,
                    meta={
                        "item": item,
                        "course_data": course_data,
                        "course_id": course_id,
                        "semester": semester,
                        "original_url": zh_url,
                        "is_direct_crawl": True,  # 標記為直接爬取
                    },
                    dont_filter=True,
                    errback=self.handle_request_error,
                )

                requests_to_schedule.append(request)

                self.api_request_count += 1
                requests_made += 1
                self.remaining_missing.remove(sub_num)

                # 每5個請求記錄一次進度
                if requests_made % 5 == 0:
                    self.logger.info(
                        f"Direct crawl progress: {requests_made} requests made"
                    )
            if requests_to_schedule:
                self.logger.info(
                    f"✅ Scheduling {len(requests_to_schedule)} direct crawl requests"
                )

                for request in requests_to_schedule:
                    # 修正：使用正確的方法簽名
                    self.crawler.engine.crawl(request)

                # 阻止 spider 關閉，直到請求完成
                raise scrapy.exceptions.DontCloseSpider(
                    "Direct crawl requests scheduled"
                )
            else:
                self.logger.info("No direct crawl requests needed")
        else:
            if not self.remaining_missing:
                self.logger.info("✅ All missing courses found via DP API")
            else:
                self.logger.info(
                    f"API limit reached, {len(self.remaining_missing)} courses remain"
                )

    def build_course_detail_url_zh(self, course_id):
        return f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/"

    def build_course_detail_url_en(self, course_id):
        return f"http://es.nccu.edu.tw/course/en/{course_id}/"

    def parse_course_detail_zh(self, response):
        """Override to add debugging and handle unique URLs"""
        item = response.meta["item"]
        course_id = response.meta["course_id"]
        course_data = response.meta["course_data"]

        if response.status != 200:
            self.failed_requests += 1
            self.logger.warning(
                f"✗ Non-200 status {response.status} for course {course_id}"
            )
            return

        try:
            self.successful_detail_requests += 1
            self.logger.debug(f"→ Processing detail page for course {course_id}")

            zh_data = json.loads(response.text)
            if len(zh_data) == 1:
                zh_course = zh_data[0]
                item["teacher"] = zh_course.get("teaNam", item["teacher"])
                item["kind"] = self.convert_kind_to_int(
                    zh_course.get("subKind", item["lmtKind"])
                )
                item["name"] = zh_course.get("subNam", item["name"])
                item["lmtKind"] = zh_course.get("lmtKind", item["lmtKind"])
                item["time"] = zh_course.get("subTime", item["time"])
                lmt_kind = zh_course.get("lmtKind", item["lmtKind"])
                item["kind"] = self.convert_kind_to_int(
                    zh_course.get("subKind", ""), lmt_kind
                )
                item["unit"] = zh_course.get("subGde", item["unit"])
                item["point"] = zh_course.get("subPoint", item["point"])
                item["subRemainUrl"] = zh_course.get("subRemainUrl", "")
                item["subSetUrl"] = zh_course.get("subSetUrl", "")
                item["subUnitRuleUrl"] = zh_course.get("subUnitRuleUrl", "")
                item["teaExpUrl"] = zh_course.get("teaExpUrl", "")
                tea_schm_url = zh_course.get("teaSchmUrl", "")
                item["teaSchmUrl"] = tea_schm_url
                course_data["teaSchmUrl"] = tea_schm_url
                item["semQty"] = zh_course.get("smtQty", item["semQty"])
                item["core"] = 1 if zh_course.get("core", "") == "是" else 0
                item["lang"] = zh_course.get("langTpe", item["lang"])
                item["classroom"] = zh_course.get("subClassroom", item["classroom"])
                item["tranTpe"] = zh_course.get("tranTpe", item["tranTpe"])
                item["info"] = zh_course.get("info", item["info"])
                item["note"] = zh_course.get("note", item["note"])

            en_url = self.build_course_detail_url_en(course_id)
            # Add unique identifier for English URL too
            unique_en_url = f"{en_url}?_spider_req={self.api_request_count}_en"

            yield scrapy.Request(
                url=unique_en_url,
                callback=self.parse_course_detail_en,
                meta={**response.meta, "original_en_url": en_url},
                dont_filter=True,
            )

        except Exception as e:
            self.failed_requests += 1
            self.logger.error(f"✗ Error processing course detail {course_id}: {e}")

    def parse_course_detail_en(self, response):
        """Override to handle unique URLs and add debugging"""
        item = response.meta["item"]
        course_data = response.meta["course_data"]
        course_id = response.meta["course_id"]

        try:
            en_data = json.loads(response.text)
            if len(en_data) == 1:
                en_course = en_data[0]
                item["nameEn"] = en_course.get("subNam", "")
                item["teacherEn"] = en_course.get("teaNam", "")
                item["timeEn"] = en_course.get("sumkbTime", "")
                item["lmtKindEn"] = en_course.get("lmtKind", "")
                item["langEn"] = en_course.get("langTpe", "")
                item["classroomId"] = en_course.get("subClassroom", item["classroom"])
                item["tranTpeEn"] = en_course.get("tranTpe", "")
                item["infoEn"] = en_course.get("info", "")
                item["unitEn"] = en_course.get("subGde", "")
                item["noteEn"] = en_course.get("note", "")

            tea_schm_url = course_data.get("teaSchmUrl", "")
            item_tea_schm_url = item.get("teaSchmUrl", "")  # DEBUG

            final_tea_schm_url = item_tea_schm_url or tea_schm_url

            if final_tea_schm_url:
                yield scrapy.Request(
                    url=final_tea_schm_url,
                    callback=self.parse_syllabus,
                    meta={"item": item, "course_data": course_data},
                    dont_filter=True,
                )
            else:
                yield from self.process_course_item(item, course_data)

        except Exception as e:
            self.logger.error(f"✗ Error processing English detail for {course_id}: {e}")
            # Continue with syllabus or item processing even if EN parsing fails
            if course_data.get("teaSchmUrl"):
                yield scrapy.Request(
                    url=course_data["teaSchmUrl"],
                    callback=self.parse_syllabus,
                    meta={"item": item, "course_data": course_data},
                    dont_filter=True,
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

        if hasattr(self, "remaining_missing"):
            self.logger.info(
                f"Remaining unprocessed courses: {len(self.remaining_missing)}"
            )
            if self.remaining_missing:
                self.logger.warning("Courses not found via DP API:")
                for course in sorted(self.remaining_missing):
                    self.logger.warning(f"  - {course}")

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
            self.logger.info(f" Created {self.total_saved_courses} CourseLegacyItems")
        else:
            self.logger.warning(" No items were created")
