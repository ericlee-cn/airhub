import json

# 读取原始数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f'原始航路数量: {len(routes)}')

# 检查是否有共享端点的情况
endpoints_map = {}
for route in routes:
    czml = json.loads(route['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    # 解析嵌套格式
    points = []
    i = 0
    while i < len(coords):
        if isinstance(coords[i], list):
            points.append((round(coords[i][0], 4), round(coords[i][1], 4)))
            i += 1
        else:
            i += 2
    
    if len(points) >= 2:
        start = points[0]
        end = points[-1]
        
        # 记录端点对应的航路
        if start not in endpoints_map:
            endpoints_map[start] = []
        endpoints_map[start].append(route['航路编号'])
        
        if end not in endpoints_map:
            endpoints_map[end] = []
        endpoints_map[end].append(route['航路编号'])

# 找出共享端点的航路
shared = {k: v for k, v in endpoints_map.items() if len(v) > 1}
print(f'\n共享端点数量: {len(shared)}')
print('共享端点示例:')
for pt, routes_list in list(shared.items())[:5]:
    print(f'  ({pt[0]:.4f}, {pt[1]:.4f}): {routes_list}')

# 检查MST数据
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    mst_data = json.load(f)

links = [r for r in mst_data if r.get('航路类型') == 'LINK']
print(f'\nMST LINK数量: {len(links)}')

# 检查无效的LINK（起点=终点）
invalid_links = []
for link in links:
    czml = json.loads(link['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    pt1 = coords[0]
    pt2 = coords[2]
    if pt1[0] == pt2[0] and pt1[1] == pt2[1]:
        invalid_links.append(link['航路编号'])

print(f'无效LINK（起点=终点）: {len(invalid_links)}')
if invalid_links:
    print(f'  示例: {invalid_links[:5]}')

# 显示几条有效的LINK
print('\n有效的LINK示例:')
valid_count = 0
for link in links:
    czml = json.loads(link['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    pt1 = coords[0]
    pt2 = coords[2]
    if not (pt1[0] == pt2[0] and pt1[1] == pt2[1]):
        valid_count += 1
        if valid_count <= 5:
            print(f"  {link['航路编号']}: ({pt1[0]:.4f}, {pt1[1]:.4f}) -> ({pt2[0]:.4f}, {pt2[1]:.4f})")

print(f'\n有效LINK总数: {valid_count}')
