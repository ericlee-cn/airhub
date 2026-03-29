"""
AirFogSim 推演核心引擎
- 加载想定数据
- 逐帧推进
- 空域/气象/冲突 联合检测
- WebSocket 实时推流
- CSV 日志输出
"""

import json
import os
import time
import asyncio
import csv
from pathlib import Path
from engine.uav_model import UAVState, check_conflict
from engine.airspace_checker import get_violated_areas
from engine.weather_checker import check_weather_affect
from utils.load_data import load_scene_config


class SimEngine:
    def __init__(self, scene_path: str):
        self.scene_path = Path(scene_path)
        self.config = load_scene_config(scene_path)
        self.sim_time = 0.0
        self.step = self.config["sim_step_s"]
        self.max_time = self.config["max_sim_time_s"]
        self.uavs: list[UAVState] = []
        self.airspace_list = []
        self.env_list = []
        self.safety_cfg = {}
        self.alarm_counter = 0
        self.frame_counter = 0
        self._running = False
        self._ws_clients = set()
        self._frame_records = []
        self._alarm_records = []
        self.speed = 1.0  # 推演倍速（1=实时, 2=2倍速, ...）
        self._paused = False  # 暂停标志
        # 告警去重：记录每架 UAV 上一帧的告警原因
        # key=uav_id, value=alarm_type str（空字符串表示无告警）
        self._alarm_active: dict[str, str] = {}

    def load(self):
        """加载想定全部数据"""
        # 加载空域
        self.airspace_list = []
        for fname in ["no_fly.json", "limit_height.json", "temp_control.json"]:
            fpath = self.scene_path / "airspace" / fname
            if fpath.exists():
                data = json.loads(fpath.read_text(encoding="utf-8"))
                self.airspace_list.extend(data.get("airspace_list", []))

        # 加载气象
        env_path = self.scene_path / "environment" / "weather_env.json"
        if env_path.exists():
            data = json.loads(env_path.read_text(encoding="utf-8"))
            self.env_list = data.get("env_list", [])

        # 加载安全配置
        base_safety_path = Path(__file__).parent.parent / "config_global" / "safety_base.json"
        if base_safety_path.exists():
            self.safety_cfg = json.loads(base_safety_path.read_text(encoding="utf-8"))
        # 想定覆盖
        override_path = self.scene_path / "scene_override.json"
        if override_path.exists():
            override = json.loads(override_path.read_text(encoding="utf-8"))
            if "weather_threshold" in override:
                self.safety_cfg["weather_threshold"] = {
                    **self.safety_cfg.get("weather_threshold", {}),
                    **override["weather_threshold"]
                }

        # 加载机群任务
        uav_path = self.scene_path / "mission" / "uav_batch.json"
        if uav_path.exists():
            data = json.loads(uav_path.read_text(encoding="utf-8"))
            for task in data.get("uav_task_list", []):
                self.uavs.append(UAVState(task))

        h_gap = self.config.get("horizontal_gap_m", 50)
        v_gap = self.config.get("vertical_gap_m", 30)
        print(f"[Engine] 加载完成: {len(self.uavs)}架UAV, {len(self.airspace_list)}个空域, {len(self.env_list)}个气象区")

    def step_frame(self) -> dict:
        """推进一帧，返回帧数据"""
        # 从 safety_cfg 读取冲突检测参数（正确来源），回退到默认值
        conflict_cfg = self.safety_cfg.get("conflict_check", {})
        h_gap = conflict_cfg.get("horizontal_gap_m", 50)
        v_gap = conflict_cfg.get("vertical_gap_m", 30)

        alarm_list = []
        uav_frames = []

        for uav in self.uavs:
            # 检查气象
            weather_result = check_weather_affect(
                uav.lon, uav.lat, uav.alt, self.sim_time,
                self.env_list, self.safety_cfg
            )
            force_hover = weather_result["forbid_fly"]

            # 检查空域违规
            violated = get_violated_areas(uav.lon, uav.lat, uav.alt,
                                          self.sim_time, self.airspace_list)

            force_ground = False
            violate_area_id = ""
            alarm_type = ""

            if violated:
                top = violated[0]
                violate_area_id = top.get("area_id", "")
                area_type = top.get("area_type", "")
                if area_type == "no_fly":
                    force_ground = True
                    alarm_type = "enter_no_fly_area"
                elif area_type == "limit_h":
                    alarm_type = "exceed_limit_height"
                elif area_type in ("control", "temp"):
                    alarm_type = "enter_control_area"

            if weather_result["forbid_fly"]:
                alarm_type = alarm_type or f"weather_{','.join(weather_result['alarm_types'])}"

            # 推进运动
            snapshot = uav.step(self.step, self.sim_time, force_hover, force_ground)
            snapshot["alarm_type"] = alarm_type
            snapshot["violate_area_id"] = violate_area_id
            uav.alarm_type = alarm_type
            uav.violate_area_id = violate_area_id

            uav_frames.append(snapshot)

            # 生成告警（去重：仅在状态变化时触发，持续违规不重复告警）
            prev_alarm = self._alarm_active.get(uav.uav_id, "")
            if alarm_type != prev_alarm:
                self._alarm_active[uav.uav_id] = alarm_type
                if alarm_type:   # 新的违规/违规类型切换 → 生成一条新告警
                    self.alarm_counter += 1
                    alarm = {
                        "alarm_id": f"ALM_{self.alarm_counter:05d}",
                        "alarm_level": 3 if "no_fly" in alarm_type or "ground" in alarm_type else 2,
                        "uav_id": uav.uav_id,
                        "reason": alarm_type,
                        "area_id": violate_area_id,
                        "sim_time": self.sim_time
                    }
                    alarm_list.append(alarm)
                    self._alarm_records.append(alarm)
                # alarm_type == "" 且 prev != "" → 告警解除，不再生成新条目（可按需扩展）

        # 冲突检测（给双方各生成一条告警，去重：同一对持续冲突不重复）
        conflicts = check_conflict(self.uavs, h_gap, v_gap)
        active_pairs = set()
        for c in conflicts:
            pair_arr = sorted([c["uav_a"], c["uav_b"]])
            pair_key = f"conflict_{pair_arr[0]}_{pair_arr[1]}"
            active_pairs.add(pair_key)
            if pair_key not in self._alarm_active:
                # 首次进入冲突 → 给双方各生成一条告警
                self._alarm_active[pair_key] = True
                level = 4 if c["severity"] == "critical" else 2
                for uav_self, uav_other in [(c["uav_a"], c["uav_b"]), (c["uav_b"], c["uav_a"])]:
                    self.alarm_counter += 1
                    alarm = {
                        "alarm_id": f"ALM_{self.alarm_counter:05d}",
                        "alarm_level": level,
                        "uav_id": uav_self,
                        "reason": f"conflict_with_{uav_other}",
                        "area_id": "",
                        "sim_time": self.sim_time,
                        "h_dist_m": c["h_dist_m"],
                        "v_dist_m": c["v_dist_m"],
                        # 冲突中点坐标，供前端在地图上显示冲突标志
                        "mid_lon": c["mid_lon"],
                        "mid_lat": c["mid_lat"],
                        "mid_alt": c["mid_alt"],
                    }
                    alarm_list.append(alarm)
                    self._alarm_records.append(alarm)
        # 清除已分离的冲突对记录，以便下次进入时再次告警
        stale = [k for k in list(self._alarm_active) if k.startswith("conflict_") and k not in active_pairs]
        for k in stale:
            del self._alarm_active[k]

        frame = {
            "sim_time": round(self.sim_time, 2),
            "step": self.step,
            "frame": self.frame_counter,
            "uavs": uav_frames,
            "alarm_list": alarm_list,
            "active_count": sum(1 for u in uav_frames if u["status"] in ("flying", "alarm", "hovering")),
            "conflict_count": len(conflicts)
        }

        self._frame_records.append({
            "sim_time": frame["sim_time"],
            "frame": frame["frame"],
            "active_count": frame["active_count"],
            "alarm_count": len(alarm_list),
            "conflict_count": len(conflicts)
        })

        self.sim_time += self.step
        self.frame_counter += 1
        return frame

    async def run_async(self, on_frame=None):
        """异步推演循环"""
        self._running = True
        self._paused = False
        print(f"[Engine] 推演开始，步长={self.step}s, 总时长={self.max_time}s")
        start_wall = time.time()
        pause_accum = 0.0  # 暂停累计时间

        while self._running and self.sim_time <= self.max_time:
            # 暂停等待
            if self._paused:
                pause_start = time.time()
                while self._paused and self._running:
                    await asyncio.sleep(0.1)
                pause_accum += time.time() - pause_start
                if not self._running:
                    break

            frame = self.step_frame()

            if on_frame:
                await on_frame(frame)

            # 检查是否全部完成
            all_done = all(
                u.status in (UAVState.STATUS_COMPLETED, UAVState.STATUS_GROUNDED)
                for u in self.uavs
            )
            if all_done:
                print(f"[Engine] 所有UAV任务完成，仿真时间={self.sim_time:.1f}s")
                break

            # 实时模式：等待下一帧（倍速缩短等待时间，扣除暂停时间）
            elapsed = time.time() - start_wall - pause_accum
            expected = self.sim_time / max(self.speed, 0.1)
            sleep_t = expected - elapsed
            if sleep_t > 0:
                await asyncio.sleep(sleep_t)

        self._running = False
        self.save_output()
        print(f"[Engine] 推演结束，共{self.frame_counter}帧")

    def run_batch(self, progress_cb=None):
        """批量快速推演（不实时）"""
        self._running = True
        print(f"[Engine] 批量推演开始...")
        total_frames = int(self.max_time / self.step)

        while self._running and self.sim_time <= self.max_time:
            frame = self.step_frame()
            if progress_cb:
                progress_cb(frame, self.frame_counter, total_frames)

            all_done = all(
                u.status in (UAVState.STATUS_COMPLETED, UAVState.STATUS_GROUNDED)
                for u in self.uavs
            )
            if all_done:
                break

        self._running = False
        self.save_output()
        return self._frame_records, self._alarm_records

    def save_output(self):
        """保存推演结果到 output/"""
        out_dir = self.scene_path / "output"
        out_dir.mkdir(exist_ok=True)

        # 保存帧记录
        if self._frame_records:
            frame_path = out_dir / "frame_record.csv"
            keys = self._frame_records[0].keys()
            with open(frame_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self._frame_records)
            print(f"[Engine] 帧记录已保存: {frame_path}")

        # 保存告警日志
        if self._alarm_records:
            alarm_path = out_dir / "alarm_log.csv"
            keys = ["alarm_id", "alarm_level", "uav_id", "reason", "area_id", "sim_time"]
            with open(alarm_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(self._alarm_records)
            print(f"[Engine] 告警日志已保存: {alarm_path}")

    def stop(self):
        self._running = False
