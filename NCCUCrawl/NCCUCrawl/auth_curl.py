import subprocess
import json
from typing import Optional
from .config import Config


class Authenticate:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self.username = username or self.config.USERNAME
        self.password = password or self.config.PASSWORD
        self.client = AuthClient()

    def login(self):
        url = self._login_api_endpoint()

        safe_url = url.replace(self.password, "******")
        print("Executing curl to:", safe_url)

        res = self.client.post(url)
        if res:
            status, body = res
            print(f"Login Response Status: {status}")

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                print("Failed to parse JSON response.")
                return False

            print(f"Login Response Content: {data}")

            if status == 200 and data and data[0].get("encstu") != "ERROR":
                self.token = data[0]["encstu"]
                self.user_info = data[0]
                return self.token
        return False

    def get_token(self):
        if not self.token:
            raise Exception("Not logged in")
        return self.token

    def _login_api_endpoint(self):
        return f"{self.config.PERSON_API}{self.username}!!){self.password}"


class AuthClient:
    def post(self, url: str, headers: Optional[dict] = None, **kwargs):
        cmd = [
            "curl",
            "-X",
            "POST",
            url,
            "-H",
            "Accept: application/json",
            "-H",
            "Connection: keep-alive",
            "--ssl-allow-beast",
            "--tls-max",
            "1.2",
            "-s",
        ]

        if headers:
            for k, v in headers.items():
                cmd += ["-H", f"{k}: {v}"]

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            return 200, output.decode("utf-8")
        except subprocess.CalledProcessError as e:
            print("curl failed:", e.output.decode("utf-8"))
            return None
