import json
import math

with open('航线信息表_含CZML_全连接.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 分析航路端点分布
def parse_positions(czml_str):
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    coords = []
    i = 0
    while i < len(positions):
        try:
            if isinstance(positions[i], list):
                lon, lat = float(positions[i][0]), float(positions[i][1])
                i += 1
                if i < len(positions) and isinstance(positions[i], (int, float)):
                    alt = float(positions[i])
                else:
                    alt = 70.0
            else:
                if i + 2 < len(positions):
                    lon = float(positions[i]) if isinstance(positions[i], (int, float)) else 70.0
                    lat = float(positions[i+1]) if isinstance(positions[i+1], (int, float)) else 0.0
                    alt = float(positions[i+2]) if isinstance(positions[i+2], (int, float)) else 70.0
                else:
                    break
                i += 3
            coords.append((lon, lat, alt))
        except:
            break
    return coords

# 按区域分组（根据坐标范围）
regions = {
    '德清东部': [],  # 经度 > 120.0
    '德清中部': [],  # 119.9 < 经度 <= 120.0
    '德清西部': [],  # 经度 <= 119.9
}

all_endpoints = []

for route in data:
    if route['航路类型'] == 'LINK':
        continue
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        start_lon = coords[0][0]
        if start_lon > 120.0:
            region = '德清东部'
        elif start_lon > 119.9:
            region = '德清中部'
        else:
            region = '德清西部'
        regions[region].append(route['航路编号'])

print("=== 航路区域分布 ===")
for region, routes in regions.items():
    print(f"{region}: {len(routes)}条航路")

# 找出跨区域连接
print("\n=== 跨区域连接 ===")
link_routes = [r for r in data if r['航路类型'] == 'LINK']
cross_region = 0
for r in link_routes:
    src = r['_source']
    parts = src.split('-')  # 分割 "AA1001(start) - BA1001(start)"
    if len(parts) >= 2:
        r1 = parts[0].split('(')[0].strip()
        r2 = parts[1].split('(')[0].strip()
        region1 = region2 = None
        for reg, routes in regions.items():
            if r1 in routes:
                region1 = reg
            if r2 in routes:
                region2 = reg
        if region1 and region2 and region1 != region2:
            cross_region += 1
            print(f"  {r['航路编号']}: {region1} <-> {region2} ({r['_distance']}米)")

print(f"\n跨区域连接: {cross_region}条")

# 找不同区域端点之间的连接
def haversine(p1, p2):
    R = 6371000
    phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
    dphi = math.radians(p2[1] - p1[1])
    dlambda = math.radians(p2[0] - p1[0])
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 收集各区域的端点
region_endpoints = {k: [] for k in regions.keys()}
for route in data:
    if route['航路类型'] == 'LINK':
        continue
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        start_lon = coords[0][0]
        if start_lon > 120.0:
            region = '德清东部'
        elif start_lon > 119.9:
            region = '德清中部'
        else:
            region = '德清西部'
        region_endpoints[region].append({
            'route': route['航路编号'],
            'start': coords[0],
            'end': coords[-1]
        })

# 找跨区域可连接对
print("\n=== 跨区域可连接对（距离<500m）===")
connections = []
for i, (r1, eps1) in enumerate(region_endpoints.items()):
    for r2, eps2 in list(region_endpoints.items())[i+1:]:
        for ep1 in eps1:
            for ep2 in eps2:
                d1 = haversine(ep1['end'], ep2['start'])
                d2 = haversine(ep1['start'], ep2['end'])
                d = min(d1, d2)
                if d < 500:
                    connections.append({
                        'region1': r1, 'region2': r2,
                        'route1': ep1['route'], 'route2': ep2['route'],
                        'distance': d
                    })

connections.sort(key=lambda x: x['distance'])
print(f"发现 {len(connections)} 对可连接")
for c in connections[:20]:
    print(f"  {c['region1']}.{c['route1']} ↔ {c['region2']}.{c['route2']}: {c['distance']:.1f}米")
