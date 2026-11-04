# 背景插画目录

把你自己的图片放到这里即可生效，**不要修改代码**。

## 目录结构

```
resources/assets/illustrations/
├── home/background.png       首页
├── devices/background.png    设备管理
├── casting/background.png    投屏中心
├── control/background.png    设备控制（详情页）
├── media/background.png      媒体管理
├── settings/background.png   投屏设置 / 设置
└── logs/background.png       运行日志
```

## 图片要求

- 文件名必须是 `background.png`（暂不支持其他格式/文件名）
- 建议使用 16:9 或更宽的横图，宽度 1600px 以上
- 单张图片建议小于 5 MB；超过 2560px 宽会被自动缩小解码以节省内存
- 图片缺失或损坏时，自动回退为纯色背景，不会影响启动

## 各页面默认展示方式

| 页面 | 显示模式 | 默认位置 | 透明度 | 遮罩 |
|---|---|---|---|---|
| 首页 | 右侧装饰 | 右 | 0.62 | 34 |
| 设备管理 | 右侧装饰 | 右 | 0.50 | 44 |
| 投屏中心 | 全区域背景 | 居中 | 0.40 | 108 |
| 设备控制 | 水印 | 居中 | 0.30 | 70 |
| 媒体管理 | 右侧装饰 | 右 | 0.44 | 52 |
| 设置 | 水印 | 右 | 0.26 | 62 |
| 日志 | 水印 | 居中 | 0.18 | 84 |

这些默认值集中定义在 `ui/background_manager.py` 的 `BACKGROUND_SPECS` 中。
