import requests
import tqdm
import logging
import datetime
from time import sleep
from fetch_description import fetch_description

def fetch_classes(args, all_semesters, YEAR_SEM, db, fetch_description):
    """Fetches and processes course data based on the provided arguments.

    Args:
        args: Command-line arguments containing options like `course` and `fast`.
        all_semesters: List of semesters to fetch courses for.
        YEAR_SEM: The current semester identifier.
        db: Database instance to store course data.
        fetch_description: Function to fetch detailed course descriptions.
    """
    if not args.course:
        print("Skipping Fetch Class")
        return

    try:
        #Identify units and categories
        response = requests.get("https://qrysub.nccu.edu.tw/assets/api/unit.json")
        response.raise_for_status()
        units = response.json()

        # Build category combinations
        categories = [
            {"dp1": dp1["utCodL1"], "dp2": dp2["utCodL2"], "dp3": dp3["utCodL3"]}
            for dp1 in units if dp1["utCodL1"] != "0"
            for dp2 in dp1["utL2"] if dp2["utCodL2"] != "0"
            for dp3 in dp2["utL3"] if dp3["utCodL3"] != "0"
        ]

        #Fetch courses
        courses_list = []
        tqdm_categories = tqdm.tqdm(categories, leave=False, desc="Processing Categories")

        for category in tqdm_categories:
            tqdm_categories.set_postfix_str(f"Category: {category}")

            semesters = [all_semesters[-1]] if args.fast else tqdm.tqdm(all_semesters, leave=False, desc="Processing Semesters")

            for semester in semesters:
                if not args.fast:
                    semesters.set_postfix_str(f"Processing: {semester}")
                try:
                    sleep(0.1)
                    url = f"https://es.nccu.edu.tw/course/zh-TW/:sem={semester} :dp1={category['dp1']} :dp2={category['dp2']} :dp3={category['dp3']}"
                    response = requests.get(url)
                    response.raise_for_status()
                    courses = response.json()

                    if len(courses) >= 500:
                        raise ValueError(f"Category {category} too large to process.")

                    # Add current semester courses to courses_list
                    if semester == YEAR_SEM:
                        courses_list += [course["subNum"] for course in courses]

                    # Write courses to the database
                    for course in tqdm.tqdm(courses, leave=False, desc="Processing Courses"):
                        course_id = f"{semester}{course['subNum']}"
                        # Uncomment the next line if database check is needed
                        # if db.isCourseExist(course_id, category):
                        #     continue
                        details = fetch_description(course_id)
                        db.add_course(
                            details["qrysub"],
                            details["qrysubEn"],
                            category["dp1"],
                            category["dp2"],
                            category["dp3"],
                            "".join(details["description"]),
                            "".join(details["objectives"]),
                        )
                except Exception as e:
                    logging.error(f"Error processing category {category}, semester {semester}: {e}")

        logging.debug(f"Fetched courses: {courses_list}")
        print(f"Fetch Class done at {datetime.datetime.now()}")

    except Exception as e:
        logging.error(f"Error fetching classes: {e}")
