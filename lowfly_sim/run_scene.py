"""
run_scene.py - AirFogSim 一键启动入口
修改 SCENE_NAME 即可切换想定，其余全自动

用法：
    python run_scene.py                    # 使用默认想定
    python run_scene.py --scene scene_02   # 指定想定名（前缀匹配）
    python run_scene.py --batch            # 批量快速推演（不实时）
    python run_scene.py --list             # 列出所有想定
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# ========================
# ★ 在这里修改想定名 ★
SCENE_NAME = "scene_01_常规城区_白天无气象"
# ========================

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def resolve_scene(name: str) -> str:
    """模糊匹配想定名"""
    scenes_dir = BASE_DIR / "scenes"
    for d in scenes_dir.iterdir():
        if d.is_dir() and d.name.startswith(name):
            return d.name
    return name


async def run_realtime(scene_name: str):
    """实时推演模式：推演 + WebSocket推流 + HTTP服务"""
    from engine.sim_engine import SimEngine
    from utils.export_data import WSBroadcaster, HTTPSceneServer
    from utils.load_data import load_scene_config

    scene_path = BASE_DIR / "scenes" / scene_name
    if not scene_path.exists():
        print(f"[ERROR] 想定不存在: {scene_path}")
        return

    # 加载配置
    cfg = load_scene_config(str(scene_path))
    ws_port = cfg.get("websocket_port", 8765)
    http_port = cfg.get("http_port", 8080)

    # 启动 WebSocket 服务器
    broadcaster = WSBroadcaster(ws_port)
    await broadcaster.start()

    # 初始化推演引擎
    engine = SimEngine(str(scene_path))
    engine.load()

    # 启动 HTTP 服务器（传入engine引用，支持倍速API）
    http_server = HTTPSceneServer(port=http_port, base_dir=str(BASE_DIR), engine=engine)
    runner = await http_server.start()

    print(f"\n{'='*60}")
    print(f"  AirFogSim 推演系统启动")
    print(f"  想定：{scene_name}")
    print(f"  前端：http://localhost:{http_port}")
    print(f"  WS：  ws://localhost:{ws_port}")
    print(f"{'='*60}\n")

    # 推演回调：广播帧
    async def on_frame(frame):
        await broadcaster.broadcast(frame)

    # 启动推演
    try:
        await engine.run_async(on_frame=on_frame)
    except KeyboardInterrupt:
        print("\n[Engine] 用户中断推演")
        engine.stop()

    print("[Done] 推演完成，服务器保持运行（Ctrl+C 退出）")
    print(f"       回放数据：{scene_path / 'output'}")
    try:
        await asyncio.get_event_loop().create_future()  # 保持运行
    except KeyboardInterrupt:
        pass


def run_batch(scene_name: str):
    """批量推演模式：快速无实时，只输出CSV"""
    from engine.sim_engine import SimEngine

    scene_path = BASE_DIR / "scenes" / scene_name
    if not scene_path.exists():
        print(f"[ERROR] 想定不存在: {scene_path}")
        return

    engine = SimEngine(str(scene_path))
    engine.load()

    total = int(engine.max_time / engine.step)
    last_pct = -1

    def progress(frame, cur, total):
        nonlocal last_pct
        pct = int(cur / total * 100)
        if pct != last_pct and pct % 5 == 0:
            print(f"  进度 {pct:3d}% | 仿真时间 {frame['sim_time']:.1f}s | "
                  f"活跃UAV {frame.get('active_count',0)} | 告警 {len(frame.get('alarm_list',[]))}")
            last_pct = pct

    print(f"\n[批量推演] 想定：{scene_name}")
    frames, alarms = engine.run_batch(progress_cb=progress)
    print(f"\n[Done] 共推演 {len(frames)} 帧，产生 {len(alarms)} 条告警")
    print(f"       输出目录：{scene_path / 'output'}")


def list_scenes():
    """列出所有想定"""
    from utils.load_data import list_scenes as _list
    scenes = _list()
    print(f"\n{'='*60}")
    print(f"  AirFogSim - 已有想定列表")
    print(f"{'='*60}")
    for s in scenes:
        print(f"  [{s['uav_count']:3d}架] {s['name']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AirFogSim 低空仿真推演系统")
    parser.add_argument("--scene", type=str, default=SCENE_NAME, help="想定名（前缀匹配）")
    parser.add_argument("--batch", action="store_true", help="批量推演模式（快速，不实时）")
    parser.add_argument("--list", action="store_true", help="列出所有想定")
    args = parser.parse_args()

    if args.list:
        list_scenes()
        sys.exit(0)

    scene = resolve_scene(args.scene)
    print(f"[Init] 选定想定：{scene}")

    if args.batch:
        run_batch(scene)
    else:
        asyncio.run(run_realtime(scene))
