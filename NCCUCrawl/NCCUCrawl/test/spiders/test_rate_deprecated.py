import asyncio
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


if "scrapy" not in sys.modules:
    scrapy_stub = types.ModuleType("scrapy")

    class _Spider:
        name = "stub"

    class _Item(dict):
        pass

    def _field():
        return None

    scrapy_stub.Spider = _Spider
    scrapy_stub.Item = _Item
    scrapy_stub.Field = _field

    class _Request:
        def __init__(self, url, callback=None, meta=None, encoding=None):
            self.url = url
            self.callback = callback
            self.meta = meta or {}
            self.encoding = encoding

    class _TextResponse:
        def __init__(self, url, body, encoding="utf-8", request=None):
            self.url = url
            self.body = body
            self.encoding = encoding
            self.request = request
            self.meta = getattr(request, "meta", {}) if request else {}
            self._table = None

        def css(self, query):
            if query == 'table[border="1"]':
                return DummySelectorList([self._table] if self._table else [])
            return DummySelectorList([])

    http_module = types.ModuleType("scrapy.http")
    http_module.Request = _Request
    http_module.TextResponse = _TextResponse
    scrapy_stub.http = http_module
    scrapy_stub.Request = _Request
    scrapy_stub.TextResponse = _TextResponse

    class DummySelectorList(list):
        def __init__(self, items):
            super().__init__(items)

        def css(self, query):
            aggregated = []
            for item in self:
                if hasattr(item, "css"):
                    result = item.css(query)
                    if isinstance(result, DummySelectorList):
                        aggregated.extend(result)
                    else:
                        aggregated.append(result)
            return DummySelectorList(aggregated)

        def get(self):
            return self[0] if self else None

    scrapy_stub.DummySelectorList = DummySelectorList

    sys.modules["scrapy"] = scrapy_stub
    sys.modules["scrapy.http"] = http_module

from scrapy.http import Request, TextResponse

from NCCUCrawl.items import RateLegacyItem
from NCCUCrawl.spiders.rate_deprecated import RateDeprecatedSpider


class DummySelectorList(types.SimpleNamespace):
    def __iter__(self):
        return iter(self.items)


class DummyCell:
    def __init__(self, text=None, link=None):
        self.text = text
        self.link = link

    def css(self, query):
        if query == "::text" or query == "td::text":
            return DummySelector([self.text] if self.text is not None else [])
        if query == "a::attr(href)":
            return DummySelector([self.link] if self.link else [])
        return DummySelector([])


class DummyRow:
    def __init__(self, cells):
        self.cells = cells

    def css(self, query):
        if query == "td":
            return DummySelector(self.cells)
        if query == "td::text":
            texts = []
            for cell in self.cells:
                texts.extend(cell.css("::text").items)
            return DummySelector(texts)
        return DummySelector([])


class DummyTable:
    def __init__(self, rows):
        self.rows = rows

    def css(self, query):
        if query == "tr":
            return DummySelector(self.rows)
        return DummySelector([])


class DummySelector:
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __bool__(self):
        return bool(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def css(self, query):
        aggregated = []
        for item in self.items:
            if hasattr(item, "css"):
                result = item.css(query)
                if isinstance(result, DummySelector):
                    aggregated.extend(result.items)
                else:
                    aggregated.append(result)
        return DummySelector(aggregated)

    def get(self):
        return self.items[0] if self.items else None


class DummyResponse(TextResponse):
    def __init__(self, url, table, request):
        super().__init__(url=url, body=b"", encoding="utf-8", request=request)
        self._table = table

    def css(self, query):
        if query == 'table[border="1"]':
            return DummySelector([self._table] if self._table else [])
        return DummySelector([])


class RateDeprecatedSpiderTest(unittest.TestCase):
    def setUp(self):
        with patch("logging.getLogger") as mock_get_logger:
            mock_get_logger.return_value = MagicMock()
            self.spider = RateDeprecatedSpider()

    @patch("sqlite3.connect")
    def test_start_generates_requests_for_teachers(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("張老師", "T000001"),
            ("李老師", "T000002"),
        ]

        async def collect_requests():
            with patch.dict(os.environ, {"YEAR": "114", "SEM": "1"}, clear=True):
                results = []
                async for request in self.spider.start():
                    results.append(request)
                return results

        requests = asyncio.run(collect_requests())

        self.assertEqual(len(requests), 2)
        self.assertIsInstance(requests[0], Request)
        self.assertTrue(requests[0].url.endswith("statistic.jsp-tnum=T000001.htm"))
        self.assertEqual(requests[0].meta["teacher_id"], "T000001")
        self.assertEqual(requests[0].meta["teacher_name"], "張老師")
        self.assertEqual(requests[0].meta["semester"], "1141")

    def test_parse_teacher_courses_emits_rate_requests(self):
        request = Request(
            url="http://example.com/statistic",
            meta={"teacher_id": "T000001", "teacher_name": "張老師", "semester": "1141"},
        )

        row = DummyRow(
            [
                DummyCell("123"),
                DummyCell("456"),
                DummyCell("789"),
                DummyCell(link="rate.jsp?param=123"),
            ]
        )
        table = DummyTable([row])
        response = DummyResponse(url=request.url, table=table, request=request)

        results = list(self.spider.parse_teacher_courses(response))

        self.assertEqual(len(results), 1)
        rate_request = results[0]
        self.assertIsInstance(rate_request, Request)
        self.assertIn("rate.jsp?param=123", rate_request.url)
        self.assertEqual(rate_request.meta["course_id"], "123456789")
        self.assertEqual(rate_request.meta["teacher_id"], "T000001")

    def test_parse_rate_yields_items(self):
        request = Request(
            url="http://example.com/rate",
            meta={"teacher_id": "T000001", "course_id": "001002003"},
        )

        row1 = DummyRow([DummyCell("好課程")])
        row2 = DummyRow([DummyCell("值得推薦")])
        table = DummyTable([row1, row2])
        response = DummyResponse(url=request.url, table=table, request=request)

        items = list(self.spider.parse_rate(response))

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["courseId"], "001002003")
        self.assertEqual(items[0]["teacherId"], "T000001")
        self.assertEqual(items[0]["content"], "好課程")


if __name__ == "__main__":
    unittest.main()
