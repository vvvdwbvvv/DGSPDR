from typing import Optional, Dict, Any, List
import requests
from .auth import Authenticate
from .config import Config


class NCCUAPIClient:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self.auth = Authenticate(username, password)
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "NCCUCrawl/1.0",
                "Accept": "application/json",
            }
        )

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_json(self, url: str, **kwargs) -> List[Dict[str, Any]]:
        response = self._make_request("GET", url, **kwargs)
        return response.json()

    def post_json(self, url: str, **kwargs) -> List[Dict[str, Any]]:
        response = self._make_request("POST", url, **kwargs)
        return response.json()

    def delete_json(self, url: str, **kwargs) -> List[Dict[str, Any]]:
        response = self._make_request("DELETE", url, **kwargs)
        return response.json()


class CourseTracker(NCCUAPIClient):
    def add_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("Course ID cannot be empty")

        url = self.auth.get_addtrack_url(course_id)
        data = self.post_json(url)

        if not data or data[0].get("procid") != "1":
            raise Exception(f"Add track failed: {course_id}")

    def delete_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("Course ID cannot be empty")

        url = self.auth.get_deltrack_url(course_id)
        data = self.delete_json(url)

        if not data or data[0].get("procid") != "9":
            raise Exception(f"Delete track failed: {course_id}")

    def get_tracks(self) -> List[Dict[str, Any]]:
        url = self.auth.get_track_url()
        return self.get_json(url)

    def clear_all_tracks(self) -> None:
        tracks = self.get_tracks()
        for course in tracks:
            try:
                self.delete_track(str(course["subNum"]))
            except Exception:
                continue

    def batch_add_tracks(self, course_ids: List[str]) -> None:
        for course_id in course_ids:
            try:
                self.add_track(course_id)
            except Exception:
                continue
