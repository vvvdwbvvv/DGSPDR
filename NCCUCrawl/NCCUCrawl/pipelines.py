# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3
from scrapy.exceptions import DropItem


class SCSRSQLitePipeline:
    def open_spider(self, spider):
        """Open a connection to the SQLite database."""
        self.conn = sqlite3.connect("data.db")
        self.cur = self.conn.cursor()
        self.cur.execute("PRAGMA journal_mode = WAL")
        self.cur.execute("PRAGMA synchronous = NORMAL")

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()

    def process_item(self, item, spider):
        if item.__class__.__name__ == "TeacherItem":
            self.upsert_teacher(item)
        elif item.__class__.__name__ == "CourseItem":
            self.upsert_course(item)
        elif item.__class__.__name__ == "RateItem":
            self.upsert_rate(item)
        elif item.__class__.__name__ == "CourseRemainItem":
            self.upsert_remain(item)
        else:
            raise DropItem(f"unknown item type: {type(item)}")
        return item

    def upsert_teacher(self, i):
        sql = """
        INSERT INTO teacher (id, name, name_en, department, first_appear)
        VALUES (:id, :name, :name_en, :department, :first_appear)
        ON CONFLICT(id) DO UPDATE SET 
            name          = excluded.name,
            name_en       = excluded.name_en,
            department    = excluded.department,
            first_appear  = excluded.first_appear;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

    def upsert_course(self, i):
        sql = """
        INSERT INTO course (
            id, year, semester, sub_num, name, name_en, teacher_id,
            kind, time, lang, lang_en, sem_qty, sem_qty_en, classroom_id,
            unit, unit_en, college, degree, department, credit,
            transition_type, transition_type_en, info, info_en,
            note, note_en, syllabus, syllabus_en, objective, objective_en,
            core, discipline, last_enroll, student_limit, student_count
        ) VALUES (
            :id, :year, :semester, :sub_num, :name, :name_en, :teacher_id,
            :kind, :time, :lang, :lang_en, :sem_qty, :sem_qty_en, :classroom_id,
            :unit, :unit_en, :college, :degree, :department, :credit,
            :transition_type, :transition_type_en, :info, :info_en,
            :note, :note_en, :syllabus, :syllabus_en, :objective, :objective_en,
            :core, :discipline, :last_enroll, :student_limit, :student_count
        )
        ON CONFLICT(id) DO UPDATE SET 
            name                = excluded.name,
            name_en             = excluded.name_en,
            kind                = excluded.kind,
            time                = excluded.time,
            lang                = excluded.lang,
            lang_en             = excluded.lang_en,
            sem_qty             = excluded.sem_qty,
            sem_qty_en          = excluded.sem_qty_en,
            classroom_id        = excluded.classroom_id,
            unit                = excluded.unit,
            unit_en             = excluded.unit_en,
            college             = excluded.college,
            degree              = excluded.degree,
            department          = excluded.department,
            credit              = excluded.credit,
            transition_type     = excluded.transition_type,
            transition_type_en  = excluded.transition_type_en,
            info                = excluded.info,
            info_en             = excluded.info_en,
            note                = excluded.note,
            note_en             = excluded.note_en,
            syllabus            = excluded.syllabus,
            syllabus_en         = excluded.syllabus_en,
            objective           = excluded.objective,
            objective_en        = excluded.objective_en,
            core                = excluded.core,
            discipline          = excluded.discipline,
            last_enroll         = excluded.last_enroll,
            student_limit       = excluded.student_limit,
            student_count       = excluded.student_count;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

    def upsert_rate(self, i):
        sql = """
        INSERT OR IGNORE INTO rate (
            course_id, teacher_id, content, content_en
        ) VALUES (
            :course_id, :teacher_id, :content, :content_en
        );
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

    def upsert_remain(self, i):
        sql = """
        INSERT INTO course_remain (
            course_id, signable, waiting_count,
            origin_maximum, origin_registered, origin_remained,
            all_maximum, all_registered, all_remained,
            other_dept_maximum, other_dept_registered, other_dept_remained,
            same_grade_maximum, same_grade_registered, same_grade_remained,
            diff_grade_maximum, diff_grade_registered, diff_grade_remained,
            minor_maximum, minor_registered, minor_remained,
            double_major_maximum, double_major_registered, double_major_remained,
            other_dept_in_college_maximum, other_dept_in_college_registered, other_dept_in_college_remained,
            other_college_maximum, other_college_registered, other_college_remained,
            program_maximum, program_registered, program_remained,
            same_grade_and_above_maximum, same_grade_and_above_registered, same_grade_and_above_remained,
            lower_grade_maximum, lower_grade_registered, lower_grade_remained,
            other_program_maximum, other_program_registered, other_program_remained
        ) VALUES (
            :course_id, :signable, :waiting_count,
            :origin_maximum, :origin_registered, :origin_remained,
            :all_maximum, :all_registered, :all_remained,
            :other_dept_maximum, :other_dept_registered, :other_dept_remained,
            :same_grade_maximum, :same_grade_registered, :same_grade_remained,
            :diff_grade_maximum, :diff_grade_registered, :diff_grade_remained,
            :minor_maximum, :minor_registered, :minor_remained,
            :double_major_maximum, :double_major_registered, :double_major_remained,
            :other_dept_in_college_maximum, :other_dept_in_college_registered, :other_dept_in_college_remained,
            :other_college_maximum, :other_college_registered, :other_college_remained,
            :program_maximum, :program_registered, :program_remained,
            :same_grade_and_above_maximum, :same_grade_and_above_registered, :same_grade_and_above_remained,
            :lower_grade_maximum, :lower_grade_registered, :lower_grade_remained,
            :other_program_maximum, :other_program_registered, :other_program_remained
        )
        ON CONFLICT(course_id) DO UPDATE SET
            signable                              = excluded.signable,
            waiting_count                         = excluded.waiting_count,
            origin_maximum                        = excluded.origin_maximum,
            origin_registered                     = excluded.origin_registered,
            origin_remained                       = excluded.origin_remained,
            all_maximum                           = excluded.all_maximum,
            all_registered                        = excluded.all_registered,
            all_remained                          = excluded.all_remained,
            other_dept_maximum                    = excluded.other_dept_maximum,
            other_dept_registered                 = excluded.other_dept_registered,
            other_dept_remained                   = excluded.other_dept_remained,
            same_grade_maximum                    = excluded.same_grade_maximum,
            same_grade_registered                 = excluded.same_grade_registered,
            same_grade_remained                   = excluded.same_grade_remained,
            diff_grade_maximum                    = excluded.diff_grade_maximum,
            diff_grade_registered                 = excluded.diff_grade_registered,
            diff_grade_remained                   = excluded.diff_grade_remained,
            minor_maximum                         = excluded.minor_maximum,
            minor_registered                      = excluded.minor_registered,
            minor_remained                        = excluded.minor_remained,
            double_major_maximum                  = excluded.double_major_maximum,
            double_major_registered               = excluded.double_major_registered,
            double_major_remained                 = excluded.double_major_remained,
            other_dept_in_college_maximum         = excluded.other_dept_in_college_maximum,
            other_dept_in_college_registered      = excluded.other_dept_in_college_registered,
            other_dept_in_college_remained        = excluded.other_dept_in_college_remained,
            other_college_maximum                 = excluded.other_college_maximum,
            other_college_registered              = excluded.other_college_registered,
            other_college_remained                = excluded.other_college_remained,
            program_maximum                       = excluded.program_maximum,
            program_registered                    = excluded.program_registered,
            program_remained                      = excluded.program_remained,
            same_grade_and_above_maximum          = excluded.same_grade_and_above_maximum,
            same_grade_and_above_registered       = excluded.same_grade_and_above_registered,
            same_grade_and_above_remained         = excluded.same_grade_and_above_remained,
            lower_grade_maximum                   = excluded.lower_grade_maximum,
            lower_grade_registered                = excluded.lower_grade_registered,
            lower_grade_remained                  = excluded.lower_grade_remained,
            other_program_maximum                 = excluded.other_program_maximum,
            other_program_registered              = excluded.other_program_registered,
            other_program_remained                = excluded.other_program_remained;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()
