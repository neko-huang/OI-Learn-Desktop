with open('modules/plan.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find and replace the search logic
old_marker = "results = []\n            if source == 'luogu':"
new_marker = "results = []\n            pool_size = count * 6  # 多取再打乱，每次不同\n            if source == 'luogu':"

if old_marker in c:
    c = c.replace(old_marker, new_marker)
    # Replace limit values
    c = c.replace("search_luogu(keyword=tag, limit=count)", "search_luogu(keyword=tag, limit=pool_size)")
    c = c.replace("search_codeforces(limit=count * 3)", "search_codeforces(limit=pool_size)")
    c = c.replace("search_atcoder(keyword='', limit=count * 3)", "search_atcoder(keyword='', limit=pool_size)")
    c = c.replace("results = results[:count * 2]", "results = results[:pool_size]")
    # Replace the dedup section ending
    c = c.replace("results = unique[:count]", '''unique.append(r)

            # 随机打乱，每次生成不同题单
            import random
            random.shuffle(unique)
            results = unique[:count]''')
    print("Fixed all replacements")
else:
    print("Marker not found, checking...")
    if "pool_size" in c:
        print("Already fixed")

with open('modules/plan.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")
