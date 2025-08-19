import sys
import os
import json
import pytest
from scrapy.http import Request, TextResponse, HtmlResponse


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from NCCUCrawl.spiders.courses_deprecated import CoursesLegacySpider
from NCCUCrawl.items import CourseLegacyItem



def make_text_response(url: str, text: str, meta=None):
    req = Request(url=url, meta=meta or {})
    return TextResponse(url=url, request=req, body=text.encode("utf-8"), encoding="utf-8")


def make_html_response(url: str, html: str, meta=None):
    req = Request(url=url, meta=meta or {})
    return HtmlResponse(url=url, request=req, body=html.encode("utf-8"), encoding="utf-8")


@pytest.fixture
def spider():
    return CoursesLegacySpider()


@pytest.fixture
def sample_units():
    # 最小可行的 unit.json（1 個 L1 / 1 個 L2 / 1 個 L3）
    return [
        {
            "utCodL1": "01",
            "utL1Text": "測試學院 / Test College",
            "utL2": [
                {
                    "utCodL2": "A1",
                    "utL2Text": "測試系A1 / Dept A1",
                    "utL3": [
                        {
                            "utCodL3": "105",
                            "utL3Text": "單位X / Unit X",
                        }
                    ],
                }
            ],
        },
        # 也可放入 "全部" 類（utCodL1 == "0"）以確保不會被計入
        {"utCodL1": "0", "utL1Text": "全部 / All", "utL2": []},
    ]


@pytest.fixture
def sample_courses():
    # 模擬 es.nccu.edu.tw 課程列表 API 回傳
    return [
        {
            "subNum": "754944001",
            "subNam": "課程A",
            "subPoint": "3",
            "subGde": "單位X",
            "teaSchmUrl": "https://example.com/syl-754944001",
        },
        {
            "subNum": "123456789",
            "subNam": "課程B",
            "subPoint": "2",
            "subGde": "單位X",
            "teaSchmUrl": "https://example.com/syl-123456789",
        },
    ]


def test_parse_units_builds_mapping_and_emits_hierarchical_requests(spider, sample_units):
    units_resp = make_text_response(
        "https://qrysub.nccu.edu.tw/assets/api/unit.json",
        json.dumps(sample_units),
    )
    out = list(spider.parse_units(units_resp))

    # 驗證 unit_mapping
    assert "01-A1-105" in spider.unit_mapping
    info = spider.unit_mapping["01-A1-105"]
    assert info["college"] == "測試學院"
    assert info["college_en"] == "Test College"
    assert info["unit"] == "單位X"
    assert info["unit_en"] == "Unit X"
    assert info["department"] == "單位X"
    assert info["department_en"] == "Unit X"

    # 因為 sample_units 只有 1 條完整階層，因此應該產生：
    # 三階層、二階層、一階層、零階層 共 4 個請求
    assert len(out) == 4
    levels = sorted([r.meta["search_level"] for r in out])
    assert levels == ["one_level", "three_level", "two_level", "zero_level"]

    # 簡單驗證 URL 格式
    urls = [r.url for r in out]
    assert any(":dp1=01%20:dp2=A1%20:dp3=105" in u for u in urls)
    assert any(":dp1=01%20:dp2=A1%20:dp3=" in u for u in urls)  # two_level
    assert any(":dp1=01%20:dp2=%20:dp3=" in u for u in urls)    # one_level
    assert any(":dp1=%20:dp2=%20:dp3=" in u for u in urls)      # zero_level


def test_parse_course_list_dedup_and_requests(spider, sample_courses):
    # 先手動建 mapping 讓 parse_course_list 可以找得到
    spider.unit_mapping = {"01-A1-105": {"college": "測試學院"}}

    sem = "1141"
    url = spider.build_course_list(sem, "01", "A1", "105")
    resp = make_text_response(url, json.dumps(sample_courses))

    # 第一次 parse 應該會為 2 門課各產出一個 zh 詳細頁 Request
    out1 = list(
        spider.parse_course_list(
            resp, sem, "01", "A1", "105", search_level="three_level"
        )
    )
    assert len(out1) == 2
    for req in out1:
        assert req.url.startswith("http://es.nccu.edu.tw/course/zh-TW/")
        assert req.meta["semester"] == sem
        assert req.meta["dp1"] == "01"
        assert req.meta["dp2"] == "A1"
        assert req.meta["dp3"] == "105"
        assert "item" in req.meta and "course_data" in req.meta

    # dedup：再丟一次一樣的清單，應該不會再產生新請求
    resp2 = make_text_response(url, json.dumps(sample_courses))
    out2 = list(
        spider.parse_course_list(
            resp2, sem, "01", "A1", "105", search_level="three_level"
        )
    )
    assert len(out2) == 0

    # search_stats 有累加
    stats = spider.search_stats["three_level"]
    assert stats["categories"] == 2  # 兩次呼叫
    assert stats["courses"] == 4     # 每次 2 筆
    assert stats["new_courses"] == 2 # 只有第一次 2 筆是新的


def test_convert_kind_to_int(spider):
    # lmtKind 特例優先
    assert spider.convert_kind_to_int("選修", "通識向度") == 4
    assert spider.convert_kind_to_int("必修", "跨領域學分學程") == 0
    # 一般 mapping
    assert spider.convert_kind_to_int("必修") == 1
    assert spider.convert_kind_to_int("選修") == 2
    assert spider.convert_kind_to_int("群修") == 3
    # 未知
    assert spider.convert_kind_to_int("其他") == 0


def test_parse_course_detail_zh_updates_and_emit_en(spider, sample_courses):
    # 準備一個 item 與 meta（延續 parse_course_list 的產物）
    sem = "1141"
    c = sample_courses[0]
    course_id = f"{sem}{c['subNum']}"
    # 建立最小的 item（直接用 spider.create_course_item 產）
    spider.unit_mapping = {"01-A1-105": {}}
    item = spider.create_course_item(c, sem, {}, "01", "A1", "105")

    meta = {
        "item": item,
        "course_data": c,
        "course_id": course_id,
        "semester": sem,
        "dp1": "01",
        "dp2": "A1",
        "dp3": "105",
        "search_level": "three_level",
        "category_key": "01-A1-105",
    }

    zh_payload = [
        {
            "teaNam": "王小明",
            "subKind": "必修",
            "subTime": "一34",
            "lmtKind": "",
            "core": "是",
            "langTpe": "中文",
            "subClassroom": "商學院101",
            "tranTpe": "實體",
            "info": "資訊",
            "note": "備註",
        }
    ]
    zh_resp = make_text_response(
        f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/", json.dumps(zh_payload), meta
    )

    out = list(spider.parse_course_detail_zh(zh_resp))
    # 會轉去 EN 詳細頁
    assert len(out) == 1
    en_req = out[0]
    assert en_req.url == f"http://es.nccu.edu.tw/course/en/{course_id}/"

    # zh 欄位已更新到 item
    updated = en_req.meta["item"]
    assert updated["teacher"] == "王小明"
    assert updated["kind"] == 1
    assert updated["time"] == "一34"
    assert updated["core"] == 1
    assert updated["lang"] == "中文"
    assert updated["classroom"] == "商學院101"
    assert updated["tranTpe"] == "實體"
    assert updated["info"] == "資訊"
    assert updated["note"] == "備註"


def test_parse_course_detail_en_then_fetch_syllabus(spider, sample_courses):
    sem = "1141"
    c = sample_courses[0]
    course_id = f"{sem}{c['subNum']}"
    item = spider.create_course_item(c, sem, {}, "01", "A1", "105")

    meta = {
        "item": item,
        "course_data": c,  # 內含 teaSchmUrl
    }
    en_payload = [
        {
            "subNam": "Course A EN",
            "teaNam": "Ming Wang",
            "subTime": "Mon.34",
            "lmtKind": "General Education",
            "langTpe": "English",
            "subClassroom": "CBA101",
            "tranTpe": "In-person",
            "info": "info EN",
            "subGde": "UnitX EN",
            "note": "note EN",
        }
    ]
    en_resp = make_text_response(
        f"http://es.nccu.edu.tw/course/en/{course_id}/", json.dumps(en_payload), meta
    )
    out = list(spider.parse_course_detail_en(en_resp))
    assert len(out) == 1
    syl_req = out[0]
    assert syl_req.url == c["teaSchmUrl"]
    assert syl_req.callback.__name__ == "parse_syllabus"


def test_parse_course_detail_en_without_syllabus_yields_item(spider, sample_courses):
    sem = "1141"
    c = {k: v for k, v in sample_courses[1].items() if k != "teaSchmUrl"}  # 沒有 syllabus URL
    course_id = f"{sem}{c['subNum']}"
    item = spider.create_course_item(c, sem, {}, "01", "A1", "105")

    meta = {"item": item, "course_data": c}
    en_payload = [
        {
            "subNam": "Course B EN",
            "teaNam": "Ann Lee",
        }
    ]
    en_resp = make_text_response(
        f"http://es.nccu.edu.tw/course/en/{course_id}/", json.dumps(en_payload), meta
    )
    out = list(spider.parse_course_detail_en(en_resp))
    # 沒有 syllabus URL 時，直接輸出 item
    assert len(out) == 1
    yielded_item = out[0]
    assert yielded_item["nameEn"] == "Course B EN"
    assert yielded_item["teacherEn"] == "Ann Lee"


def test_parse_syllabus_extracts_objective_and_description(spider):
    # 模擬 Syllabus HTML 結構
    html = """
    <body>
      <div class="container sylview-section">
        <div><div><div><p>教學目標一</p></div></div></div>
      </div>

      <div class="col-sm-7 sylview--mtop col-p-6">
        <h2 class="text-primary">Course Description</h2>
        <p>這門課介紹資料處理與分析</p>
        <div class="row sylview-mtop fa-border"></div>
      </div>
    </body>
    """

    # 最小 item/meta
    item = {
        "objective": "",
        "syllabus": "",
    }
    meta = {"item": item, "course_data": {}}

    resp = make_html_response("https://example.com/syl", html, meta)
    out = list(spider.parse_syllabus(resp))
    assert len(out) == 1
    result = out[0]
    assert result["objective"] == "教學目標一"
    assert "這門課介紹資料處理與分析" in result["syllabus"]


def test_build_urls_and_find_unit_helpers(spider):
    sem = "1141"
    list_url = spider.build_course_list(sem, "01", "A1", "105")
    assert ":sem=1141" in list_url and ":dp1=01" in list_url and ":dp2=A1" in list_url and ":dp3=105" in list_url

    zh = spider.build_course_detail_url_zh(f"{sem}754944001")
    en = spider.build_course_detail_url_en(f"{sem}754944001")
    assert zh == f"http://es.nccu.edu.tw/course/zh-TW/{sem}754944001/"
    assert en == f"http://es.nccu.edu.tw/course/en/{sem}754944001/"

    spider.unit_mapping = {
        "01-A1-105": {"unit": "單位X"},
        "01-B2-999": {"unit": "單位Y"},
    }
    # two-level
    info2 = spider._find_unit_info_for_two_level("01", "A1")
    assert info2 and info2["unit"] == "單位X"
    # one-level（回傳第一個匹配到的）
    info1 = spider._find_unit_info_for_one_level("01")
    assert info1 and info1["unit"] in {"單位X", "單位Y"}
