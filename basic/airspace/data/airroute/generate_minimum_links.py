# -*- coding: utf-8 -*-
"""
生成最小连接线，打通所有航路
使用 Kruskal 最小生成树算法找到需要的最少连线
"""

import json
import re
import math
from collections import defaultdict

# 读取原始航路数据
def read_js_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 提取 JSON 部分
    match = re.search(r'const routeData = (.+);', content)
    if match:
        return json.loads(match.group(1))
    return None

# 计算两点之间的距离（米）
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

# 提取航路端点
def extract_endpoints(route):
    """从航路中提取起点和终点坐标"""
    czml_str = route.get('CZML', '')
    try:
        czml = json.loads(czml_str)
        positions = czml.get('corridor', {}).get('positions', {}).get('cartographicDegrees', [])
        
        if len(positions) < 2:
            return None, None
        
        # 提取坐标对
        coords = []
        i = 0
        while i < len(positions):
            if isinstance(positions[i], list):
                coords.append((positions[i][0], positions[i][1]))  # lon, lat
                i += 1
            elif i + 2 < len(positions):
                coords.append((positions[i], positions[i+1]))  # lon, lat
                i += 3
            else:
                break
        
        if len(coords) >= 2:
            return coords[0], coords[-1]
    except:
        pass
    return None, None

# 并查集
class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}
    
    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True

def main():
    # 读取数据
    input_path = r'C:\mgs\basic\airspace\data\airroute\航线信息表_含CZML.js'
    output_path = r'C:\mgs\basic\airspace\data\airroute\航线信息表_含CZML_连通.js'
    
    print("读取原始航路数据...")
    route_data = read_js_file(input_path)
    print(f"原始航路数量: {len(route_data)}")
    
    # 提取所有端点
    print("\n提取航路端点...")
    endpoints = []  # (route_id, endpoint_type, lon, lat)
    route_endpoints = {}  # route_id -> (start, end)
    
    for route in route_data:
        route_id = route['航路编号']
        start, end = extract_endpoints(route)
        if start and end:
            route_endpoints[route_id] = (start, end)
            endpoints.append((route_id, 'start', start[0], start[1]))
            endpoints.append((route_id, 'end', end[0], end[1]))
    
    print(f"提取到 {len(route_endpoints)} 条航路的端点信息")
    
    # 统计唯一端点
    unique_coords = set()
    for route_id, (start, end) in route_endpoints.items():
        unique_coords.add(start)
        unique_coords.add(end)
    print(f"唯一端点数量: {len(unique_coords)}")
    
    # 为每个唯一坐标分配一个节点ID
    coord_to_node = {}
    node_to_coord = {}
    for i, coord in enumerate(unique_coords):
        coord_to_node[coord] = i
        node_to_coord[i] = coord
    
    # 构建端点到航路的映射
    node_routes = defaultdict(list)  # node_id -> [(route_id, endpoint_type), ...]
    for route_id, (start, end) in route_endpoints.items():
        node_routes[coord_to_node[start]].append((route_id, 'start'))
        node_routes[coord_to_node[end]].append((route_id, 'end'))
    
    # 已经连接的组件（同一航路的两个端点默认连通）
    uf = UnionFind()
    for route_id, (start, end) in route_endpoints.items():
        uf.union(coord_to_node[start], coord_to_node[end])
    
    # 构建所有可能的连接线（同一个端点位置只连一次）
    candidate_connections = []
    
    # 方法：对于每个唯一坐标位置，找出可以连接的其他航路
    for node_id, coord in node_to_coord.items():
        routes_at_node = node_routes[node_id]
        
        # 对于这个位置上的每对航路端点，它们已经连通了
        for i, (route1, _) in enumerate(routes_at_node):
            for j, (route2, _) in enumerate(routes_at_node):
                if i < j and route1 != route2:
                    # 同一位置的端点已经被航路连接
                    pass
    
    # 寻找需要添加的连接线
    # 使用 Kruskal 最小生成树
    print("\n构建最小连接线...")
    
    # 找出哪些组件还没连通
    components = defaultdict(list)  # component_id -> [route_ids]
    for route_id in route_endpoints.keys():
        start, end = route_endpoints[route_id]
        comp = uf.find(coord_to_node[start])
        components[comp].append(route_id)
    
    num_components = len(components)
    print(f"当前连通分量数量: {num_components}")
    
    if num_components == 1:
        print("所有航路已经连通，无需添加连接线！")
        # 直接保存原数据
        result = f"const routeData = {json.dumps(route_data, ensure_ascii=False)};"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"已保存到: {output_path}")
        return
    
    # 构建所有节点对之间的距离
    all_nodes = list(node_to_coord.items())
    edges = []
    
    # 找出哪些节点对之间可以连接（不是同一航路的端点）
    for i, (node1, coord1) in enumerate(all_nodes):
        for j, (node2, coord2) in enumerate(all_nodes):
            if i < j:
                # 检查这两个节点是否已经在同一组件中
                comp1 = uf.find(node1)
                comp2 = uf.find(node2)
                if comp1 != comp2:
                    dist = haversine(coord1[0], coord1[1], coord2[0], coord2[1])
                    edges.append((dist, node1, node2, coord1, coord2))
    
    # 按距离排序
    edges.sort()
    
    # Kruskal 算法
    link_routes = []
    added_edges = []
    
    for dist, node1, node2, coord1, coord2 in edges:
        comp1 = uf.find(node1)
        comp2 = uf.find(node2)
        
        if comp1 != comp2:
            # 添加这条边
            uf.union(node1, node2)
            added_edges.append((dist, coord1, coord2))
            
            # 生成连接线航路
            link_route = {
                '航路编号': f'EA{len(link_routes) + 1:04d}',
                '航路名称': None,
                '航路类型': 'E',  # E 表示连接线
                '航路级别': 'Ⅲ',
                '半宽(m)': 15,
                '半高(m)': 20,
                'CZML': json.dumps({
                    'id': f'EA{len(link_routes) + 1:04d}',
                    'name': f'EA{len(link_routes) + 1:04d}',
                    'corridor': {
                        'positions': {
                            'cartographicDegrees': [
                                [coord1[0], coord1[1]], coord1[1], 100,
                                [coord2[0], coord2[1]], coord2[1], 100
                            ]
                        },
                        'width': 30.0,
                        'material': {
                            'solidColor': {
                                'color': {
                                    'rgba': [255, 255, 0, 200]  # 黄色连接线
                                }
                            }
                        },
                        'extrudedHeight': 20.0,
                        'height': 0
                    }
                }, ensure_ascii=False)
            }
            link_routes.append(link_route)
            
            # 检查是否所有组件都连通了
            if len(added_edges) >= num_components - 1:
                break
    
    print(f"\n添加了 {len(link_routes)} 条连接线")
    print("\n连接线详情:")
    for i, route in enumerate(link_routes):
        czml = json.loads(route['CZML'])
        pos = czml['corridor']['positions']['cartographicDegrees']
        print(f"  {route['航路编号']}: ({pos[0][0]:.6f}, {pos[0][1]:.6f}) -> ({pos[3][0]:.6f}, {pos[3][1]:.6f}), 距离: {added_edges[i][0]:.0f}m")
    
    # 合并原始航路和连接线
    all_routes = route_data + link_routes
    
    # 保存结果
    result = f"const routeData = {json.dumps(all_routes, ensure_ascii=False)};"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(f"\n已保存到: {output_path}")
    print(f"总共航路数量: {len(all_routes)} (原始 {len(route_data)} + 连接线 {len(link_routes)})")

if __name__ == '__main__':
    main()
