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
        self,
        semester: str,
        dp1: str,
        dp2: str,
        dp3: str,
        api_courses: List[Dict],
        search_level: str = "unknown",
    ) -> List[Dict]:
        missing_courses = []
        category_key = f"{dp1}-{dp2}-{dp3}" if dp1 or dp2 or dp3 else "∅-∅-∅"

        for course in api_courses:
            sub_num = course["subNum"]
            course_id = f"{semester}{sub_num}"

            if self.should_crawl_course(sub_num):
                course["_missing_reason"] = "in_csv_not_in_db"
                course["_full_course_id"] = course_id
                course["_search_level"] = search_level
                course["_category_key"] = category_key
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
            self.remaining_missing = self.missing_courses.copy()

            self.logger.info(
                f"Found {len(self.missing_courses)} missing courses to crawl"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize database comparator: {e}")
            self.comparator = None
            self.missing_courses = set()
            self.remaining_missing = set()  # when dp fails -> use subNum to crawl

        self.scheduled_courses: Set[str] = set()
        self.successfully_processed: Set[str] = set()

        self.api_request_count = 0
        self.detail_request_count = 0
        self.api_limit = 500
        self.total_existing_courses = (
            len(self.comparator.existing_courses) if self.comparator else 0
        )
        self.total_missing_courses = len(self.missing_courses)
        self.total_processed_courses = 0
        self.total_saved_courses = 0
        self.failed_requests = 0
        self.successful_detail_requests = 0

        self.hierarchical_stats = {
            "three_level": {
                "categories": 0,
                "courses": 0,
                "new_courses": 0,
                "missing_found": 0,
            },
            "two_level": {
                "categories": 0,
                "courses": 0,
                "new_courses": 0,
                "missing_found": 0,
            },
            "one_level": {
                "categories": 0,
                "courses": 0,
                "new_courses": 0,
                "missing_found": 0,
            },
            "zero_level": {
                "categories": 0,
                "courses": 0,
                "new_courses": 0,
                "missing_found": 0,
            },
        }

    def parse_units(self, response):
        """Override to use hierarchical search strategy"""
        units = json.loads(response.text)

        self.unit_mapping = {}
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
            yield from self.generate_smart_hierarchical_requests(units, sem)

    def generate_smart_hierarchical_requests(self, units, semester):
        """生成智能階層式搜尋請求，只針對可能包含缺失課程的分類"""

        self.logger.info("Starting smart hierarchical search...")
        self.logger.info(f"Looking for {len(self.remaining_missing)} missing courses")

        # 1. 三階層搜尋 (最精確)
        three_level_categories = self.get_three_level_categories(units)
        self.logger.info(
            f"Scheduling {len(three_level_categories)} three-level category searches"
        )

        for dp1, dp2, dp3 in three_level_categories:
            url = self.build_course_list(semester, dp1, dp2, dp3)
            yield scrapy.Request(
                url=url,
                callback=self.parse_smart_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": dp2,
                    "dp3": dp3,
                    "search_level": "three_level",
                },
                meta={"search_level": "three_level"},
                priority=100,
            )

        # 2. 二階層搜尋 (中等精確)
        two_level_categories = self.get_two_level_categories(units)
        self.logger.info(
            f"Scheduling {len(two_level_categories)} two-level category searches"
        )

        for dp1, dp2 in two_level_categories:
            url = self.build_course_list(semester, dp1, dp2, "")
            yield scrapy.Request(
                url=url,
                callback=self.parse_smart_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": dp2,
                    "dp3": "",
                    "search_level": "two_level",
                },
                meta={"search_level": "two_level"},
                priority=90,
            )
        # 3. 一階層搜尋 (粗略)
        one_level_categories = self.get_one_level_categories(units)
        self.logger.info(
            f"Scheduling {len(one_level_categories)} one-level category searches"
        )

        for dp1 in one_level_categories:
            url = self.build_course_list(semester, dp1, "", "")
            yield scrapy.Request(
                url=url,
                callback=self.parse_smart_course_list,
                cb_kwargs={
                    "semester": semester,
                    "dp1": dp1,
                    "dp2": "",
                    "dp3": "",
                    "search_level": "one_level",
                },
                meta={"search_level": "one_level"},
                priority=80,
            )
        # 4. 零階層搜尋 (全部課程)
        self.logger.info("Scheduling zero-level (全部課程) search")
        url = self.build_course_list(semester, "", "", "")
        yield scrapy.Request(
            url=url,
            callback=self.parse_smart_course_list,
            cb_kwargs={
                "semester": semester,
                "dp1": "",
                "dp2": "",
                "dp3": "",
                "search_level": "zero_level",
            },
            meta={"search_level": "zero_level"},
            priority=70,
        )

    def process_course_item(self, item, course_data):
        """Override to track actually saved items"""
        from NCCUCrawl.items import CourseLegacyItem

        sub_num = item.get("subNum")
        if sub_num:
            # 標記為成功處理
            self.successfully_processed.add(sub_num)
            # 從剩餘列表中移除
            self.remaining_missing.discard(sub_num)

            self.logger.debug(f"✓ Successfully processed course: {sub_num}")

        self.total_saved_courses += 1

        if isinstance(item, dict):
            yield CourseLegacyItem(**item)
        else:
            yield item

    def parse_smart_course_list(
        self, response, semester, dp1, dp2, dp3, search_level="unknown"
    ):
        """智能解析課程列表，結合去重邏輯和缺失課程檢查"""
        try:
            courses = json.loads(response.text)
            self.api_request_count += 1

            # 統計更新
            self.hierarchical_stats[search_level]["categories"] += 1
            self.hierarchical_stats[search_level]["courses"] += len(courses)

            # 建立分類鍵值
            if dp1 and dp2 and dp3:
                category_key = f"{dp1}-{dp2}-{dp3}"
                unit_info = self.unit_mapping.get(category_key, {})
            elif dp1 and dp2:
                category_key = f"{dp1}-{dp2}-∅"
                unit_info = self._find_unit_info_for_two_level(dp1, dp2)
            elif dp1:
                category_key = f"{dp1}-∅-∅"
                unit_info = self._find_unit_info_for_one_level(dp1)
            else:
                category_key = "∅-∅-∅"
                unit_info = {}

            if not self.comparator:
                self.logger.warning("No database comparator available")
                return

            # 檢查此分類中是否有我們需要的課程
            missing_courses = self.comparator.get_missing_courses_for_category(
                semester, dp1, dp2, dp3, courses, search_level
            )

            # 過濾掉已經排程的課程
            truly_missing = []
            already_scheduled = 0

            for course in missing_courses:
                sub_num = course["subNum"]
                if sub_num in self.scheduled_courses:
                    already_scheduled += 1
                    continue

                if sub_num in self.remaining_missing:
                    truly_missing.append(course)
                    self.scheduled_courses.add(sub_num)
            # 統計更新
            self.hierarchical_stats[search_level]["new_courses"] += len(truly_missing)
            self.hierarchical_stats[search_level]["missing_found"] += len(truly_missing)

            # 日誌輸出
            if truly_missing or already_scheduled > 0:
                self.logger.info(
                    f"[{search_level}] {category_key}: "
                    f"Total={len(courses)}, Missing={len(missing_courses)}, "
                    f"New={len(truly_missing)}, Scheduled={already_scheduled}"
                )

            # 處理真正需要的新課程
            for course in truly_missing:
                if self.detail_request_count >= self.api_limit:
                    self.logger.warning(
                        f"Detail request limit reached at {self.api_limit}"
                    )
                    break

                item = self.create_course_item(
                    course, semester, unit_info, dp1, dp2, dp3
                )
                course_id = f"{semester}{course['subNum']}"

                zh_url = self.build_course_detail_url_zh(course_id)
                unique_url = (
                    f"{zh_url}?_smart_req={self.detail_request_count}_{search_level}"
                )

                yield scrapy.Request(
                    url=unique_url,
                    callback=self.parse_course_detail_zh,
                    meta={
                        "item": item,
                        "course_data": course,
                        "course_id": course_id,
                        "semester": semester,
                        "dp1": dp1,
                        "dp2": dp2,
                        "dp3": dp3,
                        "search_level": search_level,
                        "category_key": category_key,
                        "sub_num": course["subNum"],
                        "original_url": zh_url,
                    },
                    dont_filter=True,
                    errback=self.handle_request_error,
                )

                self.detail_request_count += 1

        except json.JSONDecodeError as e:
            self.logger.error(
                f"[{search_level}] JSON parse error for {category_key}: {e}"
            )
        except Exception as e:
            self.logger.error(f"[{search_level}] Error processing {category_key}: {e}")

    def handle_request_error(self, failure):
        """Handle request failures"""
        self.failed_requests += 1
        course_id = failure.request.meta.get("course_id", "unknown")
        sub_num = failure.request.meta.get("sub_num", "unknown")

        # 如果請求失敗，將課程放回待處理列表
        if sub_num != "unknown":
            self.scheduled_courses.discard(sub_num)
            self.remaining_missing.add(sub_num)

        self.logger.error(f"✗ Request failed for course {course_id}: {failure}")

    def spider_idle(self):
        """當階層式搜尋完成後，直接爬取真正剩餘的課程"""

        # 計算真正剩餘的課程
        truly_remaining = (
            self.remaining_missing
            - self.scheduled_courses
            - self.successfully_processed
        )

        self.logger.info("=== Spider Idle Check ===")
        self.logger.info(f"Original missing: {len(self.missing_courses)}")
        self.logger.info(f"Scheduled: {len(self.scheduled_courses)}")
        self.logger.info(f"Successfully processed: {len(self.successfully_processed)}")
        self.logger.info(f"Truly remaining: {len(truly_remaining)}")

        if truly_remaining and self.detail_request_count < self.api_limit:
            self.logger.info(
                f"Starting direct crawl for {len(truly_remaining)} truly remaining courses"
            )

            requests_made = 0
            available_quota = self.api_limit - self.detail_request_count

            for sub_num in list(truly_remaining)[:available_quota]:
                semester = "1141"
                course_id = f"{semester}{sub_num}"

                # 標記為已排程
                self.scheduled_courses.add(sub_num)

                item = CourseLegacyItem(
                    id=course_id,
                    subNum=sub_num,
                    y=semester[:3],
                    s=semester[3],
                    name="",
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
                unique_url = f"{zh_url}?_direct_{requests_made}"

                course_data = {
                    "subNum": sub_num,
                    "is_direct_crawl": True,
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
                        "is_direct_crawl": True,
                        "sub_num": sub_num,
                    },
                    dont_filter=True,
                    errback=self.handle_request_error,
                )

                self.crawler.engine.crawl(request)
                self.detail_request_count += 1
                requests_made += 1

            if requests_made > 0:
                self.logger.info(f"Scheduled {requests_made} direct crawl requests")
                raise scrapy.exceptions.DontCloseSpider(
                    "Direct crawl requests scheduled"
                )
            else:
                self.logger.info("No additional direct crawl requests needed")
        else:
            if not truly_remaining:
                self.logger.info("All missing courses have been processed")
            else:
                self.logger.info(
                    f"API limit reached, {len(truly_remaining)} courses remain"
                )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)
        return spider

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
