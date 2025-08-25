from typing import List, Dict, Any, Optional
import requests
from .auth import Authenticate
from .config import Config


class CourseTracker:
    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 auto_login: bool = True):
        self.config = Config()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "NCCUCrawl/1.0",
            "Accept": "application/json",
        })
        self.auth = Authenticate(username, password)
        self._token: Optional[str] = None

        if auto_login:
            token = self.auth.login()  # 建議你的 Authenticate.login() 直接回傳 token
            if not token or str(token).upper() == "ERROR":
                raise RuntimeError("Login failed: encstu token missing or ERROR")
            self._token = token


    def set_token(self, token: str) -> None:
        if not token or str(token).upper() == "ERROR":
            raise ValueError("Invalid token")
        self._token = token

    def get_token(self) -> str:
        if not self._token:
            raise RuntimeError("Token not set. Call login() or set_token() first.")
        return self._token


    def _request_json(self, method: str, url: str) -> List[Dict[str, Any]]:
        r = self._session.request(method, url, timeout=15)
        r.raise_for_status()
        return r.json()


    def add_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("course_id cannot be empty")
        token = self.get_token()
        url = self.config.get_addtrack_url(token, course_id)
        data = self._request_json("POST", url)
        if not data or data[0].get("procid") != "1":
            raise RuntimeError(f"Add track failed: {course_id}")

    def delete_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("course_id cannot be empty")
        token = self.get_token()
        url = self.config.get_deltrack_url(token, course_id)
        data = self._request_json("DELETE", url)
        if not data or data[0].get("procid") != "9":
            raise RuntimeError(f"Delete track failed: {course_id}")

    def get_tracks(self) -> List[Dict[str, Any]]:
        token = self.get_token()
        url = self.config.get_track_url(token)
        return self._request_json("GET", url)
    
    def clear_all_tracks(self) -> None:
        for c in self.get_tracks() or []:
            cid = str(c.get("subNum") or "").strip()
            if not cid:
                continue
            try:
                self.delete_track(cid)
            except Exception:
                continue

    def batch_add_tracks(self, course_ids: List[str]) -> None:
        for cid in course_ids:
            if not cid:
                continue
            try:
                self.add_track(cid)
            except Exception:
                continue
