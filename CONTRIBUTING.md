# 贡献指南

## 提交 Issue

请说明：

- 操作系统版本、Python 版本
- 设备型号 / Android 版本 / 连接方式（USB 或 Wi-Fi）
- 复现步骤与期望结果
- 日志（侧边栏「日志」→「导出」）

## 提交 Pull Request

1. Fork 本仓库并从 `main` 拉分支；
2. 遵循 [开发指南](docs/DEVELOPMENT.md) 中的代码约定；
3. 确保 `compileall` 与全部单元测试通过；
4. PR 描述中写明改动点、影响范围与测试方式。

## 代码风格

- 使用 `from __future__ import annotations`
- 类型标注优先（`list[str]`、`dict[str, Any]`）
- UI 文案使用中文，与现有界面保持一致
- 提交信息建议：`feat: ...` / `fix: ...` / `docs: ...` / `refactor: ...`
