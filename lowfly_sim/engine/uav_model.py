"""
无人机运动模型 - AirFogSim
支持：多航点飞行 / 悬停 / 强制落地
"""

import math
from typing import Optional, List, Tuple


def _haversine_m(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class UAVState:
    """单架无人机状态机"""

    STATUS_WAITING = "waiting"       # 等待起飞
    STATUS_FLYING = "flying"         # 正常飞行
    STATUS_HOVERING = "hovering"     # 被迫悬停（气象/告警）
    STATUS_COMPLETED = "completed"   # 任务完成
    STATUS_GROUNDED = "grounded"     # 强制落地
    STATUS_ALARM = "alarm"           # 告警中（仍飞行）

    def __init__(self, task: dict):
        self.uav_id = task["uav_id"]
        self.uav_type = task.get("uav_type", "generic")
        self.speed = task.get("speed_m_s", 10.0)
        self.h_gap = task.get("h_safe_gap_m", 50.0)
        self.v_gap = task.get("v_safe_gap_m", 30.0)
        self.start_delay = task.get("start_delay_s", 0.0)
        self.route = task["route"]  # [[lon,lat,alt], ...]
        self.loop = task.get("route_rule", {}).get("loop_route", False)
        self.max_climb = task.get("route_rule", {}).get("max_climb_rate", 5.0)
        self.max_desc = task.get("route_rule", {}).get("max_desc_rate", 5.0)

        # 运行时状态
        self.wp_index = 0          # 当前目标航点索引
        self.lon = self.route[0][0] if self.route else 0
        self.lat = self.route[0][1] if self.route else 0
        self.alt = 0.0             # 初始在地面
        self._prev_alt = 0.0       # 上帧高度，用于计算垂直速度
        self.status = self.STATUS_WAITING
        self.alarm_type = ""
        self.violate_area_id = ""
        self.hover_reason = ""

        # ── 外部控制注入（由 /api/uav/ctrl 写入，step_frame 消费）
        self._ctrl_hover = False    # 强制悬停
        self._ctrl_ground = False   # 触发缓降落地
        self._landing = False       # 正在缓降中（已进入落地流程，不可中断）
        self._landed = False        # 已完成落地（彻底锁定，不可恢复飞行）
        self._ctrl_resume = False   # 取消强制悬停，恢复飞行
        self._goto_wp: Optional[List[float]] = None  # [lon,lat,alt] 插队航点
        self.LAND_SPEED = 3.0       # 缓降速度 m/s

    @property
    def pos(self) -> Tuple[float, float, float]:
        return self.lon, self.lat, self.alt

    # ── 外部控制指令接口 ────────────────────────────────
    def cmd_hover(self):
        """指令：立即悬停（保持位置）"""
        self._ctrl_hover = True
        self._ctrl_ground = False
        self._ctrl_resume = False

    def cmd_resume(self):
        """指令：恢复飞行（仅清除悬停，落地后不可恢复）"""
        if self._landed or self._landing:
            return   # 已落地或正在落地，锁定，无法恢复
        self._ctrl_hover = False
        self._ctrl_ground = False
        self._ctrl_resume = True

    def cmd_land(self):
        """指令：触发缓降落地（进入后不可中断）"""
        if self._landed:
            return   # 已经落地，无需重复
        self._ctrl_ground = True
        self._ctrl_hover = False
        self._ctrl_resume = False

    def cmd_goto(self, lon: float, lat: float, alt: float):
        """指令：跳转——插入临时航点到队首，完成后继续原计划"""
        self._goto_wp = [lon, lat, alt]

    # ── 推进一帧 ─────────────────────────────────────
    def step(self, dt: float, sim_time: float, force_hover: bool = False,
             force_ground: bool = False) -> dict:
        """
        推进一帧
        :param dt: 时间步长(s)
        :param sim_time: 当前仿真时间(s)
        :param force_hover: 空域/气象强制悬停
        :param force_ground: 空域强制落地
        :return: 帧快照dict
        """
        # 等待起飞
        if sim_time < self.start_delay:
            self.status = self.STATUS_WAITING
            return self._snapshot()

        if self.status == self.STATUS_COMPLETED:
            return self._snapshot()

        # ── 已彻底落地：永久锁定 ──
        if self._landed:
            self.status = self.STATUS_GROUNDED
            self.alt = 0.0
            return self._snapshot()

        # ── 正在缓降 / 触发缓降 ──
        if self._landing or self._ctrl_ground or force_ground:
            self._landing = True
            self._ctrl_ground = False   # 消费一次性触发标志
            self.status = self.STATUS_GROUNDED
            # 每帧向下降 LAND_SPEED * dt，到0后锁定
            drop = self.LAND_SPEED * dt
            if self.alt <= drop:
                self.alt = 0.0
                self._landing = False
                self._landed = True     # ← 落地完成，永久锁定
            else:
                self.alt -= drop
            return self._snapshot()

        # ── 处理外部控制指令 ──
        # resume：清除悬停（落地相关已在上方拦截）
        if self._ctrl_resume:
            self._ctrl_hover = False
            self._ctrl_resume = False
            if self.status == self.STATUS_HOVERING:
                self.status = self.STATUS_FLYING

        # goto：将目标插入当前航点队首
        if self._goto_wp is not None:
            wp = self._goto_wp
            self._goto_wp = None
            if self.wp_index < len(self.route):
                self.route.insert(self.wp_index, wp)
            else:
                self.route.append(wp)

        # 外部强制悬停（ctrl 或 气象）
        if self._ctrl_hover or force_hover:
            self.status = self.STATUS_HOVERING
            return self._snapshot()

        # 已完成所有航点
        if self.wp_index >= len(self.route):
            if self.loop:
                self.wp_index = 0
            else:
                self.status = self.STATUS_COMPLETED
                return self._snapshot()

        target = self.route[self.wp_index]
        tlon, tlat, talt = target[0], target[1], target[2]

        # 水平距离
        h_dist = _haversine_m(self.lon, self.lat, tlon, tlat)
        v_dist = talt - self.alt
        total_dist = math.sqrt(h_dist ** 2 + v_dist ** 2)

        move_dist = self.speed * dt

        if move_dist >= total_dist:
            # 到达航点
            self.lon = tlon
            self.lat = tlat
            self.alt = talt
            self.wp_index += 1
        else:
            ratio = move_dist / total_dist if total_dist > 0 else 0
            # 水平移动
            dlat = math.degrees(_haversine_m(self.lon, self.lat, tlon, tlat) / 6371000) * \
                   math.copysign(1, tlat - self.lat) if h_dist > 0.01 else 0
            # 简化：按比例插值
            self.lon += (tlon - self.lon) * ratio
            self.lat += (tlat - self.lat) * ratio
            # 垂直速度限制
            dalt = v_dist * ratio
            max_dalt_up = self.max_climb * dt
            max_dalt_down = self.max_desc * dt
            if dalt > max_dalt_up:
                dalt = max_dalt_up
            elif dalt < -max_dalt_down:
                dalt = -max_dalt_down
            self.alt += dalt

        self.status = self.STATUS_FLYING
        return self._snapshot()

    def _snapshot(self) -> dict:
        v_speed = round(self.alt - self._prev_alt, 2)  # 垂直速度 m/帧（正=爬升，负=下降）
        self._prev_alt = self.alt
        return {
            "uav_id": self.uav_id,
            "lon": round(self.lon, 7),
            "lat": round(self.lat, 7),
            "alt": round(self.alt, 2),
            "status": self.status,
            "alarm_type": self.alarm_type,
            "violate_area_id": self.violate_area_id,
            "wp_index": self.wp_index,
            "v_speed": v_speed,   # 垂直速度，正=爬升，负=下降
        }


def check_conflict(uavs: List[UAVState], h_gap: float, v_gap: float) -> List[dict]:
    """
    无人机间冲突检测（N^2，100架内可接受）
    :return: 冲突事件列表
    """
    conflicts = []
    states = [u for u in uavs if u.status in (UAVState.STATUS_FLYING, UAVState.STATUS_ALARM)]
    n = len(states)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = states[i], states[j]
            h_dist = _haversine_m(a.lon, a.lat, b.lon, b.lat)
            v_dist = abs(a.alt - b.alt)
            if h_dist < h_gap and v_dist < v_gap:
                conflicts.append({
                    "uav_a": a.uav_id,
                    "uav_b": b.uav_id,
                    "h_dist_m": round(h_dist, 1),
                    "v_dist_m": round(v_dist, 1),
                    "severity": "critical" if h_dist < h_gap * 0.5 else "warning",
                    # 两架飞机的中点坐标，供前端显示冲突标志
                    "mid_lon": round((a.lon + b.lon) / 2, 7),
                    "mid_lat": round((a.lat + b.lat) / 2, 7),
                    "mid_alt": round((a.alt + b.alt) / 2, 1),
                })
    return conflicts
