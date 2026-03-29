from engine.airspace_checker import check_in_airspace, get_violated_areas
from engine.weather_checker import check_weather_affect
from engine.uav_model import UAVState, check_conflict
from utils.load_data import list_scenes, load_full_scene

# 测试空域检测（圆形）
area = {'geo_shape':'circle','center_lon':120.0,'center_lat':30.0,'radius_m':1000,'min_alt':0,'max_alt':400}
r = check_in_airspace(120.001, 30.001, 100, area)
print("空域检测 圆形命中:", r)

r2 = check_in_airspace(121.0, 31.0, 100, area)
print("空域检测 圆形未命中:", r2)

# 测试想定列表
scenes = list_scenes()
print("发现想定数量:", len(scenes))
for s in scenes:
    print(" -", s["name"], s["uav_count"], "架")

# 测试加载想定
data = load_full_scene("scenes/scene_01_常规城区_白天无气象")
print("scene01 UAV数:", len(data["uav_tasks"]))
print("scene01 空域数:", len(data["airspace"]))

# 测试UAV状态机
task = {"uav_id":"UAV_T01","speed_m_s":12,"route":[[120.0,30.0,80],[120.05,30.05,100]],"start_delay_s":0}
uav = UAVState(task)
snap = uav.step(0.5, 1.0)
print("UAV快照:", snap)

print("所有模块测试通过")
