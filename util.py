# util.py

from base64 import b64encode
from pyDes import des, ECB, PAD_PKCS5
from common import PERSON_API, TRACE_API, KEY
import logging

def des_ecb_encode(source: str, key: str) -> str:
    """使用 DES ECB 模式加密並進行 Base64 編碼。

    Args:
        source (str): 要加密的原始字符串。
        key (str): DES 加密的密鑰，必須為 8 個字元。

    Returns:
        str: 加密後並進行 Base64 編碼的字符串。
    """
    if len(key) != 8:
        raise ValueError("DES key must be exactly 8 characters long.")

    des_obj = des(key, ECB, pad=None, padmode=PAD_PKCS5)
    des_result = des_obj.encrypt(source)
    return b64encode(des_result).decode()


def get_login_url(username: str, password: str) -> str:
    """生成登入 URL。

    Args:
        username (str): 使用者名稱。
        password (str): 密碼。

    Returns:
        str: 登入 URL。
    """
    source = f"aNgu1ar%!{username}X_X{password}!%ASjjLInGH:lkjhdsa:)_l0OK"
    try:
        encoded = des_ecb_encode(source, KEY)
    except Exception as e:
        logging.error(f"Error encoding login URL: {e}")
        raise
    return f"{PERSON_API}{encoded}/"


def get_addtrack_url(encstu: str, courseid: str) -> str:
    """生成添加追蹤課程的 URL。

    Args:
        encstu (str): 加密的學生標識。
        courseid (str): 課程 ID。

    Returns:
        str: 添加追蹤課程的 URL。
    """
    source = f"aNgu1ar%!{courseid}!%ASjjLInGH:lkjhdsa"
    try:
        encoded = des_ecb_encode(source, KEY)
    except Exception as e:
        logging.error(f"Error encoding add track URL: {e}")
        raise
    return f"{TRACE_API}C/zh-TW/3{encoded}-{encstu}/"


def get_deltrack_url(encstu: str, courseid: str) -> str:
    """生成刪除追蹤課程的 URL。

    Args:
        encstu (str): 加密的學生標識。
        courseid (str): 課程 ID。

    Returns:
        str: 刪除追蹤課程的 URL。
    """
    source = f"aNgu1ar%!{courseid}!%ASjjLInGH:lkjhdsa"
    try:
        encoded = des_ecb_encode(source, KEY)
    except Exception as e:
        logging.error(f"Error encoding delete track URL: {e}")
        raise
    return f"{TRACE_API}D/zh-TW/{encoded}-{encstu}/"


def get_track_url(encstu: str) -> str:
    """生成獲取追蹤課程的 URL。

    Args:
        encstu (str): 加密的學生標識。

    Returns:
        str: 獲取追蹤課程的 URL。
    """
    return f"{TRACE_API}zh-TW/{encstu}/"


def get_updatetrack_url(encstu: str, courseid: str) -> str:
    """生成更新追蹤課程的 URL。

    Args:
        encstu (str): 加密的學生標識。
        courseid (str): 課程 ID。

    Returns:
        str: 更新追蹤課程的 URL。
    """
    source = f"aNgu1ar%!{courseid}!%ASjjLInGH:lkjhdsa"
    try:
        encoded = des_ecb_encode(source, KEY)
    except Exception as e:
        logging.error(f"Error encoding update track URL: {e}")
        raise
    return f"{TRACE_API}U/zh-TW/1{encoded}-{encstu}/"