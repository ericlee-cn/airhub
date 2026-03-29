import json
import math
from collections import defaultdict

# 读取数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

links = [r for r in data if r.get('航路类型') == 'LINK']
print(f'总LINK数: {len(links)}')

# 找最长连接
max_dist = 0
max_link = None
for link in links:
    dist = link.get('_distance', 0)
    if dist > max_dist:
        max_dist = dist
        max_link = link

print(f'最长连接: {max_link["航路编号"]}, 距离: {max_dist}m')

# 删除最长连接
data_removed = [r for r in data if r.get('航路编号') != max_link['航路编号']]
print(f'删除后航路数: {len(data_removed)}')

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

# 提取所有航路的端点
route_endpoints = []
for route in data_removed:
    coords = parse_positions(route['CZML'])
    if len(coords) >= 2:
        route_endpoints.append({
            'route_id': route['航路编号'],
            'start': coords[0],
            'end': coords[-1]
        })

def round_pt(pt):
    return (round(pt[0], 4), round(pt[1], 4))

endpoint_map = {}
endpoints_list = []

for ep in route_endpoints:
    for key in [ep['start'], ep['end']]:
        rp = round_pt(key)
        if rp not in endpoint_map:
            endpoint_map[rp] = len(endpoints_list)
            endpoints_list.append({
                'point': key,
                'routes': [ep['route_id']]
            })
        else:
            idx = endpoint_map[rp]
            if ep['route_id'] not in endpoints_list[idx]['routes']:
                endpoints_list[idx]['routes'].append(ep['route_id'])

print(f'唯一端点数: {len(endpoints_list)}')

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

uf = UnionFind(len(endpoints_list))

# 同一条航路的两个端点已连通
for ep in route_endpoints:
    idx_start = endpoint_map.get(round_pt(ep['start']))
    idx_end = endpoint_map.get(round_pt(ep['end']))
    if idx_start is not None and idx_end is not None:
        uf.union(idx_start, idx_end)

# 检查连通分量
components = defaultdict(int)
for i in range(len(endpoints_list)):
    components[uf.find(i)] += 1

print(f'删除最长连接后连通分量数: {len(components)}')

if len(components) == 1:
    print('仍然完全连通！可以删除')
    # 保存
    output_file = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data_removed, f, ensure_ascii=False, indent=2)

    js_content = 'const routeData = ' + json.dumps(data_removed, ensure_ascii=False) + ';'
    output_js = 'C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.js'
    with open(output_js, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f'已保存到: {output_file}')
    print(f'新总航路数: {len(data_removed)}')
else:
    print('删除后不连通了，需要保留最长连接')
