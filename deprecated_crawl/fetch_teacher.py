import logging
import requests
import tqdm
from bs4 import BeautifulSoup
from time import sleep
import datetime

import common


def delete_existing_tracks(user, courses):
    """Delete existing courses"""
    if not courses:
        return

    tqdmCourses = tqdm.tqdm(courses, leave=False, desc="Deleting Existing Tracks")
    for course in tqdmCourses:
        try:
            sleep(0.2)
            courseId = str(course["subNum"])
            tqdmCourses.set_postfix_str(f"Deleting {courseId}")
            user.delete_track(courseId)
        except Exception as e:
            logging.error(f"Error deleting track for course {courseId}: {e}")
            continue


def add_courses_to_track(user, coursesList):
    """Add courses to track"""
    tqdmCourses = tqdm.tqdm([*set(coursesList)], leave=False, desc="Adding to Tracks")
    for courseId in tqdmCourses:
        try:
            sleep(0.2)
            tqdmCourses.set_postfix_str(f"Adding {courseId}")
            user.add_track(courseId)
        except Exception as e:
            logging.error(f"Error adding track for course {courseId}: {e}")
            continue


def parse_teacher_ids(courses, db):
    """Parse id and save to db"""
    teacherIdDict = {}
    tqdmCourses = tqdm.tqdm(courses, leave=False, desc="Parsing Teacher IDs")

    for course in tqdmCourses:
        try:
            teacherStatUrl = str(course["teaStatUrl"])
            teacherName = str(course["teaNam"])
            tqdmCourses.set_postfix_str(f"Processing {teacherName}")

            if teacherStatUrl.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{common.YEAR_SEM}/statisticAll.jsp"
            ):
                teacherId = teacherStatUrl.split("/statisticAll.jsp-tnum=")[1].split(
                    ".htm"
                )[0]
                teacherIdDict[teacherName] = teacherId
                db.add_teacher(teacherId, teacherName)

            elif teacherStatUrl.startswith(
                f"https://newdoc.nccu.edu.tw/teaschm/{common.YEAR_SEM}/set20.jsp"
            ):
                res = requests.get(
                    teacherStatUrl.replace(
                        "newdoc.nccu.edu.tw", "140.119.229.20"
                    ).replace("https://", "http://"),
                    timeout=10,
                )
                res.raise_for_status()
                sleep(0.2)
                soup = BeautifulSoup(
                    res.content.decode("big5").encode("utf-8"), "html.parser"
                )
                rows = soup.find_all("tr")
                for row in (
                    x.find_all("td") for x in rows if x.find_all("td")[1].find("a")
                ):
                    teacherName = str(row[0].text)
                    teacherId = (
                        row[-1]
                        .find("a")["href"]
                        .split("statisticAll.jsp-tnum=")[1]
                        .split(".htm")[0]
                    )
                    teacherIdDict[teacherName] = teacherId
                    db.add_teacher(teacherId, teacherName)

        except Exception as e:
            logging.error(f"Error processing course {course}: {e}")
            continue

    return teacherIdDict


def fetch_teacher(db, user, args):
    """Fetches and processes teacher data based on the provided arguments.

    Args:
        db: Database instance.
        user: User instance.
        args: Command-line arguments.
    """
    if args.command not in ["teacher", "all"]:
        print("Skipping Fetch TeacherId")
        return

    try:
        year = common.YEAR
        sem = common.SEM

        coursesList = db.get_this_semester_course(year, sem)

        existingCourses = user.get_track()
        delete_existing_tracks(user, existingCourses)

        add_courses_to_track(user, coursesList)

        trackedCourses = user.get_track()

        teacherIdDict = parse_teacher_ids(trackedCourses, db)

        delete_existing_tracks(user, trackedCourses)

        print(f"Fetch TeacherId done at {datetime.datetime.now()}")

    except Exception as e:
        logging.error(f"Error fetching teachers: {e}")
