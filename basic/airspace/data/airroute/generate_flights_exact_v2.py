"""
生成固定航线：严格使用原始航路的航路点数据
每条航线直接使用原始航路的航路点，保证完全重合
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
    """解析CZML坐标，返回航路点列表"""
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    # 格式: [[lon, lat], lat_repeat, height, ...]
    points = []
    i = 0
    while i < len(positions):
        coord = positions[i]
        height = positions[i+2] if i+2 < len(positions) else 70.0
        points.append({
            'lon': float(coord[0]),
            'lat': float(coord[1]),
            'height': float(height)
        })
        i += 3
    return points

# 构建航路数据库
print("构建航路数据库...")
route_data = {}  # 航路ID -> 完整航路点列表
route_ends = {}  # 航路ID -> 起点终点

for route in original_routes:
    rid = route['航路编号']
    points = parse_positions(route['CZML'])
    route_data[rid] = points
    route_ends[rid] = {
        'start': (points[0]['lon'], points[0]['lat']),
        'end': (points[-1]['lon'], points[-1]['lat'])
    }

# 构建连通图：端点 -> 航路ID列表
endpoint_to_routes = defaultdict(list)
for rid, ends in route_ends.items():
    endpoint_to_routes[ends['start']].append(rid)
    endpoint_to_routes[ends['end']].append(rid)

# 统计端点
all_endpoints = list(endpoint_to_routes.keys())
print(f"唯一端点: {len(all_endpoints)}")

# 生成航线策略：
# 1. 每次从一条未访问航路开始
# 2. 限制每条航线的航路数量（1-3条）
# 3. 保证所有96条航路都被覆盖
# 4. 生成约50条航线

random.seed(42)
all_rids = list(route_data.keys())
random.shuffle(all_rids)

visited = set()
all_flights = []
flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ', 'Ⅲ', 'Ⅲ']

def extend_path(current_rid, current_end, visited_local, max_routes=2):
    """从当前航路的指定端点扩展，返回(航路点列表, 经过的航路ID列表)"""
    path_points = []
    path_rids = []
    current_point = current_end  # 当前端点坐标
    route_count = 0

    while current_rid and current_rid not in visited_local and route_count < max_routes:
        visited_local.add(current_rid)
        points = route_data[current_rid]
        ends = route_ends[current_rid]

        # 确定航路的起点和终点
        start_pt = ends['start']
        end_pt = ends['end']

        # 判断是否需要反向
        if current_point is None:
            # 第一次，不反向
            for p in points:
                path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
            next_point = end_pt
        else:
            dist_to_start = ((current_point[0]-start_pt[0])**2 + (current_point[1]-start_pt[1])**2)**0.5
            dist_to_end = ((current_point[0]-end_pt[0])**2 + (current_point[1]-end_pt[1])**2)**0.5

            if dist_to_start < dist_to_end:
                # 从起点方向接入，需要反向
                for p in reversed(points):
                    path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
                next_point = start_pt
            else:
                # 从终点方向接入，正向
                for p in points:
                    path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
                next_point = end_pt

        path_rids.append(current_rid)
        route_count += 1

        # 找下一个航路（只在还没达到max_routes时找）
        if route_count < max_routes:
            next_rid = None
            for connected_rid in endpoint_to_routes[next_point]:
                if connected_rid not in visited_local:
                    next_rid = connected_rid
                    break
            current_rid = next_rid
            current_point = next_point
        else:
            break

    return path_points, path_rids

# 贪心生成航线
flight_id = 1

# 第一轮：生成连接的航线（每条航线包含2条航路）
for start_rid in all_rids:
    if flight_id > 50:
        break
    if start_rid in visited:
        continue

    # 从这条航路开始扩展，最多2条航路
    # 注意：extend_path内部不会检查visited，只检查visited_local
    visited_local = set()
    waypoints, path_rids = extend_path(start_rid, None, visited_local, max_routes=2)

    if not path_rids:
        continue

    # 只添加包含新航路的航线
    new_rids = [r for r in path_rids if r not in visited]
    if not new_rids:
        continue  # 跳过没有新航路的航线

    # 计算平均高度
    avg_height = int(sum(wp['高度'] for wp in waypoints) / len(waypoints)) if waypoints else 70

    flight = {
        "航线ID": f"FL{flight_id:03d}",
        "航线名称": f"{flight_types[flight_id % len(flight_types)]}{flight_id}号",
        "业务类型": flight_types[flight_id % len(flight_types)],
        "航路级别": priorities[flight_id % len(priorities)],
        "飞行高度(m)": avg_height,
        "覆盖航路": path_rids,
        "航路点": waypoints
    }

    all_flights.append(flight)
    visited.update(path_rids)
    flight_id += 1
    
    if len(visited) % 20 == 0:
        print(f"  已覆盖 {len(visited)} 条航路")

# 第二轮：确保所有未覆盖航路都被覆盖（逐条生成）
print(f"第二轮前 visited: {len(visited)}, 未覆盖: {len(all_rids) - len(visited)}")
print(f"未覆盖航路: {[r for r in all_rids if r not in visited][:10]}")
for rid in all_rids:
    if rid in visited:
        continue
    if flight_id > 50:
        # 已经50条了，无法再添加
        print(f"  警告: 达到50条限制，剩余 {len(all_rids) - len(visited)} 条航路未覆盖")
        break

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

# 保存
output = {"航线库": {"航线数据": all_flights}}
with open('fixed_routes_library.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"已保存到 fixed_routes_library.json")
