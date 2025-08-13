# Define here the models for your scraped items
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CourseItem(scrapy.Item):
    id = scrapy.Field()  # PK
    year = scrapy.Field()
    semester = scrapy.Field()
    sub_num = scrapy.Field()
    name = scrapy.Field()
    name_en = scrapy.Field()
    teacher_id = scrapy.Field()  # FK → teacher.id
    kind = scrapy.Field()
    time = scrapy.Field()
    lang = scrapy.Field()
    lang_en = scrapy.Field()
    sem_qty = scrapy.Field()
    sem_qty_en = scrapy.Field()
    classroom_id = scrapy.Field()
    unit = scrapy.Field()
    unit_en = scrapy.Field()
    college = scrapy.Field()
    degree = scrapy.Field()
    department = scrapy.Field()
    credit = scrapy.Field()
    transition_type = scrapy.Field()
    transition_type_en = scrapy.Field()
    info = scrapy.Field()
    info_en = scrapy.Field()
    note = scrapy.Field()
    note_en = scrapy.Field()
    syllabus = scrapy.Field()
    syllabus_en = scrapy.Field()
    objective = scrapy.Field()
    objective_en = scrapy.Field()
    core = scrapy.Field()
    discipline = scrapy.Field()
    last_enroll = scrapy.Field()
    student_limit = scrapy.Field()
    student_count = scrapy.Field()


class TeacherItem(scrapy.Item):
    id = scrapy.Field()  # PK
    name = scrapy.Field()
    name_en = scrapy.Field()
    department = scrapy.Field()
    first_appear = scrapy.Field()


class CourseRemainItem(scrapy.Item):
    course_id = scrapy.Field()  # FK → course.id (PK)
    signable = scrapy.Field()
    waiting_count = scrapy.Field()
    origin_maximum = scrapy.Field()
    origin_registered = scrapy.Field()
    origin_remained = scrapy.Field()
    all_maximum = scrapy.Field()
    all_registered = scrapy.Field()
    all_remained = scrapy.Field()
    other_dept_maximum = scrapy.Field()
    other_dept_registered = scrapy.Field()
    other_dept_remained = scrapy.Field()
    same_grade_maximum = scrapy.Field()
    same_grade_registered = scrapy.Field()
    same_grade_remained = scrapy.Field()
    diff_grade_maximum = scrapy.Field()
    diff_grade_registered = scrapy.Field()
    diff_grade_remained = scrapy.Field()
    minor_maximum = scrapy.Field()
    minor_registered = scrapy.Field()
    minor_remained = scrapy.Field()
    double_major_maximum = scrapy.Field()
    double_major_registered = scrapy.Field()
    double_major_remained = scrapy.Field()
    other_dept_in_college_maximum = scrapy.Field()
    other_dept_in_college_registered = scrapy.Field()
    other_dept_in_college_remained = scrapy.Field()
    other_college_maximum = scrapy.Field()
    other_college_registered = scrapy.Field()
    other_college_remained = scrapy.Field()
    program_maximum = scrapy.Field()
    program_registered = scrapy.Field()
    program_remained = scrapy.Field()
    same_grade_and_above_maximum = scrapy.Field()
    same_grade_and_above_registered = scrapy.Field()
    same_grade_and_above_remained = scrapy.Field()
    lower_grade_maximum = scrapy.Field()
    lower_grade_registered = scrapy.Field()
    lower_grade_remained = scrapy.Field()
    other_program_maximum = scrapy.Field()
    other_program_registered = scrapy.Field()
    other_program_remained = scrapy.Field()


class RateItem(scrapy.Item):
    courseId = scrapy.Field()  # FK → course.id
    rowId = scrapy.Field()
    teacherId = scrapy.Field()  # FK → teacher.id
    content = scrapy.Field()
    contentEn = scrapy.Field()


class CourseLegacyItem(scrapy.Item):
    id = scrapy.Field()  # PK
    y = scrapy.Field()
    s = scrapy.Field()
    subNum = scrapy.Field()
    name = scrapy.Field()
    nameEn = scrapy.Field()
    teacher = scrapy.Field()
    teacherEn = scrapy.Field()
    kind = scrapy.Field()
    time = scrapy.Field()
    timeEn = scrapy.Field()
    lmtKind = scrapy.Field()
    lmtKindEn = scrapy.Field()
    lang = scrapy.Field()
    langEn = scrapy.Field()
    semQty = scrapy.Field()
    classroom = scrapy.Field()
    classroomId = scrapy.Field()
    unit = scrapy.Field()
    unitEn = scrapy.Field()
    dp1 = scrapy.Field()
    dp2 = scrapy.Field()
    dp3 = scrapy.Field()
    point = scrapy.Field()
    subRemainUrl = scrapy.Field()
    subSetUrl = scrapy.Field()
    subUnitRuleUrl = scrapy.Field()
    teaExpUrl = scrapy.Field()
    teaSchmUrl = scrapy.Field()
    tranTpe = scrapy.Field()
    tranTpeEn = scrapy.Field()
    info = scrapy.Field()
    infoEn = scrapy.Field()
    note = scrapy.Field()
    noteEn = scrapy.Field()
    syllabus = scrapy.Field()
    objective = scrapy.Field()


class TeacherLegacyItem(scrapy.Item):
    id = scrapy.Field()  # PK
    name = scrapy.Field()  # PK


class RateLegacyItem(scrapy.Item):
    courseId = scrapy.Field()  # PK
    rowId = scrapy.Field()  # PK
    teacherId = scrapy.Field()
    content = scrapy.Field()
    contentEn = scrapy.Field()


class ResultItem(scrapy.Item):
    courseId = scrapy.Field()  # PK
    yearsem = scrapy.Field()
    name = scrapy.Field()
    teacher = scrapy.Field()
    time = scrapy.Field()
    studentLimit = scrapy.Field()
    studentCount = scrapy.Field()
    lastEnroll = scrapy.Field()


class RemainLegacyItem(scrapy.Item):
    id = scrapy.Field()  # PK
    signableAdding = scrapy.Field()
    waitingList = scrapy.Field()
    originLimit = scrapy.Field()
    originRegistered = scrapy.Field()
    originAvailable = scrapy.Field()
    allLimit = scrapy.Field()
    allRegistered = scrapy.Field()
    allAvailable = scrapy.Field()
    otherDeptLimit = scrapy.Field()
    otherDeptRegistered = scrapy.Field()
    otherDeptAvailable = scrapy.Field()
    sameGradeLimit = scrapy.Field()
    sameGradeRegistered = scrapy.Field()
    sameGradeAvailable = scrapy.Field()
    diffGradeLimit = scrapy.Field()
    diffGradeRegistered = scrapy.Field()
    diffGradeAvailable = scrapy.Field()
    minorLimit = scrapy.Field()
    minorRegistered = scrapy.Field()
    minorAvailable = scrapy.Field()
    doubleMajorLimit = scrapy.Field()
    doubleMajorRegistered = scrapy.Field()
    doubleMajorAvailable = scrapy.Field()
    otherDeptInCollegeLimit = scrapy.Field()
    otherDeptInCollegeRegistered = scrapy.Field()
    otherDeptInCollegeAvailable = scrapy.Field()
    otherCollegeLimit = scrapy.Field()
    otherCollegeRegistered = scrapy.Field()
    otherCollegeAvailable = scrapy.Field()
    programLimit = scrapy.Field()
    programRegistered = scrapy.Field()
    programAvailable = scrapy.Field()
    sameGradeAndAboveLimit = scrapy.Field()
    sameGradeAndAboveRegistered = scrapy.Field()
    sameGradeAndAboveAvailable = scrapy.Field()
    lowerGradeLimit = scrapy.Field()
    lowerGradeRegistered = scrapy.Field()
    lowerGradeAvailable = scrapy.Field()
    otherProgramLimit = scrapy.Field()
    otherProgramRegistered = scrapy.Field()
    otherProgramAvailable = scrapy.Field()
