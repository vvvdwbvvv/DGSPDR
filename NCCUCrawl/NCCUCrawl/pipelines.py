# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3
from scrapy.exceptions import DropItem

# mainly hard coding sql syntax: suggest folding it
class SCSRSQLitePipeline:
    def open_spider(self, spider):
        """Open a connection to the SQLite database."""
        self.conn = sqlite3.connect("data.db")
        self.cur = self.conn.cursor()
        self.cur.execute("PRAGMA journal_mode = WAL")
        self.cur.execute("PRAGMA synchronous = NORMAL")

        self.create_tables()

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
        elif item.__class__.__name__ == "CourseLegacyItem":
            self.upsert_course_legacy(item)
        elif item.__class__.__name__ == "TeacherLegacyItem":
            self.upsert_teacher_legacy(item)
        elif item.__class__.__name__ == "RateLegacyItem":
            self.upsert_rate_legacy(item)
        elif item.__class__.__name__ == "ResultItem":
            self.upsert_result(item)
        elif item.__class__.__name__ == "RemainLegacyItem":
            self.upsert_remain_legacy(item)
        else:
            raise DropItem(f"unknown item type: {type(item)}")
        return item

    def create_tables(self):
        """Create database tables if they don't exist."""

        # Create teacher table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS teacher (
            id TEXT PRIMARY KEY,
            name TEXT,
            name_en TEXT,
            department TEXT,
            first_appear TEXT
        )
        """)

        # Create course table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS course (
            id TEXT PRIMARY KEY,
            year TEXT,
            semester TEXT,
            sub_num TEXT,
            name TEXT,
            name_en TEXT,
            teacher_id TEXT REFERENCES teacher(id),
            kind TEXT,
            time TEXT,
            lang TEXT,
            lang_en TEXT,
            sem_qty TEXT,
            sem_qty_en TEXT,
            classroom_id TEXT,
            unit TEXT,
            unit_en TEXT,
            college TEXT,
            degree TEXT,
            department TEXT,
            credit INTEGER,
            transition_type TEXT,
            transition_type_en TEXT,
            info TEXT,
            info_en TEXT,
            note TEXT,
            note_en TEXT,
            syllabus TEXT,
            syllabus_en TEXT,
            objective TEXT,
            objective_en TEXT,
            core BOOLEAN,
            discipline TEXT,
            last_enroll INTEGER,
            student_limit INTEGER,
            student_count INTEGER
        )
        """)

        # Create course_remain table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS course_remain (
            course_id TEXT PRIMARY KEY REFERENCES course(id),
            signable BOOLEAN,
            waiting_count INTEGER,
            origin_maximum INTEGER,
            origin_registered INTEGER,
            origin_remained INTEGER,
            all_maximum INTEGER,
            all_registered INTEGER,
            all_remained INTEGER,
            other_dept_maximum INTEGER,
            other_dept_registered INTEGER,
            other_dept_remained INTEGER,
            same_grade_maximum INTEGER,
            same_grade_registered INTEGER,
            same_grade_remained INTEGER,
            diff_grade_maximum INTEGER,
            diff_grade_registered INTEGER,
            diff_grade_remained INTEGER,
            minor_maximum INTEGER,
            minor_registered INTEGER,
            minor_remained INTEGER,
            double_major_maximum INTEGER,
            double_major_registered INTEGER,
            double_major_remained INTEGER,
            other_dept_in_college_maximum INTEGER,
            other_dept_in_college_registered INTEGER,
            other_dept_in_college_remained INTEGER,
            other_college_maximum INTEGER,
            other_college_registered INTEGER,
            other_college_remained INTEGER,
            program_maximum INTEGER,
            program_registered INTEGER,
            program_remained INTEGER,
            same_grade_and_above_maximum INTEGER,
            same_grade_and_above_registered INTEGER,
            same_grade_and_above_remained INTEGER,
            lower_grade_maximum INTEGER,
            lower_grade_registered INTEGER,
            lower_grade_remained INTEGER,
            other_program_maximum INTEGER,
            other_program_registered INTEGER,
            other_program_remained INTEGER
        )
        """)

        # Create rate table (if needed)
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS rate (
            course_id TEXT REFERENCES course(id),
            teacher_id TEXT REFERENCES teacher(id),
            content TEXT,
            content_en TEXT
        )
        """)

        # Course Legacy table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS course_legacy (
            id TEXT PRIMARY KEY,
            y TEXT,
            s TEXT,
            subNum TEXT,
            name TEXT,
            name_en TEXT,
            teacher TEXT,
            teacherEn TEXT,
            kind TEXT,
            time TEXT,
            timeEn TEXT,
            lmtKind TEXT,
            lmtKindEn TEXT,
            lang TEXT,
            langEn TEXT,
            semQty TEXT,
            classroom TEXT,
            classroomId TEXT,
            unit TEXT,
            unitEn TEXT,
            dp1 TEXT,
            dp2 TEXT,
            dp3 TEXT,
            point REAL,
            subRemainUrl TEXT,
            subSetUrl TEXT,
            subUnitRuleUrl TEXT,
            teaExpUrl TEXT,
            teaSchmUrl TEXT,
            tranTpe TEXT,
            tranTpeEn TEXT,
            info TEXT,
            infoEn TEXT,
            note TEXT,
            noteEn TEXT,
            syllabus TEXT,
            objective TEXT
        )
        """)

        # Teacher Legacy table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS teacher_legacy (
            id TEXT PRIMARY KEY,
            name TEXT
        )
        """)

        # Rate Legacy table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS rate_legacy (
            courseId TEXT,
            rowId TEXT,
            teacherId TEXT,
            content TEXT,
            contentEn TEXT,
            PRIMARY KEY (courseId, rowId)
        )
        """)

        # Result table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS result (
            courseId TEXT PRIMARY KEY,
            yearsem TEXT,
            name TEXT,
            teacher TEXT,
            time TEXT,
            studentLimit INTEGER,
            studentCount INTEGER,
            lastEnroll INTEGER
        )
        """)

        #  Remain Legacy table
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS remain_legacy (
            id TEXT PRIMARY KEY,
            signableAdding BOOLEAN,
            waitingList INTEGER,
            originLimit INTEGER,
            originRegistered INTEGER,
            originAvailable INTEGER,
            allLimit INTEGER,
            allRegistered INTEGER,
            allAvailable INTEGER,
            otherDeptLimit INTEGER,
            otherDeptRegistered INTEGER,
            otherDeptAvailable INTEGER,
            sameGradeLimit INTEGER,
            sameGradeRegistered INTEGER,
            sameGradeAvailable INTEGER,
            diffGradeLimit INTEGER,
            diffGradeRegistered INTEGER,
            diffGradeAvailable INTEGER,
            minorLimit INTEGER,
            minorRegistered INTEGER,
            minorAvailable INTEGER,
            doubleMajorLimit INTEGER,
            doubleMajorRegistered INTEGER,
            doubleMajorAvailable INTEGER,
            otherDeptInCollegeLimit INTEGER,
            otherDeptInCollegeRegistered INTEGER,
            otherDeptInCollegeAvailable INTEGER,
            otherCollegeLimit INTEGER,
            otherCollegeRegistered INTEGER,
            otherCollegeAvailable INTEGER,
            programLimit INTEGER,
            programRegistered INTEGER,
            programAvailable INTEGER,
            sameGradeAndAboveLimit INTEGER,
            sameGradeAndAboveRegistered INTEGER,
            sameGradeAndAboveAvailable INTEGER,
            lowerGradeLimit INTEGER,
            lowerGradeRegistered INTEGER,
            lowerGradeAvailable INTEGER,
            otherProgramLimit INTEGER,
            otherProgramRegistered INTEGER,
            otherProgramAvailable INTEGER
        )
        """)

        self.conn.commit()

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
    
    def upsert_course_legacy(self, i):
        """處理 CourseLegacyItem"""
        sql = """
        INSERT INTO course_legacy (
            id, y, s, subNum, name, name_en, teacher, teacherEn,
            kind, time, timeEn, lmtKind, lmtKindEn, lang, langEn,
            semQty, classroom, classroomId, unit, unitEn,
            dp1, dp2, dp3, point, subRemainUrl, subSetUrl,
            subUnitRuleUrl, teaExpUrl, teaSchmUrl, tranTpe, tranTpeEn,
            info, infoEn, note, noteEn, syllabus, objective
        ) VALUES (
            :id, :y, :s, :subNum, :name, :name_en, :teacher, :teacherEn,
            :kind, :time, :timeEn, :lmtKind, :lmtKindEn, :lang, :langEn,
            :semQty, :classroom, :classroomId, :unit, :unitEn,
            :dp1, :dp2, :dp3, :point, :subRemainUrl, :subSetUrl,
            :subUnitRuleUrl, :teaExpUrl, :teaSchmUrl, :tranTpe, :tranTpeEn,
            :info, :infoEn, :note, :noteEn, :syllabus, :objective
        )
        ON CONFLICT(id) DO UPDATE SET 
            name         = excluded.name,
            name_en      = excluded.name_en,
            teacher      = excluded.teacher,
            teacherEn    = excluded.teacherEn,
            kind         = excluded.kind,
            time         = excluded.time,
            timeEn       = excluded.timeEn,
            lmtKind      = excluded.lmtKind,
            lmtKindEn    = excluded.lmtKindEn,
            lang         = excluded.lang,
            langEn       = excluded.langEn,
            semQty       = excluded.semQty,
            classroom    = excluded.classroom,
            classroomId  = excluded.classroomId,
            unit         = excluded.unit,
            unitEn       = excluded.unitEn,
            dp1          = excluded.dp1,
            dp2          = excluded.dp2,
            dp3          = excluded.dp3,
            point        = excluded.point,
            subRemainUrl = excluded.subRemainUrl,
            subSetUrl    = excluded.subSetUrl,
            subUnitRuleUrl = excluded.subUnitRuleUrl,
            teaExpUrl    = excluded.teaExpUrl,
            teaSchmUrl   = excluded.teaSchmUrl,
            tranTpe      = excluded.tranTpe,
            tranTpeEn    = excluded.tranTpeEn,
            info         = excluded.info,
            infoEn       = excluded.infoEn,
            note         = excluded.note,
            noteEn       = excluded.noteEn,
            syllabus     = excluded.syllabus,
            objective    = excluded.objective;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

    def upsert_teacher_legacy(self, i):
        """處理 TeacherLegacyItem"""
        sql = """
        INSERT INTO teacher_legacy (id, name)
        VALUES (:id, :name)
        ON CONFLICT(id) DO UPDATE SET 
            name = excluded.name;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

    def upsert_rate_legacy(self, i):
        """處理 RateLegacyItem"""
        sql = """
        INSERT INTO rate_legacy (courseId, rowId, teacherId, content, contentEn)
        VALUES (:courseId, :rowId, :teacherId, :content, :contentEn)
        ON CONFLICT(courseId, rowId) DO UPDATE SET 
            teacherId = excluded.teacherId,
            content   = excluded.content,
            contentEn = excluded.contentEn;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()
    
    def upsert_remain_legacy(self, i):
        """處理 RemainLegacyItem"""
        sql = """
        INSERT INTO remain_legacy (
            id, signableAdding, waitingList,
            originLimit, originRegistered, originAvailable,
            allLimit, allRegistered, allAvailable,
            otherDeptLimit, otherDeptRegistered, otherDeptAvailable,
            sameGradeLimit, sameGradeRegistered, sameGradeAvailable,
            diffGradeLimit, diffGradeRegistered, diffGradeAvailable,
            minorLimit, minorRegistered, minorAvailable,
            doubleMajorLimit, doubleMajorRegistered, doubleMajorAvailable,
            otherDeptInCollegeLimit, otherDeptInCollegeRegistered, otherDeptInCollegeAvailable,
            otherCollegeLimit, otherCollegeRegistered, otherCollegeAvailable,
            programLimit, programRegistered, programAvailable,
            sameGradeAndAboveLimit, sameGradeAndAboveRegistered, sameGradeAndAboveAvailable,
            lowerGradeLimit, lowerGradeRegistered, lowerGradeAvailable,
            otherProgramLimit, otherProgramRegistered, otherProgramAvailable
        ) VALUES (
        :id, :signableAdding, :waitingList,
            :originLimit, :originRegistered, :originAvailable,
            :allLimit, :allRegistered, :allAvailable,
            :otherDeptLimit, :otherDeptRegistered, :otherDeptAvailable,
            :sameGradeLimit, :sameGradeRegistered, :sameGradeAvailable,
            :diffGradeLimit, :diffGradeRegistered, :diffGradeAvailable,
            :minorLimit, :minorRegistered, :minorAvailable,
            :doubleMajorLimit, :doubleMajorRegistered, :doubleMajorAvailable,
            :otherDeptInCollegeLimit, :otherDeptInCollegeRegistered, :otherDeptInCollegeAvailable,
            :otherCollegeLimit, :otherCollegeRegistered, :otherCollegeAvailable,
            :programLimit, :programRegistered, :programAvailable,
            :sameGradeAndAboveLimit, :sameGradeAndAboveRegistered, :sameGradeAndAboveAvailable,
            :lowerGradeLimit, :lowerGradeRegistered, :lowerGradeAvailable,
            :otherProgramLimit, :otherProgramRegistered, :otherProgramAvailable
        )
        ON CONFLICT(id) DO UPDATE SET
            signableAdding              = excluded.signableAdding,
            waitingList                 = excluded.waitingList,
            originLimit                 = excluded.originLimit,
            originRegistered            = excluded.originRegistered,
            originAvailable             = excluded.originAvailable,
            allLimit                    = excluded.allLimit,
            allRegistered               = excluded.allRegistered,
            allAvailable                = excluded.allAvailable,
            otherDeptLimit              = excluded.otherDeptLimit,
            otherDeptRegistered         = excluded.otherDeptRegistered,
            otherDeptAvailable          = excluded.otherDeptAvailable,
            sameGradeLimit              = excluded.sameGradeLimit,
            sameGradeRegistered         = excluded.sameGradeRegistered,
            sameGradeAvailable          = excluded.sameGradeAvailable,
            diffGradeLimit              = excluded.diffGradeLimit,
            diffGradeRegistered         = excluded.diffGradeRegistered,
            diffGradeAvailable          = excluded.diffGradeAvailable,
            minorLimit                  = excluded.minorLimit,
            minorRegistered             = excluded.minorRegistered,
            minorAvailable              = excluded.minorAvailable,
            doubleMajorLimit            = excluded.doubleMajorLimit,
            doubleMajorRegistered       = excluded.doubleMajorRegistered,
            doubleMajorAvailable        = excluded.doubleMajorAvailable,
            otherDeptInCollegeLimit     = excluded.otherDeptInCollegeLimit,
            otherDeptInCollegeRegistered = excluded.otherDeptInCollegeRegistered,
            otherDeptInCollegeAvailable = excluded.otherDeptInCollegeAvailable,
            otherCollegeLimit           = excluded.otherCollegeLimit,
            otherCollegeRegistered      = excluded.otherCollegeRegistered,
            otherCollegeAvailable       = excluded.otherCollegeAvailable,
            programLimit                = excluded.programLimit,
            rogramRegistered           = excluded.programRegistered,
            programAvailable            = excluded.programAvailable,
            sameGradeAndAboveLimit      = excluded.sameGradeAndAboveLimit,
            sameGradeAndAboveRegistered = excluded.sameGradeAndAboveRegistered,
            sameGradeAndAboveAvailable  = excluded.sameGradeAndAboveAvailable,
            lowerGradeLimit             = excluded.lowerGradeLimit,
            lowerGradeRegistered        = excluded.lowerGradeRegistered,
            lowerGradeAvailable         = excluded.lowerGradeAvailable,
            otherProgramLimit           = excluded.otherProgramLimit,
            otherProgramRegistered      = excluded.otherProgramRegistered,
            otherProgramAvailable       = excluded.otherProgramAvailable;
        """
        self.cur.execute(sql, dict(i))
        self.conn.commit()

class ETLPipeline:
    LANGUAGE_MAPPING = {
        "中文": "chinese",
        "英文": "english",
        "英語": "english",
        "日文": "japanese",
        "韓文": "korean",
        "韓語": "korean",
        "法文": "french",
        "德文": "german",
        "西班牙文": "spanish",
        "阿拉伯文": "arabic",
        "越南文": "vietnamese",
        "泰文": "thai",
        "土耳其文": "turkish",
        "印尼文": "indonesian",
        "其他": "other",
        "": "unknown",
    }

    SEM_MAPPING = {
        "單學期科目": 1,
        "全學年科目": 2,
        "三學期科目": 3,
    }

    KIND_MAPPING = {
        "必修": 1,
        "選修": 2,
        "群修": 3,
    }

    def process_item(self, item, spider):
        """Process items and clean data before storing."""
        if item.__class__.__name__ == "CourseItem":
            item = self.clean_course_item(item)
        return item

    def _transform_mappings(self, item):
        """Clean and transform course item fields."""
        item["lang_en"] = self.LANGUAGE_MAPPING.get(item["lang"], "unknown")
        item["sem_qty"] = self.SEM_MAPPING.get(item["sem_qty"], 0)
        item["kind"] = self.KIND_MAPPING.get(item["kind"], 0)
        return item

    def _ensure_required_fields(self, item):
        required_string_fields = [
            "note",
            "note_en",
            "unit_en",
            "department",
            "transition_type_en",
            "name_en",
            "objective",
            "objective_en",
            "syllabus_en",
            "teacher_id",
            "syllabus",
            "info",
            "info_en",
            "discipline",
        ]

        required_integer_fields = ["last_enroll", "student_limit", "student_count"]

        for field in required_string_fields:
            if item.get(field) is None:
                item[field] = ""

        for field in required_integer_fields:
            if item.get(field) is None:
                item[field] = None

        return item

    def _fix_data_types(self, item):
        if isinstance(item.get("syllabus"), (tuple, list)):
            item["syllabus"] = str(item["syllabus"][0]) if item["syllabus"] else ""

        if item.get("core") is not None and not isinstance(item["core"], bool):
            item["core"] = bool(item["core"])

        if item.get("credit") is not None:
            try:
                item["credit"] = float(item["credit"])
            except (ValueError, TypeError):
                item["credit"] = None

        return item

    def clean_course_item(self, item):
        item = self._transform_mappings(item)
        item = self._ensure_required_fields(item)
        item = self._fix_data_types(item)

        return item
