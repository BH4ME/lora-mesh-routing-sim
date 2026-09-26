import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  Antenna,
  BarChart3,
  Bluetooth,
  BookOpenCheck,
  BrainCircuit,
  Cable,
  Check,
  ChevronRight,
  CircuitBoard,
  Cloud,
  Cpu,
  Download,
  FileCode2,
  Flashlight,
  Github,
  Globe2,
  HardDriveDownload,
  Info,
  Layers3,
  MonitorDot,
  Network,
  PlugZap,
  Radio,
  RefreshCw,
  Route,
  Router,
  Save,
  Settings2,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Terminal,
  Usb,
  Wifi,
  Zap
} from 'lucide-react';
import {
  detectEspChip,
  flashEspTarget,
  formatError,
  hasWebBluetooth,
  hasWebSerial,
  loadReleaseManifest,
  loadTargetManifest,
  openBleUartConsole,
  openSerialConsole,
  sendWifiConfigCommand,
  type BleSession,
  type ReleaseManifest,
  type SerialSession,
  type TargetManifest
} from './deviceApi';
import './styles.css';

type RouteKey = 'home' | 'flash' | 'config' | 'research' | 'docs' | 'releases';
type TargetId = 'esp32dev_sx1262' | 'esp32dev_sx127x' | 'nrf52840_sx1262';
type FirmwareId = 'v2.0.0-stable' | 'v2.1.0-alpha' | 'custom';
type TransportId = 'serial' | 'ble' | 'wifi';
type ProtocolId = 'meshtastic-like' | 'meshcore-like' | 'meshecho';
type ChartMetricId = 'unicast_pdr' | 'total_airtime_s' | 'collision_fail';
type Language = 'en' | 'zh';

interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (text: string) => string;
}

interface Target {
  id: TargetId;
  name: string;
  chip: string;
  radio: string;
  architecture: string;
  support: 'Ready' | 'Planned';
  flashMode: 'esptool-js' | 'uf2-dfu';
  note: string;
  pins: string;
}

interface Firmware {
  id: FirmwareId;
  label: string;
  channel: string;
  date: string;
  notes: string[];
}

interface ConfigFormState {
  node_id: string;
  callsign: string;
  region: string;
  freq_mhz: string;
  bw_khz: string;
  sf: string;
  cr: string;
  tx_power: string;
  max_hops: string;
  route_ttl_s: string;
  fallback_ttl: string;
  ack_timeout_ms: string;
  ble: boolean;
  wifi: boolean;
}

interface DeviceSummaryState {
  firmware: string;
  target: string;
  chip: string;
  radio: string;
  uptime_ms: number | null;
  active_profile: string;
}

interface DeviceConfigPayload {
  node_id?: number;
  callsign?: string;
  region?: string;
  freq_mhz?: number;
  bw_khz?: number;
  sf?: number;
  cr?: number;
  tx_power?: number;
  max_hops?: number;
  route_ttl_s?: number;
  fallback_ttl?: number;
  ack_timeout_ms?: number;
  ble?: boolean;
  wifi?: boolean;
}

interface DeviceResponsePayload {
  ok?: boolean;
  version?: string;
  target?: string;
  chip?: string;
  radio?: string;
  uptime_ms?: number;
  active_profile?: string;
  config?: DeviceConfigPayload;
  error?: string;
}

interface ConfigFieldDefinition {
  key: keyof ConfigFormState;
  label: string;
  command: string;
  type?: 'text' | 'number' | 'toggle';
  unit?: string;
}

interface ConfigGroupDefinition {
  title: string;
  icon: React.ElementType;
  fields: ConfigFieldDefinition[];
}

const zhText: Record<string, string> = {
  Official: '官网',
  'Web Flasher': '网页烧录',
  Configure: '配置',
  Research: '研究',
  Docs: '文档',
  Releases: '发布',
  'Field console': '现场控制台',
  'Go to home': '回到首页',
  Primary: '主导航',
  'Switch language': '切换语言',
  English: '英语',
  Chinese: '中文',
  'RF bench and field kit': '射频工作台与现场工具箱',
  'Flash ESP32 LoRa targets, inspect release manifests, tune the command protocol, and keep device output visible while the radio work is still in your hands.':
    '烧录 ESP32 LoRa 目标板，检查发布清单，调整命令协议，并在调试无线电时持续查看设备输出。',
  'ready ESP32 targets': '个可用 ESP32 目标',
  'config transports': '种配置传输方式',
  'UI console': '界面控制台',
  'Open flasher': '打开烧录器',
  'Tune device': '调整设备',
  'View research': '查看研究',
  'Operating flow': '操作流程',
  'One console for the moments that can brick or fix a node': '一个控制台，处理可能修好或刷坏节点的关键步骤',
  'The first screen stays honest about hardware state: choose a target, check artifacts, connect a transport, then send commands with logs in view.':
    '首屏直接呈现硬件状态：选择目标板，检查固件产物，连接传输方式，再在日志可见的情况下发送命令。',
  Orient: '定位',
  'Know what MeshEcho is, which radios it supports, and where the research and firmware notes live.':
    '了解 MeshEcho 是什么，支持哪些无线电，以及研究与固件说明放在哪里。',
  Flash: '烧录',
  'Select the exact board, verify the manifest gate, detect the ESP chip, and keep the serial monitor nearby.':
    '选择准确的开发板，确认清单检查，通过 ESP 芯片检测，并保持串口监视器在旁边。',
  'Use USB Serial first, then BLE UART or WiFi HTTP when firmware exposes those transport paths.':
    '优先使用 USB Serial，固件开放后再使用 BLE UART 或 WiFi HTTP。',
  Compare: '对比',
  'Show the MeshEcho paper algorithm and compare it against Meshtastic-like and MeshCore-like baselines.':
    '展示 MeshEcho 论文算法，并与 Meshtastic-like 和 MeshCore-like 基线对比。',
  'Firmware reality': '固件现实',
  'MeshEcho is the routing layer and the workbench': 'MeshEcho 同时是路由层和工作台',
  'The UI presents the paper algorithm under the MeshEcho name, with route confidence and redundancy shown where they help users reason about the result.':
    '界面以 MeshEcho 名称呈现论文算法，并在有助于理解结果的位置展示路由置信度和冗余机制。',
  'Release gate': '发布门禁',
  'MeshEcho should be useful before hardware is connected, then progressively unlock flashing and configuration as real device endpoints respond.':
    'MeshEcho 在未连接硬件时也应有用，并在真实设备端点响应后逐步解锁烧录与配置能力。',
  'Route confidence': '路由置信度',
  'ACK aware': 'ACK 感知',
  'Animated mesh network diagram': '动态 mesh 网络示意图',
  'Rescue bounded': '受限救援',
  'Console ready': '控制台就绪',
  'Targets ready': '目标就绪',
  'Config transports': '配置传输',
  'Manifest layers': '清单层级',
  'nRF52 planned': 'nRF52 计划中',
  'Meshtastic-style flashing, rebuilt for MeshEcho': 'Meshtastic-style 网页烧录流程，为 MeshEcho 重建',
  'Select a board, choose a firmware release, pass manifest preflight, flash over Web Serial, then inspect serial logs.':
    '选择开发板和固件版本，通过清单预检，经 Web Serial 烧录，然后查看串口日志。',
  Device: '设备',
  'Target first': '先选目标',
  Firmware: '固件',
  'Release notes': '发布说明',
  'I reviewed target compatibility and release notes.': '我已检查目标兼容性和发布说明。',
  'Selected target': '已选目标',
  'Device target selected': '已选择设备目标',
  'Firmware selected': '已选择固件',
  Manifest: '清单',
  'Manifest not loaded': '清单尚未加载',
  'Loading release manifest...': '正在加载发布清单...',
  'manifest loaded': '清单已加载',
  'target manifest loaded': '目标清单已加载',
  'Loading target manifest...': '正在加载目标清单...',
  'Firmware artifacts ready': '固件产物就绪',
  'Firmware artifacts are placeholders': '固件产物仍是占位文件',
  'Release notes accepted': '已确认发布说明',
  'Serial monitor closed': '串口监视器已关闭',
  'Board support ready': '开发板支持就绪',
  'Full erase and install': '全擦除并安装',
  'Destructive. Use for clean lab demos or major firmware changes.': '会清除设备内容。适合干净演示或重大固件变更。',
  'Detect ESP Chip': '检测 ESP 芯片',
  'Start Web Serial Flash': '开始 Web Serial 烧录',
  'Resolve preflight first': '先处理预检项',
  'Show manifest status': '显示清单状态',
  'Flash progress': '烧录进度',
  'Serial monitor': '串口监视器',
  Connected: '已连接',
  Closed: '已关闭',
  Waiting: '等待中',
  'Device accepted command': '设备已接受命令',
  'Device rejected command': '设备已拒绝命令',
  'Close monitor': '关闭监视器',
  'Open monitor': '打开监视器',
  'Web Config': '网页配置',
  'One control console for serial, BLE, and WiFi': '一个控制台管理 Serial、BLE 与 WiFi',
  'The UI is ready for all three transports while clearly showing which firmware endpoints still need to land.':
    '界面已准备好三种传输方式，并清楚标明哪些固件端点仍待实现。',
  Transport: '传输',
  'USB Serial': 'USB Serial',
  Ready: '就绪',
  'Production path for firmware v2. Uses Web Serial in Chromium browsers.':
    '固件 v2 的主路径，在 Chromium 浏览器中使用 Web Serial。',
  'BLE UART': 'BLE UART',
  'Web client ready': '网页客户端就绪',
  'Nordic UART client is implemented; firmware still needs to expose the NUS service.':
    'Nordic UART 客户端已实现，固件仍需暴露 NUS 服务。',
  'WiFi Web': 'WiFi Web',
  'HTTP endpoint': 'HTTP 端点',
  'Uses POST /api/config on a MeshEcho SoftAP or LAN endpoint. Raw UDP is not browser-compatible.':
    '通过 MeshEcho SoftAP 或 LAN 端点调用 POST /api/config；浏览器不支持原始 UDP。',
  'Connect Serial': '连接 Serial',
  'Disconnect Serial': '断开 Serial',
  'Connect BLE UART': '连接 BLE UART',
  'Disconnect BLE': '断开 BLE',
  'Use WiFi Endpoint': '使用 WiFi 端点',
  'No device response yet': '尚无设备响应',
  'Serial connected': 'Serial 已连接',
  'BLE connected': 'BLE 已连接',
  'WiFi endpoint': 'WiFi 端点',
  'Device summary': '设备摘要',
  Uptime: '运行时间',
  Profile: '配置档',
  Protocol: '协议',
  Identity: '身份',
  'LoRa Radio': 'LoRa 无线电',
  'Mesh Control': 'Mesh 控制',
  Interfaces: '接口',
  'Serial protocol': '串口协议',
  'Node ID': '节点 ID',
  Callsign: '呼号',
  'Region profile': '区域配置',
  Frequency: '频率',
  Bandwidth: '带宽',
  'Spreading factor': '扩频因子',
  'Coding rate': '编码率',
  'TX power': '发射功率',
  'Max hops': '最大跳数',
  'Route TTL': '路由 TTL',
  'Fallback TTL': '回退 TTL',
  'ACK timeout': 'ACK 超时',
  On: '开',
  Off: '关',
  'Read From Device': '从设备读取',
  'Write & Save': '写入并保存',
  'Raw console': '原始控制台',
  Preview: '预览',
  'Live serial': '实时串口',
  Stable: '稳定版',
  Alpha: 'Alpha',
  Developer: '开发者',
  Next: '下一版',
  Local: '本地',
  'Primary MeshEcho v2 target. Web Serial flashing is enabled when artifacts are published.':
    'MeshEcho v2 主目标板；固件产物发布后可通过 Web Serial 烧录。',
  'Compatible ESP32 route for RFM95/RFM96 style modules with the alternate PlatformIO env.':
    '面向 RFM95/RFM96 类模块的兼容 ESP32 路径，使用备用 PlatformIO 环境。',
  'Planned after a concrete bootloader and board profile are selected.': '选定具体 bootloader 与开发板配置后再支持。',
  'Board-specific UF2/DFU profile required': '需要板级 UF2/DFU 配置',
  'MeshEcho firmware v2.0.0': 'MeshEcho firmware v2.0.0',
  'MeshEcho firmware v2.1.0 alpha': 'MeshEcho firmware v2.1.0 alpha',
  'Custom local build': '自定义本地构建',
  'MeshEcho direct-LoRa data plane': 'MeshEcho direct-LoRa 数据平面',
  'ESP32 SX1262 and SX127x build targets': 'ESP32 SX1262 与 SX127x 构建目标',
  'Manifest-ready artifacts for Web Flasher': '适配 Web Flasher 清单的固件产物',
  'Planned serial configuration protocol': '计划中的串口配置协议',
  'Device capability report for Web Config': '面向 Web Config 的设备能力报告',
  'BLE UART transport preparation': 'BLE UART 传输准备',
  'Upload a local .bin or release bundle': '上传本地 .bin 或发布包',
  'Use only with a matching board and pin profile': '仅用于匹配的开发板与引脚配置',
  'Flash logs remain downloadable': '烧录日志仍可下载',
  Documentation: '文档',
  'A field manual for a browser-first firmware': '面向浏览器优先固件的现场手册',
  'Short, operational docs for flashing, wiring, configuration, and troubleshooting.':
    '用于烧录、接线、配置和排错的简短操作文档。',
  'Quick start': '快速开始',
  'Flash ESP32 target, open serial monitor, send a test packet.': '烧录 ESP32 目标，打开串口监视器，发送测试包。',
  Wiring: '接线',
  'SX1262 and SX127x pin profiles stay separate to avoid wrong-radio flashing.':
    'SX1262 与 SX127x 引脚配置分开，避免烧录到错误无线电配置。',
  'Config protocol': '配置协议',
  'Shared JSON-line/text command layer for Serial, BLE, and WiFi.':
    'Serial、BLE 与 WiFi 共用 JSON-line/text 命令层。',
  'Browser support': '浏览器支持',
  'Chromium first; manual firmware download fallback for Safari/iOS.':
    '优先支持 Chromium；Safari/iOS 使用手动下载固件作为后备。',
  'Manifest-driven firmware artifacts': '由清单驱动的固件产物',
  UI: '界面',
  'reads release-level and target-level manifests so firmware URLs, offsets, and checksums stay out of UI code.':
    '读取发布级与目标级清单，让固件 URL、偏移量和校验和不写进界面代码。',
  Target: '目标',
  Mode: '模式',
  Status: '状态',
  Planned: '计划中',
  'MeshEcho paper algorithm, shown as a working result': 'MeshEcho 论文算法，以工作结果展示',
  'The web surface now carries the same comparison story as the paper: confidence-aware cached routing with bounded fallback, measured against Meshtastic-like flooding and MeshCore-like cached routing.':
    '网页现在承载与论文一致的对比叙事：带置信度的缓存路由与有界回退，并与 Meshtastic-like 洪泛和 MeshCore-like 缓存路由对比。',
  'Mixed-traffic PDR': '混合流量 PDR',
  'Airtime cut vs Meshtastic': '相对 Meshtastic 的 airtime 降低',
  'Collision cut vs MeshCore': '相对 MeshCore 的碰撞降低',
  'Seeds per scenario': '每个场景 seeds',
  'MeshEcho v2 algorithm': 'MeshEcho v2 算法',
  'paper model': '论文模型',
  'MeshEcho keeps a cached-route fast path, but makes every forwarding choice pass through a confidence gate. The gate weighs route age, hop cost, ACK feedback, and local link evidence before spending airtime on rescue or discovery traffic.':
    'MeshEcho 保留缓存路由快路径，但每次转发都要经过置信度门控。这个门控会权衡路由年龄、跳数成本、ACK 反馈和本地链路证据，再决定是否为救援或发现流量花费 airtime。',
  'Observe link evidence': '观测链路证据',
  'Collect ACK delivery, route age, hop count, RSSI/SNR-like reception evidence, and cached path outcomes.':
    '收集 ACK 投递、路由年龄、跳数、RSSI/SNR 类接收证据，以及缓存路径结果。',
  'Score route confidence': '评估路由置信度',
  'Estimate whether a cached route is still worth using instead of spending airtime on wide flooding.':
    '判断缓存路由是否仍值得使用，而不是花费 airtime 进行广域洪泛。',
  'Bound rescue traffic': '约束救援流量',
  'If confidence falls or ACKs fail, trigger a limited fallback path instead of letting retries grow without control.':
    '当置信度下降或 ACK 失败时，触发受限回退路径，而不是让重试无限增长。',
  'Adapt policy online': '在线调整策略',
  'Update the active profile during the run, balancing delivery reward against airtime and collision cost.':
    '运行过程中更新活动配置档，在投递收益、airtime 成本和碰撞成本之间平衡。',
  'Decision loop': '决策循环',
  'runtime sketch': '运行时草图',
  'for each packet:': 'for each packet:',
  '  update link evidence from ACK, age, hops, RSSI/SNR': '  update link evidence from ACK, age, hops, RSSI/SNR',
  '  score cached route confidence': '  score cached route confidence',
  '  if confidence is high: send cached unicast': '  if confidence is high: send cached unicast',
  '  if ACK fails: try bounded rescue/fallback': '  if ACK fails: try bounded rescue/fallback',
  '  reward = delivery - airtime cost - collision cost': '  reward = delivery - airtime cost - collision cost',
  '  update active policy profile': '  update active policy profile',
  'Protocol comparison': '协议对比',
  'MeshEcho keeps reliability high while spending less channel time': 'MeshEcho 保持高可靠性，同时减少信道占用',
  'Values are scenario means from the current simulator comparison: 50 nodes, 3000 m area, 1200 s, mixed traffic, pair-count 8, 20 seeds.':
    '数值为当前模拟器对比的场景均值：50 个节点、3000 m 区域、1200 s、混合流量、pair-count 8、20 个 seeds。',
  'Unicast PDR': '单播 PDR',
  'Total airtime': '总 airtime',
  'Collision failures': '碰撞失败',
  'Higher is better': '越高越好',
  'Lower is better': '越低越好',
  'Mixed traffic': '混合流量',
  '50 nodes, 3000 m, 1200 s, pair-count 8, 20 seeds': '50 节点，3000 m，1200 s，pair-count 8，20 seeds',
  'High shadowing': '高阴影衰落',
  'Same topology with stronger log-normal shadowing': '相同拓扑，更强的对数正态阴影衰落',
  'High offered load': '高提供负载',
  'Mixed traffic with higher offered packet rate': '更高发包率的混合流量',
  'Scenario table': '场景表',
  means: '均值',
  Scenario: '场景',
  Airtime: 'Airtime',
  Collisions: '碰撞',
  ratio: '比值',
  'bar chart': '柱状图'
};

function translateText(language: Language, text: string): string {
  return language === 'zh' ? zhText[text] ?? text : text;
}

function translateManifestStatus(t: I18nContextValue['t'], status: string): string {
  const loadingTarget = status.match(/^Loading (.+) manifest\.\.\.$/);
  if (loadingTarget && loadingTarget[1] !== 'release') {
    return `${t('Loading target manifest...')} (${loadingTarget[1]})`;
  }
  const targetLoaded = status.match(/^(.+) target manifest loaded$/);
  if (targetLoaded) {
    return `${targetLoaded[1]} ${t('target manifest loaded')}`;
  }
  const manifestLoaded = status.match(/^(.+) manifest loaded$/);
  if (manifestLoaded) {
    return `${manifestLoaded[1]} ${t('manifest loaded')}`;
  }
  return t(status);
}

const I18nContext = React.createContext<I18nContextValue>({
  language: 'en',
  setLanguage: () => undefined,
  t: (text) => text
});

function useI18n(): I18nContextValue {
  return React.useContext(I18nContext);
}

const targets: Target[] = [
  {
    id: 'esp32dev_sx1262',
    name: 'ESP32 DevKit + SX1262',
    chip: 'ESP32',
    radio: 'SX1262',
    architecture: 'ESP32',
    support: 'Ready',
    flashMode: 'esptool-js',
    note: 'Primary MeshEcho v2 target. Web Serial flashing is enabled when artifacts are published.',
    pins: 'NSS 18 / DIO1 26 / RST 14 / BUSY 27'
  },
  {
    id: 'esp32dev_sx127x',
    name: 'ESP32 DevKit + SX127x/RFM9x',
    chip: 'ESP32',
    radio: 'SX127x',
    architecture: 'ESP32',
    support: 'Ready',
    flashMode: 'esptool-js',
    note: 'Compatible ESP32 route for RFM95/RFM96 style modules with the alternate PlatformIO env.',
    pins: 'NSS 18 / DIO0 26 / RST 14 / DIO1 27'
  },
  {
    id: 'nrf52840_sx1262',
    name: 'nRF52840 + SX1262',
    chip: 'nRF52840',
    radio: 'SX1262',
    architecture: 'nRF52',
    support: 'Planned',
    flashMode: 'uf2-dfu',
    note: 'Planned after a concrete bootloader and board profile are selected.',
    pins: 'Board-specific UF2/DFU profile required'
  }
];

const firmwares: Firmware[] = [
  {
    id: 'v2.0.0-stable',
    label: 'MeshEcho firmware v2.0.0',
    channel: 'Stable',
    date: '2026-06-05',
    notes: [
      'MeshEcho direct-LoRa data plane',
      'ESP32 SX1262 and SX127x build targets',
      'Manifest-ready artifacts for Web Flasher'
    ]
  },
  {
    id: 'v2.1.0-alpha',
    label: 'MeshEcho firmware v2.1.0 alpha',
    channel: 'Alpha',
    date: 'Next',
    notes: [
      'Planned serial configuration protocol',
      'Device capability report for Web Config',
      'BLE UART transport preparation'
    ]
  },
  {
    id: 'custom',
    label: 'Custom local build',
    channel: 'Developer',
    date: 'Local',
    notes: [
      'Upload a local .bin or release bundle',
      'Use only with a matching board and pin profile',
      'Flash logs remain downloadable'
    ]
  }
];

const defaultConfigForm: ConfigFormState = {
  node_id: '1',
  callsign: 'BH4ME',
  region: 'US915',
  freq_mhz: '915.0',
  bw_khz: '125',
  sf: '9',
  cr: '7',
  tx_power: '17',
  max_hops: '6',
  route_ttl_s: '600',
  fallback_ttl: '2',
  ack_timeout_ms: '1800',
  ble: true,
  wifi: false
};

const defaultDeviceSummary: DeviceSummaryState = {
  firmware: 'v2.0.0',
  target: 'esp32dev_sx1262',
  chip: 'ESP32',
  radio: 'SX1262',
  uptime_ms: null,
  active_profile: 'balanced'
};

const configGroups: ConfigGroupDefinition[] = [
  {
    title: 'Identity',
    icon: Cpu,
    fields: [
      { key: 'node_id', label: 'Node ID', command: 'node_id', type: 'number' },
      { key: 'callsign', label: 'Callsign', command: 'callsign' },
      { key: 'region', label: 'Region profile', command: 'region' }
    ]
  },
  {
    title: 'LoRa Radio',
    icon: Radio,
    fields: [
      { key: 'freq_mhz', label: 'Frequency', command: 'freq_mhz', type: 'number', unit: 'MHz' },
      { key: 'bw_khz', label: 'Bandwidth', command: 'bw_khz', type: 'number', unit: 'kHz' },
      { key: 'sf', label: 'Spreading factor', command: 'sf', type: 'number' },
      { key: 'cr', label: 'Coding rate', command: 'cr', type: 'number' },
      { key: 'tx_power', label: 'TX power', command: 'tx_power', type: 'number', unit: 'dBm' }
    ]
  },
  {
    title: 'Mesh Control',
    icon: Network,
    fields: [
      { key: 'max_hops', label: 'Max hops', command: 'max_hops', type: 'number' },
      { key: 'route_ttl_s', label: 'Route TTL', command: 'route_ttl_s', type: 'number', unit: 's' },
      { key: 'fallback_ttl', label: 'Fallback TTL', command: 'fallback_ttl', type: 'number' },
      { key: 'ack_timeout_ms', label: 'ACK timeout', command: 'ack_timeout_ms', type: 'number', unit: 'ms' }
    ]
  },
  {
    title: 'Interfaces',
    icon: SlidersHorizontal,
    fields: [
      { key: 'ble', label: 'BLE UART', command: 'ble', type: 'toggle' },
      { key: 'wifi', label: 'WiFi Web', command: 'wifi', type: 'toggle' }
    ]
  }
];

const navItems: Array<{ id: RouteKey; label: string }> = [
  { id: 'home', label: 'Official' },
  { id: 'flash', label: 'Web Flasher' },
  { id: 'config', label: 'Configure' },
  { id: 'research', label: 'Research' },
  { id: 'docs', label: 'Docs' },
  { id: 'releases', label: 'Releases' }
];

const appVersion = '1.0.1';
const languageStorageKey = 'meshecho-language';

function initialLanguage(): Language {
  if (typeof window === 'undefined') {
    return 'en';
  }
  return window.localStorage.getItem(languageStorageKey) === 'zh' ? 'zh' : 'en';
}

const protocolLabels: Record<ProtocolId, string> = {
  'meshtastic-like': 'Meshtastic-like',
  'meshcore-like': 'MeshCore-like',
  meshecho: 'MeshEcho'
};

const researchScenarios: Array<{
  key: string;
  label: string;
  note: string;
  values: Record<ProtocolId, Record<ChartMetricId, number>>;
}> = [
  {
    key: 'mixed',
    label: 'Mixed traffic',
    note: '50 nodes, 3000 m, 1200 s, pair-count 8, 20 seeds',
    values: {
      'meshtastic-like': { unicast_pdr: 0.948, total_airtime_s: 1170, collision_fail: 122048 },
      'meshcore-like': { unicast_pdr: 0.642, total_airtime_s: 962, collision_fail: 82047 },
      meshecho: { unicast_pdr: 0.962, total_airtime_s: 828, collision_fail: 73496 }
    }
  },
  {
    key: 'shadow6',
    label: 'High shadowing',
    note: 'Same topology with stronger log-normal shadowing',
    values: {
      'meshtastic-like': { unicast_pdr: 0.95, total_airtime_s: 1178, collision_fail: 121836 },
      'meshcore-like': { unicast_pdr: 0.633, total_airtime_s: 970, collision_fail: 83424 },
      meshecho: { unicast_pdr: 0.969, total_airtime_s: 819, collision_fail: 72980 }
    }
  },
  {
    key: 'rate10',
    label: 'High offered load',
    note: 'Mixed traffic with higher offered packet rate',
    values: {
      'meshtastic-like': { unicast_pdr: 0.917, total_airtime_s: 1875, collision_fail: 198166 },
      'meshcore-like': { unicast_pdr: 0.488, total_airtime_s: 1415, collision_fail: 125205 },
      meshecho: { unicast_pdr: 0.932, total_airtime_s: 1318, collision_fail: 122431 }
    }
  }
];

const researchMetrics: Array<{
  id: ChartMetricId;
  label: string;
  unit: string;
  direction: 'higher' | 'lower';
  precision: number;
}> = [
  { id: 'unicast_pdr', label: 'Unicast PDR', unit: '', direction: 'higher', precision: 3 },
  { id: 'total_airtime_s', label: 'Total airtime', unit: 's', direction: 'lower', precision: 0 },
  { id: 'collision_fail', label: 'Collision failures', unit: 'count', direction: 'lower', precision: 0 }
];

const algorithmSteps = [
  {
    title: 'Observe link evidence',
    copy: 'Collect ACK delivery, route age, hop count, RSSI/SNR-like reception evidence, and cached path outcomes.'
  },
  {
    title: 'Score route confidence',
    copy: 'Estimate whether a cached route is still worth using instead of spending airtime on wide flooding.'
  },
  {
    title: 'Bound rescue traffic',
    copy: 'If confidence falls or ACKs fail, trigger a limited fallback path instead of letting retries grow without control.'
  },
  {
    title: 'Adapt policy online',
    copy: 'Update the active profile during the run, balancing delivery reward against airtime and collision cost.'
  }
];

function formatUptime(ms: number | null): string {
  if (ms === null) {
    return 'Waiting';
  }
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':');
}

function normalizeConfigValue(value: string | boolean): string {
  if (typeof value === 'boolean') {
    return value ? 'on' : 'off';
  }
  return value.trim();
}

function commandValueForField(config: ConfigFormState, field: ConfigFieldDefinition): string {
  return normalizeConfigValue(config[field.key]);
}

function buildConfigCommands(config: ConfigFormState): string[] {
  return configGroups.flatMap((group) =>
    group.fields.map((field) => `set ${field.command} ${commandValueForField(config, field)}`)
  );
}

function parseDeviceResponseChunk(chunk: string): DeviceResponsePayload[] {
  return chunk
    .split(/\r?\n/)
    .flatMap((line) => {
      const start = line.indexOf('{');
      const end = line.lastIndexOf('}');
      if (start < 0 || end <= start) {
        return [];
      }
      try {
        return [JSON.parse(line.slice(start, end + 1)) as DeviceResponsePayload];
      } catch {
        return [];
      }
    });
}

function applyDevicePayloadToConfig(current: ConfigFormState, config?: DeviceConfigPayload): ConfigFormState {
  if (!config) {
    return current;
  }
  return {
    ...current,
    node_id: config.node_id === undefined ? current.node_id : String(config.node_id),
    callsign: config.callsign ?? current.callsign,
    region: config.region ?? current.region,
    freq_mhz: config.freq_mhz === undefined ? current.freq_mhz : String(config.freq_mhz),
    bw_khz: config.bw_khz === undefined ? current.bw_khz : String(config.bw_khz),
    sf: config.sf === undefined ? current.sf : String(config.sf),
    cr: config.cr === undefined ? current.cr : String(config.cr),
    tx_power: config.tx_power === undefined ? current.tx_power : String(config.tx_power),
    max_hops: config.max_hops === undefined ? current.max_hops : String(config.max_hops),
    route_ttl_s: config.route_ttl_s === undefined ? current.route_ttl_s : String(config.route_ttl_s),
    fallback_ttl: config.fallback_ttl === undefined ? current.fallback_ttl : String(config.fallback_ttl),
    ack_timeout_ms: config.ack_timeout_ms === undefined ? current.ack_timeout_ms : String(config.ack_timeout_ms),
    ble: config.ble ?? current.ble,
    wifi: config.wifi ?? current.wifi
  };
}

function applyDevicePayloadToSummary(
  current: DeviceSummaryState,
  payload: DeviceResponsePayload
): DeviceSummaryState {
  return {
    firmware: payload.version ?? current.firmware,
    target: payload.target ?? current.target,
    chip: payload.chip ?? current.chip,
    radio: payload.radio ?? current.radio,
    uptime_ms: payload.uptime_ms ?? current.uptime_ms,
    active_profile: payload.active_profile ?? current.active_profile
  };
}

function App() {
  const [route, setRouteState] = useState<RouteKey>(() => routeFromLocation());
  const [language, setLanguage] = useState<Language>(() => initialLanguage());
  const [selectedTarget, setSelectedTarget] = useState<TargetId>('esp32dev_sx1262');
  const [selectedFirmware, setSelectedFirmware] = useState<FirmwareId>('v2.0.0-stable');
  const [transport, setTransport] = useState<TransportId>('serial');
  const [eraseMode, setEraseMode] = useState(false);
  const [releaseAccepted, setReleaseAccepted] = useState(true);
  const [monitorOpen, setMonitorOpen] = useState(false);
  const [flashProgress, setFlashProgress] = useState(0);
  const [releaseManifest, setReleaseManifest] = useState<ReleaseManifest | null>(null);
  const [targetManifest, setTargetManifest] = useState<TargetManifest | null>(null);
  const [manifestStatus, setManifestStatus] = useState('Manifest not loaded');
  const [flashLog, setFlashLog] = useState<string[]>([
    '[MeshEcho Web] ready',
    '[MeshEcho Web] manifest preflight will block placeholder artifacts'
  ]);
  const [serialSession, setSerialSession] = useState<SerialSession | null>(null);
  const [bleSession, setBleSession] = useState<BleSession | null>(null);
  const [wifiEndpoint, setWifiEndpoint] = useState('http://192.168.4.1');
  const [serialLog, setSerialLog] = useState<string[]>([
    '$ meshecho monitor --baud 115200',
    '[MeshEcho] command: version | show | get config | set <field> <value> | save'
  ]);

  const target = targets.find((item) => item.id === selectedTarget)!;
  const firmware = firmwares.find((item) => item.id === selectedFirmware)!;
  const manifestReady = !!targetManifest && targetManifest.target === selectedTarget;
  const artifactReady = !!targetManifest?.files.length && targetManifest.files.every((file) => file.bytes > 0 && !file.sha256.includes('placeholder'));
  const canFlash = target.support === 'Ready' && releaseAccepted && !monitorOpen && manifestReady && artifactReady;
  const i18n = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (text: string) => translateText(language, text)
    }),
    [language]
  );

  useEffect(() => {
    window.localStorage.setItem(languageStorageKey, language);
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  }, [language]);

  useEffect(() => {
    let active = true;
    setManifestStatus('Loading release manifest...');
    loadReleaseManifest()
      .then((manifest) => {
        if (!active) return;
        setReleaseManifest(manifest);
        setManifestStatus(`${manifest.project} ${manifest.version} manifest loaded`);
      })
      .catch((error) => {
        if (!active) return;
        setManifestStatus(formatError(error));
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const releaseTarget = releaseManifest?.targets.find((item) => item.id === selectedTarget);
    if (!releaseTarget) {
      setTargetManifest(null);
      return;
    }
    setManifestStatus(`Loading ${releaseTarget.id} manifest...`);
    loadTargetManifest(releaseTarget.manifest_url)
      .then((manifest) => {
        if (!active) return;
        setTargetManifest(manifest);
        setManifestStatus(`${manifest.target} target manifest loaded`);
      })
      .catch((error) => {
        if (!active) return;
        setTargetManifest(null);
        setManifestStatus(formatError(error));
      });
    return () => {
      active = false;
    };
  }, [releaseManifest, selectedTarget]);

  const setRoute = (nextRoute: RouteKey) => {
    setRouteState(nextRoute);
    const nextPath = nextRoute === 'home' ? '/' : `/${nextRoute}`;
    if (window.location.pathname !== nextPath) {
      window.history.pushState({ route: nextRoute }, '', nextPath);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    const onPopState = () => setRouteState(routeFromLocation());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const routeContent = useMemo(() => {
    switch (route) {
      case 'flash':
        return (
          <FlashPage
            selectedTarget={selectedTarget}
            setSelectedTarget={setSelectedTarget}
            selectedFirmware={selectedFirmware}
            setSelectedFirmware={setSelectedFirmware}
            eraseMode={eraseMode}
            setEraseMode={setEraseMode}
            releaseAccepted={releaseAccepted}
            setReleaseAccepted={setReleaseAccepted}
            monitorOpen={monitorOpen}
            setMonitorOpen={setMonitorOpen}
            flashProgress={flashProgress}
            setFlashProgress={setFlashProgress}
            target={target}
            firmware={firmware}
            canFlash={canFlash}
            manifestStatus={manifestStatus}
            targetManifest={targetManifest}
            artifactReady={artifactReady}
            flashLog={flashLog}
            setFlashLog={setFlashLog}
          />
        );
      case 'config':
        return (
          <ConfigPage
            transport={transport}
            setTransport={setTransport}
            serialSession={serialSession}
            setSerialSession={setSerialSession}
            bleSession={bleSession}
            setBleSession={setBleSession}
            wifiEndpoint={wifiEndpoint}
            setWifiEndpoint={setWifiEndpoint}
            serialLog={serialLog}
            setSerialLog={setSerialLog}
          />
        );
      case 'research':
        return <ResearchPage />;
      case 'docs':
        return <DocsPage />;
      case 'releases':
        return <ReleasesPage />;
      case 'home':
      default:
        return <HomePage setRoute={setRoute} />;
    }
  }, [
    route,
    selectedTarget,
    selectedFirmware,
    eraseMode,
    releaseAccepted,
    monitorOpen,
    flashProgress,
    target,
    firmware,
    canFlash,
    transport,
    manifestStatus,
    targetManifest,
    artifactReady,
    flashLog,
    serialSession,
    bleSession,
    wifiEndpoint,
    serialLog
  ]);

  return (
    <I18nContext.Provider value={i18n}>
      <div className="app-shell">
        <div className="grid-scan" />
        <SiteHeader route={route} setRoute={setRoute} />
        <main>{routeContent}</main>
      </div>
    </I18nContext.Provider>
  );
}

function routeFromLocation(): RouteKey {
  const segment = window.location.pathname.split('/').filter(Boolean).at(-1);
  if (
    segment === 'flash' ||
    segment === 'config' ||
    segment === 'research' ||
    segment === 'docs' ||
    segment === 'releases'
  ) {
    return segment;
  }
  return 'home';
}

function SiteHeader({ route, setRoute }: { route: RouteKey; setRoute: (route: RouteKey) => void }) {
  const { language, setLanguage, t } = useI18n();

  return (
    <header className="site-header">
      <button className="brand-mark" onClick={() => setRoute('home')} aria-label={t('Go to home')}>
        <span className="brand-glyph">
          <Radio size={20} />
        </span>
        <span>
          <strong>MeshEcho</strong>
          <small>
            {t('Field console')} v{appVersion}
          </small>
        </span>
      </button>
      <nav className="nav-tabs" aria-label={t('Primary')}>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={route === item.id ? 'active' : ''}
            aria-pressed={route === item.id}
            onClick={() => setRoute(item.id)}
          >
            {t(item.label)}
          </button>
        ))}
      </nav>
      <div className="header-actions">
        <span className="version-pill">UI v{appVersion}</span>
        <button
          className="language-toggle"
          type="button"
          aria-label={t('Switch language')}
          onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
        >
          {language === 'en' ? '中文' : 'EN'}
        </button>
        <a className="ghost-link" href="https://github.com/BH4ME" target="_blank" rel="noreferrer">
          <Github size={16} />
          GitHub
        </a>
      </div>
    </header>
  );
}

function HomePage({ setRoute }: { setRoute: (route: RouteKey) => void }) {
  const { t } = useI18n();

  return (
    <section className="page home-page">
      <div className="hero">
        <div className="hero-copy">
          <span className="eyebrow">
            <Sparkles size={16} />
            {t('RF bench and field kit')}
          </span>
          <h1>MeshEcho</h1>
          <p className="hero-lede">
            {t(
              'Flash ESP32 LoRa targets, inspect release manifests, tune the command protocol, and keep device output visible while the radio work is still in your hands.'
            )}
          </p>
          <div className="signal-readout" aria-label="MeshEcho system status">
            <span>
              <strong>2</strong>
              {t('ready ESP32 targets')}
            </span>
            <span>
              <strong>3</strong>
              {t('config transports')}
            </span>
            <span>
              <strong>v{appVersion}</strong>
              {t('UI console')}
            </span>
          </div>
          <div className="hero-actions">
            <button className="primary-action" onClick={() => setRoute('flash')}>
              <HardDriveDownload size={18} />
              {t('Open flasher')}
            </button>
            <button className="secondary-action" onClick={() => setRoute('config')}>
              <Settings2 size={18} />
              {t('Tune device')}
            </button>
            <button className="secondary-action" onClick={() => setRoute('research')}>
              <BarChart3 size={18} />
              {t('View research')}
            </button>
          </div>
          <div className="hero-meta">
            <Badge icon={CircuitBoard} label="ESP32 + SX1262" />
            <Badge icon={Antenna} label="SX127x/RFM9x" />
            <Badge icon={ShieldAlert} label="nRF52 planned" />
          </div>
        </div>
        <NetworkPanel />
      </div>

      <section className="band">
          <SectionHeading
            kicker="Operating flow"
            title="One console for the moments that can brick or fix a node"
            copy="The first screen stays honest about hardware state: choose a target, check artifacts, connect a transport, then send commands with logs in view."
          />
          <div className="feature-grid">
            <FeatureCard
              icon={Globe2}
              title="Orient"
              copy="Know what MeshEcho is, which radios it supports, and where the research and firmware notes live."
            />
            <FeatureCard
              icon={Flashlight}
              title="Flash"
              copy="Select the exact board, verify the manifest gate, detect the ESP chip, and keep the serial monitor nearby."
            />
            <FeatureCard
              icon={Router}
              title="Configure"
              copy="Use USB Serial first, then BLE UART or WiFi HTTP when firmware exposes those transport paths."
            />
            <FeatureCard
              icon={BookOpenCheck}
              title="Compare"
              copy="Show the MeshEcho paper algorithm and compare it against Meshtastic-like and MeshCore-like baselines."
            />
          </div>
        </section>

      <section className="band two-column">
        <div>
          <SectionHeading
            kicker="Firmware reality"
            title="MeshEcho is the routing layer and the workbench"
            copy="The UI presents the paper algorithm under the MeshEcho name, with route confidence and redundancy shown where they help users reason about the result."
          />
          <div className="metric-row">
            <Metric label="Targets ready" value="2" />
            <Metric label="Config transports" value="3" />
            <Metric label="Manifest layers" value="2" />
          </div>
        </div>
        <div className="callout-panel">
          <h3>{t('Release gate')}</h3>
          <p>
            {t(
              'MeshEcho should be useful before hardware is connected, then progressively unlock flashing and configuration as real device endpoints respond.'
            )}
          </p>
        </div>
      </section>
    </section>
  );
}

function NetworkPanel() {
  const { t } = useI18n();
  const nodes = [
    { label: 'GW', x: 18, y: 28, quality: '0.98' },
    { label: 'B2', x: 44, y: 18, quality: '0.91' },
    { label: 'C7', x: 74, y: 31, quality: '0.87' },
    { label: 'D4', x: 30, y: 69, quality: '0.94' },
    { label: 'E9', x: 65, y: 75, quality: '0.89' }
  ];

  return (
    <div className="network-panel" aria-label={t('Animated mesh network diagram')}>
      <div className="panel-topline">
        <span>{t('Route confidence')}</span>
        <strong>{t('ACK aware')}</strong>
      </div>
      <div className="mesh-map">
        <div className="radar-rings" />
        <div className="scan-beam" />
        <svg viewBox="0 0 100 100" role="img" aria-label="MeshEcho route map">
          <defs>
            <linearGradient id="route-hot" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stopColor="#e2ff6f" />
              <stop offset="45%" stopColor="#65ffd4" />
              <stop offset="100%" stopColor="#72c8ff" />
            </linearGradient>
          </defs>
          <path className="mesh-path path-a" d="M18 28 L44 18 L72 30 L63 74 L30 68 Z" />
          <path className="mesh-path path-b" d="M18 28 L30 68 L63 74" />
          <path className="mesh-path path-c" d="M44 18 L30 68 L72 30" />
          {nodes.map((node) => (
            <g key={node.label}>
              <circle className="node-halo" cx={node.x} cy={node.y} r="8" />
              <circle className="node-core" cx={node.x} cy={node.y} r="4" />
              <text x={node.x} y={node.y + 1.4}>
                {node.label}
              </text>
              <text className="node-quality" x={node.x} y={node.y + 13}>
                {node.quality}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="telemetry-strip">
        <span>
          <Activity size={14} /> PDR 0.96
        </span>
        <span>
          <Zap size={14} /> {t('Rescue bounded')}
        </span>
        <span>
          <Cloud size={14} /> {t('Console ready')}
        </span>
      </div>
    </div>
  );
}

function FlashPage({
  selectedTarget,
  setSelectedTarget,
  selectedFirmware,
  setSelectedFirmware,
  eraseMode,
  setEraseMode,
  releaseAccepted,
  setReleaseAccepted,
  monitorOpen,
  setMonitorOpen,
  flashProgress,
  setFlashProgress,
  target,
  firmware,
  canFlash,
  manifestStatus,
  targetManifest,
  artifactReady,
  flashLog,
  setFlashLog
}: {
  selectedTarget: TargetId;
  setSelectedTarget: (value: TargetId) => void;
  selectedFirmware: FirmwareId;
  setSelectedFirmware: (value: FirmwareId) => void;
  eraseMode: boolean;
  setEraseMode: (value: boolean) => void;
  releaseAccepted: boolean;
  setReleaseAccepted: (value: boolean) => void;
  monitorOpen: boolean;
  setMonitorOpen: (value: boolean) => void;
  flashProgress: number;
  setFlashProgress: (value: number) => void;
  target: Target;
  firmware: Firmware;
  canFlash: boolean;
  manifestStatus: string;
  targetManifest: TargetManifest | null;
  artifactReady: boolean;
  flashLog: string[];
  setFlashLog: React.Dispatch<React.SetStateAction<string[]>>;
}) {
  const { t } = useI18n();
  const addFlashLog = (line: string) => setFlashLog((current) => [...current.slice(-10), line]);

  const detectChip = async () => {
    try {
      addFlashLog('[MeshEcho Web] requesting Web Serial port for chip detection...');
      const chipName = await detectEspChip(addFlashLog);
      addFlashLog(`[MeshEcho Web] chip detected: ${chipName}`);
    } catch (error) {
      addFlashLog(`[MeshEcho Web] detect failed: ${formatError(error)}`);
    }
  };

  const runFlash = async () => {
    if (!targetManifest) {
      addFlashLog('[MeshEcho Web] no target manifest loaded.');
      return;
    }
    if (!canFlash) {
      addFlashLog('[MeshEcho Web] flash blocked by preflight. Publish real artifacts before flashing.');
      return;
    }
    setFlashProgress(0);
    try {
      addFlashLog('[MeshEcho Web] requesting Web Serial port for flashing...');
      await flashEspTarget(targetManifest, eraseMode, addFlashLog, setFlashProgress);
    } catch (error) {
      addFlashLog(`[MeshEcho Web] flash failed: ${formatError(error)}`);
    }
  };

  return (
    <section className="page tool-page">
      <ToolHero
        icon={HardDriveDownload}
        eyebrow="Web Flasher"
        title="Meshtastic-style flashing, rebuilt for MeshEcho"
        copy="Select a board, choose a firmware release, pass manifest preflight, flash over Web Serial, then inspect serial logs."
      />

      <div className="tool-layout">
        <div className="tool-column">
          <Panel title="Device" icon={CircuitBoard} action="Target first">
            <div className="target-grid">
              {targets.map((item) => (
                <button
                  key={item.id}
                  className={`target-card ${selectedTarget === item.id ? 'selected' : ''}`}
                  aria-pressed={selectedTarget === item.id}
                  onClick={() => setSelectedTarget(item.id)}
                >
                  <span className="target-status">{t(item.support)}</span>
                  <strong>{item.name}</strong>
                  <small>
                    {item.chip} / {item.radio}
                  </small>
                  <em>{t(item.note)}</em>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Firmware" icon={FileCode2} action="Release notes">
            <div className="firmware-list">
              {firmwares.map((item) => (
                <button
                  key={item.id}
                  className={`firmware-row ${selectedFirmware === item.id ? 'selected' : ''}`}
                  aria-pressed={selectedFirmware === item.id}
                  onClick={() => {
                    setSelectedFirmware(item.id);
                    setReleaseAccepted(item.id !== 'v2.1.0-alpha');
                    setFlashProgress(0);
                  }}
                >
                  <span>{t(item.channel)}</span>
                  <strong>{t(item.label)}</strong>
                  <small>{t(item.date)}</small>
                </button>
              ))}
            </div>
            <div className="release-notes">
              <h4>{t(firmware.label)}</h4>
              <ul>
                {firmware.notes.map((note) => (
                  <li key={note}>{t(note)}</li>
                ))}
              </ul>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={releaseAccepted}
                  onChange={(event) => setReleaseAccepted(event.target.checked)}
                />
                {t('I reviewed target compatibility and release notes.')}
              </label>
            </div>
          </Panel>
        </div>

        <div className="tool-column">
          <Panel title="Flash" icon={Flashlight} action={target.flashMode}>
            <div className="device-header">
              <div>
                <span>{t('Selected target')}</span>
                <strong>{target.name}</strong>
                <small>{t(target.pins)}</small>
              </div>
              <Badge icon={target.flashMode === 'esptool-js' ? Usb : Download} label={target.flashMode} />
            </div>

            <div className="preflight-list">
              <Preflight label="Device target selected" done />
              <Preflight label="Firmware selected" done />
              <Preflight label={`${t('Manifest')}: ${translateManifestStatus(t, manifestStatus)}`} done={!!targetManifest} />
              <Preflight label={artifactReady ? 'Firmware artifacts ready' : 'Firmware artifacts are placeholders'} done={artifactReady} />
              <Preflight label="Release notes accepted" done={releaseAccepted} />
              <Preflight label="Serial monitor closed" done={!monitorOpen} />
              <Preflight label="Board support ready" done={target.support === 'Ready'} />
            </div>

            <label className="toggle-row">
              <input type="checkbox" checked={eraseMode} onChange={(event) => setEraseMode(event.target.checked)} />
              <span>
                <strong>{t('Full erase and install')}</strong>
                <small>{t('Destructive. Use for clean lab demos or major firmware changes.')}</small>
              </span>
            </label>

            <div className="split-actions">
              <button className="secondary-action full-width" disabled={!hasWebSerial() || target.flashMode !== 'esptool-js'} onClick={detectChip}>
                <Cpu size={18} />
                {t('Detect ESP Chip')}
              </button>
              <button className="primary-action full-width" disabled={!canFlash} onClick={runFlash}>
                <PlugZap size={18} />
                {t(canFlash ? 'Start Web Serial Flash' : 'Resolve preflight first')}
              </button>
            </div>

            <button className="text-action" onClick={() => setFlashLog((current) => [...current, `[MeshEcho Web] ${manifestStatus}`])}>
              <Info size={16} />
              {t('Show manifest status')}
            </button>

            <div className="progress-block">
              <div className="progress-line">
                <span>{t('Flash progress')}</span>
                <strong>{flashProgress}%</strong>
              </div>
              <div className="progress-track">
                <span style={{ transform: `scaleX(${flashProgress / 100})` }} />
              </div>
            </div>
          </Panel>

          <Panel title="Serial monitor" icon={Terminal} action={monitorOpen ? 'Connected' : 'Closed'}>
            <button className="secondary-action full-width" onClick={() => setMonitorOpen(!monitorOpen)}>
              <Terminal size={18} />
              {t(monitorOpen ? 'Close monitor' : 'Open monitor')}
            </button>
            <div className="terminal-window">
              {flashLog.map((line, index) => (
                <p key={`${line}-${index}`}>{line}</p>
              ))}
              <p>[MeshEcho] target={target.id}</p>
              <p>[MeshEcho] firmware={firmware.id}</p>
            </div>
          </Panel>
        </div>
      </div>
    </section>
  );
}

function ConfigPage({
  transport,
  setTransport,
  serialSession,
  setSerialSession,
  bleSession,
  setBleSession,
  wifiEndpoint,
  setWifiEndpoint,
  serialLog,
  setSerialLog
}: {
  transport: TransportId;
  setTransport: (transport: TransportId) => void;
  serialSession: SerialSession | null;
  setSerialSession: React.Dispatch<React.SetStateAction<SerialSession | null>>;
  bleSession: BleSession | null;
  setBleSession: React.Dispatch<React.SetStateAction<BleSession | null>>;
  wifiEndpoint: string;
  setWifiEndpoint: React.Dispatch<React.SetStateAction<string>>;
  serialLog: string[];
  setSerialLog: React.Dispatch<React.SetStateAction<string[]>>;
}) {
  const { t } = useI18n();
  const addSerialLog = (line: string) => setSerialLog((current) => [...current.slice(-16), line]);
  const serialConnected = !!serialSession;
  const bleConnected = !!bleSession;
  const activeConnected = transport === 'serial' ? serialConnected : transport === 'ble' ? bleConnected : true;
  const [configForm, setConfigForm] = useState<ConfigFormState>(defaultConfigForm);
  const [deviceSummary, setDeviceSummary] = useState<DeviceSummaryState>(defaultDeviceSummary);
  const [lastDeviceStatus, setLastDeviceStatus] = useState('No device response yet');
  const configRef = useRef(configForm);

  useEffect(() => {
    configRef.current = configForm;
  }, [configForm]);

  const handleDeviceText = (text: string) => {
    addSerialLog(text);
    for (const payload of parseDeviceResponseChunk(text)) {
      if (payload.error) {
        setLastDeviceStatus(payload.error);
      } else if (payload.ok !== undefined) {
        setLastDeviceStatus(payload.ok ? 'Device accepted command' : 'Device rejected command');
      }
      setDeviceSummary((current) => applyDevicePayloadToSummary(current, payload));
      if (payload.config) {
        setConfigForm((current) => applyDevicePayloadToConfig(current, payload.config));
      }
    }
  };

  const connectSerial = async () => {
    try {
      addSerialLog('[MeshEcho Web] requesting USB serial port...');
      const session = await openSerialConsole(handleDeviceText);
      setSerialSession(session);
      addSerialLog('[MeshEcho Web] USB serial connected.');
      setTimeout(() => void session.sendLine('version'), 120);
      setTimeout(() => void session.sendLine('get config'), 260);
    } catch (error) {
      addSerialLog(`[MeshEcho Web] serial connect failed: ${formatError(error)}`);
    }
  };

  const connectBle = async () => {
    try {
      addSerialLog('[MeshEcho Web] requesting BLE UART device...');
      const session = await openBleUartConsole(handleDeviceText);
      setBleSession(session);
      addSerialLog('[MeshEcho Web] BLE UART connected.');
      setTimeout(() => void session.sendLine('version'), 120);
      setTimeout(() => void session.sendLine('get config'), 260);
    } catch (error) {
      addSerialLog(`[MeshEcho Web] BLE connect failed: ${formatError(error)}`);
    }
  };

  const disconnectSerial = async () => {
    if (!serialSession) return;
    try {
      await serialSession.close();
      addSerialLog('[MeshEcho Web] USB serial disconnected.');
    } catch (error) {
      addSerialLog(`[MeshEcho Web] serial disconnect failed: ${formatError(error)}`);
    } finally {
      setSerialSession(null);
    }
  };

  const disconnectBle = async () => {
    if (!bleSession) return;
    try {
      await bleSession.close();
      addSerialLog('[MeshEcho Web] BLE UART disconnected.');
    } catch (error) {
      addSerialLog(`[MeshEcho Web] BLE disconnect failed: ${formatError(error)}`);
    } finally {
      setBleSession(null);
    }
  };

  const sendSerialCommand = async (line: string) => {
    try {
      addSerialLog(`> ${line}`);
      if (transport === 'serial') {
        if (!serialSession) {
          addSerialLog(`[MeshEcho Web] USB serial is not connected; command preview only: ${line}`);
          return;
        }
        await serialSession.sendLine(line);
      } else if (transport === 'ble') {
        if (!bleSession) {
          addSerialLog(`[MeshEcho Web] BLE UART is not connected; command preview only: ${line}`);
          return;
        }
        await bleSession.sendLine(line);
      } else {
        const response = await sendWifiConfigCommand(wifiEndpoint, line);
        handleDeviceText(response);
      }
    } catch (error) {
      addSerialLog(`[MeshEcho Web] send failed: ${formatError(error)}`);
    }
  };

  const readFromDevice = async () => {
    await sendSerialCommand('show');
    await sendSerialCommand('get config');
  };

  const writeConfigToDevice = async () => {
    const commands = buildConfigCommands(configRef.current);
    for (const command of commands) {
      await sendSerialCommand(command);
    }
    await sendSerialCommand('save');
  };

  const transportMeta = {
    serial: {
      icon: Cable,
      title: 'USB Serial',
      state: serialConnected ? 'Connected' : 'Ready',
      copy: 'Production path for firmware v2. Uses Web Serial in Chromium browsers.'
    },
    ble: {
      icon: Bluetooth,
      title: 'BLE UART',
      state: bleConnected ? 'Connected' : 'Web client ready',
      copy: 'Nordic UART client is implemented; firmware still needs to expose the NUS service.'
    },
    wifi: {
      icon: Wifi,
      title: 'WiFi Web',
      state: 'HTTP endpoint',
      copy: 'Uses POST /api/config on a MeshEcho SoftAP or LAN endpoint. Raw UDP is not browser-compatible.'
    }
  } satisfies Record<TransportId, { icon: React.ElementType; title: string; state: string; copy: string }>;

  const connectAction = {
    serial: {
      disabled: !hasWebSerial(),
      label: serialConnected ? 'Disconnect Serial' : 'Connect Serial',
      icon: Cable,
      run: serialConnected ? disconnectSerial : connectSerial
    },
    ble: {
      disabled: !hasWebBluetooth(),
      label: bleConnected ? 'Disconnect BLE' : 'Connect BLE UART',
      icon: Bluetooth,
      run: bleConnected ? disconnectBle : connectBle
    },
    wifi: {
      disabled: false,
      label: 'Use WiFi Endpoint',
      icon: Wifi,
      run: async () => {
        addSerialLog(`[MeshEcho Web] WiFi endpoint set to ${wifiEndpoint}`);
        await sendSerialCommand('version');
      }
    }
  } satisfies Record<TransportId, { disabled: boolean; label: string; icon: React.ElementType; run: () => Promise<void> }>;
  const ConnectIcon = connectAction[transport].icon;
  const connectionLabel =
    transport === 'serial'
      ? serialConnected
        ? 'Serial connected'
        : lastDeviceStatus
      : transport === 'ble'
        ? bleConnected
          ? 'BLE connected'
          : lastDeviceStatus
        : 'WiFi endpoint';

  return (
    <section className="page tool-page">
      <ToolHero
        icon={Settings2}
        eyebrow="Web Config"
        title="One control console for serial, BLE, and WiFi"
        copy="The UI is ready for all three transports while clearly showing which firmware endpoints still need to land."
      />

      <div className="config-layout">
        <Panel title="Transport" icon={Router} action={transportMeta[transport].state}>
          <div className="transport-grid">
            {(Object.keys(transportMeta) as TransportId[]).map((id) => {
              const item = transportMeta[id];
              const Icon = item.icon;
              return (
                <button
                  key={id}
                  className={`transport-card ${transport === id ? 'selected' : ''}`}
                  aria-pressed={transport === id}
                  onClick={() => setTransport(id)}
                >
                  <Icon size={22} />
                  <strong>{t(item.title)}</strong>
                  <span>{t(item.state)}</span>
                  <small>{t(item.copy)}</small>
                </button>
              );
            })}
          </div>
        </Panel>

        <Panel title="Device summary" icon={MonitorDot} action={connectionLabel}>
          {transport === 'wifi' ? (
            <label className="endpoint-row">
              <span>{t('WiFi endpoint')}</span>
              <input
                value={wifiEndpoint}
                onChange={(event) => setWifiEndpoint(event.target.value)}
                placeholder="http://192.168.4.1"
              />
            </label>
          ) : null}
          <div className="summary-grid">
            <Metric label="Firmware" value={deviceSummary.firmware} />
            <Metric label="Target" value={deviceSummary.target} />
            <Metric label="Radio" value={deviceSummary.radio} />
            <Metric label="Uptime" value={t(formatUptime(deviceSummary.uptime_ms))} />
            <Metric label="Profile" value={deviceSummary.active_profile} />
            <Metric label="Protocol" value="JSONL/Text" />
          </div>
          <div className="command-strip">
            {['version', 'show', 'get config', 'save', 'reboot'].map((command) => (
              <button key={command} onClick={() => void sendSerialCommand(command)}>
                {command}
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="config-grid">
        {configGroups.map((group) => (
          <Panel key={group.title} title={group.title} icon={group.icon} action="Serial protocol">
            <div className="form-grid">
              {group.fields.map((field) => (
                <label key={`${group.title}-${field.label}`} className="field-row">
                  <span>{t(field.label)}</span>
                  {field.type === 'toggle' ? (
                    <button
                      className={`switch-control ${configForm[field.key] ? 'on' : ''}`}
                      type="button"
                      onClick={() =>
                        setConfigForm((current) => ({
                          ...current,
                          [field.key]: !current[field.key]
                        }))
                      }
                    >
                      <span />
                      {t(configForm[field.key] ? 'On' : 'Off')}
                    </button>
                  ) : (
                    <div>
                      <input
                        type={field.type === 'number' ? 'number' : 'text'}
                        value={String(configForm[field.key])}
                        onChange={(event) =>
                          setConfigForm((current) => ({
                            ...current,
                            [field.key]: event.target.value
                          }))
                        }
                      />
                      {field.unit ? <em>{field.unit}</em> : null}
                    </div>
                  )}
                </label>
              ))}
            </div>
          </Panel>
        ))}
      </div>

      <div className="action-bar">
        <button className="secondary-action" disabled={connectAction[transport].disabled} onClick={() => void connectAction[transport].run()}>
          <ConnectIcon size={18} />
          {t(connectAction[transport].label)}
        </button>
        <button className="secondary-action" disabled={!activeConnected} onClick={() => void readFromDevice()}>
          <RefreshCw size={18} />
          {t('Read From Device')}
        </button>
        <button className="primary-action" disabled={!activeConnected} onClick={() => void writeConfigToDevice()}>
          <Save size={18} />
          {t('Write & Save')}
        </button>
      </div>

      <Panel title="Raw console" icon={Terminal} action={serialConnected ? 'Live serial' : 'Preview'}>
        <div className="terminal-window config-terminal">
          {serialLog.map((line, index) => (
            <p key={`${line}-${index}`}>{line}</p>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function ResearchPage() {
  const { t } = useI18n();
  const headlineScenario = researchScenarios[0];
  const meshecho = headlineScenario.values.meshecho;
  const meshtastic = headlineScenario.values['meshtastic-like'];
  const meshcore = headlineScenario.values['meshcore-like'];
  const airtimeReduction = Math.round((1 - meshecho.total_airtime_s / meshtastic.total_airtime_s) * 100);
  const collisionReduction = Math.round((1 - meshecho.collision_fail / meshcore.collision_fail) * 100);

  return (
    <section className="page research-page">
      <ToolHero
        icon={BookOpenCheck}
        eyebrow="Research"
        title="MeshEcho paper algorithm, shown as a working result"
        copy="The web surface now carries the same comparison story as the paper: confidence-aware cached routing with bounded fallback, measured against Meshtastic-like flooding and MeshCore-like cached routing."
      />

      <div className="research-summary">
        <Metric label="Mixed-traffic PDR" value={meshecho.unicast_pdr.toFixed(3)} />
        <Metric label="Airtime cut vs Meshtastic" value={`${airtimeReduction}%`} />
        <Metric label="Collision cut vs MeshCore" value={`${collisionReduction}%`} />
        <Metric label="Seeds per scenario" value="20" />
      </div>

      <div className="research-layout">
        <Panel title="MeshEcho v2 algorithm" icon={BrainCircuit} action="paper model">
          <div className="algorithm-brief">
            <p>
              {t(
                'MeshEcho keeps a cached-route fast path, but makes every forwarding choice pass through a confidence gate. The gate weighs route age, hop cost, ACK feedback, and local link evidence before spending airtime on rescue or discovery traffic.'
              )}
            </p>
            <ol className="algorithm-steps">
              {algorithmSteps.map((step) => (
                <li key={step.title}>
                  <strong>{t(step.title)}</strong>
                  <span>{t(step.copy)}</span>
                </li>
              ))}
            </ol>
          </div>
        </Panel>

        <Panel title="Decision loop" icon={Route} action="runtime sketch">
          <div className="algorithm-code" aria-label="MeshEcho decision loop pseudocode">
            <p>{t('for each packet:')}</p>
            <p>{t('  update link evidence from ACK, age, hops, RSSI/SNR')}</p>
            <p>{t('  score cached route confidence')}</p>
            <p>{t('  if confidence is high: send cached unicast')}</p>
            <p>{t('  if ACK fails: try bounded rescue/fallback')}</p>
            <p>{t('  reward = delivery - airtime cost - collision cost')}</p>
            <p>{t('  update active policy profile')}</p>
          </div>
        </Panel>
      </div>

      <section className="band">
        <SectionHeading
          kicker="Protocol comparison"
          title="MeshEcho keeps reliability high while spending less channel time"
          copy="Values are scenario means from the current simulator comparison: 50 nodes, 3000 m area, 1200 s, mixed traffic, pair-count 8, 20 seeds."
        />
        <div className="chart-grid">
          {researchMetrics.map((metric) => (
            <ComparisonChart key={metric.id} metric={metric} />
          ))}
        </div>
      </section>

      <Panel title="Scenario table" icon={BarChart3} action="means">
        <div className="research-table">
          <div className="research-row research-head">
            <span>{t('Scenario')}</span>
            <span>{t('Protocol')}</span>
            <span>{t('Unicast PDR')}</span>
            <span>{t('Airtime')}</span>
            <span>{t('Collisions')}</span>
          </div>
          {researchScenarios.flatMap((scenario) =>
            (Object.keys(protocolLabels) as ProtocolId[]).map((protocol) => {
              const row = scenario.values[protocol];
              return (
                <div className="research-row" key={`${scenario.key}-${protocol}`}>
                  <span>{t(scenario.label)}</span>
                  <span>{protocolLabels[protocol]}</span>
                  <span>{row.unicast_pdr.toFixed(3)}</span>
                  <span>{Math.round(row.total_airtime_s)} s</span>
                  <span>{Math.round(row.collision_fail).toLocaleString()}</span>
                </div>
              );
            })
          )}
        </div>
      </Panel>
    </section>
  );
}

function ComparisonChart({
  metric
}: {
  metric: (typeof researchMetrics)[number];
}) {
  const { t } = useI18n();
  const protocolIds = Object.keys(protocolLabels) as ProtocolId[];
  const maxValue =
    metric.id === 'unicast_pdr'
      ? 1
      : Math.max(...researchScenarios.flatMap((scenario) => protocolIds.map((protocol) => scenario.values[protocol][metric.id])));

  return (
    <article className="chart-panel" aria-label={`${t(metric.label)} ${t('bar chart')}`}>
      <div className="chart-heading">
        <div>
          <h3>{t(metric.label)}</h3>
          <p>{t(metric.direction === 'higher' ? 'Higher is better' : 'Lower is better')}</p>
        </div>
        <span>{t(metric.unit || 'ratio')}</span>
      </div>
      <div className="chart-groups">
        {researchScenarios.map((scenario) => (
          <div className="chart-group" key={`${metric.id}-${scenario.key}`}>
            <div className="bar-set">
              {protocolIds.map((protocol) => {
                const value = scenario.values[protocol][metric.id];
                const height = Math.max(4, (value / maxValue) * 100);
                return (
                  <div className="bar-slot" key={`${scenario.key}-${protocol}-${metric.id}`}>
                    <span className="bar-value">{formatResearchMetric(value, metric)}</span>
                    <span
                      className={`chart-bar ${protocol}`}
                      style={{ height: `${height}%` }}
                      title={`${protocolLabels[protocol]} ${formatResearchMetric(value, metric)}`}
                    />
                  </div>
                );
              })}
            </div>
            <strong>{t(scenario.label)}</strong>
            <small>{t(scenario.note)}</small>
          </div>
        ))}
      </div>
      <div className="chart-legend">
        {protocolIds.map((protocol) => (
          <span key={`${metric.id}-${protocol}`}>
            <i className={protocol} />
            {protocolLabels[protocol]}
          </span>
        ))}
      </div>
    </article>
  );
}

function formatResearchMetric(value: number, metric: (typeof researchMetrics)[number]): string {
  if (metric.precision === 0) {
    const rounded = Math.round(value).toLocaleString();
    return metric.unit && metric.unit !== 'count' ? `${rounded} ${metric.unit}` : rounded;
  }
  return value.toFixed(metric.precision);
}

function DocsPage() {
  const { t } = useI18n();
  const docs = [
    ['Quick start', 'Flash ESP32 target, open serial monitor, send a test packet.'],
    ['Wiring', 'SX1262 and SX127x pin profiles stay separate to avoid wrong-radio flashing.'],
    ['Config protocol', 'Shared JSON-line/text command layer for Serial, BLE, and WiFi.'],
    ['Browser support', 'Chromium first; manual firmware download fallback for Safari/iOS.']
  ];

  return (
    <section className="page">
      <ToolHero
        icon={Layers3}
        eyebrow="Documentation"
        title="A field manual for a browser-first firmware"
        copy="Short, operational docs for flashing, wiring, configuration, and troubleshooting."
      />
      <div className="feature-grid">
        {docs.map(([title, copy]) => (
          <FeatureCard key={title} icon={ChevronRight} title={t(title)} copy={t(copy)} />
        ))}
      </div>
    </section>
  );
}

function ReleasesPage() {
  const { t } = useI18n();

  return (
    <section className="page">
      <ToolHero
        icon={Download}
        eyebrow="Releases"
        title="Manifest-driven firmware artifacts"
        copy={`${t('UI')} v${appVersion} ${t(
          'reads release-level and target-level manifests so firmware URLs, offsets, and checksums stay out of UI code.'
        )}`}
      />
      <div className="release-table">
        <div className="table-row table-head">
          <span>{t('Firmware')}</span>
          <span>{t('Target')}</span>
          <span>{t('Mode')}</span>
          <span>{t('Status')}</span>
        </div>
        {targets.map((target) => (
          <div className="table-row" key={target.id}>
            <span>v2.0.0</span>
            <span>{target.name}</span>
            <span>{target.flashMode}</span>
            <span>{t(target.support)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ToolHero({
  icon: Icon,
  eyebrow,
  title,
  copy
}: {
  icon: React.ElementType;
  eyebrow: string;
  title: string;
  copy: string;
}) {
  const { t } = useI18n();

  return (
    <div className="tool-hero">
      <span className="tool-icon">
        <Icon size={24} />
      </span>
      <div>
        <span className="eyebrow">
          {t(eyebrow)}
          <em>v{appVersion}</em>
        </span>
        <h2>{t(title)}</h2>
        <p>{t(copy)}</p>
      </div>
    </div>
  );
}

function Panel({
  title,
  icon: Icon,
  action,
  children
}: {
  title: string;
  icon: React.ElementType;
  action: string;
  children: React.ReactNode;
}) {
  const { t } = useI18n();

  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>
          <Icon size={18} />
          {t(title)}
        </h3>
        <span>{t(action)}</span>
      </div>
      {children}
    </section>
  );
}

function SectionHeading({ kicker, title, copy }: { kicker: string; title: string; copy: string }) {
  const { t } = useI18n();

  return (
    <div className="section-heading">
      <span>{t(kicker)}</span>
      <h2>{t(title)}</h2>
      <p>{t(copy)}</p>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  copy
}: {
  icon: React.ElementType;
  title: string;
  copy: string;
}) {
  const { t } = useI18n();

  return (
    <article className="feature-card">
      <Icon size={24} />
      <h3>{t(title)}</h3>
      <p>{t(copy)}</p>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  const { t } = useI18n();

  return (
    <div className="metric">
      <span>{t(label)}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Badge({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  const { t } = useI18n();

  return (
    <span className="badge">
      <Icon size={14} />
      {t(label)}
    </span>
  );
}

function Preflight({ label, done }: { label: string; done: boolean }) {
  const { t } = useI18n();

  return (
    <div className={`preflight ${done ? 'done' : ''}`}>
      <span>{done ? <Check size={14} /> : <Info size={14} />}</span>
      {t(label)}
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
