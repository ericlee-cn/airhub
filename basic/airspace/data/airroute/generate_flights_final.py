# -*- coding: utf-8 -*-
"""
生成50条航线，覆盖所有96条原始航路
"""

import json
import math
import random
from collections import defaultdict

# 读取数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

original_routes = [r for r in data if r.get('航路类型') != 'LINK']
link_routes = [r for r in data if r.get('航路类型') == 'LINK']

def parse_positions(czml_str):
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    coords = []
    i = 0
    while i < len(positions):
        if isinstance(positions[i], list):
            lon = float(positions[i][0])
            lat = float(positions[i][1])
            coords.append((lon, lat))
            i += 1
            if i + 1 < len(positions):
                i += 2
        else:
            break
    return coords

def calc_route_length(route):
    coords = parse_positions(route['CZML'])
    length = 0
    for i in range(len(coords) - 1):
        d = math.sqrt((coords[i+1][0] - coords[i][0])**2 + (coords[i+1][1] - coords[i][1])**2) * 111000
        length += d
    return length

route_lengths = {r['航路编号']: calc_route_length(r) for r in original_routes}

# 构建连接关系
endpoint_routes = defaultdict(set)
route_coords = {}
for route in original_routes:
    coords = parse_positions(route['CZML'])
    route_coords[route['航路编号']] = coords
    endpoint_routes[coords[0]].add(route['航路编号'])
    endpoint_routes[coords[-1]].add(route['航路编号'])

flight_types = [
    {'name': '货物运输', 'prefix': 'HT', 'color': [255, 100, 100, 200]},
    {'name': '医疗转运', 'prefix': 'YL', 'color': [255, 200, 100, 200]},
    {'name': '空中巡逻', 'prefix': 'XL', 'color': [100, 255, 100, 200]},
    {'name': '应急救援', 'prefix': 'YJ', 'color': [255, 100, 255, 200]},
    {'name': '训练飞行', 'prefix': 'PX', 'color': [100, 200, 255, 200]},
    {'name': '地形勘察', 'prefix': 'KC', 'color': [200, 100, 255, 200]},
    {'name': '物流配送', 'prefix': 'WL', 'color': [255, 150, 50, 200]},
    {'name': '航拍作业', 'prefix': 'HP', 'color': [50, 200, 150, 200]},
]

random.seed(100)

# 生成50条航线
flights = []
covered_routes = set()
route_coverage = defaultdict(int)

TARGET = 50
MAX_ROUTES_PER_FLIGHT = 3

# 第一批：覆盖所有96条航路，每条航路至少被一条航线覆盖
all_route_ids = [r['航路编号'] for r in original_routes]
random.shuffle(all_route_ids)

flight_id = 1

# 用贪心算法分配航路到航线
while len(covered_routes) < len(all_route_ids):
    # 选择未覆盖或覆盖少的航路作为起点
    uncovered = [r for r in all_route_ids if route_coverage[r] == 0]
    if not uncovered:
        uncovered = [r for r in all_route_ids if route_coverage[r] == 1]
    
    if not uncovered:
        break
    
    start_route = random.choice(uncovered)
    path = [start_route]
    
    # 尝试扩展路径
    current = start_route
    for _ in range(MAX_ROUTES_PER_FLIGHT - 1):
        coords = route_coords[current]
        neighbors = set()
        for pt in [coords[0], coords[-1]]:
            neighbors.update(endpoint_routes.get(pt, set()))
        neighbors.discard(current)
        
        # 优先选未覆盖的
        uncovered_neighbors = [n for n in neighbors if route_coverage[n] == 0]
        if uncovered_neighbors:
            path.append(random.choice(uncovered_neighbors))
            current = path[-1]
        elif neighbors:
            path.append(random.choice(list(neighbors)))
            current = path[-1]
        else:
            break
    
    # 构建路径坐标
    path_coords = []
    for i, rid in enumerate(path):
        coords = route_coords[rid]
        if i == 0:
            path_coords = list(coords)
        else:
            if path_coords[-1] == coords[0]:
                path_coords.extend(coords[1:])
            elif path_coords[-1] == coords[-1]:
                path_coords.extend(list(reversed(coords))[:-1])
    
    ftype = random.choice(flight_types)
    total_length = sum(route_lengths[r] for r in path)
    
    flight = {
        '航线编号': f"{ftype['prefix']}{flight_id:03d}",
        '航线名称': f"{ftype['name']}{flight_id}号",
        '航线类型': ftype['name'],
        '飞行时长': f"{int(total_length/200)}分钟",
        '航路数': len(path),
        '坐标': path_coords,
        '颜色': ftype['color'],
        '覆盖航路': path,
    }
    flights.append(flight)
    
    for r in path:
        covered_routes.add(r)
        route_coverage[r] += 1
    
    flight_id += 1

# 第二批：补充到50条
while len(flights) < TARGET:
    # 随机选择2-3条航路组成新航线
    path = random.sample(all_route_ids, min(3, len(all_route_ids)))
    
    # 构建路径
    path_coords = []
    for i, rid in enumerate(path):
        coords = route_coords[rid]
        if i == 0:
            path_coords = list(coords)
        else:
            if path_coords[-1] == coords[0]:
                path_coords.extend(coords[1:])
            elif path_coords[-1] == coords[-1]:
                path_coords.extend(list(reversed(coords))[:-1])
    
    ftype = random.choice(flight_types)
    total_length = sum(route_lengths[r] for r in path)
    
    flight = {
        '航线编号': f"{ftype['prefix']}{flight_id:03d}",
        '航线名称': f"{ftype['name']}{flight_id}号",
        '航线类型': ftype['name'],
        '飞行时长': f"{int(total_length/200)}分钟",
        '航路数': len(path),
        '坐标': path_coords,
        '颜色': ftype['color'],
        '覆盖航路': path,
    }
    flights.append(flight)
    
    for r in path:
        covered_routes.add(r)
        route_coverage[r] += 1
    
    flight_id += 1

print(f'生成航线: {len(flights)}条')
print(f'覆盖航路: {len(covered_routes)}/{len(original_routes)} ({len(covered_routes)/len(original_routes)*100:.1f}%)')

# 统计
type_count = defaultdict(int)
for f in flights:
    type_count[f['航线类型']] += 1

print('\n航线类型:')
for t, c in sorted(type_count.items()):
    print(f'  {t}: {c}条')

# 生成CZML
for flight in flights:
    coords = flight['坐标']
    positions = []
    for coord in coords:
        positions.append([coord[0], coord[1]])
        positions.append(coord[1])
        positions.append(70.0)
    
    czml = {
        "id": flight['航线编号'],
        "name": flight['航线名称'],
        "corridor": {
            "positions": {"cartographicDegrees": positions},
            "width": 80.0,
            "material": {"solidColor": {"color": {"rgba": flight['颜色']}}},
            "extrudedHeight": 30.0,
            "height": 0
        }
    }
    flight['CZML'] = json.dumps(czml, ensure_ascii=False)

# 保存
output = {
    'flights': flights,
    'statistics': {
        'total_flights': len(flights),
        'covered_routes': len(covered_routes),
        'total_routes': len(original_routes),
        'coverage_rate': f"{len(covered_routes)/len(original_routes)*100:.1f}%"
    }
}

output_file = 'C:/mgs/basic/airspace/data/airroute/航线数据.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

js_content = 'const flightData = ' + json.dumps(output, ensure_ascii=False) + ';'
output_js = 'C:/mgs/basic/airspace/data/airroute/航线数据.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f'\n已保存!')
