"""
生成固定航线：严格使用原始航路的航路点数据
策略：每条航线包含1-2条航路，优先尝试连接2条
"""
import json
import random
from collections import defaultdict

# 加载完整航路数据
with open('航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    all_routes = json.load(f)

original_routes = [r for r in all_routes if r.get('航路类型') != 'LINK']
print(f"原始航路: {len(original_routes)}条")

def parse_positions(czml_str):
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    points = []
    i = 0
    while i < len(positions):
        coord = positions[i]
        height = positions[i+2] if i+2 < len(positions) else 70.0
        points.append({'lon': float(coord[0]), 'lat': float(coord[1]), 'height': float(height)})
        i += 3
    return points

# 构建航路数据库
route_data = {}
route_ends = {}
for route in original_routes:
    rid = route['航路编号']
    points = parse_positions(route['CZML'])
    route_data[rid] = points
    route_ends[rid] = {'start': (points[0]['lon'], points[0]['lat']), 'end': (points[-1]['lon'], points[-1]['lat'])}

# 构建连通图
endpoint_to_routes = defaultdict(list)
for rid, ends in route_ends.items():
    endpoint_to_routes[ends['start']].append(rid)
    endpoint_to_routes[ends['end']].append(rid)

def find_connected(rid):
    """找与rid连接的航路"""
    connected = []
    ends = route_ends[rid]
    for endpoint in [ends['start'], ends['end']]:
        for connected_rid in endpoint_to_routes[endpoint]:
            if connected_rid != rid:
                connected.append(connected_rid)
    return connected

def build_flight_route(rids, waypoints_list):
    """构建航线航路点"""
    if not rids:
        return []
    
    waypoints = []
    for i, rid in enumerate(rids):
        points = route_data[rid]
        if i == 0:
            waypoints.extend([{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points])
        else:
            # 检查方向
            last_wp = waypoints[-1]['坐标']
            first_pt = (points[0]['lon'], points[0]['lat'])
            last_pt = (points[-1]['lon'], points[-1]['lat'])
            
            dist_first = ((last_wp[0]-first_pt[0])**2 + (last_wp[1]-first_pt[1])**2)**0.5
            dist_last = ((last_wp[0]-last_pt[0])**2 + (last_wp[1]-last_pt[1])**2)**0.5
            
            if dist_first < dist_last:
                for p in points[1:]:
                    waypoints.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
            else:
                for p in reversed(points[1:]):
                    waypoints.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
    
    return waypoints

# 生成航线
random.seed(42)
all_rids = list(route_data.keys())
random.shuffle(all_rids)

visited = set()
all_flights = []
flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ', 'Ⅲ', 'Ⅲ']

flight_id = 1
for start_rid in all_rids:
    if flight_id > 50:
        break
    if start_rid in visited:
        continue

    # 尝试连接另一条航路
    connected = find_connected(start_rid)
    second_rid = None
    for rid in connected:
        if rid not in visited:
            second_rid = rid
            break

    if second_rid:
        # 两条航路
        rids = [start_rid, second_rid]
        waypoints = build_flight_route(rids, None)
    else:
        # 单条航路
        rids = [start_rid]
        points = route_data[start_rid]
        waypoints = [{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points]

    avg_height = int(sum(wp['高度'] for wp in waypoints) / len(waypoints)) if waypoints else 70

    flight = {
        "航线ID": f"FL{flight_id:03d}",
        "航线名称": f"{flight_types[flight_id % len(flight_types)]}{flight_id}号",
        "业务类型": flight_types[flight_id % len(flight_types)],
        "航路级别": priorities[flight_id % len(priorities)],
        "飞行高度(m)": avg_height,
        "覆盖航路": rids,
        "航路点": waypoints
    }

    all_flights.append(flight)
    visited.update(rids)
    flight_id += 1

# 如果未达到50条且还有未覆盖航路，添加剩余航路
print(f"第一轮后: {len(all_flights)}条航线, visited={len(visited)}")
remaining = [r for r in all_rids if r not in visited]
print(f"未覆盖: {remaining}")

while len(all_flights) < 50 and len(visited) < len(all_rids):
    remaining = [r for r in all_rids if r not in visited]
    if not remaining:
        print("没有剩余航路")
        break
    
    rid = remaining[0]
    points = route_data[rid]
    waypoints = [{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points]
    avg_height = int(sum(wp['高度'] for wp in waypoints) / len(waypoints))
    
    flight = {
        "航线ID": f"FL{flight_id:03d}",
        "航线名称": f"{flight_types[flight_id % len(flight_types)]}{flight_id}号",
        "业务类型": flight_types[flight_id % len(flight_types)],
        "航路级别": priorities[flight_id % len(priorities)],
        "飞行高度(m)": avg_height,
        "覆盖航路": [rid],
        "航路点": waypoints
    }
    
    all_flights.append(flight)
    visited.add(rid)
    flight_id += 1

print(f"\n生成航线: {len(all_flights)}条")

# 统计覆盖
covered = set()
for f in all_flights:
    covered.update(f['覆盖航路'])
print(f"覆盖原始航路: {len(covered)}/{len(original_routes)}")

# 统计航线长度分布
counts = [len(f['覆盖航路']) for f in all_flights]
print(f"航线覆盖航路数: 1条={counts.count(1)}, 2条={counts.count(2)}")

# 保存
output = {"航线库": {"航线数据": all_flights}}
with open('fixed_routes_library.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"已保存到 fixed_routes_library.json")
