"""
空域检测器 - AirFogSim
支持：circle圆形 / polygon多边形 / global全局
对接规范：AirFogSim 标准版数据规范 v1.0
"""

import math
from typing import Optional, Tuple


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """计算两点球面距离(m)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(lon: float, lat: float, points: list) -> bool:
    """射线法判断点是否在多边形内"""
    n = len(points)
    inside = False
    x, y = lon, lat
    j = n - 1
    for i in range(n):
        xi, yi = points[i][0], points[i][1]
        xj, yj = points[j][0], points[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def check_in_airspace(lon: float, lat: float, alt: float, area: dict) -> bool:
    """
    判断坐标是否在空域内
    :param lon: 经度
    :param lat: 纬度
    :param alt: 高度(m)
    :param area: 空域字典
    :return: True=在空域内
    """
    # 高度范围检查
    min_alt = area.get("min_alt", 0)
    max_alt = area.get("max_alt", 9999)
    if not (min_alt <= alt <= max_alt):
        return False

    geo_shape = area.get("geo_shape", "")

    if geo_shape == "circle":
        c_lon = area["center_lon"]
        c_lat = area["center_lat"]
        radius = area["radius_m"]
        dist = _haversine_m(lon, lat, c_lon, c_lat)
        return dist <= radius

    elif geo_shape == "polygon":
        points = area["points"]
        return _point_in_polygon(lon, lat, points)

    elif geo_shape == "global":
        return True

    return False


def check_time_valid(sim_time_s: float, area: dict) -> bool:
    """
    判断空域在当前仿真时刻是否生效
    :param sim_time_s: 当前仿真时间(s)
    :param area: 空域字典
    :return: True=当前时刻生效
    """
    time_mode = area.get("time_mode", "always")

    if time_mode == "always":
        return True

    if time_mode == "period":
        start = area.get("start_time_s", 0)
        end = area.get("end_time_s", 99999)
        return start <= sim_time_s <= end

    if time_mode == "daily":
        start = area.get("start_time_s", 0)
        end = area.get("end_time_s", 86400)
        daily_t = sim_time_s % 86400
        return start <= daily_t <= end

    return True


def get_violated_areas(lon: float, lat: float, alt: float,
                       sim_time_s: float, airspace_list: list) -> list:
    """
    获取无人机当前违规的所有空域列表
    :return: 违规空域列表（按优先级排序）
    """
    violated = []
    for area in airspace_list:
        if not check_time_valid(sim_time_s, area):
            continue
        if check_in_airspace(lon, lat, alt, area):
            violated.append(area)
    # 按优先级排序（数字小=优先级高）
    violated.sort(key=lambda a: a.get("priority", 9))
    return violated
