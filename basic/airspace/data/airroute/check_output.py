import json
with open('航线信息表_含CZML_全连接.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'总航路数: {len(data)}')
link_routes = [r for r in data if r['航路类型'] == 'LINK']
print(f'连接线数量: {len(link_routes)}')
print('连接线示例:')
for r in link_routes[:10]:
    print(f"  {r['航路编号']}: {r['_source']} ({r['_distance']}米)")
