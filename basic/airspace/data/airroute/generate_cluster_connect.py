# -*- coding: utf-8 -*-
"""
航路连通性修复脚本 v3
使用空间聚类方法确保所有航路端点都被连接
"""

import json
import math
from collections import defaultdict

# 读取原始航路数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f"原始航路数量: {len(routes)}")

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
                        alt = 70.0
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
            print(f"解析错误: {e}")
            break
    
    return coords

# 计算两点之间的距离（米）
def haversine_distance(p1, p2):
    R = 6371000
    phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
    dphi = math.radians(p2[1] - p1[1])
    dlambda = math.radians(p2[0] - p1[0])
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 提取所有端点
endpoints = []
for route in routes:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        endpoints.append({
            'route_id': route['航路编号'],
            'position': coords[0],  # 起点
            'type': 'start',
            'route_type': route['航路类型']
        })
        endpoints.append({
            'route_id': route['航路编号'],
            'position': coords[-1],  # 终点
            'type': 'end',
            'route_type': route['航路类型']
        })

print(f"提取端点数量: {len(endpoints)}")

# 提取所有唯一端点位置
unique_positions = []
position_to_endpoints = defaultdict(list)

for ep in endpoints:
    pos = ep['position']
    # 查找是否已存在相近位置
    found = False
    for i, existing in enumerate(unique_positions):
        dist = haversine_distance(pos, existing)
        if dist < 10:  # 10米以内认为是同一位置
            position_to_endpoints[i].append(ep)
            found = True
            break
    if not found:
        idx = len(unique_positions)
        unique_positions.append(pos)
        position_to_endpoints[idx].append(ep)

print(f"唯一位置数量: {len(unique_positions)}")

# 统计有多少个孤立位置（没有其他航路端点共享）
isolated_positions = [i for i, eps in position_to_endpoints.items() if len(eps) == 1]
print(f"孤立端点数量: {len(isolated_positions)}")

# 使用 DBSCAN 聚类算法
def dbscan_clustering(points, eps, min_samples):
    """简单的DBSCAN实现"""
    n = len(points)
    labels = [-1] * n  # -1 表示噪声
    cluster_id = 0
    
    def region_query(idx):
        """找到所有在eps范围内的点"""
        neighbors = []
        for i in range(n):
            if haversine_distance(points[idx], points[i]) <= eps:
                neighbors.append(i)
        return neighbors
    
    for i in range(n):
        if labels[i] != -1:
            continue
        
        neighbors = region_query(i)
        
        if len(neighbors) < min_samples:
            labels[i] = -1  # 噪声点
        else:
            # 扩展聚类
            labels[i] = cluster_id
            seed_set = set(neighbors) - {i}
            
            while seed_set:
                j = seed_set.pop()
                if labels[j] == -1:
                    labels[j] = cluster_id
                    j_neighbors = region_query(j)
                    if len(j_neighbors) >= min_samples:
                        seed_set.update(set(j_neighbors) - set(range(n)))
                elif labels[j] == -1:
                    labels[j] = cluster_id
    
    return labels, cluster_id + 1

# 对端点位置进行聚类
print("\n执行DBSCAN聚类...")
eps_meters = 2000  # 2公里范围内视为同一聚类
labels, num_clusters = dbscan_clustering(unique_positions, eps_meters, 1)

print(f"聚类数量: {num_clusters}")

# 统计每个聚类的大小
cluster_sizes = defaultdict(int)
for label in labels:
    cluster_sizes[label] += 1

isolated_clusters = [c for c, size in cluster_sizes.items() if size == 1]
print(f"孤立聚类数量（只有一个端点）: {len(isolated_clusters)}")

# 策略：对于孤立端点，找到最近的端点进行连接
# 构建所有端点对之间的距离
print("\n计算端点连接...")

# 按聚类分组
cluster_endpoints = defaultdict(list)
for i, label in enumerate(labels):
    for ep in position_to_endpoints[i]:
        cluster_endpoints[label].append((i, ep))

# 生成连接线
def generate_route_id(index):
    return f"LK{index:04d}"

def create_czml(route_id, pos1, pos2, alt=70):
    """创建CZML格式的连接线"""
    cartographic = [
        [pos1[0], pos1[1]],
        float(alt),
        [pos2[0], pos2[1]],
        float(alt)
    ]
    
    return json.dumps({
        "id": route_id,
        "name": route_id,
        "corridor": {
            "positions": {"cartographicDegrees": cartographic},
            "width": 60.0,
            "material": {"solidColor": {"color": {"rgba": [255, 200, 0, 180]}}},
            "extrudedHeight": 20.0,
            "height": 0
        }
    }, ensure_ascii=False)

new_routes = []
link_counter = 0

# 第一步：在同一聚类内的端点之间建立连接
print("步骤1: 连接同一聚类内的端点...")
for cluster_id, eps_in_cluster in cluster_endpoints.items():
    if len(eps_in_cluster) < 2:
        continue
    
    # 对聚类内的端点进行全连接（但每条航路只连一次）
    route_pairs = set()
    for i, (pos_idx1, ep1) in enumerate(eps_in_cluster):
        for j, (pos_idx2, ep2) in enumerate(eps_in_cluster):
            if i >= j:
                continue
            if ep1['route_id'] == ep2['route_id']:
                continue
            
            pair = tuple(sorted([ep1['route_id'], ep2['route_id']]))
            if pair in route_pairs:
                continue
            route_pairs.add(pair)
            
            link_counter += 1
            route_id = generate_route_id(link_counter)
            
            pos1, pos2 = unique_positions[pos_idx1], unique_positions[pos_idx2]
            dist = haversine_distance(pos1, pos2)
            
            new_routes.append({
                "航路编号": route_id,
                "航路名称": "连接线",
                "航路类型": "LINK",
                "航路级别": "连接",
                "半宽(m)": 30,
                "半高(m)": 20,
                "CZML": create_czml(route_id, pos1, pos2),
                "_source": f"{ep1['route_id']}({ep1['type']}) -> {ep2['route_id']}({ep2['type']})",
                "_distance": round(dist, 1)
            })

print(f"聚类内连接: {len(new_routes)}条")

# 第二步：对于仍然孤立的航路（未被连接的），找最近的端点连接
# 检查哪些航路还没有被连接
all_route_ids = set(ep['route_id'] for ep in endpoints)
connected_routes = set()
for route in new_routes:
    src = route['_source']
    r1 = src.split('->')[0].split('(')[0].strip()
    r2 = src.split('->')[1].split('(')[0].strip()
    connected_routes.add(r1)
    connected_routes.add(r2)

unconnected = all_route_ids - connected_routes
print(f"\n步骤2: 未连接的航路: {len(unconnected)}")

# 为未连接的航路找到最近的连接点
for route_id in unconnected:
    # 找到这条航路的端点
    my_eps = [ep for ep in endpoints if ep['route_id'] == route_id]
    if not my_eps:
        continue
    
    my_pos1 = my_eps[0]['position']
    my_pos2 = my_eps[1]['position'] if len(my_eps) > 1 else my_pos1
    
    # 找最近的已连接航路
    best_dist = float('inf')
    best_target = None
    best_target_ep = None
    best_pos = None
    
    for other_ep in endpoints:
        if other_ep['route_id'] == route_id:
            continue
        if other_ep['route_id'] not in connected_routes:
            continue
        
        for my_pos in [my_pos1, my_pos2]:
            dist = haversine_distance(my_pos, other_ep['position'])
            if dist < best_dist:
                best_dist = dist
                best_target = other_ep['route_id']
                best_target_ep = other_ep
                best_pos = my_pos
    
    if best_target:
        link_counter += 1
        route_id_new = generate_route_id(link_counter)
        
        new_routes.append({
            "航路编号": route_id_new,
            "航路名称": "连接线",
            "航路类型": "LINK",
            "航路级别": "连接",
            "半宽(m)": 30,
            "半高(m)": 20,
            "CZML": create_czml(route_id_new, best_pos, best_target_ep['position']),
            "_source": f"{route_id} -> {best_target}",
            "_distance": round(best_dist, 1)
        })
        connected_routes.add(route_id)

# 第三步：确保图连通 - 使用并查集验证
print("\n步骤3: 验证连通性...")

class UnionFind:
    def __init__(self):
        self.parent = {}
    
    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px != py:
            self.parent[px] = py
            return True
        return False

uf = UnionFind()

# 原始航路内部连通
for ep in endpoints:
    uf.find(ep['route_id'])  # 初始化

# 原始航路的起点和终点是连通的
for route in routes:
    # 每条航路本身是连通的
    pass

# 连接线连接的两端
for route in new_routes:
    src = route['_source']
    try:
        r1 = src.split('->')[0].split('(')[0].strip()
        r2 = src.split('->')[1].split('(')[0].strip()
        uf.union(r1, r2)
    except:
        pass

# 检查连通分量
components = defaultdict(set)
for route_id in all_route_ids:
    comp = uf.find(route_id)
    components[comp].add(route_id)

print(f"连通分量数量: {len(components)}")

# 如果还有多个分量，添加更多连接
if len(components) > 1:
    print("\n添加额外连接以打通所有分量...")
    comp_list = list(components.keys())
    
    for i in range(len(comp_list) - 1):
        comp1_routes = list(components[comp_list[i]])
        comp2_routes = list(components[comp_list[i + 1]])
        
        # 找两个分量之间最近的一对端点
        best_dist = float('inf')
        best_pair = None
        
        for ep1 in endpoints:
            if ep1['route_id'] not in comp1_routes:
                continue
            for ep2 in endpoints:
                if ep2['route_id'] not in comp2_routes:
                    continue
                dist = haversine_distance(ep1['position'], ep2['position'])
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (ep1, ep2)
        
        if best_pair:
            ep1, ep2 = best_pair
            link_counter += 1
            route_id_new = generate_route_id(link_counter)
            
            new_routes.append({
                "航路编号": route_id_new,
                "航路名称": "连接线",
                "航路类型": "LINK",
                "航路级别": "连接",
                "半宽(m)": 30,
                "半高(m)": 20,
                "CZML": create_czml(route_id_new, ep1['position'], ep2['position']),
                "_source": f"{ep1['route_id']} -> {ep2['route_id']}",
                "_distance": round(best_dist, 1)
            })
            
            # 合并这两个分量
            uf.union(ep1['route_id'], ep2['route_id'])

# 最终验证
components = defaultdict(set)
for route_id in all_route_ids:
    comp = uf.find(route_id)
    components[comp].add(route_id)

print(f"最终连通分量数量: {len(components)}")

# 合并所有数据
all_routes = routes + new_routes

# 保存
output_file = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_聚类连通.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_routes, f, ensure_ascii=False, indent=2)

# 保存JS版本
js_content = 'const routeData = ' + json.dumps(all_routes, ensure_ascii=False) + ';'
output_js = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_聚类连通.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"\n已保存到: {output_file}")
print(f"总航路: {len(all_routes)} (原始 {len(routes)} + 连接 {len(new_routes)})")

# 统计
link_routes = [r for r in all_routes if r.get('航路类型') == 'LINK']
print(f"\n连接线统计:")
for route in link_routes[:10]:
    print(f"  {route['航路编号']}: {route.get('_distance', '?')}米")
if len(link_routes) > 10:
    print(f"  ... 还有 {len(link_routes) - 10} 条")

print("\n完成!")
