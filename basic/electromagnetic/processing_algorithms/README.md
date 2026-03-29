# 电磁仿真数据处理算法说明

## 目录结构

```
processing_algorithms/
├── gen_em_data.py              # 初始版本数据生成脚本
├── gen_em_data_v2.py          # 数据生成脚本V2版
├── gen_em_data_range1.py      # 基于新仿真范围的数据生成（当前使用版本）
├── check_em.py                # 电磁数据检查脚本
└── check_data_diff.py         # 数据差异检查脚本
```

## 核心算法说明

### 1. 信号强度计算算法 (gen_em_data_range1.py)

#### 1.1 路径损耗模型 - 双斜率模型 (realistic_path_loss)

**算法原理**：
采用双斜率路径损耗模型（Two-Ray Ground Reflection Model），在近距离使用自由空间衰减，远距离使用更强的衰减。

**公式**：

```
FSPL = 20 * log10(d) + 20 * log10(f) + 27.55

if d <= d_break (1000m):
    Loss = FSPL + factor * 5
else:
    extra_loss = 15 * log10(d / d_break)
    Loss = FSPL + factor * (5 + extra_loss) + env_loss

env_loss = factor * log10(1 + d / 5000) * 10
```

**参数说明**：
- `d_break = 1000m`：断点距离，近/远距离的分界点
- `factor`：环境遮挡因子（根据信号源类型不同）
  - 5G基站: 2.5 (城市环境，遮挡较多)
  - 监视雷达: 1.8 (开阔地带，遮挡较少)
  - CORS站: 2.2 (中等遮挡)
  - UAV中继: 1.5 (高空，遮挡最少)
- `env_loss`：环境噪声底，模拟城市环境的随机衰减

**特点**：
- 近距离（<1km）：使用20*log10(d)的自由空间衰减
- 远距离（>1km）：使用35*log10(d)的强衰减
- 包含环境遮挡和随机噪声，更贴近真实场景

#### 1.2 信号叠加算法 (calc_signal)

**综合模式**：所有信号源的功率线性叠加（瓦特级别）

```
P_total(mW) = Σ P_i(mW)
P_total(dBm) = 10 * log10(P_total(mW))
```

**单源模式**：只计算指定类型的信号源

**算法流程**：
1. 遍历所有信号源
2. 计算每个源到网格点的3D距离
3. 使用双斜率模型计算路径损耗
4. 计算接收信号功率：P_rx = P_tx - Loss
5. 所有源的功率线性叠加
6. 转换为dBm表示

#### 1.3 干扰等级判定 (interference_level)

根据信号源类型使用不同的阈值：

| 信号源类型 | 严重(Severe) | 高(High) | 中(Medium) | 低(Low) |
|-----------|--------------|----------|-----------|---------|
| 综合模式 | > -90 dBm | > -100 dBm | > -108 dBm | ≤ -108 dBm |
| 5G基站 | > -100 dBm | > -110 dBm | > -118 dBm | ≤ -118 dBm |
| 监视雷达 | > -90 dBm | > -100 dBm | > -108 dBm | ≤ -108 dBm |
| CORS站 | > -100 dBm | > -110 dBm | > -118 dBm | ≤ -118 dBm |
| UAV中继 | > -120 dBm | > -128 dBm | > -135 dBm | ≤ -135 dBm |

#### 1.4 北斗格网编码 (bds_grid_code)

**格式**：`G{经度度数}{经度网格数}{纬度度数}{纬度网格数}H{高度层号}`

**示例**：`G11912303040H000` 表示119.123°E, 30.40°N, 0号高度层

**参数**：
- `GRID_SIZE = 0.0008°` (约88.8米)
- `GALT = 80m` (高度分层间隔)

### 2. 数据生成流程

#### 2.1 输入参数

```python
GRID_SIZE = 0.0008  # 网格大小（度）
GALT = 80          # 高度分层间隔（米）
HEIGHT_MAX = 400    # 最大高度（米）
HEIGHT_MIN = 0      # 最小高度（米）
```

#### 2.2 仿真范围

```python
SIM_BBOX = {
    'lon_min': 119.83406,
    'lon_max': 120.16090,
    'lat_min': 30.47767,
    'lat_max': 30.62491
}
```

#### 2.3 干扰源配置

20个干扰源，分为4种类型：

| 类型 | 数量 | 功率(W) | 频率(MHz) | 天线高度(m) |
|-----|------|---------|-----------|-----------|
| 5G基站 | 8 | 50 | 3500 | 30 |
| 监视雷达 | 4 | 2000 | 3000 | 30 |
| CORS站 | 5 | 10 | 1575.42 | 10 |
| UAV中继 | 3 | 5 | 2400 | 280-400 |

#### 2.4 数据输出格式

每个类型生成一个文件夹（`5g/`, `radar/`, `cors/`, `uav/`, `all/`），包含：

**index.json**：元数据文件
```json
{
  "meta": {
    "source_type": "5g",
    "source_label": "5G基站",
    "total_layers": 6,
    "total_points": 325740,
    "height_range_m": [0, 400],
    "galt_m": 80,
    "grid_size_deg": 0.0008,
    "grid_size_m": 88.8,
    "bbox": {...},
    "polygon": [...],
    "source_count": 8
  },
  "layers": [...],
  "sources": [...]
}
```

**layer_XXX_altYYYYm.json**：层数据文件
```json
{
  "meta": {
    "source_type": "5g",
    "layer_idx": 0,
    "alt_m": 0,
    "point_count": 54290
  },
  "data": [
    {
      "lon": 119.83446,
      "lat": 30.47788,
      "alt_m": 0,
      "signal_dbm": -95.3,
      "level": "MEDIUM",
      "grid_code": "G11912303040H000",
      "per_src": {...}
    }
  ]
}
```

#### 2.5 数据量统计

- 总层数：6层 (0, 80, 160, 240, 320, 400米)
- 每层点数：54,290点
- 每种类型总点数：325,740点
- 所有类型总点数：1,628,700点
- 单个数据文件大小：约23MB

### 3. 辅助脚本

#### 3.1 check_em.py

检查电磁数据的完整性和正确性。

#### 3.2 check_data_diff.py

比较不同版本或不同参数生成的数据差异。

#### 3.3 check_stats.py

数据统计分析脚本（位于data文件夹）。

## 性能优化

1. **多边形内点判断**：使用射线法（Ray Casting Algorithm）
2. **距离计算**：使用3D欧几里得距离
3. **批量生成**：一次性生成所有层数据，减少IO操作
4. **降采样**：网页显示时使用STEP=4的降采样

## 使用方法

### 生成新数据

```bash
cd C:\mgs\basic\electromagnetic\processing_algorithms
python gen_em_data_range1.py
```

### 修改参数

编辑 `gen_em_data_range1.py` 中的配置参数：

```python
# 修改仿真范围
SIM_BBOX = {'lon_min': ..., 'lon_max': ..., ...}

# 修改网格大小
GRID_SIZE = 0.0008  # 改为其他值

# 修改干扰源
EM_SOURCES = [
    # 添加/删除/修改信号源
]

# 修改高度分层
GALT = 80  # 改为其他值
HEIGHT_MAX = 400  # 改为其他值
```

## 注意事项

1. **数据量大**：生成全部数据可能需要较长时间（数分钟）
2. **内存占用**：每层数据约23MB，总数据量约1GB
3. **参数敏感**：改变GRID_SIZE会显著影响数据量和计算时间
4. **路径损耗**：不同环境的损耗因子需要根据实际场景调整

## 扩展方向

1. 支持更复杂的路径损耗模型（如ITU-R模型）
2. 添加地形遮挡计算
3. 支持动态信号源（如移动UAV）
4. 优化数据压缩（使用二进制格式）
