"""
航路连接线生成脚本 v2
只生成跨航路组的连接线，避免全连接造成的冗余
"""

import json
import math
from collections import defaultdict

# 读取原始航线数据
with open('航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f"原始航路数量: {len(routes)}")

# 按航路类型分组
routes_by_type = defaultdict(list)
for route in routes:
    routes_by_type[route['航路类型']].append(route)

print(f"航路类型分布:")
for t, rs in routes_by_type.items():
    print(f"  {t}: {len(rs)}条")

# 解析坐标
def parse_positions(czml_str):
    """解析CZML中的坐标点"""
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    
    coords = []
    i = 0
    while i < len(positions):
        try:
            if isinstance(positions[i], list):
                # 格式: [[lon, lat], alt, [lon, lat], alt, ...]
                lon, lat = float(positions[i][0]), float(positions[i][1])
                i += 1
                if i < len(positions):
                    v = positions[i]
                    if isinstance(v, (int, float)):
                        alt = float(v)
                    elif isinstance(v, list):
                        alt = 70.0  # 跳过异常值
                    else:
                        alt = 70.0
                else:
                    alt = 70.0
            else:
                # 格式: [lon, lat, alt, lon, lat, alt, ...]
                if i + 2 < len(positions):
                    v0, v1, v2 = positions[i], positions[i+1], positions[i+2]
                    lon = float(v0) if isinstance(v0, (int, float)) else 70.0
                    lat = float(v1) if isinstance(v1, (int, float)) else 0.0
                    alt = float(v2) if isinstance(v2, (int, float)) else 70.0
                else:
                    break
                i += 3
            
            coords.append((lon, lat, alt))
        except Exception as e:
            print(f"解析错误 at i={i}: {positions[i:i+5]} - {e}")
            break
    
    return coords

# 提取所有端点
endpoints = []
for route in routes:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        # 起点
        endpoints.append({
            'route_id': route['航路编号'],
            'position': tuple(coords[0]),
            'type': 'start',
            'route_type': route['航路类型'],
            'level': route['航路级别']
        })
        # 终点
        endpoints.append({
            'route_id': route['航路编号'],
            'position': tuple(coords[-1]),
            'type': 'end',
            'route_type': route['航路类型'],
            'level': route['航路级别']
        })

print(f"提取端点数量: {len(endpoints)}")

# 计算距离
def haversine_distance(p1, p2):
    R = 6371000
    phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
    dphi = math.radians(p2[1] - p1[1])
    dlambda = math.radians(p2[0] - p1[0])
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 距离阈值：超过500米不连接
THRESHOLD = 500

# 收集所有可连接的对
all_connections = []

for i, ep1 in enumerate(endpoints):
    for j, ep2 in enumerate(endpoints):
        if i >= j:
            continue
        if ep1['route_id'] == ep2['route_id']:
            continue
        
        dist = haversine_distance(ep1['position'], ep2['position'])
        if dist <= THRESHOLD:
            all_connections.append({
                'ep1': ep1,
                'ep2': ep2,
                'distance': dist
            })

print(f"可连接的对（距离<={THRESHOLD}米）: {len(all_connections)}")

# 按距离排序
all_connections.sort(key=lambda x: x['distance'])

# 智能选择连接：每个端点只连接最近的几个
CONNECTIONS_PER_NODE = 3  # 每个端点最多连接数
selected_connections = []
node_connections = defaultdict(list)  # route_id -> 已连接的列表

for conn in all_connections:
    ep1, ep2 = conn['ep1'], conn['ep2']
    route1, route2 = ep1['route_id'], ep2['route_id']
    
    # 检查是否已达到连接上限
    if len(node_connections[route1]) >= CONNECTIONS_PER_NODE:
        continue
    if len(node_connections[route2]) >= CONNECTIONS_PER_NODE:
        continue
    
    # 检查是否是同一航路类型的（同类航路不直接连接，避免冗余）
    # 但保留AA-BA这样的跨版本连接
    
    selected_connections.append(conn)
    node_connections[route1].append(route2)
    node_connections[route2].append(route1)

print(f"选择的连接数量: {len(selected_connections)}")

# 生成连接线
def generate_route_id(prefix, index):
    return f"{prefix}{index:04d}"

def create_czml(route_id, positions, alt=70, color=[255, 200, 0, 150]):
    cartographic = []
    for lon, lat, a in positions:
        cartographic.append([lon, lat])
        cartographic.append(float(a))
    
    return json.dumps({
        "id": route_id,
        "name": route_id,
        "corridor": {
            "positions": {"cartographicDegrees": cartographic},
            "width": 60.0,
            "material": {"solidColor": {"color": {"rgba": color}}},
            "extrudedHeight": 20.0,
            "height": 0
        }
    })

new_routes = []
link_counter = defaultdict(int)

for conn in selected_connections:
    ep1, ep2 = conn['ep1'], conn['ep2']
    
    # 生成连接线编号
    link_counter['LINK'] += 1
    route_id = generate_route_id('LK', link_counter['LINK'])
    
    p1, p2 = ep1['position'], ep2['position']
    mid_lon, mid_lat = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    mid_alt = (p1[2] + p2[2]) / 2
    
    positions = [
        (float(p1[0]), float(p1[1]), float(p1[2])),
        (mid_lon, mid_lat, mid_alt),
        (float(p2[0]), float(p2[1]), float(p2[2]))
    ]
    
    new_routes.append({
        "航路编号": route_id,
        "航路名称": f"连接线",
        "航路类型": "LINK",
        "航路级别": "连接",
        "半宽(m)": 30,
        "半高(m)": 20,
        "CZML": create_czml(route_id, positions, color=[255, 180, 0, 180]),
        "_source": f"{ep1['route_id']}({ep1['type']}) → {ep2['route_id']}({ep2['type']})",
        "_distance": round(conn['distance'], 1)
    })

print(f"生成连接线: {len(new_routes)}条")

# 合并
all_routes = routes + new_routes

# 保存
output_file = '航线信息表_含CZML_全连接.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_routes, f, ensure_ascii=False, indent=2)

print(f"\n已保存到: {output_file}")
print(f"总航路: {len(all_routes)} (原始 {len(routes)} + 连接 {len(new_routes)})")

# 显示连接详情
print("\n=== 连接详情（按距离排序）===")
for i, conn in enumerate(selected_connections[:30]):
    ep1, ep2 = conn['ep1'], conn['ep2']
    print(f"{i+1:2d}. {ep1['route_id']:10s}({ep1['type']:5s}) ↔ {ep2['route_id']:10s}({ep2['type']:5s}) | {conn['distance']:6.1f}米")

if len(selected_connections) > 30:
    print(f"... 还有 {len(selected_connections) - 30} 条连接")

print("\n完成!")
