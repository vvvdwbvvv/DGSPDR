import scrapy
from dotenv import load_dotenv
from NCCUCrawl.items import TeacherLegacyItem
from NCCUCrawl.user import User

load_dotenv()


class TeacherDeprecatedSpider(scrapy.Spider):
    name = "teacher_deprecated"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.2,
    }

    def __init__(self):
        super().__init__()
        self.user = User()
        self.teacher_id_dict = {}
        self.courses_list = []
        self.YEAR_SEM = "1141"

    def start_requests(self):
        yield from self.start_teacher_process(response=None)

    async def start(self):
        for req in self.start_teacher_process(response=None):
            yield req

    def start_teacher_process(self, response):
        # Ensure we have a valid auth token before hitting tracing APIs
        auth = getattr(self.user, "auth", None)
        token = getattr(auth, "token", None)
        if not token or str(token).upper() == "ERROR":
            dbg = getattr(auth, "debug", "") if auth else ""
            if dbg:
                self.logger.error(f"Authentication unavailable; debug: {dbg}")
            else:
                self.logger.error("Authentication unavailable; skipping teacher process")
            return

        # Get existing tracks
        try:
            courses = self.user.get_track()
        except Exception as e:
            self.logger.error(f"Failed to fetch tracks: {e}")
            return

        # Delete existing tracks
        for course in courses or []:
            try:
                course_id = str(course.get("subNum"))
                if not course_id:
                    continue
                self.user.delete_track(course_id)
                self.logger.info(f"Pre-deleted track: {course_id}")
            except Exception as e:
                self.logger.error(f"Error deleting track: {e}")
                continue

        # Add courses to track list
        unique_courses = list(set(self.courses_list))
        for course_id in unique_courses:
            try:
                self.user.add_track(course_id)
                self.logger.info(f"Added track: {course_id}")
            except Exception as e:
                self.logger.error(f"Error adding track: {e}")
                continue

        # Get updated track list to parse teacher info
        try:
            updated_courses = self.user.get_track()
        except Exception as e:
            self.logger.error(f"Failed to fetch updated tracks: {e}")
            return

        # Process each course to extract teacher information
        for course in updated_courses or []:
            yield from self.process_teacher_from_course(course)

    def process_teacher_from_course(self, course):
        """Process teacher information from course data"""
        try:
            teacher_stat_url = str(course["teaStatUrl"])
            teacher_name = str(course["teaNam"])

            if teacher_stat_url.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/statisticAll.jsp"
            ):
                teacher_id = teacher_stat_url.split(
                    f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/statisticAll.jsp-tnum="
                )[1].split(".htm")[0]

                self.teacher_id_dict[teacher_name] = teacher_id
                yield TeacherLegacyItem(id=teacher_id, name=teacher_name)

            elif teacher_stat_url.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/set20.jsp"
            ):
                converted_url = teacher_stat_url.replace(
                    "newdoc.nccu.edu.tw", "140.119.229.20"
                ).replace("https://", "http://")

                yield scrapy.Request(
                    url=converted_url,
                    callback=self.parse_teacher_list,
                    meta={"teacher_name": teacher_name, "original_url": teacher_stat_url},
                    encoding="big5",
                )
        except Exception as e:
            self.logger.error(f"Error processing teacher from course: {e}")

    def parse_teacher_list(self, response):
        """Parse teacher list from set20.jsp page"""
        try:
            rows = response.css("tr")
            for row in rows:
                tds = row.css("td")
                if len(tds) >= 2:
                    link = tds[1].css("a::attr(href)").get()
                    if link and "statisticAll.jsp-tnum=" in link:
                        teacher_name_from_row = (tds[0].css("::text").get() or "").strip()
                        teacher_id = link.split("statisticAll.jsp-tnum=")[1].split(".htm")[0]
                        if teacher_name_from_row and teacher_id:
                            self.teacher_id_dict[teacher_name_from_row] = teacher_id
                            yield TeacherLegacyItem(id=teacher_id, name=teacher_name_from_row)
        except Exception as e:
            self.logger.error(f"Error parsing teacher list: {e}")

    def closed(self, reason):
        """Clean up tracks when spider closes"""
        try:
            auth = getattr(self.user, "auth", None)
            token = getattr(auth, "token", None)
            if not token or str(token).upper() == "ERROR":
                self.logger.info("Skip track cleanup: no auth token available")
                return

            courses = self.user.get_track()
            for course in courses or []:
                try:
                    course_id = str(course.get("subNum"))
                    if not course_id:
                        continue
                    self.user.delete_track(course_id)
                    self.logger.info(f"Final cleanup - deleted track: {course_id}")
                except Exception as e:
                    self.logger.error(f"Error in final cleanup: {e}")
                    continue
        except Exception as e:
            self.logger.error(f"Error in spider cleanup: {e}")