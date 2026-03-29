import json
with open('航线信息表_含CZML_MST连通.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
links = [r for r in data if r.get('航路类型') == 'LINK']
print(f'LINK数量: {len(links)}')
print('LINK航路ID:')
for l in links[:30]:
    print(f"  {l['航路编号']}")
