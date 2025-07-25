# Define here the models for your scraped items
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CourseItem(scrapy.Item):
    id                = scrapy.Field()   # PK
    year              = scrapy.Field()
    semester          = scrapy.Field()
    sub_num           = scrapy.Field()
    name              = scrapy.Field()
    name_en           = scrapy.Field()
    teacher_id        = scrapy.Field()   # FK → teacher.id
    kind              = scrapy.Field()
    time              = scrapy.Field()
    lang              = scrapy.Field()
    lang_en           = scrapy.Field()
    sem_qty           = scrapy.Field()
    sem_qty_en        = scrapy.Field()
    classroom_id      = scrapy.Field()
    unit              = scrapy.Field()
    unit_en           = scrapy.Field()
    college           = scrapy.Field()
    degree            = scrapy.Field()
    department        = scrapy.Field()
    credit            = scrapy.Field()
    transition_type   = scrapy.Field()
    transition_type_en = scrapy.Field()
    info              = scrapy.Field()
    info_en           = scrapy.Field()
    note              = scrapy.Field()
    note_en           = scrapy.Field()
    syllabus          = scrapy.Field()
    syllabus_en       = scrapy.Field()
    objective         = scrapy.Field()
    objective_en      = scrapy.Field()
    core              = scrapy.Field()
    discipline        = scrapy.Field()
    last_enroll       = scrapy.Field()
    student_limit     = scrapy.Field()
    student_count     = scrapy.Field()


class TeacherItem(scrapy.Item):
    id            = scrapy.Field()  # PK
    name          = scrapy.Field()
    name_en       = scrapy.Field()
    department    = scrapy.Field()
    first_appear  = scrapy.Field()


class CourseRemainItem(scrapy.Item):
    course_id                              = scrapy.Field()   # FK → course.id (PK)
    signable                              = scrapy.Field()
    waiting_count                         = scrapy.Field()
    origin_maximum                        = scrapy.Field()
    origin_registered                     = scrapy.Field()
    origin_remained                       = scrapy.Field()
    all_maximum                           = scrapy.Field()
    all_registered                        = scrapy.Field()
    all_remained                          = scrapy.Field()
    other_dept_maximum                    = scrapy.Field()
    other_dept_registered                 = scrapy.Field()
    other_dept_remained                   = scrapy.Field()
    same_grade_maximum                    = scrapy.Field()
    same_grade_registered                 = scrapy.Field()
    same_grade_remained                   = scrapy.Field()
    diff_grade_maximum                    = scrapy.Field()
    diff_grade_registered                 = scrapy.Field()
    diff_grade_remained                   = scrapy.Field()
    minor_maximum                         = scrapy.Field()
    minor_registered                      = scrapy.Field()
    minor_remained                        = scrapy.Field()
    double_major_maximum                  = scrapy.Field()
    double_major_registered               = scrapy.Field()
    double_major_remained                 = scrapy.Field()
    other_dept_in_college_maximum         = scrapy.Field()
    other_dept_in_college_registered      = scrapy.Field()
    other_dept_in_college_remained        = scrapy.Field()
    other_college_maximum                 = scrapy.Field()
    other_college_registered              = scrapy.Field()
    other_college_remained                = scrapy.Field()
    program_maximum                       = scrapy.Field()
    program_registered                    = scrapy.Field()
    program_remained                      = scrapy.Field()
    same_grade_and_above_maximum          = scrapy.Field()
    same_grade_and_above_registered       = scrapy.Field()
    same_grade_and_above_remained         = scrapy.Field()
    lower_grade_maximum                   = scrapy.Field()
    lower_grade_registered                = scrapy.Field()
    lower_grade_remained                  = scrapy.Field()
    other_program_maximum                 = scrapy.Field()
    other_program_registered              = scrapy.Field()
    other_program_remained                = scrapy.Field()


class RateItem(scrapy.Item):
    course_id     = scrapy.Field()   # FK → course.id
    teacher_id    = scrapy.Field()   # FK → teacher.id
    content       = scrapy.Field()
    content_en    = scrapy.Field()