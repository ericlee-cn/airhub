"""
生成固定航线：严格使用原始航路的航路点数据
航线 = 多条航路的航路点串联，保证完全重合
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
    """解析CZML坐标，返回[(lon, lat, height), ...]"""
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
route_ends = {}  # 航路ID -> (start, end)

for route in original_routes:
    rid = route['航路编号']
    points = parse_positions(route['CZML'])
    route_data[rid] = points
    route_ends[rid] = {
        'start': (points[0]['lon'], points[0]['lat']),
        'end': (points[-1]['lon'], points[-1]['lat']),
        'start_h': points[0]['height'],
        'end_h': points[-1]['height']
    }

print(f"航路数据: {len(route_data)}条")

# 构建端点连通图
endpoint_graph = defaultdict(list)
for rid, ends in route_ends.items():
    endpoint_graph[ends['start']].append((rid, 'end'))  # 端点是航路的end
    endpoint_graph[ends['end']].append((rid, 'start'))  # 端点是航路的start

all_endpoints = list(endpoint_graph.keys())
print(f"唯一端点: {len(all_endpoints)}")

# 生成航线：利用连通图构建完整路径
def build_path_from_route(start_rid, direction, visited, max_routes=None):
    """从一条航路开始，沿端点扩展路径"""
    path_points = []
    path_rids = []
    current_rid = start_rid
    current_end = direction  # 'start' 或 'end'
    route_count = 0

    while current_rid and current_rid not in visited:
        if max_routes and route_count >= max_routes:
            break

        visited.add(current_rid)
        points = route_data[current_rid]
        ends = route_ends[current_rid]

        if current_end == 'start':
            # 正向添加（从起点到终点）
            for p in points:
                path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
            current_end_point = ends['end']
        else:
            # 反向添加（从终点到起点）
            for p in reversed(points):
                path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
            current_end_point = ends['start']

        path_rids.append(current_rid)
        route_count += 1

        # 找下一个航路
        next_rid = None
        for connected_rid, connected_dir in endpoint_graph[current_end_point]:
            if connected_rid not in visited:
                next_rid = connected_rid
                # 如果当前端点是航路的start，说明连接点在航路终点
                current_end = 'end' if connected_dir == 'start' else 'start'
                break

        current_rid = next_rid

    return path_points, path_rids

# 生成航线策略：
# 1. 先生成完整连通路径
# 2. 然后拆分成50条航线
random.seed(42)
shuffled_rids = list(route_data.keys())
random.shuffle(shuffled_rids)

visited = set()
all_flights = []
flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ', 'Ⅲ', 'Ⅲ']

# 第一步：生成完整路径（用visited确保不重复）
full_path_points = []
full_path_rids = []

current_rid = shuffled_rids[0]
while current_rid and current_rid not in visited:
    visited.add(current_rid)
    points = route_data[current_rid]
    ends = route_ends[current_rid]

    # 添加航路点
    if not full_path_points:
        full_path_points.extend([{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points])
    else:
        # 检查方向
        last_wp = full_path_points[-1]['坐标']
        first_pt = (points[0]['lon'], points[0]['lat'])
        last_pt = (points[-1]['lon'], points[-1]['lat'])

        dist_first = ((last_wp[0]-first_pt[0])**2 + (last_wp[1]-first_pt[1])**2)**0.5
        dist_last = ((last_wp[0]-last_pt[0])**2 + (last_wp[1]-last_pt[1])**2)**0.5

        if dist_first < dist_last:
            # 正向添加
            for p in points[1:]:
                full_path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})
        else:
            # 反向添加
            for p in reversed(points[1:]):
                full_path_points.append({'坐标': [p['lon'], p['lat']], '高度': p['height']})

    full_path_rids.append(current_rid)

    # 找下一个航路
    next_rid = None
    for endpoint in [ends['start'], ends['end']]:
        for connected_rid, _ in endpoint_graph[endpoint]:
            if connected_rid not in visited:
                next_rid = connected_rid
                break
        if next_rid:
            break

    current_rid = next_rid

print(f"完整路径: {len(full_path_rids)}条航路, {len(full_path_points)}个航路点")

# 第二步：拆分成50条航线
total_routes = len(full_path_rids)
target_flights = min(50, total_routes)
routes_per_flight = max(2, total_routes // target_flights)  # 每条航线至少2条航路

idx = 0
flight_id = 1
while idx < len(full_path_rids):
    if flight_id > 50:
        break

    # 取一组航路
    group_rids = full_path_rids[idx:idx+routes_per_flight]
    if not group_rids:
        break

    # 提取这组航路的航路点
    waypoints = []
    for i, rid in enumerate(group_rids):
        points = route_data[rid]
        if i == 0:
            waypoints.extend([{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points])
        else:
            waypoints.extend([{'坐标': [p['lon'], p['lat']], '高度': p['height']} for p in points[1:]])

    # 计算平均高度
    avg_height = int(sum(wp['高度'] for wp in waypoints) / len(waypoints)) if waypoints else 70

    flight = {
        "航线ID": f"FL{flight_id:03d}",
        "航线名称": f"{flight_types[flight_id % len(flight_types)]}{flight_id}号",
        "业务类型": flight_types[flight_id % len(flight_types)],
        "航路级别": priorities[flight_id % len(priorities)],
        "飞行高度(m)": avg_height,
        "覆盖航路": group_rids,
        "航路点": waypoints
    }

    all_flights.append(flight)
    flight_id += 1
    idx += routes_per_flight

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
