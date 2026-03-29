"""
生成符合网页格式的固定航线数据
航线格式：包含航路点数组，每个航路点有坐标和名称
"""
import json
import math
import random

# 加载航路数据
with open('航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    route_data = json.load(f)

# 提取原始航路（不含连接线）
original_routes = [r for r in route_data if r.get('航路类型') != 'LINK']

def parse_coords(route):
    """解析CZML中的坐标，返回[(lon, lat, height), ...]"""
    czml = json.loads(route['CZML'])
    positions = czml['corridor']['positions']['cartographicDegrees']
    # 格式: [[lon, lat], lat_repeat, height, [lon, lat], lat_repeat, height, ...]
    coords = []
    i = 0
    while i < len(positions):
        coord = positions[i]  # [lon, lat]
        height = positions[i+2] if i+2 < len(positions) else 70.0
        coords.append((float(coord[0]), float(coord[1]), float(height)))
        i += 3
    return coords

def get_route_waypoints(route):
    """获取航路的航路点，保持航路的实际高度"""
    coords = parse_coords(route)
    waypoints = []
    for i, (lon, lat, height) in enumerate(coords):
        waypoint = {
            '名称': f'WP{i+1}',
            '坐标': [lon, lat],  # [lon, lat]
            '高度': height  # 保持航路的实际高度
        }
        waypoints.append(waypoint)
    return waypoints

# 提取所有航路的航路点
all_waypoints = {}
for route in original_routes:
    waypoints = get_route_waypoints(route)
    for wp in waypoints:
        key = f"{wp['坐标'][0]:.4f},{wp['坐标'][1]:.4f}"
        if key not in all_waypoints:
            all_waypoints[key] = wp

print(f"总航路数: {len(original_routes)}")
print(f"唯一航路点数: {len(all_waypoints)}")

# 生成50条航线，覆盖所有96条原始航路
routes_lib = []
flight_types = ['货物运输', '空中巡逻', '应急救援', '航拍作业', '训练飞行', '医疗转运', '地形勘察', '物流配送']
priorities = ['Ⅰ', 'Ⅰ', 'Ⅰ', 'Ⅱ', 'Ⅱ', 'Ⅲ', 'Ⅲ', 'Ⅲ']  # Ⅰ级主干、Ⅱ级支线、Ⅲ级辅助

# 按航路类型分组，确保每类都有覆盖
type_routes = {}
for route in original_routes:
    rtype = route.get('航路类型', 'A')
    if rtype not in type_routes:
        type_routes[rtype] = []
    type_routes[rtype].append(route)

# 统计
print(f"航路类型分布: {[(k, len(v)) for k, v in type_routes.items()]}")

# 目标：50条航线
target_count = 50
routes_per_type = max(1, target_count // len(type_routes))

flight_id = 1
for rtype, routes in type_routes.items():
    for route in routes[:routes_per_type]:
        if flight_id > target_count:
            break

        waypoints = get_route_waypoints(route)
        flight_type = random.choice(flight_types)
        priority = random.choice(priorities)
        # 使用航路第一个点的高度
        altitude = int(waypoints[0]['高度']) if waypoints else 70

        flight = {
            "航线ID": f"FL{flight_id:03d}",
            "航线名称": f"{flight_type}{flight_id}号",
            "业务类型": flight_type,
            "航路级别": priority,
            "飞行高度(m)": altitude,
            "航路点": waypoints
        }
        routes_lib.append(flight)
        flight_id += 1

    if flight_id > target_count:
        break

print(f"生成航线数: {len(routes_lib)}")

# 保存
output = {"航线库": {"航线数据": routes_lib}}
with open('fixed_routes_library.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"已保存到 fixed_routes_library.json")
