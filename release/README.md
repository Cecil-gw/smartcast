# SmartCast 发布文件

## 下载

| 文件 | 说明 |
|---|---|
| `SmartCastSetup.exe` | Windows 安装包（约 75 MB），双击安装 |
| `SmartCastSetup.exe.sha256` | SHA-256 校验值 |

校验下载完整性：

```powershell
Get-FileHash .\SmartCastSetup.exe -Algorithm SHA256
# 与 .sha256 文件中的值比对
```

## 安装

1. 双击 `SmartCastSetup.exe`；
2. 阅读并同意许可协议；
3. 选择安装位置（默认 `C:\Program Files\SmartCast`；勾选"当前用户"模式则无需管理员权限）；
4. 可选创建桌面快捷方式；
5. 完成后从开始菜单或桌面启动。

卸载：Windows「设置 → 应用 → SmartCast → 卸载」。

## 系统要求

- Windows 10 / 11 64 位
- 无需安装 Python、ADB 或 scrcpy（已内置）

## 本版本包含

- USB / Wi-Fi（ADB TCP/IP）设备连接与多设备管理
- 按设备独立 scrcpy 投屏、编码器检测、参数优化
- 手机控制、屏幕控制（亮度/旋转/常亮）
- 投屏中心（会话状态、运行时长、参数）
- 截图 / 录屏 / 媒体管理
- 7 套页面动态背景 + 页面切换动画
- 使用指南、运行日志

## 源码

完整源码在本仓库根目录，构建方式见 [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)。
