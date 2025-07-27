import scrapy
from NCCUCrawl.items import CourseRemainItem
from .courses import CoursesSpider


class CourseRemainSpider(CoursesSpider):
    name = "remain"

    # mapping for property names in the remain table
    PROPERTY_NAME = {
        "專業基礎(開放系所)人數": "origin",
        "其他系所": "otherDept",
        "總人數": "all",
        "本系本班Dept./Class": "origin",
        "本系非本班同年級Other Classes in Dept., Same Year": "sameGrade",
        "本系非本班不同年級Other Classes in Dept., Dif. Year": "diffGrade",
        "輔系Minor": "minor",
        "雙主修Double-Major": "doubleMajor",
        "全系Dept.": "origin",
        "本院非本系Other Depts. in the College": "otherDeptInCollege",
        "非本院Other Colleges": "otherCollege",
        "學分學程": "program",
        "全校All Colleges": "all",
        "本學程開課年級（含）以上Same Year (and above) in the Program": "sameGradeAndAbove",
        "本學程其他低年級Year Below you in the Program": "lowerGrade",
        "本院非學程限制人數Maximum Limits for Other Programs in the College": "otherProgram",
        "外院限制人數Maximum Limits for Other Colleges": "otherCollege",
        "總限制人數Overall Maximum Limits": "all",
    }

    ROW_NAME = {
        "限制人數 / Maximum limit": "Limit",
        "選課人數 / Number Registered": "Registered",
        "餘額 / Number of Available Spaces": "Available",
    }

    def process_course_item(self, item, course_data):
        """Override to add remain functionality"""
        yield item

        remain_url = course_data.get("subRemainUrl")
        if remain_url:
            yield scrapy.Request(
                url=remain_url,
                callback=self.parse_remain,
                meta={
                    "course_id": item["id"],
                    "course_name": item["name"],
                    "semester": item["year"] + item["semester"],
                    "sub_num": item["sub_num"],
                },
            )
        else:
            self.logger.warning(
                f"No remain URL found for course {item['id']} - skipping remain data extraction."
            )

    def parse_remain(self, response):
        course_id = response.meta["course_id"]
        course_name = response.meta["course_name"]
        semester = response.meta["semester"]
        sub_num = response.meta["sub_num"]

        # initialize result dictionary
        result = {
            prop + row: None
            for prop in self.PROPERTY_NAME.values()
            for row in self.ROW_NAME.values()
        }

        try:
            self.extract_basic_remain_info(response, result, course_id)
            self.extract_limit_table(response, result)

            item = CourseRemainItem(
                course_id=course_id,
                course_name=course_name,
                semester=semester,
                sub_num=sub_num,
                signable_adding=result.get("signableAdding", False),
                waiting_list=result.get("waitingList", 0),
                **{
                    k: v
                    for k, v in result.items()
                    if k not in ["signableAdding", "waitingList"]
                },
            )

            yield item

        except Exception as e:
            self.logger.error(f"Error parsing remain page for {course_id}: {e}")
            yield CourseRemainItem(
                course_id=course_id,
                course_name=course_name,
                semester=semester,
                sub_num=sub_num,
                signable_adding=False,
                waiting_list=0,
            )

    def extract_basic_remain_info(self, response, result, course_id):
        """基本餘額資訊"""
        table_rows = response.css("div.maintain_profile_content_table tr")

        if len(table_rows) > 6:
            # 是否開放加簽
            open_to_signable_adding = table_rows[5].css("td::text").getall()
            if len(open_to_signable_adding) > 1:
                result["signableAdding"] = open_to_signable_adding[1].strip() == "是"

            # 候補人數
            waiting_list_element = table_rows[6].css("td a::text").get()
            if waiting_list_element:
                waiting_list_text = waiting_list_element.strip()
                result["waitingList"] = (
                    int(waiting_list_text)
                    if waiting_list_text.isdigit()
                    else waiting_list_text
                )
            else:
                result["waitingList"] = 0
                self.logger.warning(
                    f"No waiting list information found for course {course_id}."
                )

    def extract_limit_table(self, response, result):
        """限制人數表格"""
        limit_table = response.css("table#tclmtcntGV tr")

        if len(limit_table) > 1:
            # 提取header
            headers = []
            header_cells = limit_table[0].css("td, th")
            for cell in header_cells:
                header_text = cell.css("::text").get()
                if header_text and header_text.strip():
                    headers.append(header_text.strip())
                else:
                    headers.append("nil")

            for row in limit_table[1:]:
                cells = row.css("td")
                if len(cells) > 0:
                    row_name = cells[0].css("::text").get()
                    if row_name and row_name.strip() in self.ROW_NAME:
                        row_key = self.ROW_NAME[row_name.strip()]
                    else:
                        self.logger.warning(
                            f"Unknown row name: {row_name}. Skipping this row."
                        )

                        for i, cell in enumerate(cells[1:], 1):
                            if i < len(headers):
                                header = headers[i]
                                if header in self.PROPERTY_NAME:
                                    prop_key = self.PROPERTY_NAME[header]
                                    cell_text = cell.css("::text").get()
                                    if cell_text:
                                        cell_value = cell_text.strip()
                                        result[prop_key + row_key] = (
                                            int(cell_value)
                                            if cell_value.isdigit()
                                            else cell_value
                                        )
                                    else:
                                        self.logger.warning(
                                            f"Empty cell for {header} in row {row_name}. Skipping this cell."
                                        )
                                else:
                                    self.logger.warning(
                                        f"Unknown header: {header}. Skipping this cell."
                                    )
