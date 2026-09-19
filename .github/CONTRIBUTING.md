# 贡献指南

感谢关注 arXiv 每日电讯！这是一个个人研究工具的公开仓库，欢迎提 Issue 和 PR。

## 开发环境

```bash
git clone https://github.com/CHGeronimo/arxivSCI-daily.git
cd arxivSCI-daily
pip install -r requirements.txt
cp backend/ai/.env.example backend/ai/.env   # 填入 GLM API Key（https://open.bigmodel.cn）
python3 daemon.py --port 8080
```

个人运行时文件（`research_profile.json` / `subscriptions.json` / `data/` / `logs/`）均自动生成且不入库，克隆后开箱即跑。

## 提交规范

- commit 标题用 `类型: 中文简述`，类型取 `feat / fix / docs / perf / chore / refactor`
- 一个 PR 聚焦一件事；关联 issue 写 `Closes #N`

## 测试要求

**所有逻辑改动必须保证回归测试全绿**（全部 Mock，不消耗 API 配额）：

```bash
for t in tests/test_*.py; do LOG_DIR=/tmp python3 "$t"; done
```

新增逻辑请配套新增 `tests/test_*.py`（参考现有脚本风格：脚本式断言 + FakeLLM Mock + `/tmp` 隔离）。

## 架构速览

- `crawler/` 六大发现源爬虫；`ai/` 分级 LLM 流水线（快筛→深读→趋势→聚类）
- `api.py` Flask 端点；`db.py` SQLite WAL + 写队列；`jobs.py` 凌晨错峰调度器
- `js/` ES modules 前端（日报/图谱/趋势/想法/简报五页）
- 详见 [README](README.md) 的流水线图与项目结构

## 安全

漏洞请勿开公开 issue，见 [SECURITY.md](.github/SECURITY.md)。
