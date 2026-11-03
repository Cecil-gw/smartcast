# 架构说明

## 总体分层

```
┌─────────────────────────────────────────────────────┐
│  UI 层  (ui/)                                        │
│  页面 / 组件 / 对话框，只负责展示与用户交互            │
└───────────────┬─────────────────────────────────────┘
                │ Qt Signal / Slot
┌───────────────▼─────────────────────────────────────┐
│  Worker 层  (workers/)                               │
│  QThread 子类，执行所有耗时 ADB / scrcpy 操作          │
└───────────────┬─────────────────────────────────────┘
                │ 普通方法调用
┌───────────────▼─────────────────────────────────────┐
│  Core 层  (core/)                                    │
│  纯 Python 业务逻辑，不依赖 Qt（scrcpy_manager 除外）   │
└───────────────┬─────────────────────────────────────┘
                │ subprocess
┌───────────────▼─────────────────────────────────────┐
│  adb.exe  /  scrcpy.exe                              │
└─────────────────────────────────────────────────────┘
```

## 核心模块

### `core/adb_manager.py`

最底层的 ADB 封装，全部命令都必须经由它：

```python
class AdbManager:
    adb_path                        # 由 resolve_tool 解析
    def start_server()
    def devices() -> list[RawDevice]        # adb devices -l，带 state
    def shell(serial, command, timeout)     # adb -s <serial> shell ...
```

- `RawDevice(serial, state)` 是设备扫描的最小单元。
- **禁止**在此模块之外拼装未指定 serial 的 ADB 命令。

### `core/device_info.py`

```python
DeviceInfo(serial, state, manufacturer, brand, model,
           android_version, sdk, resolution, density, connection_type)

connection_type_for_serial(serial) -> "usb" | "wifi" | "emulator" | "unknown"
```

判定规则：

- `emulator-*` → emulator
- `<host>:<port>`（port 为 1–65535 的数字）→ wifi
- 其他 → usb

`DeviceInfoReader` 会先尝试一次性 shell 脚本批量读取属性，失败后回退到逐条 `getprop`。

### `core/adb_network_manager.py`

无线连接的核心，对外返回 `NetworkResult`：

```python
NetworkResult(success, already_connected, serial, message, state, server_error)

AdbNetworkManager.connect(ip, port) -> NetworkResult
AdbNetworkManager.disconnect(ip, port) -> NetworkResult
AdbNetworkManager.restart_server() -> (ok, message)
```

连接判定流程（**不接受仅凭 connect 输出判断成功**）：

```
validate_ip / validate_port
  → adb connect IP:PORT (10s 超时)
  → 解析输出（10060 超时 / 10061 拒绝 / 10013 防火墙 / 10065 不可达 / daemon 异常）
  → adb devices 查该 serial 的 state
       unauthorized → 失败（提示手机授权）
       offline      → 失败（提示撤销授权重连）
       device       → 继续
  → adb -s SERIAL shell echo smartcast_ok  (4s 超时)
       无响应 → 失败（已连接但无响应）
  → 成功
```

### `core/network_scanner.py`

```
local_ipv4()                 # 通过 UDP socket 获取本机局域网 IP
subnet_hosts(ip, prefix=24)  # 枚举 /24 内 254 个主机
scan_ports(hosts, ports)     # 多端口并发探测（默认 5555-5560）
discover_serials(ports, recent)  # 子网扫描 + 历史地址直连 + 去重
```

- 单端口探测超时 0.3s，并发 128；
- 只有 TCP 端口开放的地址才会进入 `adb connect`，避免对全子网狂发 ADB 命令；
- 历史地址（`settings.recent_network_addresses`，最多 5 条）会单独直连，可覆盖 Android 11+ 的随机端口。

### `core/device_control.py`

两个管理器：

**`DeviceControlManager`** — 按键

| action | keyevent |
|---|---|
| back | 4 |
| home | 3 |
| recent | 187 |
| volume_up / volume_down | 24 / 25 |
| mute | 164 |
| lock | 26（电源键） |
| power_menu | `--longpress 26` |
| wakeup | 224 |

**`ScreenControlManager`** — 屏幕设置

- `ScreenBackup` 记录原始值：自动亮度、亮度、自动旋转、旋转角度、休眠时间；
- 每个 setter 首次调用时用 `_capture()` 记录原值（若为空）；
- `restore_all()` 只还原**已捕获**的项，绝不编造默认值；
- 范围校验：亮度 1–255。

### `core/scrcpy_manager.py`

以 serial 为键管理 QProcess：

```python
processes: dict[str, QProcess]
sessions:  dict[str, CastSession]
```

命令构建（`build_command`）：

```
-s <serial>
[--turn-screen-off]
[--video-codec <codec>]
--video-bit-rate <n>M
[--max-fps <n>]
[--max-size <n>]
[--no-audio]
[--render-driver <driver>]
[--window-title <title>]
```

窗口相关能力：

- `_find_window(serial)`：**优先按进程 PID** 枚举可见窗口；失败时回退到 `SDL_app` 类名 + 标题匹配（兼容旧版 scrcpy）；
- `toggle_fullscreen(serial)`：修改 Win32 窗口样式实现无边框全屏；
- `get_window_rect(serial)`：供悬浮控制条定位。

会话状态流转：

```
starting → running → stopping → stopped
              ↘ error
              ↘ device_offline
```

### `core/cast_session.py`

```python
CastSession(serial, model, connection_type, state, pid,
            started_monotonic, codec, bitrate_mbps, resolution,
            fps, audio, turn_screen_off, error)
```

- `duration_seconds()` 使用 `time.monotonic()`，不受系统时间调整影响；
- `duration_text()` 输出 `HH:MM:SS`；
- `params_text()` 展示**实际启动时使用的参数**（非实时采样值）。

### `core/media_manager.py`

| 能力 | 实现 |
|---|---|
| 截图 | `subprocess.run([adb, "-s", serial, "exec-out", "screencap", "-p"])` + 字节写入 |
| 录屏 | `Popen([scrcpy, "-s", serial, "--no-window", "--record", path, "--no-audio"])` |
| 停止录制 | `terminate()` → 等待 10s → `kill()`，再回填文件大小 |
| 历史 | `media_history.json`，`MediaRecord` 列表 |
| 目录 | `<data>/SmartCast/{screenshots,recordings}/<清洗后的设备型号>/` |

`sanitize_dir_name()` 只保留字母数字、下划线和短横线，其余替换为 `_`，最长 40 字符，杜绝路径穿越。

## 线程模型

| Worker | 职责 | 信号 |
|---|---|---|
| `DeviceWorker` | 定时扫描设备（QTimer 驱动，运行在独立 QThread） | `devices_changed(list, str)` |
| `NetworkConnectThread` | `adb connect` + 校验 | `finished_with_result(object)` |
| `NetworkDisconnectThread` | `adb disconnect` | 同上 |
| `LanScanThread` | 局域网扫描 + 并发连接 | `finished_with_result(list, list)` |
| `ServerRestartThread` | 用户触发启动 ADB Server | `finished_with_result(bool, str)` |
| `ControlCommandThread` | 单个按键命令 | `finished_with_result(object)` |
| `ScreenCommandThread` | 屏幕读取 / 修改 / 恢复 | `finished_with_result(str, object, str)` |
| `ScreenshotThread` | 截图 | `finished_with_result(object, str)` |
| `RecordControlThread` | 录屏启停 | `finished_with_result(bool, str, object)` |
| `EncoderDetectionThread` | 编码器检测 | 见 `detection_worker.py` |

统一约定：

- 所有 `run()` 使用 `try/except Exception` 兜底，**保证结果信号一定发出**，避免 UI 永久卡在“进行中”；
- UI 侧对同一 serial + 同类操作做防重入检查；
- worker 的 parent 设为 `MainWindow`，生命周期跟随窗口。

## UI 结构

```
MainWindow
├── TitleBar（无边框标题栏：最小化 / 最大化 / 关闭）
├── Sidebar（首页 / 设备管理 / 投屏中心 / 投屏设置 / 使用指南 / 媒体管理 / 日志 / 设置）
└── QStackedWidget
    ├── OverviewPage      首页（设备卡片 + 手机控制 + 屏幕控制 + 概况 + 快捷操作）
    ├── DevicePage        设备管理（卡片网格 + 网络连接入口）
    ├── SessionsPage      投屏中心
    ├── CastSettingsPage  投屏设置
    ├── GuidePage         使用指南
    ├── MediaPage         媒体管理
    ├── SettingsPage      设置
    ├── DetailPage        设备详情
    └── LogPage           日志
```

悬浮控制条 `CastToolBar` 是独立顶层窗口（置顶、不抢焦点），由 `MainWindow` 内 500ms 定时器同步到 scrcpy 窗口下方。

## 配置

| 文件 | 内容 |
|---|---|
| `config/settings.json` | 全局设置：工具路径、扫描间隔、默认投屏参数、主题、最近无线地址 |
| `config/devices.json` | 按 serial 的设备配置：投屏参数、`screen_backup` 原始屏幕设置 |

两者均通过 `ConfigManager` 读写，默认值与已存配置**深度合并**，旧版本配置文件可自动兼容。

## 安全与约束

- 不提供公网 ADB 能力，扫描范围限制在本机 /24 子网；
- 不自动重启 ADB Server（会打断所有连接），仅提供用户显式点击的受控恢复；
- 所有修改系统设置的操作都记录原值并可恢复；
- 删除媒体文件需二次确认，且与删除历史记录分离。
