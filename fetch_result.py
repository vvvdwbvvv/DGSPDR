import csv
import requests
import os
import json
from tqdm import tqdm
from common import courseresult_csv, COURSERESULT_YEARSEM


def ensure_directory_exists(path: str):
    os.makedirs(path, exist_ok=True)


def load_or_initialize_json(filepath: str):
    """Load JSON data from a file or initialize as an empty list."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []


def save_json(filepath: str, data: list):
    """Save data to a JSON file."""
    with open(filepath, "w") as file:
        json.dump(data, file)

def process_course(row, sem: str):
    """Process a single course entry."""
    course_id = str(row[0])
    try:
        response = requests.get(
            f"https://es.nccu.edu.tw/course/zh-TW/:sem={sem}%20{course_id}%20/"
        )
        response.raise_for_status()
        course_data = response.json()

        result = {
            "yearsem": sem,
            "time": course_data[0]["subTime"],
            "courseId": course_id,
            "studentLimit": str(row[3]),
            "studentCount": str(row[4]),
            "lastEnroll": str(row[5]) if row[5] else "-1",
        }

        teacher_name = course_data[0]["teaNam"]
        course_name = course_data[0]["subNam"]
        data_path = f"./result/{teacher_name}/{course_name}/courseResult"
        ensure_directory_exists(data_path)

        # Filepath for the JSON
        json_file = f"{data_path}/{sem}.json"

        # Load existing data, append new result, and save
        existing_data = load_or_initialize_json(json_file)
        existing_data.append(result)
        save_json(json_file, existing_data)

    except requests.RequestException as err:
        print(f"Failed to fetch data for course {course_id} in {sem}: {err}")
    except (IndexError, KeyError) as err:
        print(f"Unexpected data structure for course {course_id} in {sem}: {err}")
    except Exception as err:
        print(f"Error processing course {course_id} in {sem}: {err}")


def fetch_result():
    for sem in COURSERESULT_YEARSEM:
        # Get total rows for progress tracking
        csv_file = f"./data/{courseresult_csv(sem)}"
        try:
            row_count = sum(1 for _ in open(csv_file, "r"))
        except FileNotFoundError:
            print(f"CSV file for {sem} not found. Skipping.")
            continue

        with open(csv_file, "r") as file:
            reader = tqdm(csv.reader(file), total=row_count, desc=f"Processing {sem}")
            for row in reader:
                process_course(row, sem)
