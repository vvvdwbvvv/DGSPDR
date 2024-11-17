from bs4 import BeautifulSoup
import re
import requests
import logging


def fetch_description(course_id: str):
    """Fetches the description and objectives of a course based on its ID.

    Args:
        course_id (str): The 13-character course ID.

    Returns:
        dict: A dictionary containing course descriptions, objectives, and details.
    """
    if len(course_id) != 13:
        raise ValueError("Wrong courseId format. It must be 13 characters.")

    result = {
        "description": [],
        "objectives": [],
        "qrysub": {},
    }

    try:
        # Fetch course details in Chinese
        response = requests.get(f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/")
        response.raise_for_status()
        course_details = response.json()
        if len(course_details) != 1:
            raise ValueError("No matched course found (Chinese).")
        result["qrysub"] = course_details[0]

        # Fetch course details in English
        response = requests.get(f"http://es.nccu.edu.tw/course/en/{course_id}/")
        response.raise_for_status()
        course_details_en = response.json()
        if len(course_details_en) != 1:
            raise ValueError("No matched course found (English).")
        result["qrysubEn"] = course_details_en[0]

        # Get the teacher scheme URL and normalize the protocol
        location = str(result["qrysub"]["teaSchmUrl"]).replace("https://", "http://")

        # Fetch the teacher's page content
        response = requests.get(location)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        is_old_system = soup.find("title").text == "教師資訊整合系統"

        if is_old_system:
            # Parse the old system format
            parse_old_system(soup, result)
        else:
            # Parse the new system format
            parse_new_system(soup, result)

    except Exception as e:
        logging.error(f"Error fetching course details for {course_id}")
        logging.error(e)

    return result


def parse_old_system(soup, result):
    """Parses the old system's format for course details."""
    try:
        contents = soup.find("div", {"class": "accordionPart"}).find_all("span")
        parse_content(contents[0].find("div", {"class": "qa_content"}), result["description"])
        parse_content(contents[1].find("div", {"class": "qa_content"}), result["objectives"])
    except AttributeError:
        logging.error("Error parsing old system format.")


def parse_new_system(soup, result):
    """Parses the new system's format for course details."""
    try:
        # Parse syllabus description
        description_title = soup.find("div", {"class": "col-sm-7 sylview--mtop col-p-6"}).find("h2", {"class": "text-primary"})
        descriptions = description_title.find_next_siblings(True)
        for description in descriptions:
            if description.attrs and description.attrs.get("class") == ["row", "sylview-mtop", "fa-border"]:
                break
            parse_content(description, result["description"])

        # Parse syllabus objectives
        objectives_section = soup.find("div", {"class": "container sylview-section"}).select_one(".col-p-8")
        parse_content(objectives_section, result["objectives"])
    except AttributeError:
        logging.error("Error parsing new system format.")


def parse_content(content, target_list):
    """Parses and cleans content, appending results to a target list."""
    if not content:
        return
    for line in [x for x in re.split(r'[\n\r]+', content.get_text(strip=True)) if x.strip()]:
        target_list.append(line)


if __name__ == "__main__":
    logging.basicConfig(
        filename="fetch_description.log",
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    course_id = "1131000219521"
    result = fetch_description(course_id)
    print(result)
