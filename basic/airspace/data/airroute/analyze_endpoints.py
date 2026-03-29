import json

with open('航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def parse_coords(coords):
    """解析嵌套格式的坐标: [[lon, lat], height, ...] -> [(lon, lat), ...]"""
    result = []
    i = 0
    while i < len(coords):
        if isinstance(coords[i], list):
            # [lon, lat] 对
            result.append((coords[i][0], coords[i][1]))
            i += 1
        else:
            # height 值，跳过
            i += 2  # 跳过 height 和下一个点的 lat
    return result

# 提取所有原始航路的端点
endpoints = []
for route in data:
    if route.get('航路类型') != 'LINK':
        czml = json.loads(route['CZML'])
        coords = czml['corridor']['positions']['cartographicDegrees']
        parsed = parse_coords(coords)
        if len(parsed) >= 2:
            endpoints.append({
                'id': route['航路编号'],
                'type': route.get('航路类型', 'A'),
                'start': parsed[0],
                'end': parsed[-1],
                'all_points': parsed
            })

print(f'共解析 {len(endpoints)} 条原始航路')

# 找出经度范围
min_lon = min(min(e['start'][0], e['end'][0]) for e in endpoints)
max_lon = max(max(e['start'][0], e['end'][0]) for e in endpoints)
print(f'经度范围: {min_lon:.4f} - {max_lon:.4f}')

# 分析区域
left_routes = [e for e in endpoints if max(e['start'][0], e['end'][0]) < 120.0]
right_routes = [e for e in endpoints if min(e['start'][0], e['end'][0]) >= 120.0]
middle_routes = [e for e in endpoints if 120.0 <= max(e['start'][0], e['end'][0]) and min(e['start'][0], e['end'][0]) < 120.0]

print(f'左侧航路: {len(left_routes)} (max_lon < 120.0)')
print(f'右侧航路: {len(right_routes)} (min_lon >= 120.0)')
print(f'中间航路: {len(middle_routes)} (跨越120.0)')

# 显示右侧航路（孤立区域）
print('\n=== 右侧航路端点 (孤立区域) ===')
for e in sorted(right_routes, key=lambda x: x['start'][0]):
    print(f"  {e['id']} ({e['type']}): start({e['start'][0]:.4f}, {e['start'][1]:.4f}), end({e['end'][0]:.4f}, {e['end'][1]:.4f})")

# 显示左侧/中间最右边的端点
all_left_edge = left_routes + middle_routes
left_edge_sorted = sorted(all_left_edge, key=lambda x: -max(x['start'][0], x['end'][0]))

print('\n=== 左侧最右边的航路端点 (用于连接) ===')
for e in left_edge_sorted[:8]:
    print(f"  {e['id']} ({e['type']}): start({e['start'][0]:.4f}, {e['start'][1]:.4f}), end({e['end'][0]:.4f}, {e['end'][1]:.4f})")

# 计算右侧航路与左侧最右端点之间的距离
print('\n=== 右侧航路到左侧边界的距离 ===')
right_points = []
for e in right_routes:
    right_points.append(e['start'])
    right_points.append(e['end'])

for le in left_edge_sorted[:5]:
    for rp in right_points:
        dist = ((le['start'][0] - rp[0])**2 + (le['start'][1] - rp[1])**2)**0.5 * 111 * 1000
        print(f"  {le['id']} -> ({rp[0]:.4f}, {rp[1]:.4f}): {dist:.0f}m")
