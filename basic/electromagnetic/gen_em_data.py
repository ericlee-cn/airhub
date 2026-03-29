#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北斗立体网格电磁仿真数据生成器
范围：119.78~120.22°E，30.40~30.66°N，高度1~1000m
空间尺度：80m
"""

import json
import math
import random

random.seed(42)

# ============================================================
# 1. 仿真范围
# ============================================================
lon_min, lon_max = 119.7846, 120.2179
lat_min, lat_max = 30.3995, 30.6592

# ============================================================
# 2. 北斗立体网格参数（~80m精度）
# ============================================================
# 纬度30°处：1°经度 ≈ 96.0km → 80m ≈ 0.000833°
# 1°纬度 ≈ 111.0km → 80m ≈ 0.000720°
# 统一使用 0.0008°（约86m/88m）
GRID_LON = 0.0008   # 经度步长（~86m）
GRID_LAT = 0.0008   # 纬度步长（~88m）
GRID_ALT = 80       # 高度步长（80m）

# ============================================================
# 3. 北斗网格编码（参考BDS Grid Code规范）
# ============================================================
# 编码结构：G{经度整度:03d}{经度格号:04d}{纬度整度:02d}{纬度格号:04d}H{高度层:03d}
# 示例：G119{0623}30{3245}H002 → 119.XXX°E, 30.XXX°N, H=160m

def bds_grid_code(lon, lat, alt):
    """生成北斗立体网格编码"""
    lon_deg = int(lon)
    lon_frac = lon - lon_deg
    lon_grid = int(round(lon_frac / GRID_LON))

    lat_deg = int(lat)
    lat_frac = lat - lat_deg
    lat_grid = int(round(lat_frac / GRID_LAT))

    alt_layer = int(alt / GRID_ALT)

    return f"G{lon_deg:03d}{lon_grid:04d}{lat_deg:02d}{lat_grid:04d}H{alt_layer:03d}"


def decode_bds_grid_code(code):
    """解码北斗立体网格编码 → 中心点坐标"""
    lon_deg  = int(code[1:4])
    lon_grid = int(code[4:8])
    lat_deg  = int(code[8:10])
    lat_grid = int(code[10:14])
    alt_layer = int(code[15:18])

    lon = lon_deg + (lon_grid + 0.5) * GRID_LON
    lat = lat_deg + (lat_grid + 0.5) * GRID_LAT
    alt = alt_layer * GRID_ALT + GRID_ALT / 2
    return round(lon, 6), round(lat, 6), round(alt, 1)


# ============================================================
# 4. 电磁场仿真模型
# ============================================================
# 模拟多个电磁辐射源（地面 + 空中）
EM_SOURCES = [
    # 名称, 经度, 纬度, 高度(m), 发射功率(W), 频率(MHz), 类型
    {"name": "基站A",     "lon": 119.920, "lat": 30.530, "alt": 30,  "power_w": 50,   "freq_mhz": 900.0,   "type": "BS_5G"},
    {"name": "基站B",     "lon": 120.050, "lat": 30.480, "alt": 30,  "power_w": 50,   "freq_mhz": 1800.0,  "type": "BS_4G"},
    {"name": "北斗地站",  "lon": 119.850, "lat": 30.610, "alt": 10,  "power_w": 100,  "freq_mhz": 1575.42, "type": "GNSS"},
    {"name": "雷达站",    "lon": 120.120, "lat": 30.560, "alt": 80,  "power_w": 2000, "freq_mhz": 3000.0,  "type": "RADAR"},
    {"name": "无人机信号中继", "lon": 119.990, "lat": 30.510, "alt": 300, "power_w": 5, "freq_mhz": 2450.0, "type": "UAV_RELAY"},
]

def free_space_path_loss(dist_m, freq_mhz):
    """自由空间路径损耗（dB）"""
    if dist_m < 1:
        dist_m = 1
    fspl = 20 * math.log10(dist_m) + 20 * math.log10(freq_mhz) + 27.55
    return fspl

def calc_received_power_dbm(lon, lat, alt):
    """计算各源叠加后的接收功率（dBm）"""
    total_mw = 0.0
    per_source = {}
    for src in EM_SOURCES:
        dx = (lon - src["lon"]) * 96000   # ~96km/° at lat30
        dy = (lat - src["lat"]) * 111000  # ~111km/°
        dz = alt - src["alt"]
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        fspl = free_space_path_loss(dist, src["freq_mhz"])
        tx_dbm = 10 * math.log10(src["power_w"] * 1000)  # W→mW→dBm
        rx_dbm = tx_dbm - fspl
        rx_mw = 10 ** (rx_dbm / 10)
        total_mw += rx_mw
        per_source[src["name"]] = round(rx_dbm, 1)
    total_dbm = 10 * math.log10(max(total_mw, 1e-30))
    return round(total_dbm + random.gauss(0, 1.5), 2), per_source

def calc_e_field(signal_dbm, freq_mhz):
    """由功率密度估算电场强度矢量 (V/m)"""
    # 功率密度 S = P/A，E = sqrt(S * 377)
    rx_w_per_m2 = (10 ** (signal_dbm / 10)) * 1e-3 / (4 * math.pi)
    rx_w_per_m2 = max(rx_w_per_m2, 1e-20)
    e_mag = math.sqrt(rx_w_per_m2 * 377)
    # 添加方向分量（随机极化）
    theta = random.uniform(0, 2 * math.pi)
    phi   = random.uniform(0, math.pi)
    ex = round(e_mag * math.sin(phi) * math.cos(theta), 4)
    ey = round(e_mag * math.sin(phi) * math.sin(theta), 4)
    ez = round(e_mag * math.cos(phi), 4)
    e_total = round(e_mag, 4)
    return ex, ey, ez, e_total

def interference_level(signal_dbm):
    """根据信号强度判断干扰等级"""
    if signal_dbm > -50:
        return "SEVERE"    # 严重干扰
    elif signal_dbm > -70:
        return "HIGH"      # 高干扰
    elif signal_dbm > -90:
        return "MEDIUM"    # 中等
    else:
        return "LOW"       # 低/正常

def signal_quality(signal_dbm):
    """信号质量评估（针对北斗导航）"""
    if signal_dbm > -130:
        return "EXCELLENT"
    elif signal_dbm > -140:
        return "GOOD"
    elif signal_dbm > -150:
        return "FAIR"
    else:
        return "POOR"


# ============================================================
# 5. 生成数据
# ============================================================
n_lon_grids = int((lon_max - lon_min) / GRID_LON)
n_lat_grids = int((lat_max - lat_min) / GRID_LAT)
alt_layers = list(range(1, 1001, GRID_ALT))  # 1, 81, 161, ..., 961  → 13层

print(f"网格规模: 经度 {n_lon_grids} 格 × 纬度 {n_lat_grids} 格 × 高度 {len(alt_layers)} 层")
print(f"总网格数: {n_lon_grids * n_lat_grids * len(alt_layers):,}")

# 抽样策略：水平方向每 SAMPLE_STEP 格取一个，垂直方向全取
SAMPLE_STEP = 8  # ~640m间距，生成约 67×40×13 ≈ 3.5万条

records = []
for i_lon in range(0, n_lon_grids, SAMPLE_STEP):
    lon_c = lon_min + (i_lon + 0.5) * GRID_LON
    for i_lat in range(0, n_lat_grids, SAMPLE_STEP):
        lat_c = lat_min + (i_lat + 0.5) * GRID_LAT
        for alt in alt_layers:
            code = bds_grid_code(lon_c, lat_c, alt)
            sig, per_src = calc_received_power_dbm(lon_c, lat_c, alt)
            ex, ey, ez, e_total = calc_e_field(sig, 1575.42)

            rec = {
                "grid_code":    code,                            # 北斗网格编码
                "center": {
                    "lon": round(lon_c, 6),
                    "lat": round(lat_c, 6),
                    "alt_m": alt
                },
                "grid_meta": {
                    "lon_grid_idx": i_lon,
                    "lat_grid_idx": i_lat,
                    "alt_layer": int(alt / GRID_ALT),
                    "cell_size_m": GRID_ALT                      # 标称80m
                },
                "em_field": {
                    "total_signal_dbm": sig,                     # 叠加信号强度
                    "e_field_v_per_m": {
                        "ex": ex, "ey": ey, "ez": ez,
                        "magnitude": e_total
                    },
                    "interference_level": interference_level(sig),
                    "signal_quality": signal_quality(sig),
                    "per_source_dbm": per_src                    # 各源贡献
                },
                "dominant_freq_mhz": 1575.42,                   # 北斗L1
                "timestamp": "2026-03-22T09:41:00+08:00"
            }
            records.append(rec)

print(f"实际生成记录数: {len(records):,}")

# ============================================================
# 6. 输出 JSON
# ============================================================
output = {
    "meta": {
        "title": "电磁仿真立体网格数据",
        "crs": "EPSG:4490 (BDS2000)",
        "grid_encoding": "BDS_Grid_Code_3D",
        "grid_size_m": GRID_ALT,
        "grid_size_lon_deg": GRID_LON,
        "grid_size_lat_deg": GRID_LAT,
        "grid_size_alt_m": GRID_ALT,
        "bbox": {
            "lon_min": lon_min, "lon_max": lon_max,
            "lat_min": lat_min, "lat_max": lat_max,
            "alt_min_m": 1, "alt_max_m": 1000
        },
        "full_grid_count": n_lon_grids * n_lat_grids * len(alt_layers),
        "sample_count": len(records),
        "sample_step": SAMPLE_STEP,
        "em_sources": EM_SOURCES,
        "generated_at": "2026-03-22T09:41:00+08:00"
    },
    "data": records
}

out_path = r"C:\mgs\basic\electromagnetic\em_sim_bds_grid.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"已写入: {out_path}")
print("\n=== 前3条记录预览 ===")
for r in records[:3]:
    print(json.dumps(r, ensure_ascii=False, indent=2))
