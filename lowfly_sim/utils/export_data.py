"""
WebSocket 推流服务器 - AirFogSim
将推演帧实时推送到 Cesium 前端
"""

import asyncio
import json
import logging
from typing import Optional

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("[WS] websockets 未安装，请运行: pip install websockets")

logger = logging.getLogger(__name__)


class WSBroadcaster:
    """WebSocket 广播服务器"""

    def __init__(self, port: int = 8765):
        self.port = port
        self.clients = set()
        self.server = None
        self._latest_frame = None

    async def handler(self, websocket):
        """新客户端连接处理"""
        self.clients.add(websocket)
        addr = websocket.remote_address
        logger.info(f"[WS] 客户端连接: {addr}，当前在线: {len(self.clients)}")
        # 发送最新帧给新客户端
        if self._latest_frame:
            await websocket.send(json.dumps(self._latest_frame, ensure_ascii=False))
        try:
            await websocket.wait_closed()
        finally:
            self.clients.discard(websocket)
            logger.info(f"[WS] 客户端断开: {addr}，当前在线: {len(self.clients)}")

    async def broadcast(self, frame: dict):
        """广播帧到所有客户端"""
        self._latest_frame = frame
        if not self.clients:
            return
        msg = json.dumps(frame, ensure_ascii=False)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def start(self):
        """启动 WebSocket 服务器"""
        if not WEBSOCKETS_AVAILABLE:
            return
        self.server = await websockets.serve(self.handler, "0.0.0.0", self.port)
        logger.info(f"[WS] 服务器启动 ws://0.0.0.0:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class HTTPSceneServer:
    """简单 HTTP 服务器：提供想定列表和静态文件"""

    def __init__(self, host="0.0.0.0", port=8080, base_dir=".", engine=None):
        self.host = host
        self.port = port
        self.base_dir = base_dir
        self.engine = engine   # SimEngine 引用，用于倍速控制等

    async def start(self):
        """启动 aiohttp HTTP 服务器"""
        try:
            from aiohttp import web
        except ImportError:
            print("[HTTP] aiohttp 未安装，请运行: pip install aiohttp")
            return

        from utils.load_data import list_scenes
        import os

        app = web.Application()
        _engine = self.engine  # 闭包引用

        async def get_scenes(request):
            scenes = list_scenes()
            return web.json_response(scenes)

        async def get_scene_data(request):
            scene_name = request.match_info["scene_name"]
            from utils.load_data import load_full_scene
            import pathlib
            scene_path = pathlib.Path(self.base_dir) / "scenes" / scene_name
            if not scene_path.exists():
                return web.json_response({"error": "scene not found"}, status=404)
            data = load_full_scene(str(scene_path))
            return web.json_response(data)

        async def get_output(request):
            scene_name = request.match_info["scene_name"]
            file_type = request.match_info["file_type"]
            import pathlib, csv as csvmod
            out_path = pathlib.Path(self.base_dir) / "scenes" / scene_name / "output" / f"{file_type}.csv"
            if not out_path.exists():
                return web.json_response({"error": "file not found"}, status=404)
            rows = []
            with open(out_path, "r", encoding="utf-8") as f:
                reader = csvmod.DictReader(f)
                rows = list(reader)
            return web.json_response(rows)

        # ---- 推演控制API ----
        async def sim_start(request):
            body = await request.json()
            return web.json_response({"status": "ok", "msg": "start received", "scene": body.get("scene_name","")})

        async def sim_pause(request):
            if _engine:
                _engine._paused = True
            return web.json_response({"status": "ok", "msg": "paused"})

        async def sim_resume(request):
            if _engine:
                _engine._paused = False
            return web.json_response({"status": "ok", "msg": "resumed"})

        async def sim_stop(request):
            if _engine:
                _engine._running = False
            return web.json_response({"status": "ok", "msg": "stopped"})

        async def sim_speed(request):
            """接收倍速设置"""
            try:
                body = await request.json()
                speed = float(body.get("speed", 1))
                speed = max(0.1, min(speed, 50.0))  # 限制范围
                if _engine:
                    _engine.speed = speed
                print(f"[Engine] 倍速已设置为 x{speed}")
                return web.json_response({"status": "ok", "speed": speed})
            except Exception as e:
                return web.json_response({"status": "error", "msg": str(e)}, status=400)

        async def uav_ctrl(request):
            """单架无人机控制指令：hover / resume / land / goto / speed"""
            try:
                body = await request.json()
                uav_id = body.get("uav_id", "")
                action = body.get("action", "")
                if not _engine:
                    return web.json_response({"status": "error", "msg": "引擎未启动"}, status=503)

                # 找到目标 UAV
                uav = next((u for u in _engine.uavs if u.uav_id == uav_id), None)
                if uav is None:
                    return web.json_response({"status": "error", "msg": f"未找到 {uav_id}"}, status=404)

                if action == "hover":
                    uav.cmd_hover()
                    print(f"[Ctrl] {uav_id} → 悬停")
                elif action == "resume":
                    uav.cmd_resume()
                    print(f"[Ctrl] {uav_id} → 恢复飞行")
                elif action == "land":
                    uav.cmd_land()
                    print(f"[Ctrl] {uav_id} → 强制落地")
                elif action == "goto":
                    lon = float(body.get("lon", uav.lon))
                    lat = float(body.get("lat", uav.lat))
                    alt = float(body.get("alt", uav.alt))
                    uav.cmd_goto(lon, lat, alt)
                    print(f"[Ctrl] {uav_id} → 跳转 ({lon:.5f}, {lat:.5f}, {alt:.1f}m)")
                elif action == "speed":
                    spd = float(body.get("value", 10.0))
                    uav.speed = max(1.0, min(spd, 100.0))
                    print(f"[Ctrl] {uav_id} → 速度 {uav.speed} m/s")
                else:
                    return web.json_response({"status": "error", "msg": f"未知指令: {action}"}, status=400)

                return web.json_response({"status": "ok", "uav_id": uav_id, "action": action})
            except Exception as e:
                return web.json_response({"status": "error", "msg": str(e)}, status=500)

        app.router.add_get("/api/scenes", get_scenes)
        app.router.add_get("/api/scenes/{scene_name}", get_scene_data)
        app.router.add_get("/api/output/{scene_name}/{file_type}", get_output)
        app.router.add_post("/api/sim/start", sim_start)
        app.router.add_post("/api/sim/pause", sim_pause)
        app.router.add_post("/api/sim/resume", sim_resume)
        app.router.add_post("/api/sim/stop", sim_stop)
        app.router.add_post("/api/sim/speed", sim_speed)
        app.router.add_post("/api/uav/ctrl", uav_ctrl)   # ← 单机控制

        # 静态文件 —— 用 /static/ 前缀，避免覆盖 /api/ 路由
        frontend_dir = os.path.join(self.base_dir, "frontend")
        app.router.add_static("/static", frontend_dir)

        # 根路径和其他非 /api/ 路径都返回 index.html（SPA 兜底）
        async def serve_index(request):
            index_path = os.path.join(frontend_dir, "index.html")
            return web.FileResponse(index_path)

        app.router.add_get("/", serve_index)
        app.router.add_get("/{tail:(?!api|static).*}", serve_index)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"[HTTP] 服务器启动 http://{self.host}:{self.port}")
        return runner
