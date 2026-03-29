#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查不同类型的数据差异"""
import json

# 读取综合数据
with open(r'C:\mgs\basic\electromagnetic\data\all\layer_000_alt0000m.json', 'r', encoding='utf-8') as f:
    all_data = json.load(f)
    all_points = all_data['data']
    print(f"综合数据: 总点数={len(all_points)}, 前3个点信号={[p['signal_dbm'] for p in all_points[:3]]}")
    print(f"  最大信号: {max(p['signal_dbm'] for p in all_points):.1f} dBm")
    print(f"  平均信号: {sum(p['signal_dbm'] for p in all_points)/len(all_points):.1f} dBm")

# 读取5G数据
with open(r'C:\mgs\basic\electromagnetic\data\5g\layer_000_alt0000m.json', 'r', encoding='utf-8') as f:
    g5_data = json.load(f)
    g5_points = g5_data['data']
    print(f"\n5G数据: 总点数={len(g5_points)}, 前3个点信号={[p['signal_dbm'] for p in g5_points[:3]]}")
    print(f"  最大信号: {max(p['signal_dbm'] for p in g5_points):.1f} dBm")
    print(f"  平均信号: {sum(p['signal_dbm'] for p in g5_points)/len(g5_points):.1f} dBm")

# 读取雷达数据
with open(r'C:\mgs\basic\electromagnetic\data\radar\layer_000_alt0000m.json', 'r', encoding='utf-8') as f:
    radar_data = json.load(f)
    radar_points = radar_data['data']
    print(f"\n雷达数据: 总点数={len(radar_points)}, 前3个点信号={[p['signal_dbm'] for p in radar_points[:3]]}")
    print(f"  最大信号: {max(p['signal_dbm'] for p in radar_points):.1f} dBm")
    print(f"  平均信号: {sum(p['signal_dbm'] for p in radar_points)/len(radar_points):.1f} dBm")

# 对比同一点的信号
print(f"\n对比第100个点:")
print(f"  综合: {all_points[100]['signal_dbm']} dBm")
print(f"  5G:   {g5_points[100]['signal_dbm']} dBm")
print(f"  雷达: {radar_points[100]['signal_dbm']} dBm")
