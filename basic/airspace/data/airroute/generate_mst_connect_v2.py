# -*- coding: utf-8 -*-
"""
航路连通性修复脚本 v5
使用正确的最小生成树(MST)确保所有航路端点连通
"""

import json
import math
from collections import defaultdict

# 读取原始航路数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f"原始航路数量: {len(routes)}")

# 解析坐标 - 修复版本
def parse_positions(czml_str):
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    
    coords = []
    i = 0
    while i < len(positions):
        try:
            if isinstance(positions[i], list):
                # 嵌套格式: [[lon, lat], height, ...]
                lon = float(positions[i][0])
                lat = float(positions[i][1])
                coords.append((lon, lat))
                i += 1
                # 跳过height
                if i < len(positions) and not isinstance(positions[i], list):
                    i += 1
            else:
                # 扁平格式: [lon, lat, height, lon, lat, height, ...]
                lon = float(positions[i])
                lat = float(positions[i+1])
                coords.append((lon, lat))
                i += 3
        except:
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

# 收集所有端点（去重）
all_endpoints = []
endpoint_set = set()
for ep in route_endpoints:
    # 起点
    start_key = (round(ep['start'][0], 4), round(ep['start'][1], 4))
    if start_key not in endpoint_set:
        endpoint_set.add(start_key)
        all_endpoints.append({'point': ep['start'], 'routes': [ep['route_id']]})
    else:
        for e in all_endpoints:
            if e['point'] == ep['start']:
                e['routes'].append(ep['route_id'])
                break
    
    # 终点
    end_key = (round(ep['end'][0], 4), round(ep['end'][1], 4))
    if end_key not in endpoint_set:
        endpoint_set.add(end_key)
        all_endpoints.append({'point': ep['end'], 'routes': [ep['route_id']]})
    else:
        for e in all_endpoints:
            if e['point'] == ep['end']:
                e['routes'].append(ep['route_id'])
                break

print(f"唯一端点数量: {len(all_endpoints)}")

# 并查集 - 基于端点
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

# 初始化：同一条航路的两个端点已经连通
uf = UnionFind(len(all_endpoints))

# 建立端点到索引的映射
point_to_idx = {i: i for i, e in enumerate(all_endpoints)}

# 构建边：连接所有可能连通的端点
# 原则：如果两个端点属于同一条航路（共享起点/终点），则它们已连通
# 但如果两条航路共享端点，它们也应该连通

# 构建路由端点映射
route_to_endpoints = {}
for i, ep in enumerate(route_endpoints):
    route_to_endpoints[ep['route_id']] = {
        'start': ep['start'],
        'end': ep['end']
    }

# Kruskal最小生成树 - 基于端点
edges = []

for i, ep1 in enumerate(all_endpoints):
    for j, ep2 in enumerate(all_endpoints):
        if i >= j:
            continue
        
        # 获取连接这两个端点的航路
        routes1 = set(ep1['routes'])
        routes2 = set(ep2['routes'])
        
        # 如果有共同的航路，它们已经连通
        if routes1 & routes2:
            uf.union(i, j)
            continue
        
        # 计算距离
        dist = haversine_distance(ep1['point'], ep2['point'])
        
        # 只考虑近距离的边（小于3km）
        if dist < 3000:
            edges.append({
                'idx1': i,
                'idx2': j,
                'dist': dist,
                'routes1': list(routes1),
                'routes2': list(routes2)
            })

print(f"候选边数（<3km）: {len(edges)}")

# 按距离排序
edges.sort(key=lambda x: x['dist'])

# Kruskal算法
mst_edges = []
added_routes = set()

for edge in edges:
    idx1, idx2 = edge['idx1'], edge['idx2']
    if uf.find(idx1) != uf.find(idx2):
        uf.union(idx1, idx2)
        mst_edges.append(edge)
        # 记录添加的连接信息
        for r in edge['routes1']:
            added_routes.add(r)
        for r in edge['routes2']:
            added_routes.add(r)

print(f"MST边数: {len(mst_edges)}")

# 检查连通性
components = defaultdict(list)
for i in range(len(all_endpoints)):
    root = uf.find(i)
    components[root].append(i)

print(f"连通分量数: {len(components)}")

# 如果还有多个分量，添加更多边来连接它们
if len(components) > 1:
    print("仍有多个分量，添加更多连接...")
    
    # 重置并查集
    uf2 = UnionFind(len(all_endpoints))
    
    # 先加入MST边
    for edge in mst_edges:
        uf2.union(edge['idx1'], edge['idx2'])
    
    # 再处理剩余的边（按距离排序）
    extra_edges = 0
    for edge in edges:
        idx1, idx2 = edge['idx1'], edge['idx2']
        if uf2.find(idx1) != uf2.find(idx2):
            uf2.union(idx1, idx2)
            mst_edges.append(edge)
            extra_edges += 1
            if uf2.parent.count(uf2.find(0)) == len(all_endpoints):
                break
    
    print(f"添加额外边: {extra_edges}")
    
    # 再次检查连通性
    components2 = defaultdict(list)
    for i in range(len(all_endpoints)):
        root = uf2.find(i)
        components2[root].append(i)
    print(f"最终连通分量数: {len(components2)}")

# 生成连接线
link_counter = len([r for r in routes if r.get('航路类型') == 'LINK']) + 1

def create_link_czml(route_id, pos1, pos2, alt=70):
    """创建LINK航路的CZML"""
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

new_links = []
for edge in mst_edges:
    idx1, idx2 = edge['idx1'], edge['idx2']
    pt1 = all_endpoints[idx1]['point']
    pt2 = all_endpoints[idx2]['point']
    
    # 确保起点和终点不同
    if abs(pt1[0] - pt2[0]) < 0.0001 and abs(pt1[1] - pt2[1]) < 0.0001:
        continue
    
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
        "_distance": round(edge['dist'], 1),
        "_routes1": edge['routes1'],
        "_routes2": edge['routes2']
    })

print(f"\n生成连接线: {len(new_links)}条")

# 显示前10条连接
print("\n前10条连接:")
for r in new_links[:10]:
    pt1 = json.loads(r['CZML'])['corridor']['positions']['cartographicDegrees'][0]
    pt2 = json.loads(r['CZML'])['corridor']['positions']['cartographicDegrees'][2]
    print(f"  {r['航路编号']}: ({pt1[0]:.4f}, {pt1[1]:.4f}) -> ({pt2[0]:.4f}, {pt2[1]:.4f}), {r['_distance']}m")

# 合并数据
all_routes = routes + new_links

# 保存
output_file = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_routes, f, ensure_ascii=False, indent=2)

js_content = 'const routeData = ' + json.dumps(all_routes, ensure_ascii=False) + ';'
output_js = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"\n已保存到: {output_file}")
print(f"总航路: {len(all_routes)} (原始 {len(routes)} + 连接 {len(new_links)})")
print("\n完成!")
