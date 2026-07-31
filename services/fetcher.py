"""
外部题目获取服务
支持从洛谷和 Codeforces API 搜索题目
"""

import requests
import time

# 洛谷搜索缓存（避免重复请求）
_cache = {}


def search_luogu(keyword: str = '', difficulty: str = '', page: int = 1, limit: int = 20):
    """从洛谷搜索题目"""
    cache_key = f'{keyword}#{difficulty}#{page}'
    if cache_key in _cache:
        return _cache[cache_key]

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
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
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
        return problems

    except requests.exceptions.Timeout:
        print(f'[洛谷] 请求超时')
        return []
    except requests.exceptions.ConnectionError:
        print(f'[洛谷] 网络连接失败')
        return []
    except Exception as e:
        print(f'[洛谷] 错误: {e}')
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
        all_stats = {s['contestId'] * 100 + ord(s['index']) - 65: s.get('rating', 0)
                     for s in data['result'].get('problemStatistics', [])}

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
                'platform': r['platform'],
                'platform_id': r.get('platform_id', ''),
                'title': r['title'],
                'difficulty': r.get('difficulty', ''),
                'tags_str': r.get('tags', ''),
                'local_id': r['id'],
                'status': r.get('status', ''),
            }
            for r in rows
        ]
    except Exception:
        return []


def clear_cache():
    """清除搜索缓存"""
    _cache.clear()
