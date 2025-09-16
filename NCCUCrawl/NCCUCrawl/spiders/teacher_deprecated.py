import time
import scrapy
import sqlite3
from scrapy import signals
from typing import List
from ..items import TeacherLegacyItem
from ..auth_curl import Authenticate
from ..client import CourseTracker
from ..config import Config


def mask_token(text: str) -> str:
    if not text:
        return text
    import re

    t = re.sub(r"(/tracing/(?:[A-Z]/)?zh-TW/)([^/\s]+)", r"\1***MASKED***", text)
    t = re.sub(r"(/tracing/[CU]/zh-TW/\d+-)([^/\s]+)", r"\1***MASKED***", t)
    return t


class TeacherSpider(scrapy.Spider):
    name = "teacher_legacy"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.2,
        "CONCURRENT_REQUESTS": 16,
        "RETRY_TIMES": 2,
        "LOG_LEVEL": "INFO",
    }

    def __init__(
        self,
        db_path="data.db",
        courses_list=None,
        year_sem=None,
        batch_size=100,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect(db_path)
        self.cfg = Config()
        self.YEAR_SEM = year_sem or f"{self.cfg.YEAR}{self.cfg.SEM}"

        arg_ids: List[str] = []
        if isinstance(courses_list, str):
            arg_ids = [x.strip() for x in courses_list.split(",") if x.strip()]

        db_ids = self._load_course_ids_from_db(db_path, self.YEAR_SEM)
        self.course_ids: List[str] = sorted(set(arg_ids) | set(db_ids))

        # 批次大小（可由 -a batch_size=200 覆寫）
        try:
            self.batch_size = int(batch_size) if int(batch_size) > 0 else 100
        except Exception:
            self.batch_size = 100

        self.tracker: CourseTracker | None = None
        self.teacher_id_dict: dict[str, str] = {}
        self._shutdown = False

    def _load_course_ids_from_db(self, db_path: str, year_sem: str) -> List[str]:
        """
        Return list of subNum values for courses where id starts with year_sem.
        Example: year_sem='1121' will match ids like '112110001', '112120002'
        """
        try:
            cur = self.conn.cursor()
            # Query all subNum where course id starts with year_sem
            cur.execute(
                """
                        SELECT DISTINCT subNum
                        FROM COURSE
                        WHERE id LIKE ? || '%'
                          AND subNum IS NOT NULL
                        """,
                (year_sem,),
            )

            rows = cur.fetchall()
            result = [str(r[0]) for r in rows if r and r[0]]

            self.logger.info(
                "Loaded %d course ids for year_sem %s", len(result), year_sem
            )
            return result

        except Exception as e:
            self.logger.warning(
                "Failed to load course ids from db: %s", mask_token(str(e))
            )
            return []

    # --- batch helper ---
    @staticmethod
    def _iter_chunks(items: List[str], size: int):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    async def start(self):
        """New async entrypoint (Scrapy 2.13+)"""
        async for request in self._agen_workflow():
            yield request

    def start_requests(self):
        yield from self._run_workflow()

    async def _agen_workflow(self):
        """Async generator version of _run_workflow"""
        for request in self._run_workflow():
            yield request

    def _run_workflow(self):
        auth = Authenticate()
        token = auth.login()
        if not token or str(token).upper() == "ERROR":
            self.logger.error("Authentication failed; stop spider")
            return

        self.tracker = CourseTracker(auto_login=False)
        self.tracker.set_token(token)

        # 先清理目前系統內既有的追蹤紀錄
        try:
            tracks = self._get_tracks_with_retry()
            for c in tracks or []:
                cid = str(c.get("subNum") or "").strip()
                if cid:
                    try:
                        self.tracker.delete_track(cid)
                    except Exception as e:
                        self.logger.warning(
                            "cleanup skip %s: %s", cid, mask_token(str(e))
                        )
        except Exception as e:
            self.logger.error("cleanup pre-get failed: %s", mask_token(str(e)))

        # === batch processing ===
        total = len(self.course_ids)
        if total == 0:
            self.logger.info("No course ids to process.")
            return

        for idx, chunk in enumerate(
            self._iter_chunks(self.course_ids, self.batch_size), start=1
        ):
            self.logger.info(
                "Processing batch %d: %d items (progress %d/%d)",
                idx,
                len(chunk),
                min(idx * self.batch_size, total),
                total,
            )

            # add track
            for cid in chunk:
                try:
                    self.tracker.add_track(cid)
                except Exception as e:
                    self.logger.warning("add skip %s: %s", cid, mask_token(str(e)))

            # fetch & process
            try:
                tracked = self._get_tracks_with_retry() or []
                want = {c.strip() for c in chunk}
                for course in tracked:
                    cid = str(course.get("subNum") or "").strip()
                    if cid and cid in want:
                        # 只處理本批
                        yield from self._process_course(course)
            except Exception as e:
                self.logger.error(
                    "fetch updated tracks failed (batch %d): %s",
                    idx,
                    mask_token(str(e)),
                )

            # after process, delete track
            for cid in chunk:
                try:
                    self.tracker.delete_track(cid)
                except Exception as e:
                    self.logger.debug(
                        "batch cleanup skip %s: %s", cid, mask_token(str(e))
                    )

            # optional delay
            time.sleep(0.1)

    def _get_tracks_with_retry(self, tries: int = 3, backoffs=(0.2, 0.5, 1.0)):
        last_err = None
        for i in range(tries):
            try:
                return self.tracker.get_tracks()
            except Exception as e:
                last_err = e
                if i < tries - 1:
                    time.sleep(backoffs[min(i, len(backoffs) - 1)])
        if last_err:
            raise last_err

    def _process_course(self, course: dict):
        try:
            teacher_stat_url = str(course.get("teaStatUrl") or "")
            teacher_name = (course.get("teaNam") or "").strip()
            if not teacher_stat_url:
                self.logger.debug("No teacher_stat_url in course: %r", course)
                return

            prefix_plain = (
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/statisticAll.jsp"
            )
            if (
                teacher_stat_url.startswith(prefix_plain)
                and "statisticAll.jsp-tnum=" in teacher_stat_url
            ):
                tid = teacher_stat_url.split("statisticAll.jsp-tnum=")[1].split(".htm")[
                    0
                ]
                if tid:
                    self.teacher_id_dict[teacher_name] = tid
                    yield TeacherLegacyItem(id=tid, name=teacher_name)
                return

            prefix_set20 = (
                f"https://newdoc.nccu.edu.tw/teaschm/{self.YEAR_SEM}/set20.jsp"
            )
            if teacher_stat_url.startswith(prefix_set20):
                url = teacher_stat_url.replace(
                    "newdoc.nccu.edu.tw", "140.119.229.20"
                ).replace("https://", "http://")
                yield scrapy.Request(
                    url=url,
                    callback=self._parse_set20_big5,
                    errback=self._err_parse_set20,
                    meta={"teacher_name_hint": teacher_name, "download_timeout": 10},
                    dont_filter=True,
                )
            else:
                self.logger.debug(
                    "Unknown teacher_stat_url pattern: %s", teacher_stat_url
                )

        except Exception as e:
            self.logger.error("process course error: %s", mask_token(str(e)))

    def _err_parse_set20(self, failure):
        self.logger.warning("set20 request failed: %s", mask_token(str(failure.value)))
        self.logger.debug("Failed URL: %s", failure.request.url)

    def _parse_set20_big5(self, response: scrapy.http.Response):
        try:
            sel = response
            for row in sel.css("tr"):
                tds = row.css("td")
                if len(tds) < 2:
                    continue
                link = tds[1].css("a::attr(href)").get()
                raw_name = (tds[0].css("::text").get() or "").strip()
                if link and "statisticAll.jsp-tnum=" in link:
                    tid = link.split("statisticAll.jsp-tnum=")[1].split(".htm")[0]
                    if tid:
                        name = raw_name or response.meta.get("teacher_name_hint", "")
                        self.teacher_id_dict[name] = tid
                        yield TeacherLegacyItem(id=tid, name=name)
        except Exception as e:
            self.logger.error("parse set20 error: %s", mask_token(str(e)))

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider, reason):
        rs = (str(reason) or "").lower()
        if rs in {"shutdown", "cancelled", "keyboard interrupt"}:
            self._shutdown = True
        self.logger.info(
            "Spider closed via signal: %s (shutdown=%s)", reason, self._shutdown
        )

    def closed(self, reason):
        if self._shutdown or not self.tracker:
            return

        try:
            for c in self._get_tracks_with_retry() or []:
                cid = str(c.get("subNum") or "").strip()
                if not cid:
                    continue
                try:
                    self.tracker.delete_track(cid)
                except Exception as e:
                    self.logger.debug(
                        "final cleanup skip %s: %s", cid, mask_token(str(e))
                    )
        except Exception as e:
            self.logger.debug("final cleanup get_tracks failed: %s", mask_token(str(e)))
