#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成电磁仿真数据 - 基于新的仿真范围1.geojson，高度0-400米
"""

import json
import math
import os
from datetime import datetime

# =====================================================================
# 配置参数
# =====================================================================
GRID_SIZE = 0.0008  # 约80m
GALT = 80           # 高度分层间隔
HEIGHT_MAX = 400    # 最大高度（米）
HEIGHT_MIN = 0      # 最小高度（米）

# 仿真范围（从geojson提取）
SIM_BBOX = {
    'lon_min': 119.83406,
    'lon_max': 120.16090,
    'lat_min': 30.47767,
    'lat_max': 30.62491
}

# 干扰源数据
EM_SOURCES = [
    # 5G基站
    {'name': '5G基站-1', 'lon': 119.9712967977313, 'lat': 30.52355836887861, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-2', 'lon': 119.9624061139184, 'lat': 30.51517207893123, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-3', 'lon': 119.9762522651380, 'lat': 30.51426268892555, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-4', 'lon': 119.9591012335834, 'lat': 30.52901861304756, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-5', 'lon': 119.9185180664063, 'lat': 30.55856553798283, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-6', 'lon': 119.8819541931152, 'lat': 30.59846854371451, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-7', 'lon': 120.0372219085693, 'lat': 30.52910807064572, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    {'name': '5G基站-8', 'lon': 120.0234031677246, 'lat': 30.54688710949595, 'alt': 30, 'power_w': 50, 'freq_mhz': 3500, 'type': '5g'},
    # 监视雷达
    {'name': '监视雷达-1', 'lon': 119.9047851562500, 'lat': 30.53860787885457, 'alt': 30, 'power_w': 2000, 'freq_mhz': 3000, 'type': 'radar'},
    {'name': '监视雷达-2', 'lon': 119.9657893180847, 'lat': 30.51820247638195, 'alt': 30, 'power_w': 2000, 'freq_mhz': 3000, 'type': 'radar'},
    {'name': '监视雷达-3', 'lon': 120.0446891784668, 'lat': 30.50134260771591, 'alt': 30, 'power_w': 2000, 'freq_mhz': 3000, 'type': 'radar'},
    {'name': '监视雷达-4', 'lon': 120.0156784057617, 'lat': 30.56433032003468, 'alt': 30, 'power_w': 2000, 'freq_mhz': 3000, 'type': 'radar'},
    # CORS站
    {'name': 'CORS-1', 'lon': 119.9030685424805, 'lat': 30.57999697131928, 'alt': 10, 'power_w': 10, 'freq_mhz': 1575.42, 'type': 'cors'},
    {'name': 'CORS-2', 'lon': 119.9806594848633, 'lat': 30.56078280238087, 'alt': 10, 'power_w': 10, 'freq_mhz': 1575.42, 'type': 'cors'},
    {'name': 'CORS-3', 'lon': 119.9349975585938, 'lat': 30.54156482797521, 'alt': 10, 'power_w': 10, 'freq_mhz': 1575.42, 'type': 'cors'},
    {'name': 'CORS-4', 'lon': 119.9967956542969, 'lat': 30.49128445210019, 'alt': 10, 'power_w': 10, 'freq_mhz': 1575.42, 'type': 'cors'},
    {'name': 'CORS-5', 'lon': 120.0771331787109, 'lat': 30.52116004661714, 'alt': 10, 'power_w': 10, 'freq_mhz': 1575.42, 'type': 'cors'},
    # UAV中继
    {'name': 'UAV中继-1', 'lon': 119.9200, 'lat': 30.5400, 'alt': 280, 'power_w': 5, 'freq_mhz': 2400, 'type': 'uav'},
    {'name': 'UAV中继-2', 'lon': 120.0600, 'lat': 30.5200, 'alt': 350, 'power_w': 5, 'freq_mhz': 2400, 'type': 'uav'},
    {'name': 'UAV中继-3', 'lon': 119.9900, 'lat': 30.5000, 'alt': 400, 'power_w': 5, 'freq_mhz': 2400, 'type': 'uav'},  # 调整为30.5000，确保在范围内
]

# 信号源类型映射（用于生成独立数据）
SOURCE_TYPES = {
    'all': {'label': '综合', 'sources': [s['name'] for s in EM_SOURCES]},
    '5g': {'label': '5G基站', 'sources': [s['name'] for s in EM_SOURCES if s['type'] == '5g']},
    'radar': {'label': '监视雷达', 'sources': [s['name'] for s in EM_SOURCES if s['type'] == 'radar']},
    'cors': {'label': 'CORS站', 'sources': [s['name'] for s in EM_SOURCES if s['type'] == 'cors']},
    'uav': {'label': 'UAV中继', 'sources': [s['name'] for s in EM_SOURCES if s['type'] == 'uav']}
}

# 多边形边界坐标（用于点在多边形内判断）
POLYGON_COORDS = [
    [119.8484802246094, 30.62491370405477],
    [120.0661468505859, 30.60127591448606],
    [120.1609039306641, 30.58590825748558],
    [120.1602172851563, 30.48891767612684],
    [119.9658966064453, 30.47767470417627],
    [119.8986053466797, 30.51790671440854],
    [119.8340606689453, 30.59654766421063],
]

# =====================================================================
# 工具函数
# =====================================================================

def fspl(dist, freq_mhz):
    """自由空间路径损耗（作为参考）"""
    dist = max(dist, 1)
    return 20 * math.log10(dist) + 20 * math.log10(freq_mhz) + 27.55

def realistic_path_loss(dist, freq_mhz, source_type='default'):
    """
    真实的路径损耗模型 - 双斜率模型（Two-Ray Model）+ 环境衰减
    在近距离使用自由空间衰减（20log10(d)），远距离使用更强的衰减（35log10(d)）
    这样能更好地模拟真实环境中的信号盲区
    """
    dist = max(dist, 10)  # 最小10米
    d_break = 1000  # 断点距离（米）：1km

    # 基础损耗（自由空间）
    fspl_loss = 20 * math.log10(dist) + 20 * math.log10(freq_mhz) + 27.55

    # 根据信号源类型调整衰减特性
    # 不同类型的环境遮挡程度不同
    type_loss_factor = {
        '5g': 2.5,     # 5G基站：城市环境，遮挡较多
        'radar': 1.8,  # 雷达：开阔地带，遮挡较少但指向性强
        'cors': 2.2,   # CORS站：中等遮挡
        'uav': 1.5     # UAV中继：高空，遮挡最少
    }

    factor = type_loss_factor.get(source_type, 2.0)

    # 双斜率模型
    if dist <= d_break:
        # 近距离：自由空间衰减 + 少量额外衰减
        loss = fspl_loss + factor * 5
    else:
        # 远距离：更强的衰减（35log10(d) vs 20log10(d)）
        # 使用平滑过渡
        extra_loss = 15 * math.log10(dist / d_break)  # 额外的15*log10(d/d_break)衰减
        loss = fspl_loss + factor * (5 + extra_loss)

    # 添加环境噪声底（模拟城市环境的随机衰减）
    # 根据距离添加指数衰减的环境损耗
    env_loss = factor * math.log10(1 + dist / 5000) * 10

    return loss + env_loss

def calc_signal(lon, lat, alt, source_names=None, source_type='all'):
    """计算某点的信号强度
    source_names: None=所有源（综合模式）, list=指定源名称列表（单源模式）
    source_type: 信号源类型（'all', '5g', 'radar', 'cors', 'uav'），用于选择衰减模型
    """
    per_src = {}
    total_mw = 0

    for src in EM_SOURCES:
        # 如果指定了源名称筛选，只计算这些源
        if source_names is not None and src['name'] not in source_names:
            continue

        dx = (lon - src['lon']) * 96000
        dy = (lat - src['lat']) * 111000
        dz = alt - src['alt']
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        # 使用新的真实路径损耗模型
        # 对于单源模式，使用对应类型的衰减特性
        # 对于综合模式，使用各源自己的类型特性
        current_type = source_type if source_type != 'all' else src['type']
        loss = realistic_path_loss(dist, src['freq_mhz'], current_type)

        tx_dbm = 10 * math.log10(src['power_w'] * 1000)
        rx_dbm = tx_dbm - loss

        per_src[src['name']] = round(rx_dbm, 1)
        total_mw += math.pow(10, rx_dbm / 10)

    total_dbm = 10 * math.log10(max(total_mw, 1e-30))
    return {'dbm': round(total_dbm, 1), 'per_src': per_src}

def interference_level(dbm, source_type='all'):
    """
    干扰等级（根据信号源类型使用不同的阈值）
    """
    # 每种类型的阈值配置 [severe, high, medium]
    thresholds = {
        'all': [-90, -100, -108],
        '5g': [-100, -110, -118],
        'radar': [-90, -100, -108],
        'cors': [-100, -110, -118],
        'uav': [-120, -128, -135]
    }

    t = thresholds.get(source_type, [-90, -100, -108])
    severe, high, medium = t[0], t[1], t[2]

    if dbm > severe: return 'SEVERE'
    if dbm > high: return 'HIGH'
    if dbm > medium: return 'MEDIUM'
    return 'LOW'

def bds_grid_code(lon, lat, alt, grid=GRID_SIZE, galt=GALT):
    """北斗格网编码"""
    lon_deg = int(lon)
    lon_grid = int(round((lon - lon_deg) / grid))
    lat_deg = int(lat)
    lat_grid = int(round((lat - lat_deg) / grid))
    alt_layer = int(alt / galt)
    return f'G{lon_deg:03d}{lon_grid:04d}{lat_deg:02d}{lat_grid:04d}H{alt_layer:03d}'

def e_field_mag(dbm):
    """电场强度"""
    rx = max(math.pow(10, dbm/10) * 1e-3, 1e-20)
    return f"{math.sqrt(rx/(4*math.pi)*377):.5f}"

def point_in_polygon(lon, lat, polygon):
    """判断点是否在多边形内（射线法）"""
    x, y = lon, lat
    n = len(polygon)
    inside = False
    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)):
            intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < intersect:
                inside = not inside
    return inside

def gen_layer_points(layer_idx, alt, grid_size=GRID_SIZE, source_names=None, source_type='all'):
    """生成单层网格点
    source_names: None=综合模式, list=指定源名称列表
    source_type: 信号源类型，用于计算不同的干扰等级阈值
    """
    pts = []
    bbox = SIM_BBOX

    n_lon = int((bbox['lon_max'] - bbox['lon_min']) / grid_size)
    n_lat = int((bbox['lat_max'] - bbox['lat_min']) / grid_size)

    for i in range(n_lon):
        lon = bbox['lon_min'] + (i + 0.5) * grid_size
        for j in range(n_lat):
            lat = bbox['lat_min'] + (j + 0.5) * grid_size

            # 只保留多边形内的点
            if not point_in_polygon(lon, lat, POLYGON_COORDS):
                continue

            sig = calc_signal(lon, lat, alt, source_names, source_type)
            dbm = sig['dbm']

            pts.append({
                'lon': round(lon, 6),
                'lat': round(lat, 6),
                'alt_m': alt,
                'signal_dbm': dbm,
                'level': interference_level(dbm, source_type),
                'grid_code': bds_grid_code(lon, lat, alt),
                'per_src': sig['per_src']
            })

    return pts

# =====================================================================
# 主函数
# =====================================================================

def main():
    output_dir = r'C:\mgs\basic\electromagnetic\data'
    os.makedirs(output_dir, exist_ok=True)

    alt_layers = list(range(HEIGHT_MIN, HEIGHT_MAX + 1, GALT))
    print(f'高度层: {len(alt_layers)}层 ({HEIGHT_MIN}m ~ {HEIGHT_MAX}m, 间隔{GALT}m)')

    # 为每种信号源类型生成独立数据
    for source_type, type_info in SOURCE_TYPES.items():
        print(f'\n{"="*50}')
        print(f'生成 {type_info["label"]} 数据...')
        print(f'{"="*50}')

        type_output_dir = os.path.join(output_dir, source_type)
        os.makedirs(type_output_dir, exist_ok=True)

        total_points = 0
        layer_files = []

        for layer_idx, alt in enumerate(alt_layers):
            print(f'  第{layer_idx}层 (高度{alt}m)...', end=' ', flush=True)

            # 使用筛选后的源列表生成数据
            pts = gen_layer_points(layer_idx, alt, source_names=type_info['sources'], source_type=source_type)
            print(f'{len(pts)}点', flush=True)

            if len(pts) == 0:
                continue

            # 保存单层数据
            layer_data = {
                'meta': {
                    'source_type': source_type,
                    'source_label': type_info['label'],
                    'source_names': type_info['sources'],
                    'layer_idx': layer_idx,
                    'alt_m': alt,
                    'grid_size_m': GRID_SIZE * 111000,
                    'galt_m': GALT,
                    'point_count': len(pts),
                    'bbox': SIM_BBOX,
                    'generated_at': datetime.now().isoformat()
                },
                'data': pts
            }

            layer_file = os.path.join(type_output_dir, f'layer_{layer_idx:03d}_alt{alt:04d}m.json')
            with open(layer_file, 'w', encoding='utf-8') as f:
                json.dump(layer_data, f, ensure_ascii=False, indent=2)

            layer_files.append(os.path.basename(layer_file))
            total_points += len(pts)

        # 生成该类型的索引文件
        index_data = {
            'meta': {
                'source_type': source_type,
                'source_label': type_info['label'],
                'source_names': type_info['sources'],
                'total_layers': len(layer_files),
                'total_points': total_points,
                'height_range_m': [HEIGHT_MIN, HEIGHT_MAX],
                'galt_m': GALT,
                'grid_size_deg': GRID_SIZE,
                'grid_size_m': GRID_SIZE * 111000,
                'bbox': SIM_BBOX,
                'polygon': POLYGON_COORDS,
                'source_count': len(type_info['sources']),
                'generated_at': datetime.now().isoformat()
            },
            'layers': [
                {
                    'layer_idx': i,
                    'alt_m': alt,
                    'file': layer_file
                }
                for i, (alt, layer_file) in enumerate(zip(alt_layers[:len(layer_files)], layer_files))
            ],
            'sources': [s for s in EM_SOURCES if s['name'] in type_info['sources']]
        }

        index_file = os.path.join(type_output_dir, 'index.json')
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        print(f'  完成！总层数: {len(layer_files)}, 总格点数: {total_points:,}')
        print(f'  索引文件: {index_file}')

    print(f'\n{"="*50}')
    print('所有信号源类型数据生成完成！')
    print(f'{"="*50}')

if __name__ == '__main__':
    main()
