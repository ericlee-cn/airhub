import json
import math
from collections import defaultdict

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

def round_pt(pt):
    return (round(pt[0], 4), round(pt[1], 4))

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

def check_connectivity(data):
    route_endpoints = []
    for route in data:
        coords = parse_positions(route['CZML'])
        if len(coords) >= 2:
            route_endpoints.append({
                'route_id': route['航路编号'],
                'start': coords[0],
                'end': coords[-1]
            })

    endpoint_map = {}
    endpoints_list = []

    for ep in route_endpoints:
        for key in [ep['start'], ep['end']]:
            rp = round_pt(key)
            if rp not in endpoint_map:
                endpoint_map[rp] = len(endpoints_list)
                endpoints_list.append({'point': key, 'routes': [ep['route_id']]})
            else:
                idx = endpoint_map[rp]
                if ep['route_id'] not in endpoints_list[idx]['routes']:
                    endpoints_list[idx]['routes'].append(ep['route_id'])

    uf = UnionFind(len(endpoints_list))

    for ep in route_endpoints:
        idx_start = endpoint_map.get(round_pt(ep['start']))
        idx_end = endpoint_map.get(round_pt(ep['end']))
        if idx_start is not None and idx_end is not None:
            uf.union(idx_start, idx_end)

    components = defaultdict(int)
    for i in range(len(endpoints_list)):
        components[uf.find(i)] += 1

    return len(components)

# 读取数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

links = [r for r in data if r.get('航路类型') == 'LINK']
routes_only = [r for r in data if r.get('航路类型') != 'LINK']

# 按距离排序LINK
sorted_links = sorted(links, key=lambda x: x.get('_distance', 0), reverse=True)
print('LINK按距离排序（从长到短）:')
for i, link in enumerate(sorted_links):
    print(f'  {i+1}. {link["航路编号"]}: {link["_distance"]}m')

# 逐个删除测试
print('\n逐个删除测试:')
for remove_count in range(1, min(6, len(sorted_links) + 1)):
    removed_ids = [l['航路编号'] for l in sorted_links[:remove_count]]
    data_test = [r for r in data if r.get('航路编号') not in removed_ids]
    comp_count = check_connectivity(data_test)
    status = 'OK 连通' if comp_count == 1 else f'FAIL {comp_count}个分量'
    print(f'  删除前{remove_count}条: {status}')
