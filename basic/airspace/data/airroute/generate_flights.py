# -*- coding: utf-8 -*-
"""
生成50条航线，覆盖所有96条原始航路
航线类型：运输、巡逻、应急、训练、勘察
"""

import json
import math
import random
from collections import defaultdict

# 读取数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 分离原始航路和连接线
original_routes = [r for r in data if r.get('航路类型') != 'LINK']
link_routes = [r for r in data if r.get('航路类型') == 'LINK']

print(f'原始航路: {len(original_routes)}')
print(f'连接线: {len(link_routes)}')

# 解析坐标
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

# 构建图
route_graph = defaultdict(list)  # route_id -> [connected_route_ids]
endpoint_routes = defaultdict(set)  # (lon, lat) -> {route_ids}

for route in data:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        start = coords[0]
        end = coords[-1]
        endpoint_routes[start].add(route['航路编号'])
        endpoint_routes[end].add(route['航路编号'])

# 构建航路连接关系
for route in data:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        start = coords[0]
        end = coords[-1]
        connected = endpoint_routes[start] | endpoint_routes[end]
        connected.discard(route['航路编号'])
        route_graph[route['航路编号']] = list(connected)

# 航线类型
flight_types = [
    {'name': '货物运输', 'prefix': 'HT', 'color': [255, 100, 100, 200]},
    {'name': '医疗转运', 'prefix': 'YL', 'color': [255, 200, 100, 200]},
    {'name': '空中巡逻', 'prefix': 'XL', 'color': [100, 255, 100, 200]},
    {'name': '应急救援', 'prefix': 'YJ', 'color': [255, 100, 255, 200]},
    {'name': '训练飞行', 'prefix': 'XL', 'color': [100, 200, 255, 200]},
    {'name': '地形勘察', 'prefix': 'KC', 'color': [200, 100, 255, 200]},
    {'name': '物流配送', 'prefix': 'WL', 'color': [255, 150, 50, 200]},
    {'name': '航拍作业', 'prefix': 'HP', 'color': [50, 200, 150, 200]},
]

# 计算航路长度
def calc_route_length(route):
    coords = parse_positions(route['CZML'])
    length = 0
    for i in range(len(coords) - 1):
        d = math.sqrt((coords[i+1][0] - coords[i][0])**2 + (coords[i+1][1] - coords[i][1])**2) * 111000
        length += d
    return length

# 为每条原始航路计算长度
route_lengths = {}
for route in original_routes:
    route_lengths[route['航路编号']] = calc_route_length(route)

# 生成航线
flights = []
covered_routes = set()

# 策略1: 先为每条原始航路生成1-2条航线
random.seed(42)
route_ids = [r['航路编号'] for r in original_routes]

# 生成基础航线（每条原始航路至少被一条航线覆盖）
flight_id = 1
route_coverage_count = defaultdict(int)  # 每条航路被覆盖的次数

for route in original_routes:
    route_id = route['航路编号']
    coords = parse_positions(route['CZML'])
    
    # 随机选择航向或反向
    if random.random() > 0.5:
        path_coords = coords
    else:
        path_coords = list(reversed(coords))
    
    ftype = random.choice(flight_types)
    flight = {
        '航线编号': f"{ftype['prefix']}{flight_id:03d}",
        '航线名称': f"{ftype['name']}航线{flight_id}",
        '航线类型': ftype['name'],
        '飞行时长': f"{random.randint(15, 45)}分钟",
        '航路数': 1,
        '坐标': path_coords,
        '颜色': ftype['color'],
        '覆盖航路': [route_id],
        '起点': coords[0],
        '终点': coords[-1]
    }
    flights.append(flight)
    covered_routes.add(route_id)
    route_coverage_count[route_id] += 1
    flight_id += 1

print(f'基础航线: {len(flights)}条')
print(f'覆盖航路: {len(covered_routes)}/{len(original_routes)}')

# 策略2: 生成多航路组合航线
# 从不同区域选取航路组成长航线
def get_route_region(route_id):
    """根据航路端点位置划分区域"""
    for r in data:
        if r['航路编号'] == route_id:
            coords = parse_positions(r['CZML'])
            avg_lon = sum(c[0] for c in coords) / len(coords)
            avg_lat = sum(c[1] for c in coords) / len(coords)
            if avg_lon < 119.95:
                return 'west'
            elif avg_lon < 120.0:
                return 'center-west'
            elif avg_lon < 120.05:
                return 'center'
            else:
                return 'east'

# 分区域生成组合航线
regions = defaultdict(list)
for route in original_routes:
    region = get_route_region(route['航路编号'])
    regions[region].append(route['航路编号'])

# 生成跨区域长航线
while flight_id <= 35 and len(regions['west']) > 0 and len(regions['east']) > 0:
    # 随机选择起点区域
    start_region = random.choice(['west', 'center-west'])
    end_region = random.choice(['center', 'east'])
    
    if start_region in regions and end_region in regions:
        start_route = random.choice(regions[start_region])
        end_route = random.choice(regions[end_region])
        
        # 使用简单的贪心路径（这里简化处理，直接连接两端的连接线）
        for link in link_routes:
            coords = parse_positions(link['CZML'])
            link_start = coords[0]
            link_end = coords[-1]
            
            # 找包含起点的连接
            if any(r['航路编号'] == start_route for r in data if parse_positions(r['CZML'])[0] == link_start):
                # 找包含终点的连接
                for link2 in link_routes:
                    coords2 = parse_positions(link2['CZML'])
                    if coords2[-1] == link_end:
                        # 组合路径
                        ftype = random.choice(flight_types[:4])  # 优先运输/医疗/巡逻/应急
                        path_coords = [parse_positions(
                            [r for r in data if r['航路编号'] == start_route][0]['CZML']
                        )[0]]
                        path_coords.extend(coords)
                        path_coords.extend(coords2)
                        path_coords.append(parse_positions(
                            [r for r in data if r['航路编号'] == end_route][0]['CZML']
                        )[-1])
                        
                        flight = {
                            '航线编号': f"{ftype['prefix']}{flight_id:03d}",
                            '航线名称': f"{ftype['name']}航线{flight_id}",
                            '航线类型': ftype['name'],
                            '飞行时长': f"{random.randint(35, 55)}分钟",
                            '航路数': 4,
                            '坐标': path_coords,
                            '颜色': ftype['color'],
                            '覆盖航路': [start_route, end_route],
                        }
                        flights.append(flight)
                        flight_id += 1
                        break
        break

# 策略3: 生成更多循环航线
while flight_id <= 50:
    # 随机选择起始航路
    if len(original_routes) == 0:
        break
    
    start_route = random.choice(original_routes)
    coords = parse_coords(start_route['CZML'])
    
    # 尝试扩展形成回路
    path = [start_route['航路编号']]
    current = start_route['航路编号']
    current_coords = list(coords)
    
    # 最多添加3条航路形成小回路
    for _ in range(3):
        neighbors = route_graph.get(current, [])
        if not neighbors:
            break
        
        # 优先选择未覆盖的航路
        uncovered = [n for n in neighbors if n not in covered_routes]
        if uncovered:
            next_route = random.choice(uncovered)
        else:
            next_route = random.choice(neighbors)
        
        if next_route in path:
            break
        
        path.append(next_route)
        for r in data:
            if r['航路编号'] == next_route:
                next_coords = parse_positions(r['CZML'])
                # 判断连接方向
                if current_coords[-1] == next_coords[0]:
                    current_coords.extend(next_coords[1:])
                elif current_coords[-1] == next_coords[-1]:
                    current_coords.extend(list(reversed(next_coords))[:-1])
                else:
                    break
                current = next_route
                break
    
    if len(path) >= 1:
        ftype = random.choice(flight_types)
        total_length = sum(route_lengths.get(r, 0) for r in path)
        duration = max(10, min(50, int(total_length / 200)))
        
        flight = {
            '航线编号': f"{ftype['prefix']}{flight_id:03d}",
            '航线名称': f"{ftype['name']}航线{flight_id}",
            '航线类型': ftype['name'],
            '飞行时长': f"{duration}分钟",
            '航路数': len(path),
            '坐标': current_coords,
            '颜色': ftype['color'],
            '覆盖航路': path,
        }
        flights.append(flight)
        for r in path:
            covered_routes.add(r)
            route_coverage_count[r] += 1
        flight_id += 1

print(f'生成航线: {len(flights)}条')
print(f'覆盖航路: {len(covered_routes)}/{len(original_routes)}')

# 统计覆盖情况
fully_covered = sum(1 for r in original_routes if route_coverage_count[r['航路编号']] > 0)
print(f'完全覆盖航路: {fully_covered}/{len(original_routes)}')

# 生成航线CZML数据
flight_czmls = []
for flight in flights:
    if len(flight['坐标']) < 2:
        continue
    
    # 创建航迹CZML
    positions = []
    for coord in flight['坐标']:
        positions.append([coord[0], coord[1]])
        positions.append(coord[1])  # lat重复
        positions.append(70.0)  # 高度
    
    czml = {
        "id": flight['航线编号'],
        "name": flight['航线名称'],
        "corridor": {
            "positions": {"cartographicDegrees": positions},
            "width": 80.0,
            "material": {
                "solidColor": {
                    "color": {"rgba": flight['颜色']}
                }
            },
            "extrudedHeight": 30.0,
            "height": 0
        }
    }
    flight['CZML'] = json.dumps(czml, ensure_ascii=False)

# 保存航线数据
output = {
    'flights': flights,
    'statistics': {
        'total_flights': len(flights),
        'covered_routes': len(covered_routes),
        'total_original_routes': len(original_routes),
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
print(f'已保存到: {output_js}')
print('\n完成!')
