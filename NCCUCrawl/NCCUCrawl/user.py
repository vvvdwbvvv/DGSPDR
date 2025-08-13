from dotenv import load_dotenv
from os import getenv
import requests
from .util import get_login_url, get_addtrack_url, get_deltrack_url, get_track_url

load_dotenv()


class User:    
    def __init__(self) -> None:
        """Initialize user with credentials and obtain token"""
        self._username: str = getenv("USERNAME") or ""
        self._password: str = getenv("PASSWORD") or ""
        self._token: str = ""
        
        if not self._username or not self._password:
            raise Exception("Username or password not found in environment variables")
        
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate user and obtain token"""
        try:
            login_url = get_login_url(self._username, self._password)
            response = requests.get(login_url)
            response.raise_for_status()
            
            data = response.json()
            if not data or len(data) == 0:
                raise Exception("Empty response from login API")
                
            self._token = data[0]["encstu"]
            
        except (requests.RequestException, KeyError, IndexError) as e:
            raise Exception(f"Authentication failed: {str(e)}")
    
    def add_track(self, course_id: str) -> None:
        """Add a course to tracking list"""
        if not course_id:
            raise ValueError("Course ID cannot be empty")
            
        try:
            add_url = get_addtrack_url(self._token, course_id)
            response = requests.post(add_url)
            response.raise_for_status()
            
            data = response.json()
            if not data or data[0]["procid"] != "1":
                raise Exception(f"Add track failed: {course_id}")
                
        except requests.RequestException as e:
            raise Exception(f"Failed to add track for {course_id}: {str(e)}")
    
    def delete_track(self, course_id: str) -> None:
        """Delete a course from tracking list"""
        if not course_id:
            raise ValueError("Course ID cannot be empty")
            
        try:
            delete_url = get_deltrack_url(self._token, course_id)
            response = requests.delete(delete_url)
            response.raise_for_status()
            
            data = response.json()
            if not data or data[0]["procid"] != "9":
                raise Exception(f"Delete track failed: {course_id}")
                
        except requests.RequestException as e:
            raise Exception(f"Failed to delete track for {course_id}: {str(e)}")
    
    def get_track(self) -> list:
        """Get current tracking course list"""
        try:
            track_url = get_track_url(self._token)
            response = requests.get(track_url)
            response.raise_for_status()
            
            data = response.json()
            return data if data else []
            
        except requests.RequestException as e:
            raise Exception(f"Failed to get track list: {str(e)}")
    
    @property
    def token(self) -> str:
        """Get current token"""
        return self._token
    
    @property
    def username(self) -> str:
        """Get username"""
        return self._username