"""
赛事数据获取服务
从 Codeforces API 和 AtCoder (kenkoooo) 获取真实赛事信息
结果缓存到 data/contests_cache.json（TTL 6小时）
"""

import json
import os
import time
from datetime import date, datetime, timedelta

import requests

from config import get_data_dir


def _cache_path() -> str:
    return os.path.join(get_data_dir(), 'contests_cache.json')


def _load_cache() -> dict:
    path = _cache_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data: dict):
    path = _cache_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _is_fresh(cache: dict) -> bool:
    fetched = cache.get('fetched_at', 0)
    return (time.time() - fetched) < 6 * 3600  # 6 小时


def fetch_cf_contests() -> list:
    """从 Codeforces API 获取未来赛事"""
    cache = _load_cache()
    if _is_fresh(cache) and cache.get('cf'):
        return cache['cf']

    try:
        resp = requests.get('https://codeforces.com/api/contest.list', timeout=15)
        data = resp.json()
        if data.get('status') != 'OK':
            return []

        now = time.time()
        future_limit = now + 90 * 86400  # 90 天

        contests = []
        for c in data['result']:
            if c.get('phase') != 'BEFORE':
                continue
            start = c.get('startTimeSeconds', 0)
            if start <= now:
                continue
            if start > future_limit:
                continue

            d = date.fromtimestamp(start)
            contests.append({
                'name': c.get('name', ''),
                'date': d,
                'type': 'CF',
                'url': 'https://codeforces.com/contests',
            })

        # 保存缓存
        _save_cache({'cf': contests, 'fetched_at': time.time()})
        return contests

    except Exception:
        return cache.get('cf', [])


def fetch_atcoder_contests() -> list:
    """从 AtCoder (kenkoooo) 获取未来赛事"""
    cache = _load_cache()
    if _is_fresh(cache) and cache.get('at'):
        return cache['at']

    try:
        resp = requests.get('https://kenkoooo.com/atcoder/resources/contests.json', timeout=15)
        data = resp.json()

        now = time.time()
        future_limit = now + 90 * 86400  # 90 天

        contests = []
        for c in data:
            start = c.get('start_epoch_second', 0)
            if start <= now:
                continue  # 已结束的跳过
            if start > future_limit:
                continue  # 太远的跳过

            d = date.fromtimestamp(start)
            contest_id = c.get('id', '')
            contests.append({
                'name': c.get('title', ''),
                'date': d,
                'type': 'AT',
                'url': f'https://atcoder.jp/contests/{contest_id}',
            })

        _save_cache({'at': contests, 'fetched_at': time.time()})
        return contests

    except Exception:
        return cache.get('at', [])


def fetch_noi_events() -> list:
    """从 data/noi_events.json 读取 NOI 系列赛事"""
    path = os.path.join(get_data_dir(), 'noi_events.json')
    if not os.path.exists(path):
        # 首次运行创建默认模板
        _create_default_noi_events(path)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        today = date.today()
        contests = []
        for e in events:
            d = date.fromisoformat(e['date'])
            if d < today:
                continue  # 已过期的跳过
            contests.append({
                'name': e['name'],
                'date': d,
                'type': 'NOI 系列',
                'url': e.get('url', 'https://www.noi.cn/'),
            })
        return contests
    except Exception:
        return []


def _create_default_noi_events(path: str):
    """创建默认 NOI 赛历模板"""
    year = date.today().year
    default_events = [
        {"name": "NOI 冬令营", "date": f"{year}-02-05", "url": "https://www.noi.cn/"},
        {"name": "WC / WCCT", "date": f"{year}-02-10", "url": "https://www.noi.cn/"},
        {"name": "CTS", "date": f"{year}-02-15", "url": "https://www.noi.cn/"},
        {"name": "APIO", "date": f"{year}-05-08", "url": "https://www.noi.cn/"},
        {"name": "NOI 省选", "date": f"{year}-04-15", "url": "https://www.noi.cn/"},
        {"name": "NOI 国赛", "date": f"{year}-07-15", "url": "https://www.noi.cn/"},
        {"name": "NOI 决赛", "date": f"{year}-07-20", "url": "https://www.noi.cn/"},
        {"name": "NOI 集训队", "date": f"{year}-08-01", "url": "https://www.noi.cn/"},
        {"name": "NOIP 提高组", "date": f"{year}-11-15", "url": "https://www.noi.cn/"},
        {"name": "NOIP 普及组", "date": f"{year}-10-18", "url": "https://www.noi.cn/"},
    ]
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_events, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_all_contests() -> list:
    """获取所有赛事（CF + AT + NOI），按日期排序，数据不足时保留占位链接"""
    contests = []
    contests.extend(fetch_cf_contests())
    contests.extend(fetch_atcoder_contests())
    contests.extend(fetch_noi_events())

    # 如无 AT 赛事，加入链接指向
    has_at = any(c['type'] == 'AT' for c in contests)
    if not has_at:
        today = date.today()
        contests.append({
            'name': 'AtCoder 赛程（点击查看官网）', 'date': today,
            'type': 'AT', 'url': 'https://atcoder.jp/contests/',
        })

    # 加入洛谷赛程链接
    has_lg = any(c['type'] == '洛谷' for c in contests)
    if not has_lg:
        contests.append({
            'name': '洛谷赛程（点击查看官网）', 'date': date.today(),
            'type': '洛谷', 'url': 'https://www.luogu.com.cn/contest/list',
        })

    contests.sort(key=lambda c: (c['date'], c['type']))
    return contests


def refresh_contests():
    """强制刷新缓存"""
    path = _cache_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    return get_all_contests()
