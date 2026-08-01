"""
统一 HTTP 请求客户端
集中处理超时、重试、错误日志、UA 头等公共逻辑
"""
import requests
import json
from utils.logger import get_logger

logger = get_logger('http')

DEFAULT_TIMEOUT = 15
DEFAULT_UA = 'OI-Learn-Desktop/1.0 (Educational Tool)'


def http_get(url, params=None, headers=None, timeout=DEFAULT_TIMEOUT, 
             use_json=True, extra_headers=None):
    """
    统一 GET 请求
    返回：dict/list（JSON）或 str（文本）或 None（失败）
    """
    req_headers = {
        'User-Agent': DEFAULT_UA,
        'Accept': 'application/json, text/plain, */*',
    }
    if extra_headers:
        req_headers.update(extra_headers)
    if headers:
        req_headers.update(headers)
    
    try:
        resp = requests.get(url, params=params, headers=req_headers, timeout=timeout)
        resp.raise_for_status()
        
        if use_json:
            if resp.text.startswith('<'):
                logger.warning(f'Expected JSON but got HTML from {url}')
                return None
            return resp.json()
        return resp.text
    
    except requests.exceptions.Timeout:
        logger.warning(f'Request timeout: {url}')
        return None
    except requests.exceptions.ConnectionError:
        logger.warning(f'Connection failed: {url}')
        return None
    except json.JSONDecodeError:
        logger.warning(f'Invalid JSON response from {url}')
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning(f'HTTP error {e.response.status_code}: {url}')
        return None
    except Exception as e:
        logger.error(f'Request error: {url} - {e}')
        return None
