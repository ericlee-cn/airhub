"""
将 航线信息表_含CZML.json 转换为航路编辑系统标准 GeoJSON 格式
输出到 C:/mgs/basic/routes/data/routes_autosave.geojson

保留所有原始属性，并映射到编辑器字段结构：
  航路编号  → properties.id / properties.route_code
  航路类型  → properties.type  (A/B/C/D → airway/airway/uav/uav)
  航路级别  → properties.grade (Ⅰ→I  Ⅱ→II  Ⅲ→III)
  半宽(m)   → properties.width_m  (半宽×2 = 全宽)
  半高(m)   → properties.height_m
  CZML坐标  → geometry.coordinates [[lon,lat,alt],...]
"""

import json, re, math, os, sys
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────
SRC  = Path(__file__).parent / "航线信息表_含CZML.json"
DEST = Path("C:/mgs/basic/routes/data/routes_autosave.geojson")
DEST.parent.mkdir(parents=True, exist_ok=True)

# ── 级别映射 ──────────────────────────────────────────
LEVEL_MAP = {
    "Ⅰ": "I",  "Ⅱ": "II",  "Ⅲ": "III",
    "I": "I",   "II": "II",  "III": "III",
    "1": "I",   "2": "II",   "3": "III",
}

# 编辑器 grade 的默认高度范围（和 route_editor_olcesium.html 保持一致）
GRADE_ALT = {
    "I":   {"altMin": 8400,  "altMax": 12500, "width": 20000},
    "II":  {"altMin": 3000,  "altMax": 6000,  "width": 10000},
    "III": {"altMin": 500,   "altMax": 2000,  "width": 4000},
}

def parse_czml_positions(czml_str):
    """
    解析 CZML 字符串中的坐标，支持两种格式：
      格式A（特殊）: [[lon,lat], alt, [lon,lat], alt, ...]
      格式B（标准）: [lon, lat, alt, lon, lat, alt, ...]
    返回 [[lon,lat,alt], ...] 列表
    """
    try:
        czml = json.loads(czml_str)
    except Exception as e:
        return None, f"JSON解析失败: {e}"

    corridor = czml.get("corridor", {})
    pos_obj  = corridor.get("positions", {})
    raw      = pos_obj.get("cartographicDegrees", [])

    coords = []

    # 判断格式：如果第一个元素是 list，则为格式A
    if raw and isinstance(raw[0], list):
        idx = 0
        while idx < len(raw):
            if isinstance(raw[idx], list) and len(raw[idx]) == 2:
                lon, lat = raw[idx]
                idx += 1
                alt = raw[idx] if idx < len(raw) and isinstance(raw[idx], (int, float)) else 70
                coords.append([lon, lat, float(alt)])
            idx += 1
    else:
        # 格式B：平铺的 lon lat alt lon lat alt ...
        for i in range(0, len(raw) - 2, 3):
            lon, lat, alt = raw[i], raw[i+1], raw[i+2]
            coords.append([float(lon), float(lat), float(alt)])

    return coords, None

def normalize_level(raw):
    raw = str(raw).strip().replace("级", "")
    return LEVEL_MAP.get(raw, "III")

def calc_length_m(coords):
    """简单球面距离估算（米）"""
    total = 0.0
    R = 6371000
    for i in range(1, len(coords)):
        lo1, la1 = math.radians(coords[i-1][0]), math.radians(coords[i-1][1])
        lo2, la2 = math.radians(coords[i][0]),   math.radians(coords[i][1])
        dlat, dlon = la2-la1, lo2-lo1
        a = math.sin(dlat/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
        total += R * 2 * math.asin(math.sqrt(a))
    return round(total, 1)

# ── 主转换 ────────────────────────────────────────────
with open(SRC, encoding="utf-8") as f:
    raw_routes = json.load(f)

features = []
skip_cnt = 0

for r in raw_routes:
    code  = r.get("航路编号", "")
    czml_str = r.get("CZML")
    if not czml_str:
        skip_cnt += 1
        continue

    coords, err = parse_czml_positions(czml_str)
    if err or not coords or len(coords) < 2:
        print(f"  跳过 {code}: {err or '坐标不足'}")
        skip_cnt += 1
        continue

    grade_raw  = r.get("航路级别", "Ⅲ")
    grade      = normalize_level(grade_raw)
    grade_info = GRADE_ALT[grade]

    half_width  = float(r.get("半宽(m)", 30))
    half_height = float(r.get("半高(m)", 20))
    full_width  = half_width * 2

    # 从坐标中取高度中值作为飞行高度参考
    alts   = [c[2] for c in coords if c[2] > 0]
    avg_alt = sum(alts) / len(alts) if alts else grade_info["altMin"]
    alt_min = max(0, avg_alt - half_height)
    alt_max = avg_alt + half_height

    length_m = calc_length_m(coords)

    feature = {
        "type": "Feature",
        "properties": {
            # ── 编辑器标准字段 ──
            "id":        code,
            "name":      r.get("航路名称") or code,
            "type":      "airway",
            "grade":     grade,
            "width_m":   full_width,
            "height_m":  half_height * 2,
            "alt_min":   round(alt_min, 1),
            "alt_max":   round(alt_max, 1),
            "length_m":  length_m,
            "created":   "2026-03-24T00:00:00Z",
            "modified":  "2026-03-24T00:00:00Z",
            # ── 原始属性（完整保留）──
            "route_code":   code,
            "route_type":   r.get("航路类型", "A"),
            "route_level":  grade_raw,
            "half_width_m": half_width,
            "half_height_m":half_height,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        }
    }
    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "metadata": {
        "source": "航线信息表_含CZML.json",
        "converted": "2026-03-24",
        "total": len(features),
        "skipped": skip_cnt
    },
    "features": features
}

with open(DEST, "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f"\n✓ 转换完成: {len(features)} 条航路 → {DEST}")
print(f"  跳过: {skip_cnt} 条（无坐标/解析失败）")

# 统计各等级数量
from collections import Counter
grade_cnt = Counter(feat["properties"]["grade"] for feat in features)
for g, n in sorted(grade_cnt.items()):
    print(f"  grade {g}: {n} 条")
