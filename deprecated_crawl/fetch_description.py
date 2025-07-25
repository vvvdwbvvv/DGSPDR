from bs4 import BeautifulSoup
import re
import requests
import logging

def fetch_description(course_id: str) -> dict:
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
        "qrysubEn": {}
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
        location = str(result["qrysub"].get("teaSchmUrl", "")).replace("https://", "http://")

        if not location:
            raise ValueError("No teacher scheme URL found.")

        # Fetch the teacher's page content
        response = requests.get(location)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        is_old_system = soup.find("title").text.strip() == "教師資訊整合系統"

        if is_old_system:
            # Parse the old system format
            parse_old_system(soup, result)
        else:
            # Parse the new system format
            parse_new_system(soup, result)

    except Exception as e:
        logging.error(f"Error fetching course details for {course_id}: {e}")

    return result


def parse_old_system(soup: BeautifulSoup, result: dict):
    """Parses the old system's format for course details."""
    try:
        contents = soup.find("div", {"class": "accordionPart"}).find_all("span")
        if len(contents) < 2:
            raise ValueError("Insufficient content in old system format.")
        parse_content(contents[0].find("div", {"class": "qa_content"}), result["description"])
        parse_content(contents[1].find("div", {"class": "qa_content"}), result["objectives"])
    except AttributeError as e:
        logging.error(f"Error parsing old system format: {e}")
    except ValueError as e:
        logging.error(f"Parsing error: {e}")


def parse_new_system(soup: BeautifulSoup, result: dict):
    """Parses the new system's format for course details."""
    try:
        # Parse syllabus description
        description_section = soup.find("div", {"class": "col-sm-7 sylview--mtop col-p-6"})
        if not description_section:
            raise ValueError("Description section not found in new system format.")
        description_title = description_section.find("h2", {"class": "text-primary"})
        descriptions = description_title.find_next_siblings(True)
        for description in descriptions:
            if description.attrs and description.attrs.get("class") == ["row", "sylview-mtop", "fa-border"]:
                break
            parse_content(description, result["description"])

        # Parse syllabus objectives
        objectives_section = soup.find("div", {"class": "container sylview-section"}).select_one(".col-p-8")
        parse_content(objectives_section, result["objectives"])
    except AttributeError as e:
        logging.error(f"Error parsing new system format: {e}")
    except ValueError as e:
        logging.error(f"Parsing error: {e}")


def parse_content(content, target_list: list):
    """Parses and cleans content, appending results to a target list."""
    if not content:
        return
    for line in [x for x in re.split(r'[\n\r]+', content.get_text(strip=True)) if x.strip()]:
        target_list.append(line)


if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/fetch_description.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    course_id = "1131000219521"
    result = fetch_description(course_id)
    print(result)