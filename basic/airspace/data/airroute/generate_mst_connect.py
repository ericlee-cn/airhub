# -*- coding: utf-8 -*-
"""
航路连通性修复脚本 v4
使用最小生成树(MST)确保所有航路连通，用最少的连接线
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
        try:
            if isinstance(positions[i], list):
                lon, lat = float(positions[i][0]), float(positions[i][1])
                i += 1
                if i < len(positions):
                    v = positions[i]
                    alt = float(v) if isinstance(v, (int, float)) else 70.0
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
            'start': coords[0],
            'end': coords[-1],
            'route_type': route['航路类型']
        })

print(f"提取航路数量: {len(endpoints)}")

# 获取所有航路ID
all_route_ids = set(ep['route_id'] for ep in endpoints)

# 并查集
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
    
    def same(self, x, y):
        return self.find(x) == self.find(y)

# Kruskal最小生成树
def kruskal_mst(endpoints):
    """使用Kruskal算法确保所有航路连通"""
    
    # 构建所有可能的连接边
    edges = []
    
    for i, ep1 in enumerate(endpoints):
        for j, ep2 in enumerate(endpoints):
            if i >= j:
                continue
            if ep1['route_id'] == ep2['route_id']:
                continue
            
            # 检查是否已经在同一组件中（通过共享端点）
            # 实际上每条航路的两个端点是连通的
            
            # 计算端点到端点的距离
            dist1 = haversine_distance(ep1['start'], ep2['start'])
            dist2 = haversine_distance(ep1['start'], ep2['end'])
            dist3 = haversine_distance(ep1['end'], ep2['start'])
            dist4 = haversine_distance(ep1['end'], ep2['end'])
            
            min_dist = min(dist1, dist2, dist3, dist4)
            
            # 选择最近的连接方式
            if min_dist == dist1:
                pos1, pos2 = ep1['start'], ep2['start']
                ep_type = ('start', 'start')
            elif min_dist == dist2:
                pos1, pos2 = ep1['start'], ep2['end']
                ep_type = ('start', 'end')
            elif min_dist == dist3:
                pos1, pos2 = ep1['end'], ep2['start']
                ep_type = ('end', 'start')
            else:
                pos1, pos2 = ep1['end'], ep2['end']
                ep_type = ('end', 'end')
            
            edges.append({
                'r1': ep1['route_id'],
                'r2': ep2['route_id'],
                'dist': min_dist,
                'pos1': pos1,
                'pos2': pos2,
                'type': ep_type
            })
    
    # 按距离排序
    edges.sort(key=lambda x: x['dist'])
    
    print(f"总边数: {len(edges)}")
    
    # Kruskal算法
    uf = UnionFind()
    mst_edges = []
    
    for edge in edges:
        # 如果两个航路还不在同一组件中
        if not uf.same(edge['r1'], edge['r2']):
            uf.union(edge['r1'], edge['r2'])
            mst_edges.append(edge)
    
    return mst_edges

# 首先，每条航路内部的两个端点是连通的
# 所以我们需要找到需要添加的连接线来连接不同的组件

# 使用并查集跟踪连通性
uf = UnionFind()

# 初始化所有航路
for ep in endpoints:
    uf.find(ep['route_id'])

# 检查当前连通分量
def get_components():
    components = defaultdict(set)
    for route_id in all_route_ids:
        components[uf.find(route_id)].add(route_id)
    return components

print("\n使用Kruskal最小生成树算法...")
mst_edges = kruskal_mst(endpoints)

print(f"\n最小生成树边数: {len(mst_edges)}")

# 生成连接线
def generate_route_id(index):
    return f"LK{index:04d}"

def create_czml(route_id, pos1, pos2, alt=70):
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
for i, edge in enumerate(mst_edges):
    route_id = generate_route_id(i + 1)
    
    new_routes.append({
        "航路编号": route_id,
        "航路名称": "连接线",
        "航路类型": "LINK",
        "航路级别": "连接",
        "半宽(m)": 30,
        "半高(m)": 20,
        "CZML": create_czml(route_id, edge['pos1'], edge['pos2']),
        "_source": f"{edge['r1']}({edge['type'][0]}) -> {edge['r2']}({edge['type'][1]})",
        "_distance": round(edge['dist'], 1)
    })

print(f"生成连接线: {len(new_routes)}条")

# 合并数据
all_routes = routes + new_routes

# 统计连接距离
if new_routes:
    distances = [r['_distance'] for r in new_routes]
    print(f"\n连接距离统计:")
    print(f"  最短: {min(distances):.1f}米")
    print(f"  最长: {max(distances):.1f}米")
    print(f"  平均: {sum(distances)/len(distances):.1f}米")

# 保存
output_file = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_routes, f, ensure_ascii=False, indent=2)

js_content = 'const routeData = ' + json.dumps(all_routes, ensure_ascii=False) + ';'
output_js = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"\n已保存到: {output_file}")
print(f"总航路: {len(all_routes)} (原始 {len(routes)} + 连接 {len(new_routes)})")

# 显示前10条连接
print("\n前10条连接:")
for r in new_routes[:10]:
    print(f"  {r['航路编号']}: {r['_source']} ({r['_distance']}米)")

print("\n完成!")
