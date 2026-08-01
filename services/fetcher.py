"""
外部题目获取服务
支持从洛谷(需Cookie)、AtCoder、Codeforces、本地题库搜索题目
"""

import json
import requests
from config import Config

# 搜索缓存（避免重复请求，最多500条）
_cache = {}
_MAX_CACHE = 500


def _get_luogu_cookie() -> str:
    """从配置读取洛谷登录 Cookie"""
    try:
        cfg = Config()
        return cfg.get('luogu_cookie', '')
    except Exception:
        return ''


def search_luogu(keyword: str = '', difficulty: str = '', page: int = 1, limit: int = 20):
    """
    从洛谷搜索题目（匿名时可能触发反爬拦截）
    若返回空列表且需登录，请在设置中配置 luogu_cookie
    """
    cache_key = f'{keyword}#{difficulty}#{page}'
    if cache_key in _cache:
        return _cache[cache_key]

    cookie = _get_luogu_cookie()

    try:
        url = 'https://www.luogu.com.cn/problem/list'
        params = {'page': page, '_contentOnly': '1'}
        if keyword:
            params['keyword'] = keyword
        if difficulty:
            params['difficulty'] = difficulty

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.luogu.com.cn/problem/list',
        }
        if cookie:
            headers['Cookie'] = cookie

        resp = requests.get(url, params=params, headers=headers, timeout=15)

        # 反爬拦截检测：body 以 < 开头是 HTML 而非 JSON
        if resp.text.startswith('<'):
            if not cookie:
                print('[洛谷] 反爬拦截：请在设置中配置 luogu_cookie（登录洛谷后从浏览器复制）')
            else:
                print('[洛谷] Cookie 可能已过期，请更新')
            return []

        data = resp.json()

        if data.get('code') != 200:
            print(f'[洛谷] API 返回 code={data.get("code")}')
            return []

        result = data.get('currentData', {}).get('problems', {}).get('result', [])
        if not result:
            print(f'[洛谷] 关键词 "{keyword}" 无搜索结果')
            return []

        problems = []
        for p in result[:limit]:
            problems.append({
                'platform': '洛谷',
                'platform_id': p.get('pid', ''),
                'title': p.get('title', ''),
                'difficulty': _luogu_difficulty(p.get('difficulty', 0)),
                'tags': p.get('tags', []),
                'url': f'https://www.luogu.com.cn/problem/{p.get("pid", "")}',
            })

        _cache[cache_key] = problems
        if len(_cache) > _MAX_CACHE:
            _cache.pop(next(iter(_cache)))
        return problems

    except requests.exceptions.Timeout:
        print(f'[洛谷] 请求超时')
        return []
    except requests.exceptions.ConnectionError:
        print(f'[洛谷] 网络连接失败')
        return []
    except json.JSONDecodeError:
        print(f'[洛谷] 返回非JSON数据（可能被反爬拦截），请配置登录Cookie')
        return []
    except Exception as e:
        print(f'[洛谷] 错误: {e}')
        return []


def search_atcoder(keyword: str = '', limit: int = 20):
    """
    从 AtCoder（kenkoooo 镜像）搜索题目
    免费无需 key，数据全量缓存后客户端过滤
    """
    cache_key = f'at:{keyword}'
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        # 拉取题目列表
        resp = requests.get(
            'https://kenkoooo.com/atcoder/resources/problems.json',
            timeout=15
        )
        if resp.status_code != 200:
            print(f'[AT] HTTP {resp.status_code}')
            return []

        problems_data = resp.json()
        problems = []

        for p in problems_data:
            title = p.get('title', '')
            contest_id = p.get('contest_id', '')
            pid = p.get('id', '')

            # 过滤关键词
            if keyword and keyword.lower() not in title.lower():
                continue

            problems.append({
                'platform': 'AtCoder',
                'platform_id': pid,
                'title': title,
                'difficulty': '',
                'tags': [],
                'url': f'https://atcoder.jp/contests/{contest_id}/tasks/{pid}',
            })

            if len(problems) >= limit * 2:
                break

        # 按 contest_id 排序（保证稳定）
        problems.sort(key=lambda x: x['platform_id'])

        _cache[cache_key] = problems[:limit]
        if len(_cache) > _MAX_CACHE:
            _cache.pop(next(iter(_cache)))
        return problems[:limit]

    except requests.exceptions.Timeout:
        print(f'[AT] 请求超时')
        return []
    except Exception as e:
        print(f'[AT] 错误: {e}')
        return []


def search_vjudge(keyword: str = '', limit: int = 20):
    """
    从 vjudge 搜索题目（聚合多 OJ 含洛谷）
    vjudge 无公开题目搜索 API，使用 vjudge.net/problem/{oj}-{id} 方式
    """
    cache_key = f'vj:{keyword}'
    if cache_key in _cache:
        return _cache[cache_key]

    # vjudge 聚合了多 OJ，直接返回空（可作为未来扩展）
    # 用户可以直接在浏览器使用 vjudge.net 搜索
    return []


def search_codeforces(tags: list = None, min_rating: int = None, max_rating: int = None,
                      limit: int = 20):
    """
    从 Codeforces API 搜索题目
    参数：
        tags: 算法标签列表（如 ['dp', 'greedy']）
        min_rating: 最小 rating
        max_rating: 最大 rating
        limit: 返回数量上限
    """
    cache_key = f'cf:{";".join(tags or [])}#{min_rating}#{max_rating}'
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        url = 'https://codeforces.com/api/problemset.problems'
        params = {}
        if tags:
            params['tags'] = ';'.join(tags)

        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get('status') != 'OK':
            return []

        all_problems = data['result']['problems']

        problems = []
        for p in all_problems:
            rating = p.get('rating', 0)
            if min_rating and rating < min_rating:
                continue
            if max_rating and rating > max_rating:
                continue

            pid = f'{p["contestId"]}{p["index"]}'
            problems.append({
                'platform': 'Codeforces',
                'platform_id': pid,
                'title': p.get('name', ''),
                'difficulty': _cf_difficulty(rating) if rating else '',
                'tags': p.get('tags', []),
                'rating': rating,
                'url': f'https://codeforces.com/problemset/problem/{p["contestId"]}/{p["index"]}',
            })

            if len(problems) >= limit * 2:  # 多取一些再截断
                break

        _cache[cache_key] = problems[:limit]
        return problems[:limit]

    except Exception:
        return []


def _luogu_difficulty(diff: int) -> str:
    """洛谷难度数字 → 文字映射"""
    # 洛谷难度: 1=入门, 2=普及−, 3=普及, 4=普及+/提高−, 5=提高, 6=提高+/省选−, 7=省选/NOI−, 8=NOI
    mapping = {
        1: '入门', 2: '普及−', 3: '普及', 4: '普及+/提高−',
        5: '提高', 6: '提高+/省选−', 7: '省选/NOI−', 8: 'NOI/NOI+/CTS'
    }
    return mapping.get(diff, f'Lv.{diff}')


def _cf_difficulty(rating: int) -> str:
    """CF rating → 难度文字映射"""
    if rating == 0:
        return '暂未评定'
    if rating < 1200:
        return '入门'
    if rating < 1500:
        return '普及−'
    if rating < 1800:
        return '普及'
    if rating < 2100:
        return '普及+/提高−'
    if rating < 2400:
        return '提高'
    if rating < 2700:
        return '提高+/省选−'
    if rating < 3000:
        return '省选/NOI−'
    return 'NOI/NOI+/CTS'


def search_local(keyword: str = '', difficulty: str = ''):
    """从本地刷题库搜索题目"""
    from db.database import get_connection
    try:
        conn = get_connection()
        query = "SELECT id, title, platform, platform_id, difficulty, tags, status FROM problems WHERE 1=1"
        params = []
        if keyword:
            query += " AND (title LIKE ? OR tags LIKE ? OR platform_id LIKE ?)"
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
        query += " ORDER BY updated_at DESC LIMIT 30"
        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            {
                'platform': r['platform'] or '',
                'platform_id': r['platform_id'] or '',
                'title': r['title'],
                'difficulty': r['difficulty'] or '',
                'tags_str': r['tags'] or '',
                'local_id': r['id'],
                'status': r['status'] or '',
            }
            for r in rows
        ]
    except Exception:
        return []


def clear_cache():
    """清除搜索缓存"""
    _cache.clear()
