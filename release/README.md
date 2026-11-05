# SmartCast 发布文件

## 下载

安装包与绿色版压缩包均从 **GitHub Releases** 下载：

**https://github.com/Cecil-gw/smartcast/releases/latest**

| 文件 | 说明 |
|---|---|
| `SmartCastSetup.exe` | Windows 安装包（约 75 MB），双击安装 |
| `SmartCast-Portable.zip` | 绿色免安装版（约 96 MB），解压即用 |
| `*.sha256` | SHA-256 校验文件 |

校验下载完整性：

```powershell
Get-FileHash .\SmartCastSetup.exe -Algorithm SHA256
```

## 安装（安装包）

1. 双击 `SmartCastSetup.exe`；
2. 阅读并同意许可协议；
3. 选择安装位置（默认 `C:\Program Files\SmartCast`；选「当前用户」模式则无需管理员权限）；
4. 可选创建桌面快捷方式；
5. 完成后从开始菜单或桌面启动。

卸载：Windows「设置 → 应用 → SmartCast → 卸载」。

## 使用（绿色版）

1. 解压 `SmartCast-Portable.zip` 到任意目录；
2. 双击其中的 `SmartCast.exe` 运行；
3. 配置与日志会保存在同目录，整个文件夹可直接拷贝迁移。

## 系统要求

- Windows 10 / 11 64 位
- 无需安装 Python、ADB 或 scrcpy（已内置）

## 本版本包含

- USB / Wi-Fi（ADB TCP/IP）设备连接与多设备管理
- 按设备独立 scrcpy 投屏、编码器检测、参数优化
- 手机控制、屏幕控制（亮度 / 旋转 / 常亮），方形图标按钮
- 投屏中心（会话状态、运行时长、参数）
- 截图 / 录屏 / 媒体管理
- 8 套页面动态背景 + 背景缩放过渡
- 记忆上次窗口位置与大小
- 使用指南、运行日志

## 源码

完整源码在本仓库根目录，构建方式见 [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)。
