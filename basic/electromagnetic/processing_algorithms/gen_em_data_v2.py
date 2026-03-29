#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北斗立体网格电磁仿真数据生成器 v2
- 读取真实 GeoJSON 干扰源（5G基站、监视雷达、精准导航CORS站）
- 新增 3 个无人机中继站（虚拟）
- 输出：按高度层分片 JSON，存放于 data/ 目录
"""

import json
import math
import random
import os

random.seed(42)

BASE_DIR = r"C:\mgs\basic\electromagnetic"
OUT_DIR  = os.path.join(BASE_DIR, "data")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 1. 仿真范围
# ============================================================
lon_min, lon_max = 119.7846, 120.2179
lat_min, lat_max = 30.3995, 30.6592

# ============================================================
# 2. 北斗立体网格参数（~80m精度）
# ============================================================
GRID_LON = 0.0008   # ~86m
GRID_LAT = 0.0008   # ~88m
GRID_ALT = 80       # 80m

# ============================================================
# 3. 北斗立体网格编码 / 解码
# ============================================================
def bds_grid_code(lon, lat, alt):
    lon_deg  = int(lon)
    lon_grid = int(round((lon - lon_deg) / GRID_LON))
    lat_deg  = int(lat)
    lat_grid = int(round((lat - lat_deg) / GRID_LAT))
    alt_layer = int(alt / GRID_ALT)
    return f"G{lon_deg:03d}{lon_grid:04d}{lat_deg:02d}{lat_grid:04d}H{alt_layer:03d}"

# ============================================================
# 4. 读取 GeoJSON 干扰源
# ============================================================
def load_geojson_sources(filepath, source_type, power_w, freq_mhz, alt_m=30):
    """从 GeoJSON 点文件读取电磁源列表"""
    with open(filepath, encoding="utf-8") as f:
        gj = json.load(f)
    sources = []
    for feat in gj["features"]:
        coords = feat["geometry"]["coordinates"]
        name   = feat["properties"].get("name", source_type)
        sources.append({
            "name":      name,
            "lon":       coords[0],
            "lat":       coords[1],
            "alt":       alt_m,
            "power_w":   power_w,
            "freq_mhz":  freq_mhz,
            "type":      source_type,
        })
    return sources

# 加载三类真实干扰源
sources_5g   = load_geojson_sources(
    os.path.join(BASE_DIR, "5G基站.geojson"),
    source_type="5G_BS", power_w=50, freq_mhz=3500.0, alt_m=30)

sources_radar = load_geojson_sources(
    os.path.join(BASE_DIR, "监视雷达.geojson"),
    source_type="RADAR", power_w=2000, freq_mhz=3000.0, alt_m=30)

sources_cors  = load_geojson_sources(
    os.path.join(BASE_DIR, "精准导航CORS站.geojson"),
    source_type="CORS_GNSS", power_w=10, freq_mhz=1575.42, alt_m=10)

# 新增 3 个无人机中继站（均匀分布在仿真区域，飞行高度 200~500m）
UAV_RELAYS = [
    {
        "name":     "UAV中继-1",
        "lon":      119.9200, "lat": 30.5400, "alt": 280,
        "power_w":  5, "freq_mhz": 2400.0, "type": "UAV_RELAY",
    },
    {
        "name":     "UAV中继-2",
        "lon":      120.0600, "lat": 30.5200, "alt": 350,
        "power_w":  5, "freq_mhz": 2400.0, "type": "UAV_RELAY",
    },
    {
        "name":     "UAV中继-3",
        "lon":      119.9900, "lat": 30.4600, "alt": 420,
        "power_w":  5, "freq_mhz": 2400.0, "type": "UAV_RELAY",
    },
]

ALL_SOURCES = sources_5g + sources_radar + sources_cors + UAV_RELAYS

print(f"干扰源总数: {len(ALL_SOURCES)}")
for s in ALL_SOURCES:
    print(f"  [{s['type']:12s}] {s['name']:12s}  ({s['lon']:.4f}, {s['lat']:.4f}, {s['alt']}m)  {s['power_w']}W  {s['freq_mhz']}MHz")

# ============================================================
# 5. 电磁场仿真模型
# ============================================================
def fspl_db(dist_m, freq_mhz):
    """自由空间路径损耗 (dB)"""
    dist_m = max(dist_m, 1.0)
    return 20 * math.log10(dist_m) + 20 * math.log10(freq_mhz) + 27.55

def calc_total_signal(lon, lat, alt):
    """叠加所有源，返回总功率(dBm)及各源贡献(dBm)"""
    total_mw = 0.0
    per_src   = {}
    for src in ALL_SOURCES:
        dx   = (lon - src["lon"]) * 96000
        dy   = (lat - src["lat"]) * 111000
        dz   = alt - src["alt"]
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        loss = fspl_db(dist, src["freq_mhz"])
        tx_dbm = 10 * math.log10(src["power_w"] * 1000)
        rx_dbm = tx_dbm - loss
        total_mw += 10 ** (rx_dbm / 10)
        per_src[src["name"]] = round(rx_dbm, 1)
    total_dbm = 10 * math.log10(max(total_mw, 1e-30))
    noise     = random.gauss(0, 1.5)
    return round(total_dbm + noise, 2), per_src

def calc_e_field(signal_dbm):
    """由信号强度估算电场矢量 (V/m)"""
    rx_w   = max((10 ** (signal_dbm / 10)) * 1e-3, 1e-20)
    s_wm2  = rx_w / (4 * math.pi)
    e_mag  = math.sqrt(s_wm2 * 377)
    theta  = random.uniform(0, 2 * math.pi)
    phi    = random.uniform(0, math.pi)
    ex = round(e_mag * math.sin(phi) * math.cos(theta), 5)
    ey = round(e_mag * math.sin(phi) * math.sin(theta), 5)
    ez = round(e_mag * math.cos(phi), 5)
    return ex, ey, ez, round(e_mag, 5)

def interference_level(dbm):
    if dbm > -50:  return "SEVERE"
    if dbm > -70:  return "HIGH"
    if dbm > -90:  return "MEDIUM"
    return "LOW"

def signal_quality(dbm):
    if dbm > -125: return "EXCELLENT"
    if dbm > -135: return "GOOD"
    if dbm > -145: return "FAIR"
    return "POOR"

# ============================================================
# 6. 生成数据（抽样 step=8，水平间距约 640m）
# ============================================================
n_lon  = int((lon_max - lon_min) / GRID_LON)
n_lat  = int((lat_max - lat_min) / GRID_LAT)
ALTS   = list(range(1, 1001, GRID_ALT))   # 13 层
STEP   = 8

print(f"\n全量网格: {n_lon}×{n_lat}×{len(ALTS)} = {n_lon*n_lat*len(ALTS):,}")

# --- 按高度层分片输出 ---
total_count = 0
layer_summary = []

for layer_idx, alt in enumerate(ALTS):
    records = []
    for i_lon in range(0, n_lon, STEP):
        lon_c = lon_min + (i_lon + 0.5) * GRID_LON
        for i_lat in range(0, n_lat, STEP):
            lat_c = lat_min + (i_lat + 0.5) * GRID_LAT
            code  = bds_grid_code(lon_c, lat_c, alt)
            sig, per_src = calc_total_signal(lon_c, lat_c, alt)
            ex, ey, ez, e_mag = calc_e_field(sig)

            records.append({
                "grid_code": code,
                "center": {
                    "lon":   round(lon_c, 6),
                    "lat":   round(lat_c, 6),
                    "alt_m": alt,
                },
                "grid_meta": {
                    "lon_grid_idx": i_lon,
                    "lat_grid_idx": i_lat,
                    "alt_layer":    layer_idx,
                    "cell_size_m":  GRID_ALT,
                },
                "em_field": {
                    "total_signal_dbm":   sig,
                    "e_field_v_per_m": {
                        "ex": ex, "ey": ey, "ez": ez,
                        "magnitude": e_mag,
                        "unit": "V/m",
                    },
                    "interference_level": interference_level(sig),
                    "signal_quality":     signal_quality(sig),
                    "per_source_dbm":     per_src,
                },
                "dominant_freq_mhz": 1575.42,
                "timestamp":         "2026-03-22T09:49:00+08:00",
            })

    total_count += len(records)
    signals = [r["em_field"]["total_signal_dbm"] for r in records]
    levels  = {}
    for r in records:
        lv = r["em_field"]["interference_level"]
        levels[lv] = levels.get(lv, 0) + 1

    out = {
        "meta": {
            "title":           f"电磁仿真立体网格数据 - 高度层 {layer_idx}（{alt}m）",
            "crs":             "EPSG:4490 (BDS2000)",
            "grid_encoding":   "BDS_Grid_Code_3D",
            "alt_m":           alt,
            "alt_layer":       layer_idx,
            "grid_size_m":     GRID_ALT,
            "grid_size_lon_deg": GRID_LON,
            "grid_size_lat_deg": GRID_LAT,
            "grid_size_alt_m": GRID_ALT,
            "bbox": {
                "lon_min": lon_min, "lon_max": lon_max,
                "lat_min": lat_min, "lat_max": lat_max,
            },
            "record_count":    len(records),
            "signal_min_dbm":  round(min(signals), 2),
            "signal_max_dbm":  round(max(signals), 2),
            "signal_mean_dbm": round(sum(signals)/len(signals), 2),
            "interference_distribution": levels,
            "em_sources": ALL_SOURCES,
            "generated_at":    "2026-03-22T09:49:00+08:00",
        },
        "data": records,
    }

    fname = f"em_layer_{layer_idx:02d}_alt{alt:04d}m.json"
    fpath = os.path.join(OUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    layer_summary.append({
        "file":   fname,
        "alt_m":  alt,
        "count":  len(records),
        "sig_min": round(min(signals), 2),
        "sig_max": round(max(signals), 2),
        "levels": levels,
    })
    print(f"  层{layer_idx:2d} alt={alt:4d}m  {len(records):5d}条  "
          f"sig[{min(signals):.1f}~{max(signals):.1f}]dBm  "
          f"{levels}")

# ============================================================
# 7. 输出汇总索引文件
# ============================================================
index = {
    "meta": {
        "title":        "电磁仿真立体网格数据索引",
        "crs":          "EPSG:4490 (BDS2000)",
        "grid_encoding":"BDS_Grid_Code_3D",
        "grid_size_m":  GRID_ALT,
        "bbox": {
            "lon_min": lon_min, "lon_max": lon_max,
            "lat_min": lat_min, "lat_max": lat_max,
            "alt_min_m": 1, "alt_max_m": 1000,
        },
        "total_records":    total_count,
        "layer_count":      len(ALTS),
        "sample_step":      STEP,
        "full_grid_count":  n_lon * n_lat * len(ALTS),
        "em_sources":       ALL_SOURCES,
        "generated_at":     "2026-03-22T09:49:00+08:00",
    },
    "layers": layer_summary,
}
idx_path = os.path.join(OUT_DIR, "em_index.json")
with open(idx_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\n总记录数: {total_count:,}")
print(f"索引文件: {idx_path}")
print(f"输出目录: {OUT_DIR}")
print("\n=== 完成 ===")
