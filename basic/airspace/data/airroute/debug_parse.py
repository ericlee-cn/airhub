import json

with open('C:/mgs/basic/airspace/data/airroute/航线信息表_含CZML.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f'航路数量: {len(routes)}')

# 检查第一条航路的CZML格式
route = routes[0]
czml = json.loads(route['CZML'])
positions = czml['corridor']['positions']['cartographicDegrees']

print(f'\n航路编号: {route["航路编号"]}')
print(f'坐标类型: {type(positions)}')
print(f'坐标长度: {len(positions)}')
print(f'前30个元素: {positions[:30]}')
print(f'元素类型: {[type(p) for p in positions[:10]]}')
