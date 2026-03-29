import json
import os

# 读取原始飞行计划数据
with open('flyplanlist.json', 'r', encoding='utf-8') as f:
    plans = json.load(f)

# 转换为航线库格式
routes = []
for plan in plans:
    # 提取航点坐标
    waypoints = plan.get('flightAirroute', [])
    coords = [[wp['longitude'], wp['latitude'], wp['altitude']] for wp in waypoints]
    
    # 计算航线长度（米）
    length = 0
    for i in range(len(coords) - 1):
        # 简化的距离计算
        lon1, lat1 = coords[i][0], coords[i][1]
        lon2, lat2 = coords[i+1][0], coords[i+1][1]
        import math
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        length += c * 6371000  # 地球半径
    
    # 提取起止点
    start_point = waypoints[0]['name'] if waypoints else ''
    end_point = waypoints[-1]['name'] if waypoints else ''
    
    # 确定航线类型（基于申请类型）
    apply_type = plan.get('faa_applyType', 1)
    route_type_map = {1: '定期航线', 2: '登记航线', 3: '累积航线'}
    route_type = route_type_map.get(apply_type, '定期航线')
    
    # 飞行频率
    time_range = plan.get('faa_planflightTime', {}).get('timeRange', [])
    if time_range:
        fly_freq = '定期'
    else:
        fly_freq = '按需'
    
    route = {
        'route_id': plan.get('faa_applyNo', ''),
        'route_name': plan.get('faa_applyName', ''),
        'route_type': route_type,
        'fly_freq': fly_freq,
        'biz_type': '巡检',  # 默认
        'data_source': '飞行计划库',
        'start_point': start_point,
        'end_point': end_point,
        'waypoint_count': len(waypoints),
        'route_length_m': round(length, 2),
        'geojson': {
            'type': 'LineString',
            'coordinates': coords
        }
    }
    routes.append(route)

# 保存为航线库JSON
with open('route_library.json', 'w', encoding='utf-8') as f:
    json.dump(routes, f, ensure_ascii=False, indent=2)

print(f'已生成 route_library.json，共 {len(routes)} 条航线')
print('示例:', routes[0])
