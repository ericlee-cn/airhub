# AirFogSim 低空仿真推演系统

> 多想定 · 空域管理 · 气象联动 · Cesium 3D 可视化 · 纯 JSON/CSV 无数据库

---

## 一、目录结构

```
lowfly_sim/
├── main.py                     # 交互式主入口（推荐新手使用）
├── run_scene.py                # 命令行快速启动
├── requirements.txt
├── test_modules.py             # 模块冒烟测试
│
├── engine/                     # 推演核心引擎
│   ├── sim_engine.py           # 主推演引擎（帧循环/输出/WebSocket）
│   ├── airspace_checker.py     # 空域检测（圆/多边形/全局）
│   ├── weather_checker.py      # 气象检测（复用空域几何）
│   └── uav_model.py            # 无人机运动模型 + 冲突检测
│
├── utils/
│   ├── load_data.py            # 数据加载（全局配置+想定覆盖合并）
│   └── export_data.py          # WebSocket广播 + HTTP服务器
│
├── config_global/              # 全局公共配置
│   ├── sim_global.json         # 推演步长、端口等
│   └── safety_base.json        # 基础安全阈值
│
├── frontend/
│   └── index.html              # Cesium 前端可视化界面
│
└── scenes/                     # 所有想定（每个独立文件夹）
    ├── scene_01_常规城区_白天无气象/
    ├── scene_02_机场周边_大风管制/
    ├── scene_03_城市核心_百机密集/    ← 100架UAV
    └── scene_04_赛事活动_临时禁飞/
```

---

## 二、快速开始

### 安装依赖
```bash
pip install websockets aiohttp
```

### 方式1：交互菜单（推荐）
```bash
cd C:\mgs\lowfly_sim
python main.py
```
按提示选择想定编号，再选 `r`（实时）或 `b`（批量）。

### 方式2：命令行直接运行
```bash
# 列出所有想定
python run_scene.py --list

# 实时推演（启动WebSocket+HTTP服务）
python run_scene.py --scene scene_01

# 批量快速推演（输出CSV，不开服务器）
python run_scene.py --batch --scene scene_01
```

### 方式3：在 run_scene.py 顶部改一行
```python
SCENE_NAME = "scene_03_城市核心_百机密集"  # ← 只改这里
```
然后直接 `python run_scene.py`

---

## 三、实时推演访问地址

启动后：
| 服务 | 地址 |
|---|---|
| 前端可视化 | http://localhost:8080 |
| WebSocket | ws://localhost:8765 |
| 想定列表API | http://localhost:8080/api/scenes |
| 想定数据API | http://localhost:8080/api/scenes/{名称} |
| 推演输出API | http://localhost:8080/api/output/{名称}/alarm_log |

---

## 四、新建想定（极简，0代码改动）

```bash
# 1. 复制任意已有想定文件夹
cp -r scenes/scene_01_常规城区_白天无气象 scenes/scene_05_新场景名称

# 2. 修改里面的 JSON/CSV 数据
#    - airspace/no_fly.json       → 禁飞区
#    - airspace/limit_height.json → 限高区
#    - airspace/temp_control.json → 临时管制
#    - environment/weather_env.json → 气象
#    - mission/uav_batch.json     → 无人机任务
#    - scene_override.json        → 覆盖全局参数

# 3. 直接运行
python run_scene.py --scene scene_05
```

---

## 五、想定内数据格式速查

### 空域（3种几何）
```json
// 圆形
{"geo_shape":"circle","center_lon":120.0,"center_lat":30.0,"radius_m":1000}

// 多边形
{"geo_shape":"polygon","points":[[lon1,lat1],[lon2,lat2],...]}

// 全域
{"geo_shape":"global"}
```

### 无人机任务
```json
{
  "uav_id": "UAV_001",
  "uav_type": "delivery",
  "speed_m_s": 12,
  "start_delay_s": 10,
  "route": [[lon,lat,alt], [lon,lat,alt], ...]
}
```

### 气象环境
```json
{
  "env_id": "ENV_001",
  "env_type": "wind",          // wind/rain/fog/thunder
  "level": 4,
  "wind_speed_ms": 18.5,
  "forbid_fly": true,
  "geo_shape": "circle",       // 复用空域几何格式
  ...
}
```

### 想定参数覆盖（scene_override.json）
```json
{
  "sim_step_s": 0.2,
  "horizontal_gap_m": 30,
  "vertical_gap_m": 20,
  "max_sim_time_s": 7200
}
```

---

## 六、推演输出

每次推演结束，自动保存到想定自己的 `output/`：

| 文件 | 内容 |
|---|---|
| `frame_record.csv` | 每帧摘要（时间/活跃数/告警数/冲突数）|
| `alarm_log.csv` | 完整告警日志（UAV ID/原因/时间/空域）|

---

## 七、推演帧格式（WebSocket 推送）
```json
{
  "sim_time": 25.5,
  "step": 0.5,
  "frame": 51,
  "uavs": [
    {"uav_id":"UAV_001","lon":120.412,"lat":30.913,"alt":95,
     "status":"flying","alarm_type":"","violate_area_id":""}
  ],
  "alarm_list": [
    {"alarm_id":"ALM_00001","alarm_level":3,"uav_id":"UAV_002",
     "reason":"enter_no_fly_area","area_id":"AREA_001"}
  ],
  "active_count": 4,
  "conflict_count": 0
}
```

---

## 八、自动生成百架无人机

```bash
cd scenes/scene_03_城市核心_百机密集/mission
python gen_100uav.py
# 输出：uav_batch.json（100架随机航线）
```

---

## 九、前端使用说明

1. 启动推演后，浏览器打开 `http://localhost:8080`
2. 顶部下拉框选择想定
3. 点击 **🗺 加载空域** → 渲染禁飞区/气象区/航线到三维地球
4. 点击 **▶ 开始推演** → 自动连接 WebSocket，实时渲染 UAV
5. 左侧面板查看实时统计和告警列表
6. 右侧面板查看每架 UAV 实时状态，点击可聚焦飞行
7. 右上角图层控制，可开关各类图层
8. 底部 **⏪ 回放模式** → 拖拽时间轴复盘历史帧

---

## 十、告警类型说明

| 告警 | 等级 | 说明 |
|---|---|---|
| `enter_no_fly_area` | 3 | 闯入禁飞区 |
| `exceed_limit_height` | 2 | 超出限高 |
| `enter_control_area` | 2 | 进入管制区 |
| `weather_wind` | 2~4 | 大风悬停 |
| `weather_fog` | 2~3 | 大雾强制停飞 |
| `conflict_with_XXX` | 2~4 | UAV间隔不足 |
