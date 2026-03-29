# -*- coding: utf-8 -*-
"""
航路连通性修复脚本 - 简单贪心算法
1. 先分析当前连通分量
2. 对每个分量，找连接度为1的端点
3. 连接最近的孤立端点
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

# 计算两点之间的距离（米）
def haversine_distance(p1, p2):
    R = 6371000
    phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
    dphi = math.radians(p2[1] - p1[1])
    dlambda = math.radians(p2[0] - p1[0])
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 提取所有航路的端点
route_endpoints = []
for route in routes:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        route_endpoints.append({
            'route_id': route['航路编号'],
            'route_type': route['航路类型'],
            'start': coords[0],
            'end': coords[-1]
        })

print(f"解析航路数量: {len(route_endpoints)}")

# 收集所有端点
def round_pt(pt):
    return (round(pt[0], 4), round(pt[1], 4))

endpoint_map = {}  # (lon, lat) -> index
endpoints_list = []  # index -> {point, routes, degree}

for ep in route_endpoints:
    for key in [ep['start'], ep['end']]:
        rp = round_pt(key)
        if rp not in endpoint_map:
            endpoint_map[rp] = len(endpoints_list)
            endpoints_list.append({
                'point': key,
                'routes': [ep['route_id']],
                'degree': 0
            })
        else:
            idx = endpoint_map[rp]
            if ep['route_id'] not in endpoints_list[idx]['routes']:
                endpoints_list[idx]['routes'].append(ep['route_id'])

print(f"唯一端点数量: {len(endpoints_list)}")

# 计算每个端点的度数（连接的航路数）
for ep in endpoints_list:
    ep['degree'] = len(ep['routes'])

# 统计度数分布
degree_count = defaultdict(int)
for ep in endpoints_list:
    degree_count[ep['degree']] += 1

print(f"端点度数分布: {dict(degree_count)}")

# 并查集
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
    
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px != py:
            self.parent[px] = py
            return True
        return False
    
    def connected(self, x, y):
        return self.find(x) == self.find(y)

# 构建图
uf = UnionFind(len(endpoints_list))

# 同一条航路的两个端点已连通
for ep in route_endpoints:
    idx_start = endpoint_map.get(round_pt(ep['start']))
    idx_end = endpoint_map.get(round_pt(ep['end']))
    if idx_start is not None and idx_end is not None:
        uf.union(idx_start, idx_end)

# 统计初始连通分量
def get_components():
    comps = defaultdict(list)
    for i in range(len(endpoints_list)):
        comps[uf.find(i)].append(i)
    return comps

comps = get_components()
print(f"\n初始连通分量数: {len(comps)}")
for i, (root, indices) in enumerate(sorted(comps.items(), key=lambda x: -len(x[1]))):
    print(f"  分量{i+1}: {len(indices)}个端点, {len(set(r for i in indices for r in endpoints_list[i]['routes']))}条航路")

# 贪心连接算法
new_links = []
link_counter = 1

def create_link_czml(route_id, pos1, pos2, alt=70):
    cartographic = [
        [pos1[0], pos1[1]],
        pos1[1],
        float(alt),
        [pos2[0], pos2[1]],
        pos2[1],
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

# 迭代连接直到完全连通
max_iterations = 100
iteration = 0

while len(get_components()) > 1 and iteration < max_iterations:
    iteration += 1
    comps = get_components()
    comp_list = list(comps.values())
    
    if len(comp_list) == 1:
        break
    
    # 找最近的跨分量端点对
    best_dist = float('inf')
    best_pair = None
    
    for i in range(len(comp_list)):
        for j in range(i + 1, len(comp_list)):
            for idx1 in comp_list[i]:
                for idx2 in comp_list[j]:
                    dist = haversine_distance(endpoints_list[idx1]['point'], endpoints_list[idx2]['point'])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (idx1, idx2)
    
    if best_pair:
        idx1, idx2 = best_pair
        pt1 = endpoints_list[idx1]['point']
        pt2 = endpoints_list[idx2]['point']
        
        # 创建连接
        route_id = f"LK{link_counter:04d}"
        link_counter += 1
        
        new_links.append({
            "航路编号": route_id,
            "航路名称": "连接线",
            "航路类型": "LINK",
            "航路级别": "连接",
            "半宽(m)": 30,
            "半高(m)": 20,
            "CZML": create_link_czml(route_id, pt1, pt2),
            "_distance": round(best_dist, 1)
        })
        
        # 合并分量
        uf.union(idx1, idx2)
        
        print(f"迭代{iteration}: 连接 ({pt1[0]:.4f},{pt1[1]:.4f}) <-> ({pt2[0]:.4f},{pt2[1]:.4f}), 距离{best_dist:.0f}m")

print(f"\n生成连接线: {len(new_links)}条")

# 合并数据
all_routes = routes + new_links

# 保存（先保存再打印）
output_file = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_routes, f, ensure_ascii=False, indent=2)

js_content = 'const routeData = ' + json.dumps(all_routes, ensure_ascii=False) + ';'
output_js = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"\n已保存到: {output_file}")
print(f"总航路: {len(all_routes)} (原始 {len(routes)} + 连接 {len(new_links)})")
print("\n完成!")
