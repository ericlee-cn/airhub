#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于航路生成固定航线
确保固定航线沿着现有航路飞行
"""
import json
import math
import re

def parse_js_file(file_path):
    """解析JavaScript文件中的数组数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 routeData = [...] 中的数组内容
    match = re.search(r'const routeData\s*=\s*(\[.*\]);', content, re.DOTALL)
    if not match:
        raise ValueError("无法找到 routeData 数组")
    
    array_str = match.group(1)
    
    # 将JavaScript格式的NaN替换为null
    array_str = array_str.replace('NaN', 'null')
    
    # 使用json.loads解析（JS和JSON语法兼容）
    route_data = json.loads(array_str)
    
    return route_data

def calculate_distance(lat1, lon1, lat2, lon2):
    """计算两点之间的距离（单位：米）"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return 6371000 * c  # 地球半径6371km

def extract_waypoints_from_czml(czml_str):
    """从CZML字符串中提取航路点坐标"""
    czml = json.loads(czml_str)
    positions = czml['corridor']['positions']['cartographicDegrees']

    waypoints = []
    i = 0
    while i < len(positions):
        item = positions[i]
        # 处理嵌套数组格式: [[lon, lat], lat(重复), height, ...]
        if isinstance(item, list) and len(item) >= 2:
            lon = item[0]
            lat = item[1]
            # 下一个元素是重复的lat，跳过，再下一个是height
            if i + 2 < len(positions) and not isinstance(positions[i+1], list):
                # 跳过重复的lat
                i += 1
                # 获取高度
                if i + 1 < len(positions) and not isinstance(positions[i+1], list):
                    height = positions[i + 1]
                    i += 2
                else:
                    height = 70
                    i += 1
            else:
                height = 70
                i += 1
        # 处理普通数字格式
        elif isinstance(item, (int, float)):
            lon = item
            if i + 2 < len(positions) and not isinstance(positions[i+1], list) and not isinstance(positions[i+2], list):
                lat = positions[i + 1]
                height = positions[i + 2]
                i += 3
            else:
                break
        else:
            i += 1
            continue

        # 验证坐标有效性
        if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
            waypoints.append([lon, lat, height if isinstance(height, (int, float)) else 70])

    return waypoints

def main():
    # 读取航路数据
    print("正在读取航路数据...")
    route_data = parse_js_file('data/airline/航线信息表_含CZML.js')
    print(f"成功读取 {len(route_data)} 条航路")
    
    # 创建固定航线数据结构
    fixed_routes = {
        '航线库': {
            '元数据': {
                '版本': '2.0',
                '创建时间': '2026-03-21',
                '坐标系': 'WGS84',
                '高度基准': '海拔高度',
                '说明': '固定航线沿航路飞行，主要飞行阶段在航路内'
            },
            '任务类型定义': {
                '物资运输': '用于无人机物资配送任务,沿航路飞行',
                '应急医疗': '紧急医疗救援航线,沿航路飞行',
                '农林植保': '农业喷洒和林业巡查航线,沿航路飞行',
                '巡逻安防': '边境巡逻和城市安防巡逻航线,沿航路飞行',
                '应急救援': '自然灾害救援航线,沿航路飞行',
                '测绘巡检': '地理测绘和基础设施巡检航线,沿航路飞行'
            },
            '航线数据': []
        }
    }
    
    # 航路任务类型映射
    route_type_missions = {
        'A': ['物资运输', '农林植保', '测绘巡检'],
        'B': ['物资运输', '农林植保', '测绘巡检'],
        'C': ['物资运输', '巡逻安防', '应急救援'],
        'D': ['应急救援', '巡逻安防', '测绘巡检']
    }
    
    # 航路级别映射
    route_type_level = {
        'A': 'Ⅲ',
        'B': 'Ⅲ',
        'C': 'Ⅱ',
        'D': 'Ⅱ'
    }
    
    # 航路高度映射 (m)
    route_type_height = {
        'A': 70,
        'B': 120,
        'C': 170,
        'D': 220
    }
    
    # 优先级映射
    mission_priority = {
        '应急医疗': 'S',
        '应急救援': 'A',
        '巡逻安防': 'A',
        '物资运输': 'B',
        '农林植保': 'B',
        '测绘巡检': 'B'
    }
    
    # 颜色映射（根据航路级别）
    level_color_rgba = {
        'Ⅰ': [255, 0, 0, 180],      # 红色
        'Ⅱ': [255, 165, 0, 150],    # 橙色
        'Ⅲ': [0, 255, 0, 120]       # 绿色
    }
    
    # 选择航路生成固定航线（选择前20条）
    selected_routes = route_data[:20]
    
    print(f"\n开始生成固定航线...")
    
    for i, route in enumerate(selected_routes):
        route_id = route['航路编号']
        route_type = route['航路类型']
        route_level = route['航路级别']
        half_width = route['半宽(m)']
        
        # 提取航路点坐标
        wp_coords = extract_waypoints_from_czml(route['CZML'])
        
        # 计算总距离
        total_distance = 0
        for j in range(len(wp_coords) - 1):
            lon1, lat1, _ = wp_coords[j]
            lon2, lat2, _ = wp_coords[j + 1]
            total_distance += calculate_distance(lat1, lon1, lat2, lon2)
        
        total_distance_km = round(total_distance / 1000, 2)
        estimated_time = round(total_distance_km / 1.5)  # 假设速度90km/h=1.5km/min
        flight_height = route_type_height[route_type]
        
        # 选择任务类型
        mission_types = route_type_missions[route_type]
        mission_type = mission_types[i % len(mission_types)]
        priority = mission_priority[mission_type]
        fixed_route_level = route_type_level[route_type]
        
        # 生成航路点（每隔一定距离取一个点，大约6-8个航路点）
        waypoints = []
        num_waypoints = min(len(wp_coords), 8)
        if len(wp_coords) > num_waypoints:
            step = len(wp_coords) // num_waypoints
        else:
            step = 1
        
        for j in range(0, len(wp_coords), step):
            waypoints.append({
                '序号': len(waypoints) + 1,
                '名称': f'{route_id}_WP{len(waypoints)+1:02d}',
                '坐标': wp_coords[j],
                '停留时间(s)': 0
            })
        
        # 确保包含终点
        if waypoints[-1]['坐标'] != wp_coords[-1]:
            waypoints.append({
                '序号': len(waypoints) + 1,
                '名称': f'{route_id}_END',
                '坐标': wp_coords[-1],
                '停留时间(s)': 60
            })
        
        # 更新起点和终点名称
        waypoints[0]['名称'] = f'{route_id}_START'
        
        # 重新编号
        for j, wp in enumerate(waypoints):
            wp['序号'] = j + 1
        
        # 构建航线数据
        fixed_route = {
            '航线ID': f'FIX{route_id}',
            '航线名称': f'{route_id}_{mission_type}线',
            '任务类型': mission_type,
            '优先级': priority,
            '总里程': total_distance_km,
            '总里程(km)': total_distance_km,
            '预计用时': estimated_time,
            '预计用时(min)': estimated_time,
            '飞行高度': flight_height,
            '飞行高度(m)': flight_height,
            '航路半宽': half_width,
            '航路半宽(m)': half_width,
            '最大速度': 90,
            '最大速度(km/h)': 90,
            '航路级别': fixed_route_level,
            '起点': {
                '名称': f'{route_id}起点',
                '坐标': wp_coords[0],
                '类型': '航路起点'
            },
            '终点': {
                '名称': f'{route_id}终点',
                '坐标': wp_coords[-1],
                '类型': '航路终点'
            },
            '航路点': waypoints,
            '关联航路': route_id,
            'CZML': route['CZML'],
            '备注': f'沿{route_id}航路飞行（{route_type}类，{flight_height}m），主要飞行阶段在航路内'
        }
        
        # 更新CZML（修改ID和名称，颜色根据航路级别）
        czml = json.loads(route['CZML'])
        czml['id'] = fixed_route['航线ID']
        czml['name'] = fixed_route['航线名称']
        
        # 更新颜色（根据航线级别，而不是航路类型）
        czml['corridor']['material']['solidColor']['color']['rgba'] = level_color_rgba[fixed_route_level]
        
        # 更新宽度
        czml['corridor']['width'] = half_width * 2
        
        fixed_route['CZML'] = json.dumps(czml, ensure_ascii=False)
        
        fixed_routes['航线库']['航线数据'].append(fixed_route)
        
        print(f"  [{i+1}/20] {fixed_route['航线ID']}: {fixed_route['航线名称']} ({total_distance_km}km, {fixed_route_level}级)")
    
    # 保存文件
    output_file = 'data/airline/fixed_routes_library.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fixed_routes, f, ensure_ascii=False, indent=2)
    
    print(f"\n成功生成 {len(fixed_routes['航线库']['航线数据'])} 条固定航线数据")
    print(f"文件已保存到: {output_file}")

if __name__ == '__main__':
    main()
