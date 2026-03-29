import json
from collections import defaultdict

with open('航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def parse_coords(coords):
    result = []
    i = 0
    while i < len(coords):
        if isinstance(coords[i], list):
            result.append((coords[i][0], coords[i][1]))
            i += 1
        else:
            i += 2
    return result

def round_pt(pt):
    return (round(pt[0], 3), round(pt[1], 3))

# 构建图 - 包含原始航路和LINK航路
graph = defaultdict(set)
route_endpoints = {}

for route in data:
    rid = route['航路编号']
    rtype = route.get('航路类型', 'A')
    czml = json.loads(route['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    parsed = parse_coords(coords)
    
    if len(parsed) >= 2:
        start_key = round_pt(parsed[0])
        end_key = round_pt(parsed[-1])
        
        # 添加端点
        graph[start_key].add(rid)
        graph[end_key].add(rid)
        route_endpoints[rid] = {
            'type': rtype,
            'start': start_key,
            'end': end_key
        }

print(f'总端点数量: {len(graph)}')
print(f'总航路数量: {len(route_endpoints)}')

# 找连通分量
visited = set()
components = []

def dfs(node, component):
    visited.add(node)
    component.add(node)
    for route_id in graph[node]:
        start_key = route_endpoints[route_id]['start']
        end_key = route_endpoints[route_id]['end']
        if start_key not in visited:
            dfs(start_key, component)
        if end_key not in visited:
            dfs(end_key, component)

for node in graph:
    if node not in visited:
        component = set()
        dfs(node, component)
        if component:
            components.append(component)

print(f'连通分量数量: {len(components)}')

# 分析每个分量
for i, comp in enumerate(components):
    lons = [pt[0] for pt in comp]
    lats = [pt[1] for pt in comp]
    
    # 找出属于这个分量的航路
    comp_routes = set()
    for pt in comp:
        for route_id in graph[pt]:
            comp_routes.add(route_id)
    
    route_types = defaultdict(int)
    for rid in comp_routes:
        route_types[route_endpoints[rid]['type']] += 1
    
    print(f'\n分量 {i+1} ({len(comp)} 个端点, {len(comp_routes)} 条航路): 经度 {min(lons):.4f}-{max(lons):.4f}, 纬度 {min(lats):.4f}-{max(lats):.4f}')
    print(f'  航路类型: {dict(route_types)}')
