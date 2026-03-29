import json
with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML_连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
links = [r for r in data if r.get('航路类型') == 'LINK']
print(f'总航路数: {len(data)}')
print(f'LINK数: {len(links)}')

# 验证LINK格式
for link in links[:5]:
    czml = json.loads(link['CZML'])
    coords = czml['corridor']['positions']['cartographicDegrees']
    print(f"  {link['航路编号']}: {coords}")
