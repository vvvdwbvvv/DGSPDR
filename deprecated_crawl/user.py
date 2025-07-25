from dotenv import load_dotenv
from os import getenv
import requests
from util import get_login_url, get_addtrack_url, get_deltrack_url, get_track_url
import logging

load_dotenv()


class User:
    _username: str
    _password: str
    _token: str
    _session: requests.Session

    def __init__(self) -> None:
        """初始化 User 類別，進行用戶身份驗證並獲取令牌。"""
        self._username = getenv("USERNAME") or ""
        self._password = getenv("PASSWORD") or ""
        self._session = requests.Session()
        try:
            login_url = get_login_url(self._username, self._password)
            response = self._session.get(login_url)
            response.raise_for_status()
            res = response.json()
            self._token = res[0]["encstu"]
            logging.info(f"User {self._username} authenticated successfully.")
        except (requests.RequestException, KeyError, IndexError) as e:
            logging.error(f"Failed to authenticate user {self._username}: {e}")
            raise Exception("Authentication error")

    def add_track(self, course_id: str):
        """添加課程到追蹤列表。

        Args:
            course_id (str): 課程 ID。

        Raises:
            Exception: 如果添加失敗。
        """
        try:
            add_url = get_addtrack_url(self._token, course_id)
            response = self._session.post(add_url)
            response.raise_for_status()
            addres = response.json()
            if addres[0]["procid"] != "1":
                raise Exception(f"Add fail: {course_id}")
            logging.info(f"Course {course_id} added to track successfully.")
        except (requests.RequestException, KeyError, IndexError) as e:
            logging.error(f"Failed to add track for course {course_id}: {e}")
            raise Exception(f"Add track error for {course_id}")

    def delete_track(self, course_id: str):
        """從追蹤列表中刪除課程。

        Args:
            course_id (str): 課程 ID。

        Raises:
            Exception: 如果刪除失敗。
        """
        try:
            del_url = get_deltrack_url(self._token, course_id)
            response = self._session.delete(del_url)
            response.raise_for_status()
            deleteres = response.json()
            if deleteres[0]["procid"] != "9":
                raise Exception(f"Delete fail: {course_id}")
            logging.info(f"Course {course_id} deleted from track successfully.")
        except (requests.RequestException, KeyError, IndexError) as e:
            logging.error(f"Failed to delete track for course {course_id}: {e}")
            raise Exception(f"Delete track error for {course_id}")

    def get_track(self) -> list[dict]:
        """獲取目前追蹤的課程列表。

        Returns:
            list[dict]: 追蹤課程的列表，每個課程為一個字典。
        """
        try:
            track_url = get_track_url(self._token)
            response = self._session.get(track_url)
            response.raise_for_status()
            courseres = response.json()
            logging.info(f"Fetched track data successfully for user {self._username}.")
            return courseres
        except (requests.RequestException, ValueError) as e:
            logging.error(f"Failed to fetch track data: {e}")
            return []
