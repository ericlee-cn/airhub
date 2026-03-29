import json

with open('航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

links = [r for r in data if r.get('航路类型') == 'LINK']
print(f'LINK数量: {len(links)}')

# 检查LINK的坐标格式
for i, link in enumerate(links[:5]):
    czml = json.loads(link['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    print(f'\nLINK {i+1} ({link["航路编号"]}):')
    print(f'  coords类型: {type(coords)}')
    print(f'  coords长度: {len(coords)}')
    print(f'  前20个元素: {coords[:20]}')
