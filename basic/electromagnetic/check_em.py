import json, os
from collections import Counter

path = r'C:\mgs\basic\electromagnetic\em_sim_bds_grid.json'
size = os.path.getsize(path)
print(f'文件大小: {size/1024/1024:.2f} MB')

with open(path, encoding='utf-8') as f:
    d = json.load(f)

data = d['data']
print(f'记录总数: {len(data)}')

signals = [r['em_field']['total_signal_dbm'] for r in data]
print(f'信号强度范围: {min(signals):.1f} ~ {max(signals):.1f} dBm')
print(f'信号强度均值: {sum(signals)/len(signals):.1f} dBm')

levels = Counter(r['em_field']['interference_level'] for r in data)
print(f'干扰等级分布: {dict(levels)}')

alt_set = sorted(set(r['center']['alt_m'] for r in data))
print(f'高度层({len(alt_set)}层): {alt_set}')

print()
print('=== 编码格式说明 ===')
r = data[100]
code = r['grid_code']
print(f'网格编码: {code}')
print(f'  G = 标识符')
print(f'  {code[1:4]} = 经度整度')
print(f'  {code[4:8]} = 经度格号（×0.0008°）')
print(f'  {code[8:10]} = 纬度整度')
print(f'  {code[10:14]} = 纬度格号（×0.0008°）')
print(f'  H{code[15:18]} = 高度层（×80m）')
print(f'  对应坐标: ({r["center"]["lon"]}, {r["center"]["lat"]}, {r["center"]["alt_m"]}m)')

# 靠近雷达站的最强点
src_lon, src_lat = 120.120, 30.560
def dist2(r):
    dx = r['center']['lon'] - src_lon
    dy = r['center']['lat'] - src_lat
    return dx*dx + dy*dy

nearest = sorted(data, key=dist2)[:5]
print()
print('=== 靠近雷达站的格点 ===')
for nr in nearest:
    print(f'  {nr["grid_code"]}  信号:{nr["em_field"]["total_signal_dbm"]} dBm  干扰:{nr["em_field"]["interference_level"]}  高:{nr["center"]["alt_m"]}m')
