import json

with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

links = [r for r in data if r.get('航路类型') == 'LINK']
print(f'LINK数量: {len(links)}')

# 检查LINK的坐标格式
invalid_count = 0
valid_count = 0

for link in links:
    czml = json.loads(link['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    
    # 解析格式: [[lon, lat], lat, alt, [lon, lat], lat, alt]
    if isinstance(coords[0], list) and isinstance(coords[2], list):
        pt1 = coords[0]
        pt2 = coords[2]
        
        # 检查是否是有效连接
        if abs(pt1[0] - pt2[0]) > 0.0001 or abs(pt1[1] - pt2[1]) > 0.0001:
            valid_count += 1
            if valid_count <= 10:
                print(f"  {link['航路编号']}: ({pt1[0]:.4f}, {pt1[1]:.4f}) -> ({pt2[0]:.4f}, {pt2[1]:.4f})")
        else:
            invalid_count += 1
            if invalid_count <= 3:
                print(f"  [无效] {link['航路编号']}: ({pt1[0]:.4f}, {pt1[1]:.4f}) -> ({pt2[0]:.4f}, {pt2[1]:.4f})")
    else:
        invalid_count += 1
        if invalid_count <= 3:
            print(f"  [格式错误] {link['航路编号']}: coords={coords[:6]}")

print(f'\n有效连接: {valid_count}')
print(f'无效连接: {invalid_count}')
