import json
with open('fixed_routes_library.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

routes = data['航线库']['航线数据']
r = routes[0]
print(f'航线: {r["航线ID"]}')
print(f'覆盖航路: {r["覆盖航路"]}')
print(f'航路点数量: {len(r["航路点"])}')
print('前5个航路点:')
for wp in r['航路点'][:5]:
    print(f'  坐标: ({wp["坐标"][0]:.4f}, {wp["坐标"][1]:.4f}), 高度: {wp["高度"]}m')
