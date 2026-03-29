# 电磁仿真数据源系统说明

## 系统概述

本系统支持多个电磁环境数据源，可以快速切换不同的仿真场景，方便对比不同电磁环境下的干扰情况。

## 目录结构

```
electromagnetic/
├── data/                           # 默认数据文件夹（当前数据）
├── data_templates/                  # 数据源模板目录
│   └── template_001/              # 模板001
│       ├── data/                   # 数据文件
│       │   ├── 5g/             # 5G基站信号数据
│       │   ├── radar/           # 监视雷达信号数据
│       │   ├── cors/            # CORS站信号数据
│       │   ├── uav/             # UAV中继信号数据
│       │   └── all/             # 综合信号数据
│       └── README.md             # 数据源说明文档
├── processing_algorithms/           # 数据处理算法
│   ├── gen_em_data_range1.py   # 数据生成脚本（当前使用）
│   ├── gen_em_data.py          # 初始版本
│   ├── gen_em_data_v2.py      # V2版本
│   ├── check_em.py            # 数据检查
│   ├── check_data_diff.py     # 数据差异检查
│   └── README.md             # 算法说明文档
└── electromagnetic.html            # 网页（支持数据源切换）
```

## 数据源类型

### 模板001: 标准城市环境

- **编号**: 001
- **名称**: template_001
- **场景**: 标准/郊区混合电磁环境
- **仿真范围**:
  - 经度: 119.83°E ~ 120.16°E
  - 纬度: 30.48°N ~ 30.62°N
  - 面积: 约600km²
- **高度范围**: 0m ~ 400m
- **干扰源数量**: 20个
  - 5G基站: 8个
  - 监视雷达: 4个
  - CORS站: 5个
  - UAV中继: 3个
- **数据量**:
  - 总层数: 6层
  - 每层格点: 54,290点
  - 总格点数: 1,628,700点
  - 数据大小: 约1GB

## 使用方法

### 1. 创建新数据源

#### 步骤1: 复制模板
```bash
copy data_templates\template_001 data_templates\template_002
```

#### 步骤2: 修改参数
编辑 `processing_algorithms/gen_em_data_range1.py`：

```python
# 修改仿真范围
SIM_BBOX = {
    'lon_min': 119.83406,
    'lon_max': 120.16090,
    'lat_min': 30.47767,
    'lat_max': 30.62491
}

# 修改网格大小
GRID_SIZE = 0.0008  # 改为其他值（如0.0004提高精度）

# 修改高度范围
HEIGHT_MAX = 400  # 改为其他值（如600增加层数）

# 修改干扰源
EM_SOURCES = [
    # 添加/删除/修改信号源
    {'name': '新信号源', 'lon': 120.0, 'lat': 30.5, ...}
]
```

#### 步骤3: 生成数据
```bash
cd processing_algorithms
python gen_em_data_range1.py
```

#### 步骤4: 更新网页
编辑 `electromagnetic.html`，在下拉框中添加新选项：

```html
<select id="dataSourceSelect" onchange="switchDataSource(this.value)">
  <option value="001">模板001: 标准城市环境</option>
  <option value="002">模板002: 新环境（自定义）</option>
</select>
```

### 2. 切换数据源

在网页中：
1. 打开左侧面板
2. 在"数据源选择"下拉框中选择不同的模板
3. 系统自动切换到对应的数据源
4. 网格信息、干扰源位置、热力图数据都会更新

### 3. 验证数据

使用检查脚本：
```bash
cd processing_algorithms
python check_em.py
```

## 数据处理算法

### 核心算法

1. **路径损耗模型**: 双斜率模型（Two-Ray Ground Reflection Model）
   - 近距离（<1km）: 自由空间衰减 20*log10(d)
   - 远距离（>1km）: 强衰减 35*log10(d)
   - 包含环境遮挡因子和随机噪声

2. **信号叠加**: 瓦特级线性叠加
   ```
   P_total(dBm) = 10 * log10(Σ P_i(mW))
   ```

3. **干扰等级判定**: 根据信号强度划分4个等级
   - SEVERE（严重）
   - HIGH（高）
   - MEDIUM（中）
   - LOW（低）

详细说明见 `processing_algorithms/README.md`

## 扩展建议

### 不同场景的参数配置

| 场景 | GRID_SIZE | GALT(m) | HEIGHT_MAX(m) | 特点 |
|-----|-----------|----------|--------------|-----|
| 城市密集区 | 0.0004 (44m) | 40 | 300 | 高精度，多遮挡 |
| 开阔郊区 | 0.0010 (110m) | 100 | 500 | 低精度，少遮挡 |
| 山区 | 0.0015 (165m) | 150 | 800 | 大范围，地形复杂 |
| 海岸线 | 0.0008 (88m) | 80 | 400 | 标准精度，混合环境 |

### 未来扩展方向

1. 支持地形数据（DEM）
2. 添加建筑物遮挡计算
3. 支持动态信号源（如移动UAV）
4. 数据压缩优化（使用二进制格式）
5. 自动参数优化工具

## 文档参考

- **数据源说明**: `data_templates/template_001/README.md`
- **算法详解**: `processing_algorithms/README.md`
- **数据生成**: `processing_algorithms/gen_em_data_range1.py`
- **检查工具**: `processing_algorithms/check_em.py`

## 注意事项

1. **数据量大**: 生成全部数据可能需要较长时间（数分钟）
2. **内存占用**: 每层数据约23MB，总数据量约1GB
3. **参数敏感**: 改变GRID_SIZE会显著影响数据量和计算时间
4. **路径损耗**: 不同环境的损耗因子需要根据实际场景调整
5. **缓存策略**: 切换数据源时会清空缓存，首次加载较慢

## 版本历史

| 版本 | 日期 | 说明 |
|-----|------|-----|
| 1.0 | 2026-03-22 | 初始版本，支持多数据源切换 |

## 联系方式

如有问题或建议，请联系技术支持团队。
