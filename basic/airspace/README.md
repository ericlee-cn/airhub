# 空域管理系统 (Airspace Management System)

## 项目概述
基于Cesium 3D平台开发的低空仿真系统空域航路管理子系统，实现了空域区域可视化、设备管理和交互式操作。

## 当前版本
- **版本**: V2.1.5 (独立版)
- **最后更新**: 2026-03-20
- **主文件**: `cesium_airspace_standalone.html`

## 功能特性

### 1. 空域区域管理
- 7类空域区域：禁飞区、限高区、法规限制区（A/B）、适飞区、警示区、风景示范区
- 颜色编码：红、橙、黄、绿、青、紫、蓝
- 双向联动：树节点↔地图区域点击联动
- 显示开关：每个图层独立控制

### 2. 设备管理（CNS）
- **通讯设备**: 5G基站（8个），绿色标识
- **导航设备**: 导航设施（5个），蓝色标识
- **监视设备**: 雷达（4个），紫色标识
- 自定义Canvas图标：信号塔、卫星定位、雷达扫描
- 距离缩放：近大远小显示效果

### 3. 交互界面
- **左侧资源树**：支持折叠/展开，一级目录默认展开，二级目录默认折叠
- **右侧详情面板**：显示选中区域或设备的详细信息
- **图层控制**：每个大类型有独立的显示开关（眼睛图标）
- **面板收起**：左右侧栏目可收起，节省屏幕空间

### 4. 视角系统
- 默认视角：经度119.995842°，纬度30.382550°，高度19879米，俯仰角-45°
- 支持手动调整视角，实时更新

## 技术栈

### 前端技术
- **CesiumJS**: v1.114 - 3D地球可视化引擎
- **TailwindCSS**: v3.4.17 - 样式框架
- **Iconify**: v3.1.0 - 图标库
- **原生JavaScript**: 无框架依赖

### 数据格式
- **GeoJSON**: 地理数据标准格式
- **内嵌数据**: 独立版本将所有数据内嵌到HTML
- **外部加载**: 服务器版本支持从外部文件加载GeoJSON

### 地图服务
- **高德卫星影像**: `https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}`

## 目录结构

```
c:/mgs/basic/airspace/
├── cesium_airspace_standalone.html    # 主应用（独立版）
├── cesium_airspace.html              # 主应用（服务器版）
├── cesium_airspace_ion.html          # Cesium Ion版本
├── 启动系统.bat                     # 便捷启动脚本
├── start_server.bat                   # HTTP服务器启动脚本
├── data/                           # 数据目录
│   ├── 导航设备.geojson             # 导航设备数据
│   ├── 监视雷达.geojson             # 监视设备数据
│   ├── 通讯设备.geojson             # 通讯设备数据
│   ├── 先飞区航路12.26.geojson     # 航路数据
│   └── legacy/                      # 旧版数据文件
│       ├── drone_flight_zone.json
│       ├── height_limit_zone.json
│       ├── no_fly_zone_core.json
│       ├── restricted_zone_a.json
│       ├── restricted_zone_b.json
│       ├── scenic_zone.json
│       └── warning_zone.json
├── docs/                           # 文档目录
│   └── 更新记录.md                # 更新日志
├── .workbuddy/                     # WorkBuddy工作目录
│   └── memory/                      # 开发记忆和决策记录
└── (测试文件...)
```

## 快速开始

### 方式1：独立版本（推荐）
无需服务器，直接在浏览器中打开：
```
双击 cesium_airspace_standalone.html
```

### 方式2：服务器版本
需要HTTP服务器支持，运行启动脚本：
```
双击 启动系统.bat
选择选项2
```
或手动启动：
```
双击 start_server.bat
访问 http://localhost:8000/cesium_airspace.html
```

## 使用说明

### 基本操作
1. **浏览地图**：鼠标左键拖拽旋转，右键拖拽平移，滚轮缩放
2. **查看区域**：点击左侧资源树的节点，地图会高亮对应区域并飞行到该位置
3. **查看设备**：展开"全要素保障层"下的设备分类，点击设备名称查看详情
4. **图层控制**：点击各类型右侧的眼睛图标（👁️/👁️‍🗨️）控制显示/隐藏
5. **折叠/展开**：点击箭头（▼/▶）折叠或展开目录内容
6. **面板收起**：点击左侧或右侧的收起按钮（‹/›）隐藏/显示面板

### 键盘快捷键
- **Home**: 返回默认视角
- **C**: 切换地图模式（2D/2.5D/3D）

## 依赖资源

### CDN链接
- CesiumJS: https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Cesium.js
- Iconify: https://cdnjs.cloudflare.com/ajax/libs/iconify/3.1.0/iconify.min.js

### 本地数据
- 所有GeoJSON文件位于 `data/` 目录
- 独立版本已将数据内嵌到HTML中

## 开发日志
详细更新记录请查看 `docs/更新记录.md`

## 注意事项
1. **独立版本**：推荐使用，无需服务器，所有数据已内嵌
2. **服务器版本**：需要HTTP服务器，无法通过file://协议加载外部文件
3. **旧版数据**：保存在 `data/legacy/` 目录，仅供参考
4. **调试模式**：按F12打开浏览器控制台，`window.viewer` 可访问Cesium实例

## 后续计划
- [ ] 添加更多设备类型和点位数据
- [ ] 实现航路动画显示
- [ ] 添加实时数据更新机制
- [ ] 优化性能和加载速度
- [ ] 添加更多交互功能

---

**开发团队**: MGS团队
**技术支持**: Cesium官方文档、高德地图API
