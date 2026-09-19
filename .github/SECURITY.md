# 安全策略

## 支持版本

| 版本 | 状态 |
|------|------|
| main | ✅ 持续维护 |

## 报告漏洞

**请不要用公开 issue 报告安全漏洞。**

推荐方式（需仓库管理员在 Settings → Code security 中开启后可用）：
**Security → Report a vulnerability**（私有漏洞报告通道）。

暂时也接受：新建 issue 选择 **私下联系维护者** 的任何合理方式（如在 [bug 模板](.github/ISSUE_TEMPLATE/bug_report.md) 中隐去细节后先建立联系）。

请在报告中尽量包含：影响面（本地 daemon / API / 前端）、复现条件、日志片段（**先抹掉 API Key**）。

## 说明

本项目是**本地自托管**的个人工具（默认只监听 localhost），不暴露公网；主要风险面为 ai/.env 中的 API Key——该文件已 gitignore，任何时候不要把它提交或粘贴到 issue 中。
