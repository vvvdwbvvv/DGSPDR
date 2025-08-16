import os
import sys
from typing import Optional

import requests
import urllib3
from requests import ssl
from requests.adapters import HTTPAdapter

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from NCCUCrawl.NCCUCrawl.config import Config


class Auth:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.client = AuthClient()

    def login(self):
        # Simulate a login process
        res = self.client.post(self._login_api_endpoint())
        if res is not None:
            print(f"Login Response Status: {res.status_code}")
            print(f"Login Response Content: {res.text}")
            return res.status_code == 200

    def _login_api_endpoint(self):
        return Config().PERSON_API + self.username + "!!)" + self.password


class AuthClient:
    """Client for making requests to NCCU endpoints with specific SSL requirements."""

    def __init__(self):
        self.session = requests.Session()
        self._setup_ssl_adapter()

    def _setup_ssl_adapter(self):
        """Set up custom SSL adapter matching curl requirements."""

        class CustomTLSAdapter(HTTPAdapter):
            def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
                ctx = self._create_legacy_ssl_context()
                kwargs["ssl_context"] = ctx
                return super().init_poolmanager(connections, maxsize, block=block, **kwargs)

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
                    ctx.set_ciphers("ALL:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA")

                # Additional options for legacy compatibility
                ctx.options |= ssl.OP_NO_SSLv2
                ctx.options |= ssl.OP_NO_SSLv3
                ctx.options |= ssl.OP_ALL

                return ctx

        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)

        # Mount custom adapter
        self.session.mount("https://", CustomTLSAdapter())

    def get(
        self, url: str, headers: Optional[dict] = None, **kwargs
    ) -> Optional[requests.Response]:
        """Make GET request."""
        default_headers = {
            "Accept": "application/json",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (compatible; NCCU-Crawler/1.0)",
        }

        if headers:
            default_headers.update(headers)

        try:
            print(f"Making GET request to: {url}")
            response = self.session.get(
                url=url, headers=default_headers, verify=False, timeout=30, **kwargs
            )
            return response
        except Exception as e:
            print(f"GET request failed: {e}")
            return None

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
