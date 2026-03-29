"""
server.py - AirFogSim 常驻服务入口

一次启动，永久运行。前端通过 HTTP API 控制推演启动/停止/切换想定。

用法：
    python server.py              # 默认 HTTP:8080 WS:8765
    python server.py --http 8080 --ws 8765
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("server")


class SimController:
    """推演控制器：管理推演协程的生命周期"""

    def __init__(self, broadcaster):
        self.broadcaster = broadcaster
        self.engine = None
        self._sim_task = None       # asyncio.Task
        self.current_scene = ""
        self.status = "idle"        # idle / running / paused / done

    # ---------- 状态查询 ----------
    def get_status(self):
        return {
            "status": self.status,
            "scene": self.current_scene,
            "sim_time": round(self.engine.sim_time, 2) if self.engine else 0,
            "max_time": self.engine.max_time if self.engine else 0,
            "frame": self.engine.frame_counter if self.engine else 0,
            "speed": self.engine.speed if self.engine else 1.0,
        }

    # ---------- 启动推演 ----------
    async def start(self, scene_name: str):
        """异步启动推演（不阻塞HTTP响应）"""
        # 先停掉旧的
        await self.stop()

        from engine.sim_engine import SimEngine
        from utils.load_data import load_full_scene

        scene_path = BASE_DIR / "scenes" / scene_name
        if not scene_path.exists():
            # 尝试前缀匹配
            for d in (BASE_DIR / "scenes").iterdir():
                if d.is_dir() and d.name.startswith(scene_name):
                    scene_path = d
                    scene_name = d.name
                    break
            else:
                logger.error(f"想定不存在: {scene_name}")
                return False, f"想定不存在: {scene_name}"

        self.current_scene = scene_name
        self.status = "running"

        self.engine = SimEngine(str(scene_path))
        self.engine.load()
        logger.info(f"[Sim] 想定加载完成: {scene_name}")

        # 在事件循环中启动推演协程（不阻塞）
        self._sim_task = asyncio.create_task(self._run_sim())
        logger.info(f"[Sim] 推演协程已启动")
        return True, "ok"

    async def _run_sim(self):
        """推演主循环（在后台task中运行）"""
        broadcaster = self.broadcaster
        try:
            async def on_frame(frame):
                await broadcaster.broadcast(frame)

            await self.engine.run_async(on_frame=on_frame)
            self.status = "done"
            logger.info("[Sim] 推演完成")
        except asyncio.CancelledError:
            self.status = "idle"
            logger.info("[Sim] 推演被取消")
        except Exception as e:
            self.status = "idle"
            logger.error(f"[Sim] 推演异常: {e}", exc_info=True)

    # ---------- 停止推演 ----------
    async def stop(self):
        if self._sim_task and not self._sim_task.done():
            if self.engine:
                self.engine._running = False
            self._sim_task.cancel()
            try:
                await asyncio.wait_for(self._sim_task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        self._sim_task = None
        self.engine = None
        self.current_scene = ""
        self.status = "idle"

    # ---------- 暂停/继续 ----------
    def pause(self):
        if self.engine:
            self.engine._paused = True
            self.status = "paused"

    def resume(self):
        if self.engine:
            self.engine._paused = False
            self.status = "running"

    # ---------- 倍速 ----------
    def set_speed(self, speed: float):
        speed = max(0.1, min(float(speed), 50.0))
        if self.engine:
            self.engine.speed = speed
        return speed


async def build_app(controller, base_dir, broadcaster):
    """构建 aiohttp 应用"""
    from aiohttp import web
    from utils.load_data import list_scenes, load_full_scene
    import csv as csvmod

    app = web.Application()

    # ---------- 场景 API ----------
    async def api_scenes(request):
        return web.json_response(list_scenes())

    async def api_scene_data(request):
        name = request.match_info["scene_name"]
        path = Path(base_dir) / "scenes" / name
        if not path.exists():
            return web.json_response({"error": "not found"}, status=404)
        return web.json_response(load_full_scene(str(path)))

    async def api_output(request):
        name = request.match_info["scene_name"]
        ftype = request.match_info["file_type"]
        fpath = Path(base_dir) / "scenes" / name / "output" / f"{ftype}.csv"
        if not fpath.exists():
            return web.json_response({"error": "not found"}, status=404)
        rows = []
        with open(fpath, encoding="utf-8") as f:
            rows = list(csvmod.DictReader(f))
        return web.json_response(rows)

    # ---------- 推演控制 API ----------
    async def api_sim_start(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        scene_name = body.get("scene_name", "")
        if not scene_name:
            return web.json_response({"status": "error", "msg": "缺少 scene_name"}, status=400)
        ok, msg = await controller.start(scene_name)
        if ok:
            return web.json_response({"status": "ok", "scene": controller.current_scene})
        else:
            return web.json_response({"status": "error", "msg": msg}, status=404)

    async def api_sim_stop(request):
        await controller.stop()
        return web.json_response({"status": "ok"})

    async def api_sim_pause(request):
        controller.pause()
        return web.json_response({"status": "ok"})

    async def api_sim_resume(request):
        controller.resume()
        return web.json_response({"status": "ok"})

    async def api_sim_speed(request):
        try:
            body = await request.json()
            speed = controller.set_speed(body.get("speed", 1))
            return web.json_response({"status": "ok", "speed": speed})
        except Exception as e:
            return web.json_response({"status": "error", "msg": str(e)}, status=400)

    async def api_sim_status(request):
        return web.json_response(controller.get_status())

    # ---------- 单机控制 API ----------
    async def api_uav_ctrl(request):
        """POST /api/uav/ctrl  body: {uav_id, action, ...}"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"status": "error", "msg": "JSON解析失败"}, status=400)

        uav_id = body.get("uav_id", "")
        action  = body.get("action", "")

        engine = controller.engine
        if not engine:
            return web.json_response({"status": "error", "msg": "推演未启动，请先开始推演"}, status=503)

        uav = next((u for u in engine.uavs if u.uav_id == uav_id), None)
        if uav is None:
            return web.json_response({"status": "error", "msg": f"未找到 {uav_id}"}, status=404)

        if action == "hover":
            uav.cmd_hover()
            logger.info(f"[Ctrl] {uav_id} → 悬停")
        elif action == "resume":
            uav.cmd_resume()
            logger.info(f"[Ctrl] {uav_id} → 恢复飞行")
        elif action == "land":
            uav.cmd_land()
            logger.info(f"[Ctrl] {uav_id} → 强制落地")
        elif action == "goto":
            lon = float(body.get("lon", uav.lon))
            lat = float(body.get("lat", uav.lat))
            alt = float(body.get("alt", uav.alt))
            uav.cmd_goto(lon, lat, alt)
            logger.info(f"[Ctrl] {uav_id} → goto ({lon:.5f},{lat:.5f},{alt:.1f}m)")
        elif action == "speed":
            spd = float(body.get("value", 10.0))
            uav.speed = max(1.0, min(spd, 100.0))
            logger.info(f"[Ctrl] {uav_id} → 飞行速度 {uav.speed} m/s")
        else:
            return web.json_response({"status": "error", "msg": f"未知指令: {action}"}, status=400)

        return web.json_response({"status": "ok", "uav_id": uav_id, "action": action})

    # ---------- 全局配置 API ----------
    async def api_config_safety(request):
        """GET /api/config/safety  返回 safety_base.json 供前端展示规则"""
        safety_path = Path(base_dir) / "config_global" / "safety_base.json"
        if not safety_path.exists():
            return web.json_response({"error": "not found"}, status=404)
        return web.json_response(json.loads(safety_path.read_text(encoding="utf-8")))

    # ---------- 注册路由----------
    app.router.add_get("/api/config/safety", api_config_safety)
    app.router.add_get("/api/scenes", api_scenes)
    app.router.add_get("/api/scenes/{scene_name}", api_scene_data)
    app.router.add_get("/api/output/{scene_name}/{file_type}", api_output)
    app.router.add_post("/api/sim/start", api_sim_start)
    app.router.add_post("/api/sim/stop", api_sim_stop)
    app.router.add_post("/api/sim/pause", api_sim_pause)
    app.router.add_post("/api/sim/resume", api_sim_resume)
    app.router.add_post("/api/sim/speed", api_sim_speed)
    app.router.add_get("/api/sim/status", api_sim_status)
    app.router.add_post("/api/uav/ctrl", api_uav_ctrl)    # ← 单机控制

    # 静态文件：通过自定义handler处理，不用add_static避免拦截API路由
    frontend_dir = os.path.join(base_dir, "frontend")

    async def static_handler(request):
        """处理前端静态文件请求（排除/api/路径）"""
        path = request.match_info.get("path", "index.html") or "index.html"
        # 不处理API请求
        if path.startswith("api/"):
            raise web.HTTPNotFound()
        # 安全检查：不允许路径穿越
        filepath = os.path.normpath(os.path.join(frontend_dir, path))
        if not filepath.startswith(os.path.normpath(frontend_dir)):
            return web.Response(status=403, text="Forbidden")
        if os.path.isdir(filepath):
            filepath = os.path.join(filepath, "index.html")
        if not os.path.exists(filepath):
            # 回退到 index.html（SPA支持）
            filepath = os.path.join(frontend_dir, "index.html")
        return web.FileResponse(filepath)

    app.router.add_get("/", static_handler)
    app.router.add_get("/{path:.*}", static_handler)

    return app


async def main(http_port=8080, ws_port=8765):
    from aiohttp import web
    from utils.export_data import WSBroadcaster

    # 启动 WS 广播器
    broadcaster = WSBroadcaster(ws_port)
    await broadcaster.start()
    logger.info(f"[WS] 广播服务启动 ws://0.0.0.0:{ws_port}")

    # 推演控制器
    controller = SimController(broadcaster)

    # HTTP 应用
    app = await build_app(controller, str(BASE_DIR), broadcaster)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", http_port)
    await site.start()

    print(f"\n{'='*60}")
    print(f"  AirFogSim 常驻服务已启动")
    print(f"  前端访问：http://localhost:{http_port}")
    print(f"  WS 地址：ws://localhost:{ws_port}")
    print(f"  在前端选择想定，点击「开始推演」即可自动启动")
    print(f"  按 Ctrl+C 停止服务")
    print(f"{'='*60}\n")

    # 永久运行
    try:
        await asyncio.get_event_loop().create_future()
    except KeyboardInterrupt:
        pass
    finally:
        await controller.stop()
        await runner.cleanup()
        await broadcaster.stop()
        logger.info("服务已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AirFogSim 常驻服务")
    parser.add_argument("--http", type=int, default=8080, help="HTTP 端口（默认8080）")
    parser.add_argument("--ws", type=int, default=8765, help="WebSocket 端口（默认8765）")
    args = parser.parse_args()

    try:
        asyncio.run(main(http_port=args.http, ws_port=args.ws))
    except KeyboardInterrupt:
        print("\n[服务] 已退出")
