"""
main.py - AirFogSim 带交互菜单的主入口
支持：列出想定 / 选择想定 / 实时推演 / 批量推演
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║         AirFogSim - 低空仿真推演系统 v1.0              ║
║         多想定 | 空域管理 | 气象联动 | Cesium可视化     ║
╚══════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()
    from utils.load_data import list_scenes

    while True:
        scenes = list_scenes()
        print("─" * 56)
        print("  可用想定：")
        for i, s in enumerate(scenes, 1):
            print(f"  [{i}] {s['name']}  ({s['uav_count']}架)")
        print()
        print("  [r] 实时推演（启动WebSocket+HTTP服务器）")
        print("  [b] 批量推演（快速输出CSV，不实时）")
        print("  [q] 退出")
        print("─" * 56)

        choice = input("  选择想定编号 (或r/b/q): ").strip()

        if choice.lower() == 'q':
            print("  再见！")
            break

        # 选择想定
        scene_name = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(scenes):
                scene_name = scenes[idx]['name']
            else:
                print("  [!] 序号超出范围\n")
                continue
        elif choice.lower() not in ('r', 'b'):
            # 尝试按名字匹配
            matches = [s for s in scenes if choice in s['name']]
            if matches:
                scene_name = matches[0]['name']
            else:
                print("  [!] 未找到想定\n")
                continue

        if not scene_name:
            print("  请先输入想定编号再选模式\n")
            continue

        print(f"\n  已选想定：{scene_name}")
        mode = input("  推演模式 [r=实时/b=批量]: ").strip().lower()

        if mode == 'b':
            import importlib
            import run_scene
            run_scene.run_batch(scene_name)
        else:
            import asyncio
            import run_scene
            try:
                asyncio.run(run_scene.run_realtime(scene_name))
            except KeyboardInterrupt:
                print("\n  [!] 用户中断\n")

        print()


if __name__ == "__main__":
    main()
