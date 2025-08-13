import scrapy
from NCCUCrawl.items import RateLegacyItem


class RateDeprecatedSpider(scrapy.Spider):
    name = "rate_deprecated"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.2,
    }

    def start_requests(self):
        """Load teacher data and start crawling"""

        teacher_list = {}

        all_semesters = ["1111", "1112"]

        for teacher_name, teacher_id in teacher_list.items():
            for semester in all_semesters:
                statistic_url = f"http://newdoc.nccu.edu.tw/teaschm/{semester}/statistic.jsp-tnum={teacher_id}.htm"
                yield scrapy.Request(
                    url=statistic_url,
                    callback=self.parse_teacher_courses,
                    meta={
                        "teacher_id": teacher_id,
                        "teacher_name": teacher_name,
                        "semester": semester,
                    },
                    encoding="big5",
                )

    def parse_teacher_courses(self, response):
        """Parse teacher's courses page to find available courses"""
        teacher_id = response.meta["teacher_id"]
        teacher_name = response.meta["teacher_name"]
        semester = response.meta["semester"]

        courses_table = response.css('table[border="1"]')
        if not courses_table:
            self.logger.warning(
                f"No courses table found for teacher {teacher_name} in semester {semester}"
            )
            return

        rows = courses_table.css("tr")

        for row in rows:
            tds = row.css("td")
            if len(tds) < 4:
                continue

            last_td_link = tds[-1].css("a::attr(href)").get()
            first_td_text = tds[0].css("::text").get()

            if last_td_link and first_td_text:
                try:
                    if int(first_td_text.strip()) > 100:
                        course_id_parts = []
                        for i in range(3):
                            if i < len(tds):
                                text = tds[i].css("::text").get()
                                if text:
                                    course_id_parts.append(text.strip())

                        if len(course_id_parts) == 3:
                            course_id = "".join(course_id_parts)

                            rate_url = f"http://newdoc.nccu.edu.tw/teaschm/{semester}/{last_td_link}"

                            yield scrapy.Request(
                                url=rate_url,
                                callback=self.parse_rate,
                                meta={
                                    "teacher_id": teacher_id,
                                    "teacher_name": teacher_name,
                                    "semester": semester,
                                    "course_id": course_id,
                                },
                            )
                except ValueError:
                    continue

    def parse_rate(self, response):
        """Parse teacher rating page"""
        teacher_id = response.meta["teacher_id"]
        course_id = response.meta["course_id"]

        rates_table = response.css('table[border="1"]')

        if rates_table:
            rows = rates_table.css("tr")

            for index, row in enumerate(rows):
                first_td = row.css("td::text").get()
                if first_td:
                    rate_text = first_td.strip()

                    yield RateLegacyItem(
                        courseId=course_id,
                        rowId=str(index),  # 使用 index 作為 rowId
                        teacherId=teacher_id,
                        content=rate_text,
                        contentEn="",
                    )
        else:
            self.logger.warning(f"No rate table found for course {course_id}")
