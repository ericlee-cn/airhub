"""
gen_100uav.py - 自动生成100架无人机任务数据
用于 scene_03_城市核心_百机密集
运行：python gen_100uav.py
"""

import json
import random
import math

random.seed(42)

# 仿真区域：杭州城市核心
CENTER_LON = 120.150
CENTER_LAT = 30.270
SPREAD_LON = 0.08   # 经度范围±
SPREAD_LAT = 0.05   # 纬度范围±

UAV_TYPES = ["delivery", "inspection", "patrol", "emergency", "survey"]
SPEEDS = {"delivery": 12, "inspection": 8, "patrol": 10, "emergency": 18, "survey": 6}

tasks = []
for i in range(1, 101):
    uav_type = random.choice(UAV_TYPES)
    speed = SPEEDS[uav_type] + random.uniform(-2, 2)
    delay = random.uniform(0, 120)
    num_wps = random.randint(3, 6)
    
    # 起点
    s_lon = CENTER_LON + random.uniform(-SPREAD_LON, SPREAD_LON)
    s_lat = CENTER_LAT + random.uniform(-SPREAD_LAT, SPREAD_LAT)
    
    route = []
    lon, lat = s_lon, s_lat
    for _ in range(num_wps):
        alt = random.randint(50, 200)
        route.append([round(lon, 6), round(lat, 6), alt])
        lon += random.uniform(-0.02, 0.02)
        lat += random.uniform(-0.015, 0.015)
        # 边界限制
        lon = max(CENTER_LON - SPREAD_LON, min(CENTER_LON + SPREAD_LON, lon))
        lat = max(CENTER_LAT - SPREAD_LAT, min(CENTER_LAT + SPREAD_LAT, lat))
    
    tasks.append({
        "uav_id": f"UAV_{i:03d}",
        "uav_type": uav_type,
        "speed_m_s": round(speed, 1),
        "h_safe_gap_m": 30,
        "v_safe_gap_m": 20,
        "start_delay_s": round(delay, 1),
        "route": route,
        "route_rule": {
            "allow_alt_change": True,
            "max_climb_rate": 5,
            "max_desc_rate": 5,
            "loop_route": False
        }
    })

output = {"uav_task_list": tasks}
out_path = "uav_batch.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"已生成 {len(tasks)} 架无人机任务 → {out_path}")
