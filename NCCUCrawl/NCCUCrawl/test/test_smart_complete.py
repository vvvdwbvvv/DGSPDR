# tests/spiders/test_smart_courses.py
import os
import sys
import json
import types
import pytest
from scrapy.http import Request, TextResponse, HtmlResponse
from scrapy.exceptions import DontCloseSpider

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
from NCCUCrawl.spiders.courses_deprecated_patch import SmartCoursesSpider, DatabaseComparator
from NCCUCrawl.items import CourseLegacyItem


def make_text_response(url: str, text: str, meta=None):
    req = Request(url=url, meta=meta or {})
    return TextResponse(url=url, request=req, body=text.encode("utf-8"), encoding="utf-8")


def make_html_response(url: str, html: str, meta=None):
    req = Request(url=url, meta=meta or {})
    return HtmlResponse(url=url, request=req, body=html.encode("utf-8"), encoding="utf-8")


@pytest.fixture
def sample_units():
    # 1 個 L1 / 1 個 L2 / 1 個 L3（最小可行）
    return [
        {
            "utCodL1": "01",
            "utL1Text": "測試學院 / Test College",
            "utL2": [
                {"utCodL2": "A1", "utL2Text": "測試系A1 / Dept A1", "utL3": [
                    {"utCodL3": "105", "utL3Text": "單位X / Unit X"}
                ]}
            ],
        }
    ]


@pytest.fixture
def sample_courses_list():
    return [
        {"subNum": "B", "subNam": "課程B", "subPoint": "2", "subGde": "單位X"},
        {"subNum": "C", "subNam": "課程C", "subPoint": "3", "subGde": "單位X"},
    ]


@pytest.fixture
def spider(tmp_path, sample_units):
    s = SmartCoursesSpider()

    # 建立假的 comparator（CSV: A,B / DB: A）
    comp = types.SimpleNamespace()
    comp.existing_courses = {"A"}
    comp.csv_courses = {"A", "B"}

    def _get_missing(semester, dp1, dp2, dp3, api_courses, search_level="unknown"):
        out = []
        for c in api_courses:
            if c["subNum"] in comp.csv_courses and c["subNum"] not in comp.existing_courses:
                cc = dict(c)
                cc["_missing_reason"] = "in_csv_not_in_db"
                cc["_full_course_id"] = f"{semester}{c['subNum']}"
                cc["_search_level"] = search_level
                cc["_category_key"] = f"{dp1}-{dp2}-{dp3}" if (dp1 or dp2 or dp3) else "∅-∅-∅"
                out.append(cc)
        return out

    comp.get_missing_courses_for_category = _get_missing
    s.comparator = comp

    # 建 unit_mapping 供 parse_smart_course_list 取用
    s.unit_mapping = {"01-A1-105": {"unit": "單位X"}}

    return s


def test_parse_units_emits_smart_hierarchical_requests(spider, sample_units):
    resp = make_text_response(
        "https://qrysub.nccu.edu.tw/assets/api/unit.json", json.dumps(sample_units)
    )
    out = list(spider.parse_units(resp))
    # 會產生：三階層、二階層、一階層、零階層 共 4 個請求，callback= parse_smart_course_list
    assert len(out) == 4
    assert sorted([r.meta["search_level"] for r in out]) == ["one_level", "three_level", "two_level", "zero_level"]
    assert all(r.callback.__name__ == "parse_smart_course_list" for r in out)


def test_parse_smart_course_list_filters_and_schedules(spider, sample_courses_list):
    sem = "1141"
    url = spider.build_course_list(sem, "01", "A1", "105")
    resp = make_text_response(url, json.dumps(sample_courses_list))

    spider.missing_courses = {"B"}
    spider.remaining_missing = {"B"}
    spider.scheduled_courses = set()

    # B 在 CSV 且不在 DB，C 不在 CSV → 只會排 B
    out = list(spider.parse_smart_course_list(resp, sem, "01", "A1", "105", search_level="three_level"))
    assert len(out) == 1
    req = out[0]
    assert req.callback.__name__ == "parse_course_detail_zh"
    assert req.meta["sub_num"] == "B"
    assert "original_url" in req.meta
    assert req.url.startswith("http://es.nccu.edu.tw/course/zh-TW/1141B/")
    # 已標記排程
    assert "B" in spider.scheduled_courses
    # 統計
    st = spider.hierarchical_stats["three_level"]
    assert st["categories"] == 1
    assert st["courses"] == 2
    assert st["new_courses"] == 1
    assert st["missing_found"] == 1

    # 再丟一次同樣列表，B 已排程 → 不會再產生
    resp2 = make_text_response(url, json.dumps(sample_courses_list))
    out2 = list(spider.parse_smart_course_list(resp2, sem, "01", "A1", "105", search_level="three_level"))
    assert len(out2) == 0


def test_process_course_item_tracks_and_yields(spider):
    spider.remaining_missing = {"B"}
    item = {
        "id": "1141B",
        "subNum": "B",
        "y": "114",
        "s": "1",
        "name": "",
        "teacher": "",
        "classroom": "",
        "time": "",
        "point": None,
        "lang": "",
        "lmtKind": "",
        "tranTpe": "",
        "info": "",
        "note": "",
        "kind": 0,
        "core": 0,
        "nameEn": "",
        "teacherEn": "",
        "timeEn": "",
        "lmtKindEn": "",
        "langEn": "",
        "classroomId": "",
        "tranTpeEn": "",
        "infoEn": "",
        "unitEn": "",
        "noteEn": "",
        "dp1": "",
        "dp2": "",
        "dp3": "",
        "unit": "",
        "semQty": "",
        "subRemainUrl": "",
        "subSetUrl": "",
        "subUnitRuleUrl": "",
        "teaExpUrl": "",
        "teaSchmUrl": "",
        "syllabus": "",
        "objective": "",
    }

    out = list(spider.process_course_item(item, {"subNum": "B"}))
    assert len(out) == 1
    assert isinstance(out[0], CourseLegacyItem)
    # 成功處理追蹤
    assert "B" in spider.successfully_processed
    assert "B" not in spider.remaining_missing
    assert spider.total_saved_courses == 1


def test_parse_course_detail_zh_updates_then_to_en(spider):
    # 準備 meta 與 item
    sem = "1141"
    course_id = f"{sem}B"
    item = CourseLegacyItem(
        id=course_id, subNum="B", y="114", s="1",
        name="", teacher="", classroom="", time="", point=None, lang="", lmtKind="",
        tranTpe="", info="", note="", kind=0, core=0, nameEn="", teacherEn="",
        timeEn="", lmtKindEn="", langEn="", classroomId="", tranTpeEn="", infoEn="",
        unitEn="", noteEn="", dp1="01", dp2="A1", dp3="105", unit="", semQty="",
        subRemainUrl="", subSetUrl="", subUnitRuleUrl="", teaExpUrl="", teaSchmUrl="",
        syllabus="", objective=""
    )
    meta = {
        "item": item,
        "course_data": {},
        "course_id": course_id,
        "semester": sem,
        "dp1": "01", "dp2": "A1", "dp3": "105",
        "search_level": "three_level",
        "category_key": "01-A1-105",
        "sub_num": "B",
        "original_url": f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/",
    }

    zh_payload = [{
        "teaNam": "王小明", "subKind": "必修", "subTime": "一34",
        "lmtKind": "通識向度", "core": "是", "langTpe": "中文",
        "subClassroom": "CBA101", "tranTpe": "實體", "info": "資訊", "note": "備註",
        "subNam": "資料處理", "subGde": "單位X", "subPoint": "2",
        "teaSchmUrl": "https://example.com/syl-B", "smtQty": "1"
    }]
    resp = make_text_response(f"http://es.nccu.edu.tw/course/zh-TW/{course_id}/?_smart_x", json.dumps(zh_payload), meta)
    out = list(spider.parse_course_detail_zh(resp))
    # 會接著請 EN
    assert len(out) == 1
    en_req = out[0]
    assert en_req.callback.__name__ == "parse_course_detail_en"
    updated = en_req.meta["item"]
    assert updated["teacher"] == "王小明"
    assert updated["kind"] in (4, 1)  # lmtKind=通識向度 → 4（程式邏輯會以 lmtKind 特例覆蓋）
    assert updated["core"] == 1
    assert updated["time"] == "一34"
    assert updated["name"] == "資料處理"
    assert updated["unit"] == "單位X"
    assert updated["point"] == "2"
    assert updated["teaSchmUrl"] == "https://example.com/syl-B"


def test_parse_course_detail_en_then_syllabus(spider):
    sem = "1141"
    course_id = f"{sem}B"
    item = CourseLegacyItem(
        id=course_id, subNum="B", y="114", s="1",
        name="", teacher="", classroom="", time="", point=None, lang="", lmtKind="",
        tranTpe="", info="", note="", kind=0, core=0, nameEn="", teacherEn="",
        timeEn="", lmtKindEn="", langEn="", classroomId="", tranTpeEn="", infoEn="",
        unitEn="", noteEn="", dp1="01", dp2="A1", dp3="105", unit="", semQty="",
        subRemainUrl="", subSetUrl="", subUnitRuleUrl="", teaExpUrl="", teaSchmUrl="https://example.com/syl-B",
        syllabus="", objective=""
    )
    meta = {"item": item, "course_data": {"teaSchmUrl": "https://example.com/syl-B"}, "course_id": course_id}
    # 注意：你的程式用 'sumkbTime'（看起來像原 API 的 typo），我們照著餵
    en_payload = [{
        "subNam": "Data Processing", "teaNam": "Ming Wang", "sumkbTime": "Mon.34",
        "lmtKind": "GE", "langTpe": "English", "subClassroom": "CBA101",
        "tranTpe": "In-person", "info": "info EN", "subGde": "UnitX EN", "note": "note EN"
    }]
    resp = make_text_response(f"http://es.nccu.edu.tw/course/en/{course_id}/?_smart_en", json.dumps(en_payload), meta)
    out = list(spider.parse_course_detail_en(resp))
    # 有 syllabus URL → 會再抓 syllabus
    assert len(out) == 1
    syl_req = out[0]
    assert syl_req.callback.__name__ == "parse_syllabus"
    it = syl_req.meta["item"]
    assert it["nameEn"] == "Data Processing"
    assert it["teacherEn"] == "Ming Wang"
    assert it["timeEn"] == "Mon.34"


def test_parse_syllabus_extracts_and_yields(spider):
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
    item = CourseLegacyItem(
        id="1141B", subNum="B", y="114", s="1",
        name="", teacher="", classroom="", time="", point=None, lang="", lmtKind="",
        tranTpe="", info="", note="", kind=0, core=0, nameEn="", teacherEn="",
        timeEn="", lmtKindEn="", langEn="", classroomId="", tranTpeEn="", infoEn="",
        unitEn="", noteEn="", dp1="", dp2="", dp3="", unit="", semQty="",
        subRemainUrl="", subSetUrl="", subUnitRuleUrl="", teaExpUrl="", teaSchmUrl="",
        syllabus="", objective=""
    )
    resp = make_html_response("https://example.com/syl-B", html, {"item": item, "course_data": {}})
    out = list(spider.parse_syllabus(resp))
    assert len(out) == 1
    it = out[0]
    assert it["objective"] == "教學目標一"
    assert "這門課介紹資料處理與分析" in it["syllabus"]


def test_handle_request_error_unschedules_and_counts(spider):
    spider.scheduled_courses = {"Z"}
    spider.remaining_missing = set()
    # 構造最小 Failure stub：具有 .request.meta
    class _Req: 
        def __init__(self): self.meta = {"course_id": "1141Z", "sub_num": "Z"}
    class _Failure:
        def __init__(self): self.request = _Req()
        def __str__(self): return "failure"
    spider.handle_request_error(_Failure())
    assert spider.failed_requests == 1
    assert "Z" not in spider.scheduled_courses
    assert "Z" in spider.remaining_missing


def test_spider_idle_schedules_direct_crawls_and_raises(tmp_path):
    s = SmartCoursesSpider()
    s.comparator = types.SimpleNamespace(existing_courses=set(), csv_courses=set())  # 允許屬性存取
    s.remaining_missing = {"070394021", "999999999"}
    s.scheduled_courses = set()
    s.successfully_processed = set()
    s.api_limit = 5
    s.detail_request_count = 0

    # 假 crawler.engine 收集 crawl(req)
    class DummyEngine:
        def __init__(self): self.requests = []
        def crawl(self, req): self.requests.append(req)
    class DummyCrawler:
        def __init__(self): self.engine = DummyEngine()
    s.crawler = DummyCrawler()

    with pytest.raises(DontCloseSpider):
        s.spider_idle()

    # 應該排入兩個 direct zh 詳細頁請求
    reqs = s.crawler.engine.requests
    assert len(reqs) == 2
    urls = [r.url for r in reqs]
    assert all(u.startswith("http://es.nccu.edu.tw/course/zh-TW/1141") for u in urls)
    assert any("_direct_0" in u for u in urls) or any("_direct_1" in u for u in urls)
    # meta 正確
    for r in reqs:
        assert r.meta["is_direct_crawl"] is True
        assert "sub_num" in r.meta
    # 計數被增加
    assert s.detail_request_count == 2


def test_spider_idle_hit_api_limit(tmp_path):
    s = SmartCoursesSpider()
    s.comparator = types.SimpleNamespace(existing_courses=set(), csv_courses=set())
    s.remaining_missing = {"070394021"}
    s.scheduled_courses = set()
    s.successfully_processed = set()
    s.api_limit = 10
    s.detail_request_count = 10  # 沒額度
    class DummyEngine:
        def __init__(self): self.requests = []
        def crawl(self, req): self.requests.append(req)
    class DummyCrawler:
        def __init__(self): self.engine = DummyEngine()
    s.crawler = DummyCrawler()

    # 不會 raise，也不會新增 request
    s.spider_idle()
    assert len(s.crawler.engine.requests) == 0
