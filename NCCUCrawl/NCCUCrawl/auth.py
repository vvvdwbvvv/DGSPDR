from typing import Optional
import ssl
import urllib3
import requests
from requests.adapters import HTTPAdapter
from .config import Config


class Authenticate:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.config = Config()
        self.username = username or self.config.USERNAME
        self.password = password or self.config.PASSWORD
        self._auth_debug: str = ""
        self.client = AuthClient()

    def login(self):
        # Simulate a login process
        res = self.client.post(self._login_api_endpoint())
        if res is not None:
            print(f"Login Response Status: {res.status_code}")
            print(f"Login Response Content: {res.text}")
            return res.status_code == 200

    def _login_api_endpoint(self):
        return self.config.PERSON_API + self.username + "!!)" + self.password


class AuthClient:
    def __init__(self):
        self._session = requests.Session()
        self._mount_legacy_tls_adapter()

    def _mount_legacy_tls_adapter(self) -> None:
        class LegacyTLSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
                    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                kwargs["ssl_context"] = ctx
                return super().init_poolmanager(*args, **kwargs)

            def _create_legacy_ssl_context(self):
                """Create SSL context that allows legacy renegotiation."""
                assert ssl is not None, "SSL module is required for custom TLS adapter"
                # Create a custom SSL context
                ctx = ssl.create_default_context()

                # Allow unsafe legacy renegotiation (equivalent to curl --ssl-allow-beast)
                ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT

                # Set maximum TLS version to 1.2
                ctx.maximum_version = ssl.TLSVersion.TLSv1_2
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2

                # Disable hostname and certificate verification
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                # Set cipher suites (lower security level)
                try:
                    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
                except ssl.SSLError:
                    # Fallback if SECLEVEL is not supported
                    ctx.set_ciphers(
                        "ALL:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA"
                    )

                # Additional options for legacy compatibility
                ctx.options |= ssl.OP_NO_SSLv2
                ctx.options |= ssl.OP_NO_SSLv3
                ctx.options |= ssl.OP_ALL

                return ctx

        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)

        self._session.mount("https://", LegacyTLSAdapter())

    def post(
        self, url: str, headers: Optional[dict] = None, **kwargs
    ) -> Optional[requests.Response]:
        """Make POST request with custom SSL settings."""

        default_headers = {
            "Accept": "application/json",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (compatible; NCCU-Crawler/1.0)",
        }

        if headers:
            default_headers.update(headers)

        try:
            print(f"Making POST request to: {url}")
            response = self.session.post(
                url=url, headers=default_headers, verify=False, timeout=30, **kwargs
            )
            return response

        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    @property
    def session(self) -> requests.Session:
        return self._session
