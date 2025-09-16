from typing import List, Dict, Any, Optional
import os
import json
import shutil
import subprocess
import logging
from .auth import Authenticate
from .config import Config


class CourseTracker:
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auto_login: bool = True,
    ):
        self.config = Config()
        self._curl_path = shutil.which("curl") or "/usr/bin/curl"
        if not os.path.exists(self._curl_path):
            raise RuntimeError("curl not found in PATH")

        self._default_headers = {
            "User-Agent": "NCCUCrawl/1.0",
            "Accept": "application/json",
        }

        self.auth = Authenticate(username, password)
        self._token: Optional[str] = None

        if auto_login:
            token = self.auth.login()
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

    # ---------------- Low-level: curl ----------------

    def _curl_run(
        self, method: str, url: str, headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        用系統 curl 發請求，帶上 TLS 1.2 + allow beast（可過 NCCU 伺服器）。
        失敗會丟出 CalledProcessError（附帶 response body）。
        """
        cmd = [
            self._curl_path,
            "-X",
            method,
            url,
            "-H",
            f"User-Agent: {self._default_headers['User-Agent']}",
            "-H",
            f"Accept: {self._default_headers['Accept']}",
            "--ssl-allow-beast",
            "--tls-max",
            "1.2",
            "--fail-with-body",
            "-sS",
            "--compressed",
        ]

        if method.upper() == "POST":
            cmd += ["--data", ""]
            cmd += ["-H", "Content-Type: text/plain"]

        for k, v in (headers or {}).items():
            cmd += ["-H", f"{k}: {v}"]

        merge_stderr = True
        if os.getenv("DEBUG_CURL") == "1":
            cmd.append("-v")
            merge_stderr = False

        stderr_pipe = subprocess.STDOUT if merge_stderr else None
        out = subprocess.check_output(cmd, stderr=stderr_pipe)
        return out.decode("utf-8", "replace")

    def _request_json(self, method: str, url: str) -> List[Dict[str, Any]]:
        try:
            out = self._curl_run(method, url)
            return json.loads(out)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"curl {method} {url} failed: {e.output.decode('utf-8', 'replace')}"
            )
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid JSON from {url}: {out[:200]}")

    def update_track(self, course_id: str) -> None:
        """
        呼叫 U/zh-TW/{course_id}-{encstu}/
        確認追蹤清單有被更新
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        token = self.get_token()
        url = self.config.get_updatetrack_url(token, course_id)
        data = self._request_json("POST", url)

        if not data or data[0].get("procid") != "5":
            raise RuntimeError(f"Update track failed: {course_id}")

    def add_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("course_id cannot be empty")
        token = self.get_token()
        url = self.config.get_addtrack_url(token, course_id)
        try:
            data = self._request_json("POST", url)
            if not data:
                raise RuntimeError("Empty response")

            proc_id = data[0].get("procid")
            error_msg = data[0].get("msg", "Unknown error")

            if proc_id == "1":
                return  # Success
            elif proc_id in {"2", "3", "4"}:  # Known error codes
                raise RuntimeError(f"{error_msg}")
            else:
                raise RuntimeError(f"Invalid procid '{proc_id}': {error_msg}")

        except ValueError as ve:
            logging.warning(
                f"add skip {course_id}: Add track failed: {course_id} - Invalid procid '{proc_id}': {str(ve)}"
            )
            return False
        except Exception as e:
            logging.error(f"add skip {course_id}: Unexpected error: {str(e)}")
            return False

    def delete_track(self, course_id: str) -> None:
        if not course_id:
            raise ValueError("course_id cannot be empty")
        token = self.get_token()
        url = self.config.get_deltrack_url(token, course_id)
        data = self._request_json("POST", url)
        if not data or data[0].get("procid") != "9":
            raise RuntimeError(f"Delete track failed: {course_id}")

    def get_tracks(self) -> List[Dict[str, Any]]:
        token = self.get_token()
        url = self.config.get_track_url(token)
        return self._request_json("POST", url)  # 注意這邊是POST

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
