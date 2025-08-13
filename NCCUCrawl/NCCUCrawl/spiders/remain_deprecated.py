import scrapy
from NCCUCrawl.items import CourseRemainItem
from .courses_deprecated import CoursesLegacySpider


class CourseRemainLegacySpider(CoursesLegacySpider):  # implement the course spider
    name = "remain_deprecated"
#TODO: adjust the name
    PROPERTY_NAME = {
        "專業基礎(開放系所)人數": "origin",
        "其他系所": "other_dept",
        "總人數": "all",
        "本系本班Dept./Class": "origin",
        "本系非本班同年級Other Classes in Dept., Same Year": "same_grade",
        "本系非本班不同年級Other Classes in Dept., Dif. Year": "diff_grade",
        "輔系Minor": "minor",
        "雙主修Double-Major": "double_major",
        "全系Dept.": "origin",
        "本院非本系Other Depts. in the College": "other_dept_in_college",
        "非本院Other Colleges": "other_college",
        "學分學程": "program",
        "全校All Colleges": "all",
        "本學程開課年級（含）以上Same Year (and above) in the Program": "same_grade_and_above",
        "本學程其他低年級Year Below you in the Program": "lower_grade",
        "本院非學程限制人數Maximum Limits for Other Programs in the College": "other_program",
        "外院限制人數Maximum Limits for Other Colleges": "other_college",
        "總限制人數Overall Maximum Limits": "all",
    }

    ROW_NAME = {
        "限制人數 / Maximum limit": "maximum",
        "選課人數 / Number Registered": "registered",
        "餘額 / Number of Available Spaces": "remained",
    }

    def process_course_item(self, item, course_data):
        """Override to add remain functionality"""
        remain_url = course_data.get("subRemainUrl")
        if remain_url:
            yield scrapy.Request(
                url=remain_url,
                callback=self.parse_remain,
                meta={"course_id": item["id"]},
            )
        else:
            self.logger.warning(
                f"No remain URL found for course {item['id']} - skipping remain data extraction."
            )

    def parse_remain(self, response):
        """
        解析課程餘額頁面，提取所有資訊並產出 CourseRemainItem。
        """
        course_id = response.meta["course_id"]
        try:
            item_data = self.create_default_remain_item(course_id)._values

            basic_info = self.extract_basic_info(response)
            item_data.update(basic_info)

            table_info = self.extract_limit_table(response)
            item_data.update(table_info)

            yield CourseRemainItem(**item_data)

        except Exception as e:
            self.logger.error(f"Error parsing remain page for {course_id}: {e}")
            yield self.create_default_remain_item(course_id)

    def extract_basic_info(self, response):
        """提取基本資訊（加簽、候補）"""
        info = {"signable": False, "waiting_count": 0}
        try:
            signable_text = response.css("#Open_to_signable_addingL::text").get()
            if signable_text:
                info["signable"] = signable_text.strip() == "是"

            rows = response.css("div.maintain_profile_content_table tr")
            if len(rows) > 6:
                wait_text = rows[6].css("td a::text").get()
                if wait_text and wait_text.strip().isdigit():
                    info["waiting_count"] = int(wait_text.strip())
        except Exception as e:
            self.logger.warning(f"Could not extract basic info: {e}")
        return info

    def extract_limit_table(self, response):
        """提取限制人數表格"""
        table_data = {}
        try:
            rows = response.css("table#tclmtcntGV tr")
            if len(rows) <= 1:
                return table_data

            headers = [
                h.strip()
                for h in rows[0].css("td::text, th::text").getall()
                if h.strip()
            ]

            for row in rows[1:]:
                cells = row.css("td")
                if not cells:
                    continue

                row_name_text = cells[0].css("::text").get("").strip()
                if row_name_text not in self.ROW_NAME:
                    continue

                row_key_suffix = self.ROW_NAME[row_name_text]  # e.g., "maximum"

                for i, cell in enumerate(cells[1:], 1):
                    if i >= len(headers):
                        continue

                    header_text = headers[i]
                    if header_text not in self.PROPERTY_NAME:
                        continue

                    prop_key_prefix = self.PROPERTY_NAME[header_text]  # e.g., "origin"
                    final_key = (
                        f"{prop_key_prefix}_{row_key_suffix}"  # e.g., "origin_maximum"
                    )

                    cell_text = cell.css("::text").get("").strip()
                    if cell_text.isdigit():
                        table_data[final_key] = int(cell_text)

        except Exception as e:
            self.logger.warning(f"Could not extract limit table: {e}")
        return table_data

    def create_default_remain_item(self, course_id):
        fields = CourseRemainItem.fields.keys()
        default_data = {field: None for field in fields}

        default_data.update(
            {
                "course_id": course_id,
                "signable": False,
                "waiting_count": 0,
            }
        )
        return CourseRemainItem(**default_data)
