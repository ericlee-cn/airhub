import json
with open('fixed_routes_library.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

routes = data['航线库']['航线数据']
print(f'航线数: {len(routes)}')

# 统计类型
types = {}
for r in routes:
    t = r['业务类型']
    types[t] = types.get(t, 0) + 1
print('\n业务类型分布:')
for t, c in types.items():
    print(f'  {t}: {c}条')

print('\n第一条航线:')
r = routes[0]
print(f"  ID: {r['航线ID']}, 名称: {r['航线名称']}")
print(f"  类型: {r['业务类型']}, 级别: {r['航路级别']}")
print(f"  高度: {r['飞行高度(m)']}m")
print(f"  覆盖航路: {r['覆盖航路']}")
print(f"  航路点数: {len(r['航路点'])}")
