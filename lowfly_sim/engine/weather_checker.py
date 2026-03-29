"""
气象环境检测器 - AirFogSim
支持：wind大风 / rain降雨 / fog大雾 / thunder雷雨
复用空域几何解析，一套代码
"""

from engine.airspace_checker import check_in_airspace, check_time_valid


def check_weather_affect(lon: float, lat: float, alt: float,
                         sim_time_s: float, env_list: list,
                         thresholds: dict) -> dict:
    """
    检查无人机当前位置的气象影响
    :return: {
        "forbid_fly": bool,
        "alarm_types": [str],
        "env_ids": [str],
        "max_level": int
    }
    """
    result = {
        "forbid_fly": False,
        "alarm_types": [],
        "env_ids": [],
        "max_level": 0
    }

    wind_max = thresholds.get("weather_threshold", {}).get("wind_speed_max_ms", 15)
    rain_limit = thresholds.get("weather_threshold", {}).get("rain_level_limit", 3)
    fog_vis = thresholds.get("weather_threshold", {}).get("fog_visibility_m", 800)
    thunder_forbid = thresholds.get("weather_threshold", {}).get("thunder_forbid", True)

    for env in env_list:
        if not check_time_valid(sim_time_s, env):
            continue

        # 复用空域几何检测
        area_fake = {
            "geo_shape": env.get("geo_shape", "global"),
            "min_alt": env.get("min_alt", 0),
            "max_alt": env.get("max_alt", 9999),
        }
        # 复制几何字段
        for k in ["center_lon", "center_lat", "radius_m", "points"]:
            if k in env:
                area_fake[k] = env[k]

        if not check_in_airspace(lon, lat, alt, area_fake):
            continue

        env_type = env.get("env_type", "")
        level = env.get("level", 1)
        forbid = env.get("forbid_fly", False)

        # 阈值判断
        if env_type == "wind":
            wind_speed = env.get("wind_speed_ms", 0)
            if wind_speed > wind_max:
                forbid = True
        elif env_type == "rain":
            if level >= rain_limit:
                forbid = True
        elif env_type == "fog":
            visibility = env.get("visibility_m", 9999)
            if visibility < fog_vis:
                forbid = True
        elif env_type == "thunder":
            if thunder_forbid:
                forbid = True

        result["env_ids"].append(env.get("env_id", ""))
        result["alarm_types"].append(env_type)
        result["max_level"] = max(result["max_level"], level)
        if forbid:
            result["forbid_fly"] = True

    return result
