from urllib.parse import quote, urljoin
import ssl
from typing import Optional
from base64 import b64decode, b64encode
from pyDes import des, ECB, PAD_PKCS5
import requests
from .config import Config
from requests.adapters import HTTPAdapter


class Authenticate:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self._username = username or self.config.USERNAME
        self._password = password or self.config.PASSWORD
        self._token: Optional[str] = None
        self._des_key = self._derive_des_key(self.config.KEY)
        self._des = des(self._des_key, ECB, padmode=PAD_PKCS5)
        self._session = requests.Session()
        self._mount_legacy_tls_adapter()

        if not self._username or not self._password:
            raise Exception("Username or password not found")

        self._authenticate()

    def _derive_des_key(self, key) -> bytes:
        """
        Accepts:
          - bytes of length 8
          - base64 string that decodes to 8 bytes
          - hex string that decodes to 8 bytes
          - 8-char ASCII/UTF-8 string
        """
        if isinstance(key, bytes):
            if len(key) == 8:
                return key
            raise ValueError("Invalid DES key size. Key must be exactly 8 bytes long.")
        if not isinstance(key, str):
            raise ValueError("DES key must be bytes or string.")

        # Try base64
        try:
            kb = b64decode(key, validate=True)
            if len(kb) == 8:
                return kb
        except Exception:
            pass

        # Try hex
        try:
            kb = bytes.fromhex(key)
            if len(kb) == 8:
                return kb
        except Exception:
            pass

        for enc in ("utf-8", "ascii", "latin-1"):
            try:
                kb = key.encode(enc)
                if len(kb) == 8:
                    return kb
            except Exception:
                pass

        raise ValueError(
            "Invalid DES key size. Config.KEY must be exactly 8 bytes. "
            "Use an 8-char ASCII string or provide a base64/hex value that decodes to 8 bytes."
        )

    def _mount_legacy_tls_adapter(self) -> None:
        """
        Mount an HTTPS adapter that allows legacy server connections
        (needed for servers requiring unsafe legacy renegotiation).
        """

        class LegacyTLSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                # Allow legacy servers (OpenSSL: OP_LEGACY_SERVER_CONNECT)
                if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
                    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                kwargs["ssl_context"] = ctx
                return super().init_poolmanager(*args, **kwargs)

            def proxy_manager_for(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
                    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                kwargs["ssl_context"] = ctx
                return super().proxy_manager_for(*args, **kwargs)

        self._session.mount("https://", LegacyTLSAdapter())

    def _des_encrypt(self, source: str) -> str:
        # Use bytes input and reuse the DES object
        des_result = self._des.encrypt(source.encode("utf-8"))
        return b64encode(des_result).decode("ascii")

    def _authenticate(self) -> None:
        source = (
            f"aNgu1ar%!{self._username}X_X{self._password}!%ASjjLInGH:lkjhdsa:)_l0OK"
        )
        encrypted_data = self._des_encrypt(source)
        # Keep raw base64 (server appears to expect slashes in the path)
        enc_path = encrypted_data

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self.config.SERVER_URL,
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            response = self._try_person_endpoints(enc_path, headers)
            data = response.json()
            if not data:
                raise Exception("Empty response from login API")
            self._token = data[0]["encstu"]

        except requests.exceptions.SSLError as e:
            if "UNSAFE_LEGACY_RENEGOTIATION_DISABLED" in str(e):
                raise Exception(
                    "TLS requires UnsafeLegacyRenegotiation. Set OPENSSL_CONF to a config with 'Options = UnsafeLegacyRenegotiation' and rerun."
                ) from e
            raise
        except (requests.RequestException, KeyError, IndexError) as e:
            raise Exception(f"Authentication failed: {str(e)}")

    def _post_with_manual_redirects(
        self,
        url: str,
        headers: dict,
        *,
        data=None,
        json=None,
        timeout: int = 15,
        max_redirects: int = 5,
    ) -> requests.Response:
        """
        Send POST but handle redirects manually to preserve method and body.
        """
        current_url = url
        for _ in range(max_redirects):
            resp = self._session.post(
                current_url,
                headers=headers,
                data=data,
                json=json,
                timeout=timeout,
                allow_redirects=False,
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                if not loc:
                    return resp
                current_url = urljoin(current_url, loc)
                # continue loop and re-POST to the redirected URL
                continue
            return resp
        return resp  # return last response after exceeding redirects

    def _try_person_endpoints(self, enc_path: str, headers: dict) -> requests.Response:
        """
        Prefer POST (server Allow=POST). Try multiple shapes before failing, preserving POST on redirects.
        """
        urls = [
            f"{self.config.PERSON_API}{enc_path}",
            f"{self.config.PERSON_API}{enc_path}/",
            f"{self.config.PERSON_API}",
        ]

        last = None

        # 1) POST to path with/without trailing slash, no body (preserve POST across redirects)
        for url in urls[:2]:
            resp = self._post_with_manual_redirects(url, headers, timeout=15)
            if resp.status_code == 200:
                return resp
            last = (url, "POST(no-body)", resp)

        # 2) POST form to base endpoint (common patterns)
        for key in ("q", "data", "token"):
            resp = self._post_with_manual_redirects(
                urls[2], headers, data={key: enc_path}, timeout=15
            )
            if resp.status_code == 200:
                return resp
            last = (urls[2], f"POST(form) {key}", resp)

        # 3) POST JSON to base endpoint
        json_headers = {**headers, "Content-Type": "application/json"}
        for key in ("q", "data", "token"):
            resp = self._post_with_manual_redirects(
                urls[2], json_headers, json={key: enc_path}, timeout=15
            )
            if resp.status_code == 200:
                return resp
            last = (urls[2], f"POST(json) {key}", resp)

        # 4) As a last resort, try GET (with/without slash)
        for url in urls[:2]:
            resp = self._session.get(
                url, headers=headers, timeout=15, allow_redirects=True
            )
            if resp.status_code == 200:
                return resp
            last = (url, "GET", resp)

        if last:
            url, how, resp = last
            snippet = (resp.text or "")[:300]
            raise Exception(
                f"Authentication failed: {resp.status_code} {resp.reason} via {how} at {url}. "
                f"Allow={resp.headers.get('Allow', '')}. Body: {snippet}"
            )

        raise Exception("Authentication failed: unexpected empty response chain")

    def get_addtrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        enc_seg = quote(encrypted_data, safe="")
        return f"{self.config.TRACE_API}C/zh-TW/3{enc_seg}-{self._token}/"

    def get_deltrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        enc_seg = quote(encrypted_data, safe="")
        return f"{self.config.TRACE_API}D/zh-TW/{enc_seg}-{self._token}/"

    def get_track_url(self) -> str:
        return f"{self.config.TRACE_API}zh-TW/{self._token}/"

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def username(self) -> str:
        return self._username
