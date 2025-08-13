from base64 import b64encode
from pyDes import des, ECB, PAD_PKCS5
from .config import PERSON_API, TRACE_API, KEY


def des_ecb_encode(source: str, key: str) -> str:
    """
    Encode source string using DES ECB encryption
    
    Args:
        source: String to encode
        key: Encryption key
        
    Returns:
        Base64 encoded encrypted string
    """
    des_obj = des(key, ECB, IV=None, pad=None, padmode=PAD_PKCS5)
    des_result = des_obj.encrypt(source)
    return b64encode(des_result).decode()


def get_login_url(username: str, password: str) -> str:
    """
    Generate login URL with encrypted credentials
    
    Args:
        username: User login name
        password: User password
        
    Returns:
        Complete login API URL
    """
    if not username or not password:
        raise ValueError("Username and password cannot be empty")
    
    source = f"aNgu1ar%!{username}X_X{password}!%ASjjLInGH:lkjhdsa:)_l0OK"
    encrypted_data = des_ecb_encode(source, KEY)
    return f"{PERSON_API}{encrypted_data}/"


def get_addtrack_url(encstu: str, course_id: str) -> str:
    """
    Generate URL for adding course to tracking list
    
    Args:
        encstu: Encrypted student token
        course_id: Course ID to add
        
    Returns:
        Complete add track API URL
    """
    if not encstu or not course_id:
        raise ValueError("Token and course ID cannot be empty")
    
    source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
    encrypted_data = des_ecb_encode(source, KEY)
    return f"{TRACE_API}C/zh-TW/3{encrypted_data}-{encstu}/"


def get_deltrack_url(encstu: str, course_id: str) -> str:
    """
    Generate URL for deleting course from tracking list
    
    Args:
        encstu: Encrypted student token
        course_id: Course ID to delete
        
    Returns:
        Complete delete track API URL
    """
    if not encstu or not course_id:
        raise ValueError("Token and course ID cannot be empty")
    
    source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
    encrypted_data = des_ecb_encode(source, KEY)
    return f"{TRACE_API}D/zh-TW/{encrypted_data}-{encstu}/"


def get_track_url(encstu: str) -> str:
    """
    Generate URL for getting tracking list
    
    Args:
        encstu: Encrypted student token
        
    Returns:
        Complete get track API URL
    """
    if not encstu:
        raise ValueError("Token cannot be empty")
    
    return f"{TRACE_API}zh-TW/{encstu}/"


def get_updatetrack_url(encstu: str, course_id: str) -> str:
    """
    Generate URL for updating course tracking
    
    Args:
        encstu: Encrypted student token
        course_id: Course ID to update
        
    Returns:
        Complete update track API URL
    """
    if not encstu or not course_id:
        raise ValueError("Token and course ID cannot be empty")
    
    source = f"aNgu1ar%!{course_id}!%ASjjLInGH:lkjhdsa"
    encrypted_data = des_ecb_encode(source, KEY)
    return f"{TRACE_API}U/zh-TW/1{encrypted_data}-{encstu}/"