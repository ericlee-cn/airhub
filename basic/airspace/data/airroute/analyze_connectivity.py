import json
from collections import defaultdict

with open('航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def parse_coords(coords):
    """解析嵌套格式的坐标: [[lon, lat], height, ...] -> [(lon, lat), ...]"""
    result = []
    i = 0
    while i < len(coords):
        if isinstance(coords[i], list):
            result.append((coords[i][0], coords[i][1]))
            i += 1
        else:
            i += 2
    return result

# 构建图 - 每个航路端点是一个节点
# 节点格式: (lon, lat) 四舍五入到小数点后3位
def round_pt(pt):
    return (round(pt[0], 3), round(pt[1], 3))

# 收集所有端点
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

# 构建邻接表
graph = defaultdict(set)
for e in endpoints:
    start_key = round_pt(e['start'])
    end_key = round_pt(e['end'])
    graph[start_key].add(e['id'])
    graph[end_key].add(e['id'])

# 找连通分量
visited = set()
components = []

def dfs(node, component):
    visited.add(node)
    component.add(node)
    for neighbor in graph[node]:
        for n2 in graph:
            if neighbor in graph[n2] and n2 not in visited:
                dfs(n2, component)

for node in graph:
    if node not in visited:
        component = set()
        dfs(node, component)
        if component:
            components.append(component)

print(f'原始航路端点数量: {len(graph)}')
print(f'连通分量数量: {len(components)}')

# 分析每个分量
for i, comp in enumerate(components):
    lons = [pt[0] for pt in comp]
    lats = [pt[1] for pt in comp]
    print(f'\n分量 {i+1} ({len(comp)} 个端点): 经度 {min(lons):.4f}-{max(lons):.4f}, 纬度 {min(lats):.4f}-{max(lats):.4f}')
    
    # 找出属于这个分量的航路
    comp_routes = set()
    for pt in comp:
        for route_id in graph[pt]:
            comp_routes.add(route_id)
    print(f'  包含航路: {sorted(list(comp_routes))[:10]}...' if len(comp_routes) > 10 else f'  包含航路: {sorted(list(comp_routes))}')

# 找出需要连接的端点对（跨分量的最近点对）
print('\n=== 跨分量连接建议 ===')
if len(components) >= 2:
    # 按经度排序分量
    sorted_comps = sorted(components, key=lambda c: min(pt[0] for pt in c))
    
    # 检查相邻分量之间的距离
    for i in range(len(sorted_comps) - 1):
        comp1 = sorted_comps[i]
        comp2 = sorted_comps[i + 1]
        
        # 找最近的跨分量点对
        min_dist = float('inf')
        best_pair = None
        for pt1 in comp1:
            for pt2 in comp2:
                dist = ((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)**0.5 * 111 * 1000
                if dist < min_dist:
                    min_dist = dist
                    best_pair = (pt1, pt2)
        
        print(f'分量 {i+1} <-> 分量 {i+2}: 最近距离 {min_dist:.0f}m')
        print(f'  点1: ({best_pair[0][0]:.4f}, {best_pair[0][1]:.4f})')
        print(f'  点2: ({best_pair[1][0]:.4f}, {best_pair[1][1]:.4f})')
        
        # 找出属于这两个点的航路
        routes1 = graph[best_pair[0]]
        routes2 = graph[best_pair[1]]
        print(f'  点1属于航路: {routes1}')
        print(f'  点2属于航路: {routes2}')
