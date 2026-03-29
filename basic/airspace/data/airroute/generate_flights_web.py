# -*- coding: utf-8 -*-
"""
生成50条航线（网页格式），覆盖所有96条原始航路
"""

import json
import math
import random
from collections import defaultdict

# 读取数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

original_routes = [r for r in data if r.get('航路类型') != 'LINK']

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

# 业务类型
business_types = [
    {'type': '货物运输', 'goal': '紧急物资配送', 'analysis': '适用于无人机快递、同城配送等场景'},
    {'type': '医疗转运', 'goal': '器官、血液紧急运输', 'analysis': '用于医疗急救、稀缺药品配送'},
    {'type': '空中巡逻', 'goal': '城市安全监控', 'analysis': '适用于交通监控、违章抓拍、安防巡逻'},
    {'type': '应急救援', 'goal': '灾害现场勘察', 'analysis': '用于山区搜救、火灾监测、洪水勘测'},
    {'type': '训练飞行', 'goal': '驾驶员培训', 'analysis': '飞行训练、考核、标准航线验证'},
    {'type': '地形勘察', 'goal': '地理信息采集', 'analysis': '航测制图、倾斜摄影、三维建模'},
    {'type': '物流配送', 'goal': '偏远地区配送', 'analysis': '山区海岛配送、农产品运输'},
    {'type': '航拍作业', 'goal': '影视广告拍摄', 'analysis': '婚礼摄影、广告航拍、直播转播'},
]

# 航路级别颜色映射
route_colors = {'A': 'Ⅰ', 'B': 'Ⅱ', 'C': 'Ⅲ', 'D': 'Ⅲ'}

random.seed(100)

# 生成50条航线
flights = []
covered_routes = set()
route_coverage = defaultdict(int)

TARGET = 50
all_route_ids = [r['航路编号'] for r in original_routes]
random.shuffle(all_route_ids)

flight_id = 1

# 贪心分配
while len(covered_routes) < len(all_route_ids):
    uncovered = [r for r in all_route_ids if route_coverage[r] == 0]
    if not uncovered:
        uncovered = [r for r in all_route_ids if route_coverage[r] == 1]
    if not uncovered:
        break
    
    start_route = random.choice(uncovered)
    path = [start_route]
    
    # 扩展路径
    current = start_route
    for _ in range(2):  # 最多3条航路
        coords = route_coords[current]
        neighbors = set()
        for pt in [coords[0], coords[-1]]:
            neighbors.update(endpoint_routes.get(pt, set()))
        neighbors.discard(current)
        
        uncovered_neighbors = [n for n in neighbors if route_coverage[n] == 0]
        if uncovered_neighbors:
            path.append(random.choice(uncovered_neighbors))
            current = path[-1]
        elif neighbors:
            path.append(random.choice(list(neighbors)))
            current = path[-1]
        else:
            break
    
    # 构建路径坐标（带高度）
    path_coords = []
    for i, rid in enumerate(path):
        coords = route_coords[rid]
        if i == 0:
            for c in coords:
                path_coords.append((c[0], c[1], 70))
        else:
            if path_coords[-1][0:2] == coords[0]:
                for c in coords[1:]:
                    path_coords.append((c[0], c[1], 70))
            elif path_coords[-1][0:2] == coords[-1]:
                for c in reversed(coords[:-1]):
                    path_coords.append((c[0], c[1], 70))
    
    # 获取航路信息
    route_info = next((r for r in original_routes if r['航路编号'] == path[0]), None)
    route_type = route_info.get('航路类型', 'A') if route_info else 'A'
    route_level = route_colors.get(route_type, 'Ⅲ')
    
    business = random.choice(business_types)
    total_length = sum(route_lengths[r] for r in path)
    duration = max(10, min(60, int(total_length / 150)))
    speed = random.randint(60, 120)
    
    flight = {
        '航线ID': f"FL{flight_id:03d}",
        '航线名称': f"{business['type']}{flight_id}号",
        '航线坐标': path_coords,
        '起点坐标': {'lon': path_coords[0][0], 'lat': path_coords[0][1], 'height': path_coords[0][2]},
        '终点坐标': {'lon': path_coords[-1][0], 'lat': path_coords[-1][1], 'height': path_coords[-1][2]},
        '起点名称': f"起降点{flight_id}",
        '终点名称': f"降落点{flight_id}",
        '所属航路': ','.join(path[:2]) + ('...' if len(path) > 2 else ''),
        '航路级别': route_level,
        '航路类型': route_type,
        '航线距离_m': int(total_length),
        '最高限速_kmh': speed,
        '预计飞行时间_min': duration,
        '业务类型': business['type'],
        '业务目标': business['goal'],
        '业务分析': business['analysis'],
    }
    flights.append(flight)
    
    for r in path:
        covered_routes.add(r)
        route_coverage[r] += 1
    
    flight_id += 1

# 补充到50条
while len(flights) < TARGET:
    path = random.sample(all_route_ids, min(3, len(all_route_ids)))
    
    path_coords = []
    for i, rid in enumerate(path):
        coords = route_coords[rid]
        if i == 0:
            for c in coords:
                path_coords.append((c[0], c[1], 70))
        else:
            if path_coords[-1][0:2] == coords[0]:
                for c in coords[1:]:
                    path_coords.append((c[0], c[1], 70))
            elif path_coords[-1][0:2] == coords[-1]:
                for c in reversed(coords[:-1]):
                    path_coords.append((c[0], c[1], 70))
    
    route_info = next((r for r in original_routes if r['航路编号'] == path[0]), None)
    route_type = route_info.get('航路类型', 'A') if route_info else 'A'
    route_level = route_colors.get(route_type, 'Ⅲ')
    
    business = random.choice(business_types)
    total_length = sum(route_lengths[r] for r in path)
    duration = max(10, min(60, int(total_length / 150)))
    speed = random.randint(60, 120)
    
    flight = {
        '航线ID': f"FL{flight_id:03d}",
        '航线名称': f"{business['type']}{flight_id}号",
        '航线坐标': path_coords,
        '起点坐标': {'lon': path_coords[0][0], 'lat': path_coords[0][1], 'height': path_coords[0][2]},
        '终点坐标': {'lon': path_coords[-1][0], 'lat': path_coords[-1][1], 'height': path_coords[-1][2]},
        '起点名称': f"起降点{flight_id}",
        '终点名称': f"降落点{flight_id}",
        '所属航路': ','.join(path[:2]) + ('...' if len(path) > 2 else ''),
        '航路级别': route_level,
        '航路类型': route_type,
        '航线距离_m': int(total_length),
        '最高限速_kmh': speed,
        '预计飞行时间_min': duration,
        '业务类型': business['type'],
        '业务目标': business['goal'],
        '业务分析': business['analysis'],
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
    type_count[f['业务类型']] += 1

print('\n业务类型统计:')
for t, c in sorted(type_count.items()):
    print(f'  {t}: {c}条')

# 保存
output = {
    '航线库': {
        '航线数据': flights
    }
}

output_file = 'C:/mgs/basic/airspace/data/airline/fixed_routes_library.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n已保存到: {output_file}')
print('完成!')
