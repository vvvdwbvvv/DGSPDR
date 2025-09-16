import unittest
import sqlite3
from unittest.mock import MagicMock, patch
from scrapy.http import Response, Request, TextResponse
import sys
import os
import logging

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from NCCUCrawl.spiders.teacher_deprecated import TeacherSpider, mask_token
from NCCUCrawl.items import TeacherLegacyItem


class MaskTokenTest(unittest.TestCase):
    def test_mask_token(self):
        text1 = "some/path/tracing/A/zh-TW/TOKEN123/other"
        masked1 = "some/path/tracing/A/zh-TW/***MASKED***/other"
        self.assertEqual(mask_token(text1), masked1)

        text2 = "another/tracing/C/zh-TW/123-TOKEN456/end"
        masked2 = "another/tracing/C/zh-TW/***MASKED***/end"
        self.assertEqual(mask_token(text2), masked2)

        text_no_match = "this should not be masked"
        self.assertEqual(mask_token(text_no_match), text_no_match)
        self.assertEqual(mask_token(""), "")
        self.assertIsNone(mask_token(None))


class TeacherSpiderTest(unittest.TestCase):
    def setUp(self):
        # Create an instance for testing
        with patch('logging.getLogger') as mock_get_logger:
            mock_get_logger.return_value = MagicMock()
            self.spider = TeacherSpider()
            self.logger_mock = mock_get_logger.return_value

        # Set other attributes manually
        self.spider.YEAR_SEM = "1141"
        self.spider.teacher_id_dict = {}
        self.spider.course_ids = []
        self.spider.batch_size = 10

    def test_iter_chunks(self):
        # Static method test doesn't use logger
        items = ['a', 'b', 'c', 'd', 'e']
        chunks = list(TeacherSpider._iter_chunks(items, 2))
        self.assertEqual(chunks, [['a', 'b'], ['c', 'd'], ['e']])

        chunks_empty = list(TeacherSpider._iter_chunks([], 2))
        self.assertEqual(chunks_empty, [])

    @patch('sqlite3.connect')
    @patch('NCCUCrawl.spiders.teacher_deprecated.Config')
    def test_init(self, mock_config, mock_connect):
        # Test initialization logic
        mock_config.return_value.YEAR = "114"
        mock_config.return_value.SEM = "1"

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [('754944001',)]

        # Create a new spider, patch logger during creation
        with patch('logging.getLogger') as mock_get_logger:
            mock_get_logger.return_value = MagicMock()
            spider = TeacherSpider(
                db_path="dummy.db",
                courses_list="002381001",
                year_sem="1141",
                batch_size=50
            )

        mock_connect.assert_called_with("dummy.db")
        self.assertEqual(spider.YEAR_SEM, "1141")
        self.assertEqual(spider.batch_size, 50)
        self.assertEqual(spider.course_ids, ['002381001', '754944001'])

    @patch('NCCUCrawl.spiders.teacher_deprecated.Authenticate')
    @patch('NCCUCrawl.spiders.teacher_deprecated.CourseTracker')
    def test_run_workflow_auth_failed(self, mock_tracker, mock_auth):
        # Set up mocks
        mock_auth_instance = MagicMock()
        mock_auth.return_value = mock_auth_instance
        mock_auth_instance.login.return_value = "ERROR"

        # Capture logs
        with self.assertLogs(level='ERROR') as log:
            results = list(self.spider._run_workflow())

        # Verify results
        self.assertEqual(results, [])
        # Check that the expected log message is present
        found = any("Authentication failed; stop spider" in message for message in log.output)
        self.assertTrue(found, f"Expected log message not found in logs: {log.output}")

    @patch('time.sleep')
    @patch('NCCUCrawl.spiders.teacher_deprecated.Authenticate')
    @patch('NCCUCrawl.spiders.teacher_deprecated.CourseTracker')
    def test_full_workflow(self, mock_course_tracker, mock_authenticate, mock_sleep):
        # Setup
        mock_auth_instance = MagicMock()
        mock_authenticate.return_value = mock_auth_instance
        mock_auth_instance.login.return_value = "DUMMY_TOKEN"

        mock_tracker_instance = MagicMock()
        mock_course_tracker.return_value = mock_tracker_instance

        self.spider.course_ids = ["754944001", "002381001"]
        self.spider.batch_size = 2
        self.spider.tracker = mock_tracker_instance

        # Configure mock response
        mock_tracker_instance.get_tracks.side_effect = [
            [{"subNum": "999999"}],
            [
                {"subNum": "754944001", "teaNam": "陳老師", "teaStatUrl": "https://newdoc.nccu.edu.tw/teaschm/1141/statisticAll.jsp-tnum=T000101.htm"},
                {"subNum": "002381001", "teaNam": "林老師", "teaStatUrl": "https://newdoc.nccu.edu.tw/teaschm/1141/set20.jsp?course=002381001"}
            ]
        ]

        # Use patch to replace the _process_course method with a mock
        with patch.object(self.spider, '_process_course') as mock_process:
            # Configure the mock to return our expected items
            item1 = TeacherLegacyItem(id='T000101', name='陳老師')
            request1 = Request(
                url="http://140.119.229.20/teaschm/1141/set20.jsp?course=002381001",
                callback=self.spider._parse_set20_big5,
                meta={"teacher_name_hint": "林老師"}
            )

            mock_process.side_effect = [
                [item1],
                [request1]
            ]

            # Execute the workflow
            results = list(self.spider._run_workflow())

            # Verify the results
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['id'], 'T000101')
            self.assertEqual(results[0]['name'], '陳老師')
            self.assertTrue(results[1].url.endswith("set20.jsp?course=002381001"))

            # Verify tracker interactions
            mock_tracker_instance.delete_track.assert_any_call("999999")
            mock_tracker_instance.add_track.assert_any_call("754944001")
            mock_tracker_instance.add_track.assert_any_call("002381001")
            mock_tracker_instance.delete_track.assert_any_call("754944001")
            mock_tracker_instance.delete_track.assert_any_call("002381001")
            self.assertEqual(mock_tracker_instance.get_tracks.call_count, 2)

    def test_process_course_statistic_all(self):
        url = "https://newdoc.nccu.edu.tw/teaschm/1141/statisticAll.jsp-tnum=T000123.htm"
        course = {"teaNam": "林老師", "teaStatUrl": url}

        results = list(self.spider._process_course(course))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], TeacherLegacyItem)
        self.assertEqual(results[0]['id'], 'T000123')
        self.assertEqual(results[0]['name'], '林老師')
        self.assertEqual(self.spider.teacher_id_dict['林老師'], 'T000123')

    def test_process_course_set20(self):
        url = "https://newdoc.nccu.edu.tw/teaschm/1141/set20.jsp?course=123&class=A"
        course = {"teaNam": "張老師", "teaStatUrl": url}

        results = list(self.spider._process_course(course))

        self.assertEqual(len(results), 1)
        request = results[0]
        self.assertIsInstance(request, Request)
        self.assertEqual(request.url, "http://140.119.229.20/teaschm/1141/set20.jsp?course=123&class=A")
        self.assertEqual(request.callback, self.spider._parse_set20_big5)
        self.assertEqual(request.meta['teacher_name_hint'], '張老師')

    def test_parse_set20_big5(self):
        html_body = """
        <tr><td>王大明</td><td><a href="...statisticAll.jsp-tnum=T98765.htm">link</a></td></tr>
        <tr><td></td><td><a href="...statisticAll.jsp-tnum=T54321.htm">link</a></td></tr>
        """
        # Use TextResponse which allows us to set request with meta
        request = Request(url="http://example.com", meta={"teacher_name_hint": "備用名"})
        response = TextResponse(
            url="http://example.com",
            body=html_body.encode('big5'),
            encoding='big5',
            request=request
        )

        results = list(self.spider._parse_set20_big5(response))

        self.assertEqual(len(results), 2)
        item1, item2 = results[0], results[1]
        self.assertEqual(item1['id'], 'T98765')
        self.assertEqual(item1['name'], '王大明')
        self.assertEqual(item2['id'], 'T54321')
        self.assertEqual(item2['name'], '備用名')

    @patch('time.sleep')
    def test_get_tracks_with_retry(self, mock_sleep):
        tracker_mock = MagicMock()
        self.spider.tracker = tracker_mock

        tracker_mock.get_tracks.side_effect = [Exception("fail"), ["track1"]]
        result = self.spider._get_tracks_with_retry()
        self.assertEqual(result, ["track1"])
        self.assertEqual(tracker_mock.get_tracks.call_count, 2)
        mock_sleep.assert_called_once()

        tracker_mock.reset_mock()
        mock_sleep.reset_mock()
        tracker_mock.get_tracks.side_effect = [Exception("fail1"), Exception("fail2"), Exception("fail3")]
        with self.assertRaisesRegex(Exception, "fail3"):
            self.spider._get_tracks_with_retry(tries=3)
        self.assertEqual(tracker_mock.get_tracks.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()