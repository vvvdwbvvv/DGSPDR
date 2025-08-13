from typing import Optional
from base64 import b64encode
from pyDes import des, ECB, PAD_PKCS5
import requests
from .config import Config


class Authenticate:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self._username = username or self.config.USERNAME
        self._password = password or self.config.PASSWORD
        self._token: Optional[str] = None

        if not self._username or not self._password:
            raise Exception("Username or password not found")

        self._authenticate()

    def _des_encrypt(self, source: str) -> str:
        des_obj = des(self.config.KEY, ECB, IV=None, pad=None, padmode=PAD_PKCS5)
        des_result = des_obj.encrypt(source)
        return b64encode(des_result).decode()

    def _authenticate(self) -> None:
        source = (
            f"aNgu1ar%!{self._username}X_X{self._password}!%ASjjLInGH:lkjhdsa:)_l0OK"
        )
        encrypted_data = self._des_encrypt(source)
        login_url = f"{self.config.PERSON_API}{encrypted_data}/"

        try:
            response = requests.get(login_url)
            response.raise_for_status()
            data = response.json()

            if not data:
                raise Exception("Empty response from login API")

            self._token = data[0]["encstu"]

        except (requests.RequestException, KeyError, IndexError) as e:
            raise Exception(f"Authentication failed: {str(e)}")

    def get_addtrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        return f"{self.config.TRACE_API}C/zh-TW/3{encrypted_data}-{self._token}/"

    def get_deltrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        return f"{self.config.TRACE_API}D/zh-TW/{encrypted_data}-{self._token}/"

    def get_track_url(self) -> str:
        return f"{self.config.TRACE_API}zh-TW/{self._token}/"

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def username(self) -> str:
        return self._username
