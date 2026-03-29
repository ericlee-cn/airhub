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

print(f'原始航路: {len(original_routes)}')

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

# 航路长度
route_lengths = {r['航路编号']: calc_route_length(r) for r in original_routes}

# 构建连接关系
endpoint_routes = defaultdict(set)
for route in original_routes:
    coords = parse_positions(route['CZML'])
    endpoint_routes[coords[0]].add(route['航路编号'])
    endpoint_routes[coords[-1]].add(route['航路编号'])

# 航线类型
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

random.seed(42)

# 目标：50条航线覆盖96条航路
TARGET_FLIGHTS = 50
TARGET_ROUTES = len(original_routes)

flights = []
covered_routes = set()
route_coverage_count = defaultdict(int)

# 策略：每条航路分配到1-2条航线
route_assignments = defaultdict(list)  # route_id -> [flight_indices]

# 第一批：单航路航线（覆盖所有96条）
flight_id = 1
for route in original_routes:
    coords = parse_positions(route['CZML'])
    ftype = random.choice(flight_types)
    
    flight = {
        '航线编号': f"{ftype['prefix']}{flight_id:03d}",
        '航线名称': f"{ftype['name']}{flight_id}号",
        '航线类型': ftype['name'],
        '飞行时长': f"{random.randint(10, 25)}分钟",
        '航路数': 1,
        '坐标': coords,
        '颜色': ftype['color'],
        '覆盖航路': [route['航路编号']],
    }
    flights.append(flight)
    covered_routes.add(route['航路编号'])
    route_coverage_count[route['航路编号']] += 1
    route_assignments[route['航路编号']].append(flight_id - 1)
    flight_id += 1

print(f'阶段1: {len(flights)}条航线, 覆盖{len(covered_routes)}条航路')

# 第二批：合并短航路形成长航线
# 将一些短航路合并到现有航线
while flight_id <= TARGET_FLIGHTS and len(original_routes) > len(flights):
    # 找一个已经有航线的航路作为基础
    base_routes = [r for r in original_routes if route_coverage_count[r['航路编号']] == 1]
    if not base_routes:
        break
    
    # 找一条短航路
    short_routes = sorted(base_routes, key=lambda r: route_lengths[r['航路编号']])[:10]
    if not short_routes:
        break
    
    short_route = random.choice(short_routes)
    
    # 找它相邻的航路
    coords = parse_positions(short_route['CZML'])
    neighbors = set()
    for pt in [coords[0], coords[-1]]:
        neighbors.update(endpoint_routes.get(pt, set()))
    neighbors.discard(short_route['航路编号'])
    
    if neighbors:
        neighbor = random.choice(list(neighbors))
        neighbor_coords = None
        for r in original_routes:
            if r['航路编号'] == neighbor:
                neighbor_coords = parse_positions(r['CZML'])
                break
        
        if neighbor_coords:
            # 尝试合并
            ftype = random.choice(flight_types)
            
            # 判断方向
            if coords[-1] == neighbor_coords[0]:
                merged_coords = coords + neighbor_coords[1:]
            elif coords[-1] == neighbor_coords[-1]:
                merged_coords = coords + list(reversed(neighbor_coords))[:-1]
            elif coords[0] == neighbor_coords[0]:
                merged_coords = list(reversed(coords))[:-1] + neighbor_coords
            elif coords[0] == neighbor_coords[-1]:
                merged_coords = neighbor_coords + coords[1:]
            else:
                continue
            
            # 更新航线
            old_idx = route_assignments[short_route['航路编号']][0]
            old_flight = flights[old_idx]
            
            old_coords = old_flight['坐标']
            if old_coords[-1] == neighbor_coords[0]:
                new_coords = old_coords + neighbor_coords[1:]
            elif old_coords[-1] == neighbor_coords[-1]:
                new_coords = old_coords + list(reversed(neighbor_coords))[:-1]
            else:
                continue
            
            total_length = calc_route_length(short_route) + calc_route_length(neighbor)
            
            old_flight['坐标'] = new_coords
            old_flight['航路数'] += 1
            old_flight['覆盖航路'].append(neighbor)
            old_flight['飞行时长'] = f"{int(total_length/200)}分钟"
            
            covered_routes.add(neighbor)
            route_coverage_count[neighbor] += 1
            route_assignments[neighbor].append(old_idx)
            
            flight_id += 1

print(f'阶段2: {len(flights)}条航线, 覆盖{len(covered_routes)}条航路')

# 第三批：补充剩余航线达到50条
while len(flights) < TARGET_FLIGHTS:
    # 从未充分覆盖的区域选取航路组成新航线
    uncovered = [r['航路编号'] for r in original_routes if route_coverage_count[r['航路编号']] < 2]
    
    if uncovered:
        # 选择2-3条相邻航路
        path = [random.choice(uncovered)]
        
        for _ in range(2):
            last_coords = None
            for r in original_routes:
                if r['航路编号'] == path[-1]:
                    last_coords = parse_positions(r['CZML'])
                    break
            
            neighbors = set()
            for pt in [last_coords[0], last_coords[-1]]:
                neighbors.update(endpoint_routes.get(pt, set()))
            neighbors.discard(path[-1])
            
            if neighbors:
                path.append(random.choice(list(neighbors)))
            else:
                break
        
        # 构建路径坐标
        path_coords = []
        for i, rid in enumerate(path):
            for r in original_routes:
                if r['航路编号'] == rid:
                    coords = parse_positions(r['CZML'])
                    if i == 0:
                        path_coords = coords
                    else:
                        if path_coords[-1] == coords[0]:
                            path_coords.extend(coords[1:])
                        elif path_coords[-1] == coords[-1]:
                            path_coords.extend(list(reversed(coords))[:-1])
                    break
        
        if len(path_coords) >= 2:
            ftype = random.choice(flight_types)
            total_length = sum(route_lengths[r] for r in path)
            
            flight = {
                '航线编号': f"{ftype['prefix']}{len(flights)+1:03d}",
                '航线名称': f"{ftype['name']}{len(flights)+1}号",
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
                route_coverage_count[r] += 1
    else:
        # 复制一些现有航线作为备份
        base = random.choice(flights)
        ftype = random.choice(flight_types)
        
        new_flight = base.copy()
        new_flight['航线编号'] = f"{ftype['prefix']}{len(flights)+1:03d}"
        new_flight['航线名称'] = f"{ftype['name']}{len(flights)+1}号"
        flights.append(new_flight)
        flight_id += 1

print(f'\n最终: {len(flights)}条航线')
print(f'覆盖航路: {len(covered_routes)}/{len(original_routes)}')

# 统计
type_count = defaultdict(int)
for f in flights:
    type_count[f['航线类型']] += 1

print('\n航线类型统计:')
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

print(f'\n已保存到: {output_file}')
print('完成!')
