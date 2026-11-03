# 开发指南

## 环境

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11 64 位 |
| Python | 3.11+ |
| GUI | PySide6 6.7+ |
| 打包 | PyInstaller 6.6+、Inno Setup 6/7（可选） |

> 仓库内的 `vendor/`（若存在）为本地依赖缓存，已被 `.gitignore` 排除，勿提交。

## 初始化

```powershell
git clone https://github.com/Cecil-gw/smartcast.git
cd smartcast
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

运行：

```powershell
python main.py
```

## 代码约定

- **禁止**在 UI 线程直接执行 ADB / scrcpy 命令，一律走 `workers/` 下的 QThread；
- **禁止**拼装不带 `-s <serial>` 的 ADB 命令；
- Core 层不导入 Qt（`scrcpy_manager.py` 因 QProcess 例外）；
- Worker 的 `run()` 必须捕获所有异常并保证信号发出；
- 修改系统设置的功能必须实现“记录原值 + 手动恢复”；
- 不擅自修改 `parameter_optimizer.py` 的码率算法与 `settings.json` 默认码率 8。

## 目录职责

见 [ARCHITECTURE.md](ARCHITECTURE.md#核心模块)。

## 测试

### 全量单元测试

```powershell
python -m unittest discover tests -p "test_*.py"
```

当前覆盖：94 个用例

| 文件 | 覆盖内容 |
|---|---|
| `test_adb_network_manager.py` | IP/端口校验、connect/disconnect、10060/10013、daemon 异常、设备状态、地址解析、扫描、worker 异常兜底 |
| `test_device_control.py` | 全部按键映射、serial 隔离、未知操作、worker 异常 |
| `test_screen_control.py` | 亮度范围、自动亮度、旋转、常亮与恢复、备份序列化、worker |
| `test_cast_sessions.py` | 时长格式化、会话状态、多设备隔离、离线标记、活动会话过滤 |
| `test_media_manager.py` | 截图字节流、失败路径、文件名冲突、录屏启停、历史持久化、删除语义、目录名清洗 |
| `test_wheel_guard.py` | 选项框 / 数字框滚轮拦截 |

### UI 冒烟测试（无头）

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH='.;vendor'   # 若依赖位于 vendor/
python tests\ui_refactor_smoke.py
python tests\home_layout_smoke.py
python tests\overview_smoke.py
python tests\main_window_network_smoke.py
python tests\title_bar_guide_smoke.py
python tests\dialog_smoke.py
python tests\cast_layout_smoke.py
python tests\parser_smoke.py
```

### 编译检查

```powershell
python -m compileall core ui workers utils main.py
```

### 测试原则

- 全部使用 `unittest.mock` 隔离真实 ADB / scrcpy，不依赖真机；
- 必须覆盖异常路径与线程生命周期；
- **不得**为了通过测试而删除断言或降低标准。

## 新增一个设备操作（示例）

1. 在 `core/` 新增纯逻辑方法，内部调用 `adb.shell(serial, ...)`；
2. 在 `workers/` 新增 QThread，`run()` 里调用逻辑并 emit 结果；
3. 在 UI 组件定义 `Signal`，由 `MainWindow` 接线到 worker；
4. 在 `tests/` 新增 mock 测试。

## 打包

### 1. 生成程序目录

```powershell
python -m PyInstaller --noconfirm --windowed --name SmartCast `
  --icon resources\assets\app-icon.ico `
  --add-data "resources;resources" main.py
```

产物：`dist\SmartCast\SmartCast.exe`（onedir，启动快）。

### 2. 生成安装包

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" SmartCast.iss
```

产物：`dist\SmartCastSetup.exe`

安装包特性（见 `SmartCast.iss`）：

- 简体中文向导；
- 许可协议页；
- 安装路径选择、当前用户 / 全部用户双模式；
- 可选创建桌面快捷方式；
- 开始菜单项 + 控制面板卸载入口；
- 覆盖安装时自动关闭正在运行的实例。

## 提交前检查清单

- [ ] `python -m compileall core ui workers utils main.py` 通过
- [ ] `python -m unittest discover tests -p "test_*.py"` 全绿
- [ ] UI 冒烟测试通过
- [ ] 未提交 `vendor/`、`dist/`、`build/`、`config/`、`logs/`
- [ ] 未修改码率算法与默认码率 8
