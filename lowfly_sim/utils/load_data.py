"""
数据加载工具 - AirFogSim
统一加载：全局配置 + 想定覆盖 + 各类数据文件
"""

import json
import csv
from pathlib import Path
from typing import Optional


_BASE_DIR = Path(__file__).parent.parent


def load_global_config() -> dict:
    """加载全局推演配置"""
    cfg_path = _BASE_DIR / "config_global" / "sim_global.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}


def load_scene_config(scene_path: str) -> dict:
    """
    加载想定配置（全局 + 想定覆盖合并）
    优先级：scene_override > config_global
    """
    global_cfg = load_global_config()
    override_path = Path(scene_path) / "scene_override.json"
    if override_path.exists():
        override = json.loads(override_path.read_text(encoding="utf-8"))
        global_cfg.update(override)
    return global_cfg


def load_airspace(scene_path: str) -> list:
    """加载想定全部空域（合并三个文件）"""
    airspace_list = []
    scene = Path(scene_path)
    for fname in ["no_fly.json", "limit_height.json", "temp_control.json"]:
        fpath = scene / "airspace" / fname
        if fpath.exists():
            data = json.loads(fpath.read_text(encoding="utf-8"))
            airspace_list.extend(data.get("airspace_list", []))
    return airspace_list


def load_environment(scene_path: str) -> list:
    """加载气象环境数据"""
    env_path = Path(scene_path) / "environment" / "weather_env.json"
    if env_path.exists():
        data = json.loads(env_path.read_text(encoding="utf-8"))
        return data.get("env_list", [])
    return []


def load_uav_tasks(scene_path: str) -> list:
    """加载机群任务（JSON格式）"""
    uav_path = Path(scene_path) / "mission" / "uav_batch.json"
    if uav_path.exists():
        data = json.loads(uav_path.read_text(encoding="utf-8"))
        return data.get("uav_task_list", [])
    return []


def load_route_lib(scene_path: str) -> dict:
    """加载航线库（CSV格式）→ {route_id: [[lon,lat,alt],...]}"""
    route_path = Path(scene_path) / "mission" / "route_lib.csv"
    routes = {}
    if not route_path.exists():
        return routes
    with open(route_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["route_id"]
            lon = float(row["lon"])
            lat = float(row["lat"])
            alt = float(row["alt"])
            if rid not in routes:
                routes[rid] = []
            routes[rid].append([lon, lat, alt])
    return routes


def load_full_scene(scene_path: str) -> dict:
    """一次性加载想定全部数据"""
    return {
        "config": load_scene_config(scene_path),
        "airspace": load_airspace(scene_path),
        "environment": load_environment(scene_path),
        "uav_tasks": load_uav_tasks(scene_path),
        "route_lib": load_route_lib(scene_path),
    }


def list_scenes(base_dir: Optional[str] = None) -> list:
    """列出所有可用想定"""
    scenes_dir = Path(base_dir) if base_dir else _BASE_DIR / "scenes"
    if not scenes_dir.exists():
        return []
    result = []
    for d in sorted(scenes_dir.iterdir()):
        if d.is_dir() and d.name.startswith("scene_"):
            uav_count = 0
            uav_path = d / "mission" / "uav_batch.json"
            if uav_path.exists():
                try:
                    data = json.loads(uav_path.read_text(encoding="utf-8"))
                    uav_count = len(data.get("uav_task_list", []))
                except Exception:
                    pass
            result.append({
                "name": d.name,
                "path": str(d),
                "uav_count": uav_count,
            })
    return result
