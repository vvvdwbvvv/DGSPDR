import re
from typing import Optional, Tuple
from urllib.parse import urljoin
from base64 import b64decode, b64encode
import ssl
import requests
from requests.adapters import HTTPAdapter
from pyDes import des, ECB, PAD_PKCS5
from .config import Config


class Authenticate:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self._username = username or self.config.USERNAME
        self._password = password or self.config.PASSWORD
        self._token: Optional[str] = None
        self._auth_debug: str = ""

        if not self._username or not self._password:
            raise Exception("Username or password not found in environment")

        # DES key and cipher
        self._des_key = self._derive_des_key(self.config.KEY)
        self._des = des(self._des_key, ECB, padmode=PAD_PKCS5)

        # Requests session with legacy TLS enabled
        self._session = requests.Session()
        self._mount_legacy_tls_adapter()

        # Authenticate and set token
        self._authenticate()

    def _derive_des_key(self, key) -> bytes:
        """
        Accepts:
          - bytes of length 8
          - base64 string that decodes to 8 bytes
          - hex string that decodes to 8 bytes
          - 8-char ASCII/UTF-8/latin1 string
        """
        if isinstance(key, bytes):
            if len(key) == 8:
                return key
            raise ValueError("Config.KEY bytes must be exactly 8 bytes")

        if not isinstance(key, str):
            raise ValueError("Config.KEY must be bytes or str")

        # Try base64
        try:
            b = b64decode(key, validate=True)
            if len(b) == 8:
                return b
        except Exception:
            pass

        # Try hex
        try:
            b = bytes.fromhex(key)
            if len(b) == 8:
                return b
        except Exception:
            pass

        # Try encodings
        for enc in ("utf-8", "ascii", "latin-1"):
            try:
                b = key.encode(enc)
                if len(b) == 8:
                    return b
            except Exception:
                pass

        raise ValueError("Invalid DES key size. KEY must decode to exactly 8 bytes.")

    def _mount_legacy_tls_adapter(self) -> None:
        class LegacyTLSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
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
        ct = self._des.encrypt(source.encode("utf-8"))
        return b64encode(ct).decode("ascii")

    def _authenticate(self) -> None:
        source = f"aNgu1ar%!{self._username}X_X{self._password}!%ASjjLInGH:lkjhdsa:)_l0OK"
        encrypted_data = self._des_encrypt(source)

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self.config.SERVER_URL,
            "Origin": self.config.SERVER_URL.rstrip("/"),
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            resp, trace = self._try_person_endpoints(encrypted_data, headers)
            ctype = resp.headers.get("Content-Type", "")
            snippet = ""
            try:
                snippet = (resp.text or "")[:300]
            except Exception:
                pass
            self._auth_debug = f"{trace} | final={resp.status_code} {ctype} | body={snippet}"

            resp.raise_for_status()
            token = self._extract_token(resp)
            if not token:
                raise Exception("Token not found in response")
            self._token = token

        except requests.exceptions.SSLError as e:
            if "UNSAFE_LEGACY_RENEGOTIATION_DISABLED" in str(e):
                raise Exception(
                    "TLS requires UnsafeLegacyRenegotiation. Set OPENSSL_CONF to a config with 'Options = UnsafeLegacyRenegotiation' and rerun."
                ) from e
            raise
        except Exception as e:
            raise Exception(f"Authentication failed: {e}. Trace={self._auth_debug}")
        
    def _extract_token(self, resp: requests.Response) -> Optional[str]:
        # Try JSON list: [ { "encstu": "..." } ]
        try:
            data = resp.json()
            if isinstance(data, list) and data:
                v = data[0]
                if isinstance(v, dict) and "encstu" in v and v["encstu"]:
                    return str(v["encstu"])
            if isinstance(data, dict):
                # { "encstu": "..." } or { "data": [ { "encstu": "..." } ] }
                if "encstu" in data and data["encstu"]:
                    return str(data["encstu"])
                if "data" in data and isinstance(data["data"], list) and data["data"]:
                    v = data["data"][0]
                    if isinstance(v, dict) and "encstu" in v and v["encstu"]:
                        return str(v["encstu"])
        except Exception:
            pass

        # Fallback: regex from text
        try:
            txt = resp.text or ""
            m = re.search(r'"encstu"\s*:\s*"([^"]+)"', txt)
            if m:
                return m.group(1)
        except Exception:
            pass

        return None

    def _post_with_manual_redirects(
        self,
        url: str,
        headers: dict,
        *,
        data=None,
        json=None,
        timeout: int = 15,
        max_redirects: int = 5,
    ) -> Tuple[requests.Response, str]:
        steps = []
        current_url = url
        last = None
        for _ in range(max_redirects):
            resp = self._session.post(
                current_url,
                headers=headers,
                data=data,
                json=json,
                timeout=timeout,
                allow_redirects=False,
            )
            last = resp
            steps.append(f"POST {current_url} -> {resp.status_code}")
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                if not loc:
                    break
                current_url = urljoin(current_url, loc)
                continue
            break
        return (last or resp), " | ".join(steps)

    def _try_person_endpoints(self, enc_path: str, headers: dict) -> Tuple[requests.Response, str]:
        urls = [
            f"{self.config.PERSON_API}{enc_path}",
            f"{self.config.PERSON_API}{enc_path}/",
            f"{self.config.PERSON_API}",
        ]
        traces = []

        # Prefer POST to path (no body)
        for url in urls[:2]:
            resp, tr = self._post_with_manual_redirects(url, headers, timeout=15)
            traces.append(tr)
            if resp.status_code == 200:
                return resp, " || ".join(traces)

        # Try form to base
        for key in ("q", "data", "token"):
            resp, tr = self._post_with_manual_redirects(urls[2], headers, data={key: enc_path}, timeout=15)
            traces.append(tr)
            if resp.status_code == 200:
                return resp, " || ".join(traces)

        # Try JSON to base
        json_headers = {**headers, "Content-Type": "application/json"}
        for key in ("q", "data", "token"):
            resp, tr = self._post_with_manual_redirects(urls[2], json_headers, json={key: enc_path}, timeout=15)
            traces.append(tr)
            if resp.status_code == 200:
                return resp, " || ".join(traces)

        return resp, " || ".join(traces)

    def get_addtrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        return f"{self.config.TRACE_API}C/zh-TW/3{encrypted_data}-{self._token or 'ERROR'}/"

    def get_deltrack_url(self, course_id: str) -> str:
        source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
        encrypted_data = self._des_encrypt(source)
        return f"{self.config.TRACE_API}D/zh-TW/{encrypted_data}-{self._token or 'ERROR'}/"

    def get_track_url(self) -> str:
        return f"{self.config.TRACE_API}zh-TW/{self._token or 'ERROR'}/"

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def debug(self) -> str:
        return self._auth_debug

    @property
    def session(self) -> requests.Session:
        return self._session