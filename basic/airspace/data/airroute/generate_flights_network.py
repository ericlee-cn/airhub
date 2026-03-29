"""
生成固定航线：基于完整航路网络（原始96条+21条连接线）
每条航线由多条航路串联组成，覆盖所有原始航路
"""
import json
import random
from collections import defaultdict

# 加载完整航路数据（原始96条 + 21条连接线）
with open('航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    all_routes = json.load(f)

original_routes = [r for r in all_routes if r.get('航路类型') != 'LINK']
link_routes = [r for r in all_routes if r.get('航路类型') == 'LINK']

print(f"原始航路: {len(original_routes)}条")
print(f"连接线: {len(link_routes)}条")

def parse_positions(czml_str):
    """解析CZML坐标格式"""
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    # 格式: [[lon, lat], lat_repeat, height, ...]
    points = []
    i = 0
    while i < len(positions):
        coord = positions[i]
        height = positions[i+2] if i+2 < len(positions) else 70.0
        points.append({
            'coord': (float(coord[0]), float(coord[1])),
            'height': float(height)
        })
        i += 3
    return points

# 构建航路端点和航路点数据库
print("\n构建航路数据库...")
route_ends = {}  # 航路ID -> (start_point, end_point)
route_points = {}  # 航路ID -> 所有航路点
point_to_routes = defaultdict(list)  # 航路点 -> 航路ID列表

for route in all_routes:
    rid = route['航路编号']
    points = parse_positions(route['CZML'])
    route_points[rid] = points

    start = points[0]['coord']
    end = points[-1]['coord']
    route_ends[rid] = {'start': start, 'end': end, 'start_height': points[0]['height'], 'end_height': points[-1]['height']}

    # 记录端点到航路的映射
    point_to_routes[start].append(rid)
    point_to_routes[end].append(rid)

print(f"航路端点数量: {len(route_ends)}")

# 构建连通图：航路端点 -> 连接的航路ID
endpoint_graph = defaultdict(set)
for rid, ends in route_ends.items():
    endpoint_graph[ends['start']].add(rid)
    endpoint_graph[ends['end']].add(rid)

# 统计端点
all_endpoints = list(set(p for ends in route_ends.values() for p in [ends['start'], ends['end']]))
print(f"唯一端点数量: {len(all_endpoints)}")

# 生成航线策略：
# 1. 每条航线从一个端点开始
# 2. 沿着航路网络前进
# 3. 收集经过的所有航路ID
# 4. 航线总数控制在50条以内

def build_route_path(start_rid, visited_routes):
    """从一条航路开始，构建完整路径"""
    path = []
    route_ids = []  # 经过的航路ID

    # 可以双向扩展
    current_start = route_ends[start_rid]['start']
    current_end = route_ends[start_rid]['end']
    visited = set(visited_routes)
    visited.add(start_rid)

    # 向起点方向扩展
    forward_rid = start_rid
    forward_end = route_ends[start_rid]['end']

    # 向终点方向扩展
    backward_rid = start_rid
    backward_start = route_ends[start_rid]['start']

    # 收集航路点（按顺序）
    waypoints = []

    # 添加起始航路的所有点
    waypoints.extend([(p['coord'], p['height']) for p in route_points[start_rid]])

    return waypoints, route_ids

# 贪心策略：从每个未访问的端点开始扩展
visited = set()
all_flights = []
flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ']

# 按连通性分组航路
def get_connected_routes(start_rid):
    """获取与某航路连通的所有航路"""
    connected = set()
    queue = [start_rid]

    while queue:
        rid = queue.pop(0)
        if rid in connected:
            continue
        connected.add(rid)

        # 找到这个航路的端点
        ends = route_ends[rid]
        for endpoint in [ends['start'], ends['end']]:
            # 找所有以这个端点为起点的航路
            for connected_rid in endpoint_graph[endpoint]:
                if connected_rid not in connected:
                    queue.append(connected_rid)

    return connected

# 找连通分量
components = []
checked = set()
for rid in route_ends.keys():
    if rid not in checked:
        comp = get_connected_routes(rid)
        components.append(comp)
        checked.update(comp)

print(f"\n连通分量数: {len(components)}")
for i, comp in enumerate(components):
    originals = [r for r in comp if not r.startswith('LK')]
    print(f"  分量{i+1}: {len(comp)}条航路 ({len(originals)}条原始)")

# 生成航线：每个连通分量生成若干条航线
flight_id = 1
for comp_idx, comp in enumerate(components):
    comp_rids = list(comp)
    original_rids = [r for r in comp_rids if not r.startswith('LK')]

    if not original_rids:
        continue

    # 根据原始航路数量决定航线数量
    # 目标：每条航线平均覆盖2条原始航路，确保50条能覆盖96条
    routes_per_flight = 2  # 每条航线覆盖2条原始航路

    # 将原始航路分成若干组
    random.seed(42)
    shuffled = original_rids.copy()
    random.shuffle(shuffled)

    # 确保所有航路都被分配
    for i in range(0, len(shuffled), routes_per_flight):
        if flight_id > 50:
            break

        group = shuffled[i:i+routes_per_flight]
        if not group:
            continue

        # 构建航线航路点：按顺序串联组内的航路
        waypoints = []
        covered_rids = set()

        for rid in group:
            if rid in covered_rids:
                continue

            # 获取航路的航路点
            points = route_points[rid]

            # 如果waypoints为空，直接添加
            if not waypoints:
                waypoints.extend([{'坐标': [p['coord'][0], p['coord'][1]], '高度': p['height']} for p in points])
            else:
                # 检查是否需要反向添加
                last_wp = waypoints[-1]['坐标']
                first_pt = points[0]['coord']
                last_pt = points[-1]['coord']

                dist_to_first = ((last_wp[0]-first_pt[0])**2 + (last_wp[1]-first_pt[1])**2)**0.5
                dist_to_last = ((last_wp[0]-last_pt[0])**2 + (last_wp[1]-last_pt[1])**2)**0.5

                if dist_to_first < dist_to_last * 0.1:  # 基本重合
                    # 正向添加
                    for p in points[1:]:
                        waypoints.append({'坐标': [p['coord'][0], p['coord'][1]], '高度': p['height']})
                else:
                    # 反向添加
                    for p in reversed(points[1:]):
                        waypoints.append({'坐标': [p['coord'][0], p['coord'][1]], '高度': p['height']})

            covered_rids.add(rid)

        # 生成航线
        flight_type = flight_types[flight_id % len(flight_types)]
        priority = priorities[flight_id % len(priorities)]

        # 计算平均高度
        avg_height = sum(wp['高度'] for wp in waypoints) // len(waypoints) if waypoints else 70

        flight = {
            "航线ID": f"FL{flight_id:03d}",
            "航线名称": f"{flight_type}{flight_id}号",
            "业务类型": flight_type,
            "航路级别": priority,
            "飞行高度(m)": avg_height,
            "覆盖航路": list(covered_rids),
            "航路点": waypoints
        }

        all_flights.append(flight)
        flight_id += 1

    if flight_id > 50:
        break

print(f"\n生成航线: {len(all_flights)}条")

# 统计覆盖
all_covered = set()
for f in all_flights:
    all_covered.update(f['覆盖航路'])

original_covered = [r for r in all_covered if not r.startswith('LK')]
print(f"覆盖原始航路: {len(original_covered)}/{len(original_routes)}")

# 保存
output = {"航线库": {"航线数据": all_flights}}
with open('fixed_routes_library.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n已保存到 fixed_routes_library.json")
