// 设备类别配置
const deviceCategories = [
    { 
        key: 'av', 
        name: '飞行器', 
        csvFile: 'data/av_drones.csv', 
        icon: 'mdi:drone',
        color: '#3b82f6',
        bgColor: 'bg-blue-500/10',
        textColor: 'text-blue-400',
        borderColor: 'border-blue-500'
    },
    { 
        key: 'com', 
        name: '通讯设备', 
        csvFile: 'data/com_devices.csv', 
        icon: 'mdi:radio-tower',
        color: '#10b981',
        bgColor: 'bg-green-500/10',
        textColor: 'text-green-400',
        borderColor: 'border-green-500'
    },
    { 
        key: 'nav', 
        name: '导航设备', 
        csvFile: 'data/nav_devices.csv', 
        icon: 'mdi:map-marker-path',
        color: '#8b5cf6',
        bgColor: 'bg-purple-500/10',
        textColor: 'text-purple-400',
        borderColor: 'border-purple-500'
    },
    { 
        key: 'sur', 
        name: '监视设备', 
        csvFile: 'data/sur_devices.csv', 
        icon: 'mdi:cctv',
        color: '#f59e0b',
        bgColor: 'bg-orange-500/10',
        textColor: 'text-orange-400',
        borderColor: 'border-orange-500'
    },
    { 
        key: 'ctr', 
        name: '反制设备', 
        csvFile: 'data/ctr_devices.csv', 
        icon: 'mdi:shield-alert',
        color: '#ef4444',
        bgColor: 'bg-red-500/10',
        textColor: 'text-red-400',
        borderColor: 'border-red-500'
    },
    { 
        key: 'wth', 
        name: '气象设备', 
        csvFile: 'data/wth_devices.csv', 
        icon: 'mdi:weather-partly-cloudy',
        color: '#06b6d4',
        bgColor: 'bg-cyan-500/10',
        textColor: 'text-cyan-400',
        borderColor: 'border-cyan-500'
    }
];

// 设备详情维度配置
const deviceDimensions = {
    'av': ['物理属性', '动力学特征', '感知能力', '能源续航', '决策闭环'],
    'com': ['静态属性', '通信性能', '传输能力', '运维适配'],
    'nav': ['静态属性', '定位性能', '信号适配', '运维参数'],
    'sur': ['静态属性', '探测性能', '跟踪适配', '运维保障'],
    'ctr': ['静态属性', '干扰性能', '适配范围', '运维参数'],
    'wth': ['静态属性', '探测性能', '数据传输', '运维保障']
};

// 设备属性映射
const deviceAttributeLabels = {
    // 飞行器属性
    'drone_id': '设备ID',
    'unique_product_code': '产品代码',
    'model_type': '型号',
    'manufacturer': '生产厂商',
    'manufacturer_code': '厂商代码',
    'nature': '设备性质',
    'product_type': '产品类型',
    'product_category': '产品类别',
    'registration_country': '注册国家',
    'real_name_reg_id': '实名注册号',
    'owner_type': '所有权类型',
    'airworthiness': '适航状态',
    'mass_empty': '空机重量(kg)',
    'mass_total_max': '最大起飞重量(kg)',
    'length_total': '全长(m)',
    'width_total': '全宽(m)',
    'height_total': '全高(m)',
    'rotor_count': '旋翼数量',
    'working_temp_range': '工作温度范围',
    'protection_level': '防护等级',
    'max_speed': '最大速度(m/s)',
    'cruise_speed': '巡航速度(m/s)',
    'climb_rate_typical': '典型爬升率(m/s)',
    'climb_rate_max': '最大爬升率(m/s)',
    'descent_rate_typical': '典型下降率(m/s)',
    'descent_rate_max': '最大下降率(m/s)',
    'turn_rate_typical': '典型转弯率(°/s)',
    'turn_rate_max': '最大转弯率(°/s)',
    'takeoff_landing_wind_resist': '起降抗风等级',
    'operation_wind_resist': '作业抗风等级',
    'control_frequency': '控制频率(GHz)',
    'navigation_mode': '导航模式',
    'autonomous_capability': '自主能力',
    'obstacle_avoidance': '避障能力',
    'sensor_list': '传感器列表',
    'electronic_fence': '电子围栏',
    'perception_range': '感知范围(m)',
    'flight_time_avg': '平均续航(分钟)',
    'flight_time_max': '最大续航(分钟)',
    'energy_type': '能源类型',
    'battery_capacity': '电池容量(mAh)',
    'battery_voltage': '电池电压(V)',
    'energy_consumption_rate': '能耗率(W)',
    'charging_time': '充电时间(分钟)',
    'observe_data_sources': '观测数据源',
    'orient_context': '态势认知',
    'decide_strategy': '决策策略',
    'act_command_types': '动作指令类型',
    'ooda_cycle_time': 'OODA循环时间(ms)',
    
    // 通用属性
    'image_filename': '图片文件',
    'status': '状态',
    'current_location': '当前位置',
    'last_update': '最后更新时间',
    '备注': '备注'
};

// Vue应用
const { createApp, ref, computed, onMounted, watch } = Vue;

const App = {
    template: `
        <div class="flex flex-col h-screen">
            <!-- 顶部导航栏 -->
            <header class="h-16 flex items-center justify-between px-6 border-b border-slate-700 glass-panel z-50">
                <div class="flex items-center gap-3">
                    <iconify-icon icon="material-symbols:airplanemode-active" class="text-3xl text-blue-400"></iconify-icon>
                    <h1 class="text-xl font-bold tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">基础模型管理子系统</h1>
                </div>
                <nav class="flex gap-1 h-full">
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">系统总览</a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">
                        <iconify-icon icon="lucide:map" class="mr-2"></iconify-icon>地理环境
                    </a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">
                        <iconify-icon icon="lucide:waves" class="mr-2"></iconify-icon>电磁环境
                    </a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">
                        <iconify-icon icon="lucide:cloud-sun" class="mr-2"></iconify-icon>气象环境
                    </a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">
                        <iconify-icon icon="lucide:layers" class="mr-2"></iconify-icon>空域航路
                    </a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800" href="#">
                        <iconify-icon icon="lucide:gavel" class="mr-2"></iconify-icon>飞行规则
                    </a>
                    <a class="flex items-center px-4 transition-all hover:bg-slate-800 nav-active" href="#">
                        <iconify-icon icon="lucide:database" class="mr-2"></iconify-icon>装备库
                    </a>
                </nav>
            </header>

            <!-- 主内容区 - 三栏布局 -->
            <div class="flex-1 flex overflow-hidden">
                <!-- 左侧边栏：设备分类导航 -->
                <aside class="w-80 glass-panel border-r border-slate-700 flex flex-col z-20">
                    <div class="p-4 border-b border-slate-800 bg-slate-900/40">
                        <h2 class="font-bold flex items-center gap-2">
                            <iconify-icon icon="lucide:box" class="text-blue-400"></iconify-icon> 
                            装备资源目录
                        </h2>
                    </div>
                    
                    <div class="flex-1 overflow-y-auto p-4">
                        <!-- 分类导航 -->
                        <div class="space-y-1">
                            <div v-for="category in deviceCategories" 
                                 :key="category.key"
                                 class="mb-6">
                                <div class="flex items-center justify-between p-3 rounded-lg cursor-pointer hover:bg-slate-800 transition-all"
                                     :class="{'bg-blue-500/20': activeCategory === category.key}"
                                     @click="toggleCategory(category.key)">
                                    <div class="flex items-center gap-3">
                                        <iconify-icon :icon="category.icon" class="text-xl" :class="category.textColor"></iconify-icon>
                                        <div>
                                            <h3 class="font-semibold">{{ category.name }}</h3>
                                            <p class="text-xs text-slate-400">{{ getDeviceCount(category.key) }} 个设备</p>
                                        </div>
                                    </div>
                                    <iconify-icon icon="lucide:chevron-right" 
                                                  class="transition-transform duration-200"
                                                  :class="{'rotate-90': isCategoryExpanded(category.key)}"></iconify-icon>
                                </div>
                                
                                <!-- 设备列表 -->
                                <div v-if="isCategoryExpanded(category.key)" class="mt-2 ml-8 space-y-1">
                                    <div v-for="device in getDevicesByCategory(category.key)" 
                                         :key="device.unique_product_code"
                                         class="flex items-center justify-between p-2 rounded cursor-pointer hover:bg-slate-800 transition-all"
                                         :class="{'bg-slate-800': selectedDevice && selectedDevice.unique_product_code === device.unique_product_code}"
                                         @click="selectDevice(device)">
                                        <div>
                                            <p class="text-sm">{{ device.model_type }}</p>
                                            <p class="text-xs text-slate-500">{{ device.unique_product_code }}</p>
                                        </div>
                                        <span class="text-xs px-2 py-1 rounded"
                                              :class="getStatusClass(device.status)">
                                            {{ device.status || '未知' }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 数据统计 -->
                    <div class="p-4 border-t border-slate-800">
                        <div class="grid grid-cols-2 gap-2 text-sm">
                            <div class="text-center p-3 rounded-lg bg-slate-900/50">
                                <p class="text-xs text-slate-400">设备总数</p>
                                <p class="text-xl font-bold">{{ totalDevices }}</p>
                            </div>
                            <div class="text-center p-3 rounded-lg bg-slate-900/50">
                                <p class="text-xs text-slate-400">在线设备</p>
                                <p class="text-xl font-bold text-green-400">{{ onlineDevices }}</p>
                            </div>
                        </div>
                        <button @click="loadAllData" 
                                class="w-full mt-3 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-bold flex items-center justify-center gap-2 transition"
                                :disabled="loading">
                            <iconify-icon icon="lucide:refresh-cw" :class="{'animate-spin': loading}"></iconify-icon>
                            {{ loading ? '加载中...' : '重新加载数据' }}
                        </button>
                    </div>
                </aside>

                <!-- 中间区域：设备预览 -->
                <main class="flex-1 relative map-bg overflow-hidden">
                    <!-- 网格背景 -->
                    <div class="absolute inset-0 grid-bg opacity-20"></div>
                    
                    <!-- 设备预览区域 -->
                    <div class="relative h-full flex items-center justify-center p-8">
                        <div v-if="selectedDevice" class="w-full max-w-4xl">
                            <!-- 设备标识 -->
                            <div class="mb-8 text-center">
                                <h2 class="text-3xl font-bold text-white">{{ selectedDevice.model_type }}</h2>
                                <p class="text-slate-400">{{ selectedDevice.manufacturer }}</p>
                                <div class="flex justify-center gap-2 mt-2">
                                    <span class="px-3 py-1 text-xs rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                        {{ selectedDevice.unique_product_code }}
                                    </span>
                                    <span :class="'px-3 py-1 text-xs rounded-full ' + getStatusClass(selectedDevice.status)">
                                        {{ selectedDevice.status || '未知' }}
                                    </span>
                                </div>
                            </div>
                            
                            <!-- 设备图片 -->
                            <div class="relative h-64 mb-8 rounded-xl overflow-hidden border-2 border-slate-700">
                                <img v-if="selectedDevice.image_filename" 
                                     :src="'images/' + getDeviceImagePath(selectedDevice)" 
                                     :alt="selectedDevice.model_type"
                                     class="w-full h-full object-contain p-4 bg-gradient-to-b from-slate-900 to-slate-950"
                                     @error="handleImageError">
                                <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-b from-slate-900 to-slate-950">
                                    <iconify-icon :icon="getDeviceIcon(selectedDevice)" class="text-8xl text-slate-700"></iconify-icon>
                                </div>
                                <div class="absolute inset-0 w-full h-[1px] bg-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.5)] top-0 animate-scan"></div>
                            </div>
                            
                            <!-- 核心参数 -->
                            <div class="grid grid-cols-3 gap-4 mb-8">
                                <div v-if="selectedDevice.mass_empty" class="glass-panel p-4 rounded-lg text-center">
                                    <p class="text-xs text-slate-400 mb-1">空机重量</p>
                                    <p class="text-xl font-bold">{{ selectedDevice.mass_empty }} <span class="text-sm text-slate-500">kg</span></p>
                                </div>
                                <div v-if="selectedDevice.working_temp_range" class="glass-panel p-4 rounded-lg text-center">
                                    <p class="text-xs text-slate-400 mb-1">工作温度</p>
                                    <p class="text-xl font-bold">{{ selectedDevice.working_temp_range }}</p>
                                </div>
                                <div v-if="selectedDevice.max_speed" class="glass-panel p-4 rounded-lg text-center">
                                    <p class="text-xs text-slate-400 mb-1">最大速度</p>
                                    <p class="text-xl font-bold">{{ selectedDevice.max_speed }}</p>
                                </div>
                            </div>
                            
                            <!-- 维度导航 -->
                            <div class="flex justify-center space-x-2 mb-8">
                                <button v-for="(dimension, index) in getDeviceDimensions(selectedDevice.category)" 
                                        :key="index"
                                        @click="activeDimension = index"
                                        :class="['px-4 py-2 rounded-lg transition-all', activeDimension === index ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700']">
                                    {{ dimension }}
                                </button>
                            </div>
                        </div>
                        
                        <!-- 无设备选中时的提示 -->
                        <div v-else class="text-center">
                            <iconify-icon icon="lucide:package" class="text-8xl text-slate-600 mb-4"></iconify-icon>
                            <h2 class="text-2xl text-slate-400 mb-2">请选择设备</h2>
                            <p class="text-slate-500">从左侧选择设备查看详细参数</p>
                        </div>
                    </div>
                </main>

                <!-- 右侧边栏：设备详情 -->
                <aside class="w-96 glass-panel border-l border-slate-700 flex flex-col overflow-hidden">
                    <div class="p-4 border-b border-slate-800 bg-slate-900/40">
                        <h2 class="font-bold flex items-center gap-2">
                            <iconify-icon icon="lucide:database" class="text-blue-400"></iconify-icon> 
                            装备五维模型数据
                        </h2>
                    </div>
                    
                    <div v-if="selectedDevice" class="flex-1 overflow-y-auto p-4">
                        <!-- 当前维度内容 -->
                        <div v-for="(dimension, index) in getDeviceDimensions(selectedDevice.category)" 
                             :key="index"
                             v-show="activeDimension === index">
                            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
                                <iconify-icon icon="lucide:layers" class="text-blue-400"></iconify-icon>
                                {{ dimension }}
                            </h3>
                            
                            <div class="space-y-3">
                                <!-- 根据维度和设备类型显示不同属性 -->
                                <div v-for="(value, key) in getDimensionAttributes(selectedDevice, index)" 
                                     :key="key"
                                     v-if="value"
                                     class="p-3 rounded-lg bg-slate-900/50 border border-slate-700/50">
                                    <p class="text-xs text-slate-400 mb-1">{{ getAttributeLabel(key) }}</p>
                                    <p class="text-sm">{{ value }}</p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 备注信息 -->
                        <div v-if="selectedDevice.备注" class="mt-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <p class="text-sm text-blue-400 font-semibold mb-2">系统备注</p>
                            <p class="text-slate-300">{{ selectedDevice.备注 }}</p>
                        </div>
                    </div>
                    
                    <div v-else class="flex-1 flex items-center justify-center p-4">
                        <div class="text-center text-slate-500">
                            <iconify-icon icon="lucide:info" class="text-3xl mb-3"></iconify-icon>
                            <p>请从左侧选择设备查看详细参数</p>
                        </div>
                    </div>
                    
                    <!-- 底部状态栏 -->
                    <div class="p-4 border-t border-slate-800 text-xs text-slate-500">
                        <p>数据源: CSV | 记录数: {{ totalDevices }} | 最后更新: {{ lastUpdateTime }}</p>
                    </div>
                </aside>
            </div>
        </div>
    `,
    
    setup() {
        // 状态管理
        const loading = ref(false);
        const allDevices = ref({});
        const selectedDevice = ref(null);
        const activeCategory = ref('av');
        const activeDimension = ref(0);
        const expandedCategories = ref({});
        const lastUpdateTime = ref('');
        const error = ref(null);
        
        // 计算属性
        const totalDevices = computed(() => {
            return Object.values(allDevices.value).reduce((total, devices) => total + devices.length, 0);
        });
        
        const onlineDevices = computed(() => {
            return Object.values(allDevices.value)
                .flat()
                .filter(device => device.status === '在线').length;
        });
        
        // 方法
        const loadCSVData = async (category) => {
            const categoryConfig = deviceCategories.find(c => c.key === category);
            if (!categoryConfig) return [];
            
            try {
                const response = await fetch(categoryConfig.csvFile);
                if (!response.ok) {
                    throw new Error(`无法加载 ${categoryConfig.csvFile}: ${response.status}`);
                }
                
                const csvText = await response.text();
                
                return new Promise((resolve) => {
                    Papa.parse(csvText, {
                        header: true,
                        skipEmptyLines: true,
                        complete: (results) => {
                            // 为每个设备添加类别标识
                            const devices = results.data.map(device => ({
                                ...device,
                                category: category
                            }));
                            
                            console.log(`成功加载 ${category}:`, devices.length, '条记录');
                            resolve(devices);
                        },
                        error: (err) => {
                            console.error(`解析 ${category} CSV 失败:`, err);
                            resolve([]);
                        }
                    });
                });
            } catch (err) {
                console.warn(`加载 ${category} CSV 失败:`, err.message);
                return [];
            }
        };
        
        const loadAllData = async () => {
            loading.value = true;
            error.value = null;
            
            try {
                const allData = {};
                for (const category of deviceCategories) {
                    allData[category.key] = await loadCSVData(category.key);
                }
                
                allDevices.value = allData;
                
                // 默认展开所有分类
                deviceCategories.forEach(cat => {
                    expandedCategories.value[cat.key] = true;
                });
                
                // 默认选择第一个设备
                const firstCategory = deviceCategories[0];
                if (allData[firstCategory.key] && allData[firstCategory.key].length > 0) {
                    selectedDevice.value = allData[firstCategory.key][0];
                    activeCategory.value = firstCategory.key;
                }
                
                lastUpdateTime.value = new Date().toLocaleString('zh-CN');
            } catch (err) {
                error.value = `数据加载失败: ${err.message}`;
                console.error('数据加载失败:', err);
            } finally {
                loading.value = false;
            }
        };
        
        const getDeviceCount = (category) => {
            return (allDevices.value[category] || []).length;
        };
        
        const getDevicesByCategory = (category) => {
            return allDevices.value[category] || [];
        };
        
        const isCategoryExpanded = (category) => {
            return expandedCategories.value[category] || false;
        };
        
        const toggleCategory = (category) => {
            expandedCategories.value[category] = !expandedCategories.value[category];
        };
        
        const selectDevice = (device) => {
            selectedDevice.value = device;
            activeCategory.value = device.category;
            activeDimension.value = 0;
        };
        
        const getStatusClass = (status) => {
            switch (status) {
                case '在线': return 'bg-green-500/20 text-green-400';
                case '离线': return 'bg-red-500/20 text-red-400';
                case '维护中': return 'bg-yellow-500/20 text-yellow-400';
                default: return 'bg-slate-500/20 text-slate-400';
            }
        };
        
        const getDeviceIcon = (device) => {
            const categoryConfig = deviceCategories.find(c => c.key === device.category);
            return categoryConfig ? categoryConfig.icon : 'lucide:package';
        };
        
        const getDeviceImagePath = (device) => {
            const categoryConfig = deviceCategories.find(c => c.key === device.category);
            if (!categoryConfig) return '';
            
            const categoryName = categoryConfig.key;
            const imageFileName = device.image_filename || 'default.jpg';
            
            return `${categoryName}_devices/${imageFileName}`;
        };
        
        const handleImageError = (event) => {
            event.target.style.display = 'none';
            const parent = event.target.parentElement;
            const placeholder = document.createElement('iconify-icon');
            placeholder.setAttribute('icon', getDeviceIcon(selectedDevice.value));
            placeholder.className = 'text-6xl text-slate-700';
            parent.appendChild(placeholder);
        };
        
        const getDeviceDimensions = (category) => {
            return deviceDimensions[category] || ['详情信息'];
        };
        
        const getDimensionAttributes = (device, dimensionIndex) => {
            const category = device.category;
            const dimensions = getDeviceDimensions(category);
            const dimension = dimensions[dimensionIndex];
            
            // 根据维度和设备类型返回对应的属性
            const attributes = {};
            
            switch (dimension) {
                case '物理属性':
                    if (device.mass_empty) attributes.mass_empty = device.mass_empty;
                    if (device.working_temp_range) attributes.working_temp_range = device.working_temp_range;
                    if (device.protection_level) attributes.protection_level = device.protection_level;
                    break;
                case '动力学特征':
                    if (device.max_speed) attributes.max_speed = device.max_speed;
                    if (device.cruise_speed) attributes.cruise_speed = device.cruise_speed;
                    break;
                // 其他维度的处理类似
                default:
                    // 返回前几个属性
                    Object.keys(device).slice(0, 5).forEach(key => {
                        if (device[key]) attributes[key] = device[key];
                    });
            }
            
            return attributes;
        };
        
        const getAttributeLabel = (key) => {
            return deviceAttributeLabels[key] || key;
        };
        
        // 生命周期
        onMounted(() => {
            loadAllData();
        });
        
        return {
            // 状态
            loading,
            allDevices,
            selectedDevice,
            activeCategory,
            activeDimension,
            lastUpdateTime,
            error,
            
            // 配置
            deviceCategories,
            
            // 计算属性
            totalDevices,
            onlineDevices,
            
            // 方法
            loadAllData,
            getDeviceCount,
            getDevicesByCategory,
            isCategoryExpanded,
            toggleCategory,
            selectDevice,
            getStatusClass,
            getDeviceIcon,
            getDeviceImagePath,
            handleImageError,
            getDeviceDimensions,
            getDimensionAttributes,
            getAttributeLabel
        };
    }
};

// 创建并挂载Vue应用
createApp(App).mount('#app');