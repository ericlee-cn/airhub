"""
生成固定航线：航路作为公共通道，可被多条航线复用
- 航线 = 多个航路点的串联
- II级航路承接更多航线（繁忙）
- I级航路承接较少航线（主干）
"""
import json
import random
from collections import defaultdict, Counter

# 加载完整航路数据
with open('航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    all_routes = json.load(f)

original_routes = [r for r in all_routes if r.get('航路类型') != 'LINK']
print(f"原始航路: {len(original_routes)}条")

# 按航路类型统计
type_count = Counter(r.get('航路类型', 'A') for r in original_routes)
print(f"航路类型分布: {dict(type_count)}")

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
route_data = {}  # 航路ID -> 航路点列表
route_ends = {}  # 航路ID -> 起点终点
route_type = {}  # 航路ID -> 类型

for route in original_routes:
    rid = route['航路编号']
    rtype = route.get('航路类型', 'A')
    points = parse_positions(route['CZML'])
    route_data[rid] = points
    route_ends[rid] = {'start': (points[0]['lon'], points[0]['lat']), 'end': (points[-1]['lon'], points[-1]['lat'])}
    route_type[rid] = rtype

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

def build_flight_route(rids):
    """构建航线航路点（严格使用航路的原始航路点）"""
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

# 航路覆盖率统计
route_coverage = defaultdict(int)  # 航路ID -> 被航线使用次数

# 生成50条航线
random.seed(42)
all_rids = list(route_data.keys())

# 航线配置：航路级别 -> 每条航线包含的航路数
# A/B类 -> I级(主干)，C/D类 -> II级(繁忙支线)
type_to_level = {'A': 'Ⅰ', 'B': 'Ⅰ', 'C': 'Ⅱ', 'D': 'Ⅱ'}

flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ', 'Ⅲ', 'Ⅲ']

all_flights = []
flight_id = 1

# 策略：每条航线由2-4条航路串联
# II级航路(C/D类)更容易被选中，每条航线至少包含1条II级
for i in range(50):
    # 确保每条航线至少包含一条II级航路
    candidates = [rid for rid in all_rids if route_type[rid] in ['C', 'D']]
    if not candidates:
        candidates = all_rids
    
    start_rid = random.choice(candidates)
    
    # 构建航线：起始航路 + 可连接的航路
    rids = [start_rid]
    current_rid = start_rid
    
    # 尝试扩展2-3条航路，优先选择II级
    for _ in range(random.randint(2, 3)):
        connected = find_connected(current_rid)
        # 优先选II级
        level_2_candidates = [rid for rid in connected if rid not in rids and route_type[rid] in ['C', 'D']]
        if level_2_candidates:
            next_rid = random.choice(level_2_candidates)
        else:
            level_1_candidates = [rid for rid in connected if rid not in rids]
            if level_1_candidates:
                next_rid = random.choice(level_1_candidates)
            else:
                next_rid = None
        
        if next_rid:
            rids.append(next_rid)
            current_rid = next_rid
    
    # 构建航路点
    waypoints = build_flight_route(rids)
    avg_height = int(sum(wp['高度'] for wp in waypoints) / len(waypoints)) if waypoints else 70
    
    # 确定航线级别：包含II级航路则为II级
    has_type_2 = any(route_type[rid] in ['C', 'D'] for rid in rids)
    level = 'Ⅱ' if has_type_2 else 'Ⅰ'
    
    flight = {
        "航线ID": f"FL{flight_id:03d}",
        "航线名称": f"{flight_types[flight_id % len(flight_types)]}{flight_id}号",
        "业务类型": flight_types[flight_id % len(flight_types)],
        "航路级别": level,
        "飞行高度(m)": avg_height,
        "覆盖航路": rids,
        "航路点": waypoints
    }
    
    all_flights.append(flight)
    
    # 统计覆盖率
    for rid in rids:
        route_coverage[rid] += 1
    
    flight_id += 1

print(f"\n生成航线: {len(all_flights)}条")

# 统计覆盖率
level_1_routes = [rid for rid in all_rids if route_type[rid] in ['A', 'B']]
level_2_routes = [rid for rid in all_rids if route_type[rid] in ['C', 'D']]

level_1_coverage = sum(route_coverage[rid] for rid in level_1_routes)
level_2_coverage = sum(route_coverage[rid] for rid in level_2_routes)

print(f"\nI级航路(A/B类): {len(level_1_routes)}条, 总覆盖: {level_1_coverage}次, 平均: {level_1_coverage/len(level_1_routes):.1f}次/条")
print(f"II级航路(C/D类): {len(level_2_routes)}条, 总覆盖: {level_2_coverage}次, 平均: {level_2_coverage/len(level_2_routes):.1f}次/条")

# 统计航线长度分布
counts = [len(f['覆盖航路']) for f in all_flights]
print(f"\n航线覆盖航路数: {Counter(counts)}")

# 保存
output = {"航线库": {"航线数据": all_flights}}
with open('fixed_routes_library.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n已保存到 fixed_routes_library.json")
