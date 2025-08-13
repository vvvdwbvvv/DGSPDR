import scrapy
import json
import os
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
        """Start by getting course list and managing track"""
        # self.courses_list = db.get_this_semester_course(YEAR, SEM)
        
        self.courses_list = []
        
        # Start the teacher fetching process
        yield scrapy.Request(
            url="about:blank",  # dummy URL to start the process
            callback=self.start_teacher_process,
            dont_filter=True
        )

    def start_teacher_process(self, response):
        """Delete existing tracks and add new ones"""
        try:
            # Get existing tracks
            courses = self.user.get_track()
            
            # Delete existing tracks
            for course in courses:
                try:
                    course_id = str(course["subNum"])
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
            updated_courses = self.user.get_track()
            
            # Process each course to extract teacher information
            for course in updated_courses:
                yield from self.process_teacher_from_course(course)

        except Exception as e:
            self.logger.error(f"Error in teacher process: {e}")

    def process_teacher_from_course(self, course):
        """Process teacher information from course data"""
        try:
            teacher_stat_url = str(course["teaStatUrl"])
            teacher_name = str(course["teaNam"])
            
            if teacher_stat_url.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/statisticAll.jsp"
            ):
                # Direct teacher statistics URL
                teacher_id = teacher_stat_url.split(
                    f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/statisticAll.jsp-tnum="
                )[1].split(".htm")[0]
                
                self.teacher_id_dict[teacher_name] = teacher_id
                
                # Yield teacher item
                yield TeacherLegacyItem(
                    id=teacher_id,
                    name=teacher_name
                )
                
            elif teacher_stat_url.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/set20.jsp"
            ):
                # Need to scrape the set20.jsp page for teacher list
                converted_url = teacher_stat_url.replace(
                    "newdoc.nccu.edu.tw", "140.119.229.20"
                ).replace("https://", "http://")
                
                yield scrapy.Request(
                    url=converted_url,
                    callback=self.parse_teacher_list,
                    meta={
                        'teacher_name': teacher_name,
                        'original_url': teacher_stat_url
                    },
                    encoding='big5'
                )
                
        except Exception as e:
            self.logger.error(f"Error processing teacher from course: {e}")

    def parse_teacher_list(self, response):
        """Parse teacher list from set20.jsp page"""
        teacher_name = response.meta.get('teacher_name')
        
        try:
            # Find all rows with teacher information
            rows = response.css('tr')
            
            for row in rows:
                tds = row.css('td')
                if len(tds) >= 2:
                    # Check if second td has a link
                    link = tds[1].css('a::attr(href)').get()
                    if link and 'statisticAll.jsp-tnum=' in link:
                        teacher_name_from_row = tds[0].css('::text').get()
                        if teacher_name_from_row:
                            teacher_name_from_row = teacher_name_from_row.strip()
                            
                            # Extract teacher ID from link
                            teacher_id = link.split('statisticAll.jsp-tnum=')[1].split('.htm')[0]
                            
                            self.teacher_id_dict[teacher_name_from_row] = teacher_id
                            
                            # Yield teacher item
                            yield TeacherLegacyItem(
                                id=teacher_id,
                                name=teacher_name_from_row
                            )
                            
        except Exception as e:
            self.logger.error(f"Error parsing teacher list: {e}")

    def closed(self, reason):
        """Clean up tracks when spider closes"""
        try:
            # Delete all tracks when done
            courses = self.user.get_track()
            for course in courses:
                try:
                    course_id = str(course["subNum"])
                    self.user.delete_track(course_id)
                    self.logger.info(f"Final cleanup - deleted track: {course_id}")
                except Exception as e:
                    self.logger.error(f"Error in final cleanup: {e}")
                    continue
        except Exception as e:
            self.logger.error(f"Error in spider cleanup: {e}")