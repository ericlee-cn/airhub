#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
航线自动生成服务
提供HTTP API供前端调用
"""

import json
import random
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re

# 路径配置
BASE_DIR = r'C:\mgs\basic\airspace'
DATA_DIR = os.path.join(BASE_DIR, 'data', 'airline')
ROUTE_FILE = os.path.join(DATA_DIR, '航线信息表_含CZML_最小连接.js')
OUTPUT_FILE = os.path.join(DATA_DIR, '航线信息表_30条.js')

# 业务类型定义
BUSINESS_TYPES = {
    '景区': [
        {'code': '4.1', 'type': '低空游览', 'goal': '景区空中观光游览服务', 'analysis': '为游客提供独特空中观光体验，带动旅游消费升级。'}
    ],
    '农林': [
        {'code': '1.1', 'type': '航空护林', 'goal': '森林防火巡护与灭火作业', 'analysis': '利用无人机进行森林火情监测，快速发现火情并定位，降低森林火灾损失。'},
        {'code': '1.2', 'type': '农林作业', 'goal': '农作物病虫害防治与施肥作业', 'analysis': '精准农业航空作业，提高农药喷洒效率，减少人工成本和农药用量。'}
    ],
    '市区': [
        {'code': '3.1', 'type': '快递物流运输', 'goal': '快递包裹末端配送', 'analysis': '解决偏远地区最后一公里配送难题，提升快递配送效率。'}
    ],
    '应急': [
        {'code': '2.1', 'type': '医疗救护', 'goal': '偏远地区医疗急救物资与人员转运', 'analysis': '为偏远地区提供快速医疗救护服务，缩短急救响应时间。'},
        {'code': '2.8', 'type': '电力巡线', 'goal': '输电线路日常巡检与故障排查', 'analysis': '替代人工巡线，快速发现线路隐患，保障电网安全稳定运行。'},
        {'code': '2.10', 'type': '遥感测绘', 'goal': '地形测绘与三维建模', 'analysis': '快速获取高精度地形数据，用于城市规划、土地利用监测等。'}
    ]
}

# POI地名
POI_NAMES = {
    '景区': ['莫干山旅游集散中心', '下渚湖湿地公园', '防风古国景区', '上渚山公园', '碧坞龙潭景区'],
    '农林': ['雷甸农业基地', '洛舍农业产业园', '乾元农业示范区', '新安农业基地', '禹越农林基地'],
    '市区': ['德清县物流中心', '武康镇政府', '地理信息小镇', '科技创业园', '人才公寓'],
    '应急': ['中医院', '妇幼保健院', '消防救援中心', '电力调度中心', '应急物资储备库']
}


def load_route_data():
    """加载航路数据"""
    with open(ROUTE_FILE, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    content = content.replace('const routeData = ', '', 1).replace(';', '')
    return json.loads(content)


def parse_airway_3d_coords(route):
    """解析航路三维坐标"""
    try:
        czml = json.loads(route['CZML'])
        pos = czml['corridor']['positions']['cartographicDegrees']
        coords_3d = []
        i = 0
        while i < len(pos):
            if isinstance(pos[i], list) and len(pos[i]) >= 2:
                lon, lat = pos[i][0], pos[i][1]
                if i + 1 < len(pos) and isinstance(pos[i + 1], (int, float)):
                    coords_3d.append((lon, lat, pos[i + 1]))
                    i += 2
                else:
                    coords_3d.append((lon, lat, 70))
                    i += 1
            else:
                i += 1
        return coords_3d
    except:
        return []


def classify_location(lon, lat):
    """根据坐标判断位置类型"""
    if lon > 120.0:
        return 'east_mountain' if lat > 30.55 else 'east_plain'
    elif lon < 119.9:
        return 'west_wetland' if lat > 30.55 else 'west_plain'
    else:
        return 'city'


def calc_distance(coords):
    """计算航路距离（米）"""
    dist = 0
    for i in range(len(coords) - 1):
        lon1, lat1, _ = coords[i]
        lon2, lat2, _ = coords[i + 1]
        dx = (lon2 - lon1) * 111000 * abs(lat1)
        dy = (lat2 - lat1) * 111000
        dist += (dx**2 + dy**2) ** 0.5
    return dist


def get_partial_coords(coords, max_distance_km=40):
    """获取航路的一部分，限制最大距离"""
    if not coords or len(coords) < 2:
        return coords

    total_dist = calc_distance(coords)
    if total_dist / 1000 <= max_distance_km:
        return coords

    target_dist = max_distance_km * 1000
    current_dist = 0
    partial = [coords[0]]

    for i in range(1, len(coords)):
        lon1, lat1, h1 = partial[-1]
        lon2, lat2, h2 = coords[i]
        dx = (lon2 - lon1) * 111000 * abs(lat1)
        dy = (lat2 - lat1) * 111000
        seg_dist = (dx**2 + dy**2) ** 0.5

        if current_dist + seg_dist <= target_dist:
            partial.append(coords[i])
            current_dist += seg_dist
        else:
            ratio = (target_dist - current_dist) / seg_dist if seg_dist > 0 else 1
            new_lon = lon1 + (lon2 - lon1) * ratio
            new_lat = lat1 + (lat2 - lat1) * ratio
            new_h = h1 + (h2 - h1) * ratio
            partial.append((new_lon, new_lat, new_h))
            break

    return partial


def generate_flights(params):
    """生成航线"""
    # 解析参数
    flight_count = params.get('flight_count', 30)
    max_flight_time = params.get('max_flight_time', 50)
    max_distance = params.get('max_distance', 40)
    speeds = params.get('speeds', {'A': 60, 'B': 75, 'C': 90, 'D': 100})
    business_types_filter = params.get('business_types', ['景区', '农林', '市区', '应急'])

    # 加载航路数据
    routes = load_route_data()

    # 排除LK连接线
    airways = [r for r in routes if not r['航路编号'].startswith('LK')]

    # 解析航路坐标
    for r in airways:
        coords = parse_airway_3d_coords(r)
        r['_coords_3d'] = coords
        if coords:
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            r['_center_lon'] = sum(lons) / len(lons)
            r['_center_lat'] = sum(lats) / len(lats)
        else:
            r['_center_lon'] = 0
            r['_center_lat'] = 0

    # 按位置分类航路
    locations = {'east_mountain': [], 'east_plain': [], 'west_wetland': [], 'west_plain': [], 'city': []}
    for a in airways:
        loc = classify_location(a['_center_lon'], a['_center_lat'])
        locations[loc].append(a)

    # 根据选中的业务类型构建分配策略
    allocation = []
    remaining_count = flight_count

    # 景区/农林 - 东部山区和西部湿地
    if '景区' in business_types_filter:
        count = min(remaining_count // 3, 9)
        allocation.extend([
            ('east_mountain', '景区', count // 2 + count % 2),
            ('west_wetland', '景区', count // 2)
        ])
        remaining_count -= count

    if '农林' in business_types_filter:
        count = min(remaining_count // 4, 8)
        allocation.extend([
            ('west_wetland', '农林', count // 2),
            ('east_mountain', '农林', count - count // 2)
        ])
        remaining_count -= count

    # 市区 - 快递
    if '市区' in business_types_filter:
        count = min(remaining_count // 2, 8)
        allocation.append(('city', '市区', count))
        remaining_count -= count

    # 应急/电力/测绘
    if '应急' in business_types_filter or '电力' in business_types_filter or '测绘' in business_types_filter:
        count = remaining_count
        allocation.append(('east_plain', '应急', count))

    # 生成航线
    flights = []
    flight_id = 1
    used_airways = set()

    for loc, biz_type, count in allocation:
        available = locations.get(loc, [])
        if not available:
            continue

        selected = random.choices(available, k=min(count, len(available)))

        for airway in selected:
            used_airways.add(airway['航路编号'])
            coords = airway['_coords_3d']
            if len(coords) < 2:
                continue

            # 限制航线长度
            coords = get_partial_coords(coords, max_distance_km=max_distance)
            if len(coords) < 2:
                continue

            # 选择业务
            biz = random.choice(BUSINESS_TYPES.get(biz_type, []))
            poi = random.choice(POI_NAMES.get(biz_type, ['通用点']))
            poi2 = random.choice([p for p in POI_NAMES.get(biz_type, ['通用点']) if p != poi])

            # 计算飞行时间
            start_lon, start_lat, start_h = coords[0]
            end_lon, end_lat, end_h = coords[-1]
            distance = calc_distance(coords)
            route_type = airway['航路类型']
            max_speed = speeds.get(route_type, 80)
            flight_time = (distance / 1000) / max_speed * 60

            # 检查时间约束
            if flight_time > max_flight_time:
                continue

            flight = {
                '航线ID': f'FL{flight_id:03d}',
                '航线名称': f'{biz["code"]}-{biz["type"]}',
                '所属航路': airway['航路编号'],
                '航路级别': airway['航路级别'],
                '航路类型': airway['航路类型'],
                '起点名称': poi,
                '终点名称': poi2,
                '起点坐标': {'lon': round(start_lon, 6), 'lat': round(start_lat, 6), 'height': start_h},
                '终点坐标': {'lon': round(end_lon, 6), 'lat': round(end_lat, 6), 'height': end_h},
                '航线距离_m': round(distance),
                '最高限速_kmh': max_speed,
                '预计飞行时间_min': round(flight_time, 1),
                '业务类型': biz['type'],
                '业务目标': biz['goal'],
                '业务分析': biz['analysis'],
                '航线坐标': coords
            }
            flights.append(flight)
            flight_id += 1

            if len(flights) >= flight_count:
                break

        if len(flights) >= flight_count:
            break

    return flights, list(used_airways)


def save_flights(flights):
    """保存航线到文件"""
    output = 'const flightData = ' + json.dumps(flights, ensure_ascii=False, indent=2) + ';'
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)
    return True


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f'[API] {args[0]}')

    def send_json_response(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_file_response(self, file_path, content_type='text/html'):
        """发送文件响应"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, 'File Not Found')

    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # 静态文件服务
        if path == '/' or path == '/flight_generator.html':
            self.send_file_response(os.path.join(BASE_DIR, 'flight_generator.html'))
        elif path == '/routes_and_airlines_map.html':
            self.send_file_response(os.path.join(BASE_DIR, 'routes_and_airlines_map.html'))
        elif path == '/api/health':
            self.send_json_response({'status': 'ok', 'service': '航线生成服务'})
        elif path == '/api/options':
            options = {
                'business_types': list(BUSINESS_TYPES.keys()),
                'speed_ranges': {'A': [30, 100], 'B': [40, 120], 'C': [50, 150], 'D': [60, 180]},
                'route_count': len([r for r in load_route_data() if not r['航路编号'].startswith('LK')])
            }
            self.send_json_response(options)
        else:
            self.send_json_response({'error': 'Not Found'}, 404)

    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            params = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response({'success': False, 'message': 'Invalid JSON'}, 400)
            return

        if path == '/api/generate-flights':
            try:
                flights, coverage = generate_flights(params)
                self.send_json_response({
                    'success': True,
                    'flights': flights,
                    'coverage': coverage,
                    'count': len(flights)
                })
            except Exception as e:
                self.send_json_response({'success': False, 'message': str(e)}, 500)

        elif path == '/api/save-flights':
            try:
                flights = params.get('flights', [])
                save_flights(flights)
                self.send_json_response({'success': True, 'message': '保存成功'})
            except Exception as e:
                self.send_json_response({'success': False, 'message': str(e)}, 500)

        else:
            self.send_json_response({'error': 'Not Found'}, 404)


def main():
    """启动服务"""
    port = 5500
    server = HTTPServer(('127.0.0.1', port), RequestHandler)
    print(f'=' * 50)
    print(f'航线自动生成服务已启动')
    print(f'API地址: http://127.0.0.1:{port}')
    print(f'前端页面: http://127.0.0.1:{port}/flight_generator.html')
    print(f'=' * 50)
    print(f'按 Ctrl+C 停止服务')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.shutdown()


if __name__ == '__main__':
    main()
