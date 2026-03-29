import json
import csv

# 读取飞行计划数据
with open('C:/mgs/flyplan/flyplanlist.json', 'r', encoding='utf-8') as f:
    flight_plans = json.load(f)

# 提取航线库数据
route_data = []

for plan in flight_plans:
    # 跳过没有航线的记录
    if not plan.get('flightAirroute') or len(plan.get('flightAirroute', [])) == 0:
        continue
    
    # 构建GeoJSON格式的坐标序列
    coordinates = []
    for point in plan['flightAirroute']:
        coordinates.append([
            round(point.get('longitude', 0), 6),
            round(point.get('latitude', 0), 6),
            round(point.get('altitude', 0), 1)
        ])
    
    # 构建GeoJSON LineString
    geojson_line = {
        "type": "LineString",
        "coordinates": coordinates
    }
    
    # 计算航线长度（简单估算）
    route_length = 0
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i][0], coordinates[i][1]
        lon2, lat2 = coordinates[i+1][0], coordinates[i+1][1]
        # 简单距离估算（1度经度约111km，1度纬度约111km）
        import math
        d = math.sqrt(((lon2-lon1)*111000)**2 + ((lat2-lat1)*111000)**2)
        route_length += d
    
    # 提取需要的字段（去掉飞行器和时间信息）
    # 根据申请号生成航线类型和业务类型（模拟数据）
    apply_no = plan.get('faa_applyNo', '')
    if '91' in apply_no:
        route_type = '定期航线'
        fly_freq = '每日'  # 定期航线默认每日
    elif '35' in apply_no or '34' in apply_no:
        route_type = '登记航线'
        fly_freq = '每周'
    else:
        route_type = '累积航线'
        fly_freq = '按需'
    
    # 根据任务类型(faa_taskType)或备注判断业务类型
    task_type = plan.get('faa_taskType', '')
    if task_type == '2.8':
        biz_type = '巡检'
    elif '测试' in plan.get('faa_applyName', ''):
        biz_type = '测试'
    elif '仿真' in plan.get('faa_applyName', ''):
        biz_type = '仿真'
    else:
        biz_type = '其他'
    
    route_item = {
        'route_id': plan.get('faa_applyNo', ''),
        'route_name': plan.get('faa_applyName', ''),
        'route_type': route_type,
        'fly_freq': fly_freq,
        'biz_type': biz_type,
        'data_source': '飞行计划库',
        'start_point': plan.get('startPointId', ''),
        'end_point': plan.get('endPointId', ''),
        'waypoint_count': len(coordinates),
        'route_length_m': round(route_length, 2),
        'geojson': json.dumps(geojson_line, ensure_ascii=False)
    }
    
    route_data.append(route_item)

# 写入CSV文件
csv_file = 'C:/mgs/flyplan/route_library.csv'
fieldnames = ['route_id', 'route_name', 'route_type', 'fly_freq', 'biz_type', 'data_source',
              'start_point', 'end_point', 'waypoint_count', 'route_length_m', 'geojson']

with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(route_data)

print(f"已生成航线库CSV文件: {csv_file}")
print(f"共提取 {len(route_data)} 条航线")
