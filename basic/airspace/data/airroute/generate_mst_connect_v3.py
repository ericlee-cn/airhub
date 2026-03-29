# -*- coding: utf-8 -*-
"""
航路连通性修复脚本 v6 - 修复版
使用正确的最小生成树(MST)确保所有航路端点连通
"""

import json
import math
from collections import defaultdict

# 读取原始航路数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f"原始航路数量: {len(routes)}")

# 解析坐标 - 正确的版本
def parse_positions(czml_str):
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']
    
    coords = []
    i = 0
    while i < len(positions):
        if isinstance(positions[i], list):
            # 格式: [[lon, lat], lat_repeat, height, ...]
            lon = float(positions[i][0])
            lat = float(positions[i][1])
            coords.append((lon, lat))
            i += 1  # 跳过 [lon, lat]
            # 跳过 lat_repeat 和 height
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

# 验证解析结果
print(f"示例: {route_endpoints[0]['route_id']} 起点={route_endpoints[0]['start']}, 终点={route_endpoints[0]['end']}")

# 收集所有端点（去重，使用4位小数精度）
def round_pt(pt):
    return (round(pt[0], 4), round(pt[1], 4))

endpoint_map = {}  # (lon, lat) -> index
endpoints_list = []  # index -> {point, routes}

for ep in route_endpoints:
    for key, ep_type in [(ep['start'], 'start'), (ep['end'], 'end')]:
        rp = round_pt(key)
        if rp not in endpoint_map:
            endpoint_map[rp] = len(endpoints_list)
            endpoints_list.append({
                'point': key,
                'routes': [ep['route_id']],
                'type': ep_type
            })
        else:
            idx = endpoint_map[rp]
            if ep['route_id'] not in endpoints_list[idx]['routes']:
                endpoints_list[idx]['routes'].append(ep['route_id'])

print(f"唯一端点数量: {len(endpoints_list)}")

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

# 构建边
edges = []
for i in range(len(endpoints_list)):
    for j in range(i + 1, len(endpoints_list)):
        # 获取连接这两个端点的航路
        routes1 = set(endpoints_list[i]['routes'])
        routes2 = set(endpoints_list[j]['routes'])
        
        # 如果有共同的航路，它们已经连通
        common = routes1 & routes2
        if common:
            continue
        
        # 计算距离
        dist = haversine_distance(endpoints_list[i]['point'], endpoints_list[j]['point'])
        
        # 只考虑近距离的边（小于5km）
        if dist < 5000:
            edges.append({
                'idx1': i,
                'idx2': j,
                'dist': dist
            })

print(f"候选边数（<5km）: {len(edges)}")

# 按距离排序
edges.sort(key=lambda x: x['dist'])

# Kruskal算法
uf = UnionFind(len(endpoints_list))
mst_edges = []

for edge in edges:
    idx1, idx2 = edge['idx1'], edge['idx2']
    if not uf.connected(idx1, idx2):
        uf.union(idx1, idx2)
        mst_edges.append(edge)

print(f"MST边数: {len(mst_edges)}")

# 检查连通性
components = defaultdict(int)
for i in range(len(endpoints_list)):
    root = uf.find(i)
    components[root] += 1

print(f"连通分量数: {len(components)}")

# 如果还有多个分量，添加更多边来连接
if len(components) > 1:
    print("仍有多个分量，添加更多连接...")
    
    # 重置并查集
    uf2 = UnionFind(len(endpoints_list))
    
    # 先加入MST边
    for edge in mst_edges:
        uf2.union(edge['idx1'], edge['idx2'])
    
    # 处理剩余边
    extra = 0
    for edge in edges:
        if not uf2.connected(edge['idx1'], edge['idx2']):
            uf2.union(edge['idx1'], edge['idx2'])
            mst_edges.append(edge)
            extra += 1
    
    print(f"添加额外边: {extra}")
    
    # 再次检查
    components2 = defaultdict(int)
    for i in range(len(endpoints_list)):
        root = uf2.find(i)
        components2[root] += 1
    print(f"最终连通分量数: {len(components2)}")

# 生成连接线
link_counter = 1

def create_link_czml(route_id, pos1, pos2, alt=70):
    """创建LINK航路的CZML - 正确的格式"""
    cartographic = [
        [pos1[0], pos1[1]],
        pos1[1],  # lat重复
        float(alt),
        [pos2[0], pos2[1]],
        pos2[1],  # lat重复
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
    pt1 = endpoints_list[idx1]['point']
    pt2 = endpoints_list[idx2]['point']
    
    # 确保起点和终点不同
    if abs(pt1[0] - pt2[0]) < 0.00001 and abs(pt1[1] - pt2[1]) < 0.00001:
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
        "_distance": round(edge['dist'], 1)
    })

print(f"\n生成连接线: {len(new_links)}条")

# 显示前10条连接
print("\n前10条连接:")
for r in new_links[:10]:
    czml = json.loads(r['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    pt1 = coords[0]
    pt2 = coords[2]
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
