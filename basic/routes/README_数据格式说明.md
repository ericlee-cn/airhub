# 航路编辑系统 - 数据格式说明文档

## 1. 总体架构

### 存储位置
- **实时存储**: `localStorage` 中键名 `routes_library`
- **文件导出**: JSON 格式，建议保存为 `routes_YYYYMMDD_HHMMSS.json`
- **数据库**: 可选 IndexedDB 用于大容量备份

### 版本信息
```json
{
  "version": "1.0",
  "timestamp": "2026-03-23T18:35:00Z",
  "routes": [...]
}
```

---

## 2. 顶层数据结构

### 完整示例

```json
{
  "version": "1.0",
  "timestamp": "2026-03-23T18:35:00Z",
  "routes": [
    {
      "id": "route_1711263300000",
      "name": "杭州-上海北上通道",
      "description": "商业运输主航线",
      "type": "commercial",
      "priority": 1,
      "enabled": true,
      "created": "2026-03-23T10:00:00Z",
      "modified": "2026-03-23T18:35:00Z",
      "metadata": {
        "maxAltitude": 5000,
        "minAltitude": 500,
        "restrictedZones": ["zone_a", "zone_b"],
        "costRating": 3,
        "estimatedFlightTime": 50
      },
      "geometry": {
        "type": "RouteChannel3D",
        "centerline": {
          "type": "LineString",
          "coordinates": [
            [120.1, 30.5, 1500],
            [120.2, 30.6, 1500],
            [120.3, 30.7, 1500]
          ]
        },
        "profile": {
          "width": 2000,
          "height": 800,
          "widthUnit": "meters",
          "heightUnit": "meters"
        }
      },
      "waypoints": [
        {
          "id": "wp_1711263300001",
          "index": 0,
          "position": [120.1, 30.5, 1500],
          "label": "起点-杭州",
          "type": "checkpoint",
          "properties": {
            "holdingPattern": false
          }
        },
        {
          "id": "wp_1711263300002",
          "index": 1,
          "position": [120.2, 30.6, 1500],
          "label": "转向点-1",
          "type": "waypoint",
          "properties": {
            "turnRadius": 5000,
            "speedLimit": 450
          }
        }
      ],
      "restrictions": [
        {
          "id": "res_001",
          "type": "noFly",
          "severity": "critical",
          "reason": "空军禁区",
          "geometry": {
            "type": "Polygon",
            "coordinates": [
              [[120.15, 30.55], [120.25, 30.55], [120.25, 30.65], [120.15, 30.65], [120.15, 30.55]]
            ]
          }
        }
      ]
    }
  ]
}
```

---

## 3. 字段详解

### 3.1 航路顶级字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `id` | string | ✓ | 唯一标识符，使用时间戳 | `route_1711263300000` |
| `name` | string | ✓ | 航路名称 | `杭州-上海北上通道` |
| `description` | string | ✗ | 航路描述 | `商业运输主航线` |
| `type` | enum | ✓ | 航路类型 | `commercial/military/uav` |
| `priority` | number | ✗ | 优先级 1-10 | `1` |
| `enabled` | boolean | ✗ | 是否启用 | `true` |
| `created` | ISO8601 | ✓ | 创建时间 | `2026-03-23T10:00:00Z` |
| `modified` | ISO8601 | ✓ | 修改时间 | `2026-03-23T18:35:00Z` |
| `metadata` | object | ✓ | 元数据容器 | 见 3.2 |
| `geometry` | object | ✓ | 几何定义 | 见 3.3 |
| `waypoints` | array | ✓ | 途径点数组 | 见 3.4 |
| `restrictions` | array | ✗ | 限制区域数组 | 见 3.5 |

### 3.2 元数据字段 (metadata)

```json
{
  "maxAltitude": 5000,           // 最大飞行高度 (米)
  "minAltitude": 500,            // 最小飞行高度 (米)
  "restrictedZones": ["zone_a"], // 禁飞区ID列表
  "costRating": 3,               // 成本等级 1-10
  "estimatedFlightTime": 50,     // 预估飞行时间 (分钟)
  "remark": "需要空管批准",      // 备注
  "authorizedBy": "ATC"          // 授权方
}
```

### 3.3 几何字段 (geometry)

#### 3.3.1 中心线 (centerline)
```json
{
  "type": "RouteChannel3D",
  "centerline": {
    "type": "LineString",
    "coordinates": [
      [经度, 纬度, 海拔高度(米)],
      [120.1, 30.5, 1500],
      [120.2, 30.6, 1500],
      [120.3, 30.7, 1500]
    ]
  }
}
```

**坐标规范:**
- 经度范围: -180 ~ 180 (东半球为正)
- 纬度范围: -90 ~ 90 (北半球为正)
- 海拔: 米 (相对海平面)

#### 3.3.2 截面 (profile)

矩形通道的截面定义:

```json
{
  "profile": {
    "width": 2000,          // 通道宽度 (米) - 建议 500-5000
    "height": 800,          // 通道高度 (米) - 建议 200-2000
    "widthUnit": "meters",  // 宽度单位
    "heightUnit": "meters"  // 高度单位
  }
}
```

**三维通道计算原理:**

每个途径点处计算矩形截面的四个顶点:

```
        ┌─────────┐  (上方)
        │  高度H  │
    ┌───┼─────────┼───┐
    │   │ 中心线  │   │  通道宽度 W
    └───┼─────────┼───┘
        │         │
        └─────────┘
```

对于中心线上的每个点 P:
- 计算前进方向向量 F (到下一个点)
- 计算垂直向量 R = F × Z (右侧)
- 四个顶点 = P ± R*(W/2) ± Z*(H/2)

### 3.4 途径点字段 (waypoints)

```json
{
  "id": "wp_1711263300001",
  "index": 0,                    // 顺序索引
  "position": [120.1, 30.5, 1500], // 经纬度 + 高度
  "label": "起点-杭州",
  "type": "checkpoint",          // checkpoint | waypoint | turnpoint
  "properties": {
    "holdingPattern": false,     // 是否是等待点
    "turnRadius": 5000,          // 转向半径 (米)
    "speedLimit": 450,           // 速度限制 (km/h)
    "procedure": "ILS"           // 进近程序
  }
}
```

**类型说明:**

| 类型 | 说明 | 用途 |
|------|------|------|
| `checkpoint` | 检查点 | 起点/终点 |
| `waypoint` | 转向点 | 中间路由点 |
| `turnpoint` | 转向点 | 强制转向点 |

### 3.5 限制区域字段 (restrictions)

```json
{
  "id": "res_001",
  "type": "noFly",               // noFly | restricted | warning
  "severity": "critical",        // critical | high | medium | low
  "reason": "空军禁区",
  "activeTime": "2026-03-23",   // 生效日期
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [120.15, 30.55],
        [120.25, 30.55],
        [120.25, 30.65],
        [120.15, 30.65],
        [120.15, 30.55]           // 必须闭合
      ]
    ]
  }
}
```

---

## 4. 数据操作示例

### 4.1 创建航路 (JavaScript)

```javascript
const newRoute = {
  id: `route_${Date.now()}`,
  name: "新航线",
  type: "commercial",
  priority: 1,
  enabled: true,
  created: new Date().toISOString(),
  modified: new Date().toISOString(),
  metadata: {
    maxAltitude: 5000,
    minAltitude: 500
  },
  geometry: {
    type: "RouteChannel3D",
    centerline: { 
      type: "LineString", 
      coordinates: [] 
    },
    profile: { 
      width: 2000, 
      height: 800, 
      widthUnit: "meters", 
      heightUnit: "meters" 
    }
  },
  waypoints: [],
  restrictions: []
};
```

### 4.2 添加途径点

```javascript
const waypoint = {
  id: `wp_${Date.now()}`,
  index: route.waypoints.length,
  position: [120.1, 30.5, 1500],
  label: `转向点${route.waypoints.length + 1}`,
  type: "waypoint",
  properties: {}
};

route.waypoints.push(waypoint);
route.geometry.centerline.coordinates = route.waypoints.map(wp => wp.position);
```

### 4.3 更新中心线

```javascript
function updateCenterline(route) {
  const coords = route.waypoints.map(wp => wp.position);
  route.geometry.centerline.coordinates = coords;
  route.modified = new Date().toISOString();
}
```

### 4.4 验证冲突

```javascript
function checkCollision(route, restrictedZone) {
  // 检查航路是否与禁飞区相交
  const centerline = route.geometry.centerline.coordinates;
  const width = route.geometry.profile.width;
  
  // 简单版: 检查中心线是否进入禁飞区
  return centerline.some(coord => {
    return pointInPolygon(coord, restrictedZone.geometry.coordinates[0]);
  });
}
```

---

## 5. 文件导入导出

### 5.1 导出为JSON

```javascript
function exportToFile() {
  const data = {
    version: "1.0",
    timestamp: new Date().toISOString(),
    routes: manager.routes
  };
  
  const blob = new Blob([JSON.stringify(data, null, 2)], 
    { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `routes_${new Date().getTime()}.json`;
  a.click();
}
```

### 5.2 从JSON导入

```javascript
function importFromFile(file) {
  const reader = new FileReader();
  reader.onload = (event) => {
    const data = JSON.parse(event.target.result);
    if (data.version === "1.0") {
      manager.routes = data.routes;
      manager.save();
    }
  };
  reader.readAsText(file);
}
```

---

## 6. 数据验证规则

### 6.1 必填项检查

```javascript
function validateRoute(route) {
  const errors = [];
  
  if (!route.id) errors.push('id 必填');
  if (!route.name) errors.push('name 必填');
  if (!route.type) errors.push('type 必填');
  if (!route.geometry) errors.push('geometry 必填');
  if (!Array.isArray(route.waypoints)) errors.push('waypoints 必须是数组');
  
  return errors;
}
```

### 6.2 坐标合法性

```javascript
function validateCoordinates(coords) {
  const [lon, lat, alt] = coords;
  
  if (lon < -180 || lon > 180) return false;
  if (lat < -90 || lat > 90) return false;
  if (alt < 0) return false;
  
  return true;
}
```

### 6.3 几何合理性

```javascript
function validateGeometry(route) {
  const coords = route.geometry.centerline.coordinates;
  
  // 至少2个途径点
  if (coords.length < 2) {
    return { valid: false, error: '至少需要2个途径点' };
  }
  
  // 检查所有坐标合法性
  for (let coord of coords) {
    if (!validateCoordinates(coord)) {
      return { valid: false, error: `不合法的坐标: ${coord}` };
    }
  }
  
  return { valid: true };
}
```

---

## 7. 扩展和升级指南

### 7.1 添加新字段

保持向后兼容:

```javascript
const routeWithNewField = {
  ...existingRoute,
  newField: {
    version: 1,
    data: {}
  }
};
```

### 7.2 版本迁移

```javascript
function migrateRoute(route, fromVersion, toVersion) {
  if (fromVersion === "1.0" && toVersion === "2.0") {
    // 添加新字段的默认值
    if (!route.metadata.newField) {
      route.metadata.newField = defaultValue;
    }
  }
  return route;
}
```

### 7.3 批量操作

```javascript
function batchUpdateRoutes(routes, updates) {
  return routes.map(route => ({
    ...route,
    ...updates,
    modified: new Date().toISOString()
  }));
}
```

---

## 8. 最佳实践

### 8.1 数据备份策略

```
实时数据 (localStorage)
    ↓
每5分钟自动备份 (IndexedDB)
    ↓
用户主动导出 (JSON文件)
    ↓
定期上传云端存储
```

### 8.2 命名规范

- **ID**: 使用时间戳 `route_1711263300000`
- **名称**: 包含起终点和方向 `杭州-上海北上通道`
- **变量**: 使用小驼峰 `routeManager`, `waypointList`

### 8.3 性能优化

- 单个航路文件限制在 10MB 以内
- 途径点数量不超过 1000 个
- 使用增量更新而非全量保存

---

## 9. 常见问题

**Q: 如何处理跨越国界线的航路?**
A: 在几何中断处添加特殊标记，坐标直接使用 ±180° 过渡

**Q: 高度如何处理?**
A: 所有高度采用相对海平面的海拔值 (米)

**Q: 如何实现时间限制?**
A: 在 restrictions 中使用 activeTime 字段标记生效日期

---

## 10. 联系方式

- 文档版本: 1.0
- 最后更新: 2026-03-23
- 系统支持: route-editor@example.com
