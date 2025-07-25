# 模擬測試的環境設置與代碼結構
import logging
import sys
from unittest.mock import Mock
from time import sleep
import tqdm

# 模擬 DB 類
class MockDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_this_semester_course(self, year, sem):
        # 模擬返回課程清單
        return [{"course_id": "101", "subNum": "C101"}, {"course_id": "102", "subNum": "C102"}]

    def add_teacher(self, teacher_id, teacher_name):
        logging.info(f"Teacher added to DB: {teacher_name} ({teacher_id})")

# 模擬 User 類
class MockUser:
    def __init__(self):
        self.tracks = []

    def get_track(self):
        # 模擬返回當前追蹤的課程
        return [{"subNum": "C101"}, {"subNum": "C102"}]

    def delete_track(self, course_id):
        logging.info(f"Deleted track: {course_id}")
        self.tracks = [t for t in self.tracks if t["subNum"] != course_id]

    def add_track(self, course_id):
        logging.info(f"Added track: {course_id}")
        self.tracks.append({"subNum": course_id})

# 模擬 fetch_teacher 函數
def fetch_teacher(db, user, args):
    logging.info("Fetching teacher data...")
    courses_list = db.get_this_semester_course("112", "1")
    existing_tracks = user.get_track()

    # 刪除現有追蹤課程
    tqdm_courses = tqdm.tqdm(existing_tracks, desc="Deleting Tracks", leave=False)
    for course in tqdm_courses:
        sleep(0.1)
        user.delete_track(course["subNum"])

    # 添加課程到追蹤清單
    tqdm_courses = tqdm.tqdm(courses_list, desc="Adding Tracks", leave=False)
    for course in tqdm_courses:
        sleep(0.1)
        user.add_track(course["subNum"])

    # 模擬解析教師 ID（省略實際 URL 請求）
    tracked_courses = user.get_track()
    teacher_id_dict = {}
    tqdm_courses = tqdm.tqdm(tracked_courses, desc="Parsing Teacher IDs", leave=False)
    for course in tqdm_courses:
        sleep(0.1)
        teacher_id = f"T{course['subNum']}"
        teacher_name = f"Teacher_{course['subNum']}"
        teacher_id_dict[teacher_name] = teacher_id
        db.add_teacher(teacher_id, teacher_name)

    logging.info("Fetch TeacherId done.")

# 測試運行的主函數
def main():
    # 配置日誌
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # 初始化模擬對象
    db = MockDB("mock_database.db")
    user = MockUser()

    # 模擬命令行參數
    args = Mock(command="teacher")

    # 測試 fetch_teacher 函數
    fetch_teacher(db, user, args)

# 運行主函數進行測試
main()