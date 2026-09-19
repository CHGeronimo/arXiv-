## 改动说明

做了什么、为什么这么做（关联 issue 请写 `Closes #N`）。

## 影响面

- [ ] 仅前端（js/css/index.html）
- [ ] 仅爬虫/AI 流水线
- [ ] 涉及 API 端点
- [ ] 涉及存储 schema（说明迁移方式）

## 测试

- [ ] `for t in tests/test_*.py; do LOG_DIR=/tmp python3 "$t"; done` 全部通过
- [ ] 新增/更新了对应回归测试（若改了逻辑）
- [ ] 手动验证了受影响的页面/任务（附截图或日志）
