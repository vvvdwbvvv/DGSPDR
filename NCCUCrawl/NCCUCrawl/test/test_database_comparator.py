# tests/test_database_comparator.py
import os 
import sys
import sqlite3
import csv
from pathlib import Path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from NCCUCrawl.spiders.courses_deprecated_patch import DatabaseComparator


def make_temp_db(db_path: Path, subnums):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS course_legacy (subNum TEXT)")
    cur.executemany("INSERT INTO course_legacy(subNum) VALUES(?)", [(s,) for s in subnums])
    conn.commit()
    conn.close()


def make_csv(csv_path: Path, indices):
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["CourseIndex"])
        w.writeheader()
        for idx in indices:
            w.writerow({"CourseIndex": idx})


def test_comparator_loads_sets_and_diff(tmp_path):
    # DB 先有 A, X；CSV 有 A, B, C
    db_path = tmp_path / "data.db"
    csv_path = tmp_path / "CoursesList.csv"
    make_temp_db(db_path, subnums=["A", "X"])
    make_csv(csv_path, indices=["A", "B", "C"])

    comp = DatabaseComparator(db_path=str(db_path), csv_path=str(csv_path))

    # 讀到集合
    assert comp.existing_courses == {"A", "X"}
    assert comp.csv_courses == {"A", "B", "C"}

    # 判斷：B/C 需要爬、A 不需要、X 不在 CSV
    assert comp.is_course_exists("A") is True
    assert comp.should_crawl_course("B") is True
    assert comp.should_crawl_course("C") is True
    assert comp.should_crawl_course("A") is False
    assert comp.should_crawl_course("X") is False

    # get_missing_courses_for_category 只挑 CSV∩!DB
    api_courses = [{"subNum": "A"}, {"subNum": "B"}, {"subNum": "Z"}]
    missing = comp.get_missing_courses_for_category(
        semester="1141", dp1="01", dp2="A1", dp3="105", api_courses=api_courses, search_level="three_level"
    )
    # 只有 B 符合（在 CSV 但不在 DB）
    assert [m["subNum"] for m in missing] == ["B"]
    assert missing[0]["_missing_reason"] == "in_csv_not_in_db"
    assert missing[0]["_full_course_id"] == "1141B"
    assert missing[0]["_search_level"] == "three_level"
    assert missing[0]["_category_key"] == "01-A1-105"
