# 定时投递：创建、修改、暂停

## 原则

- **skill 本身不会定时**：05:00 触发必须由宿主（DSH 的会话提醒 `schedule_create`、cron、systemd timer 等）驱动。
- 定时任务到期时，宿主把一段提示文本投递回原会话，agent 再按 `SKILL.md` 跑整套流程。
- 无论定时是否启用，手动“跑一份 / 补发某天”始终可用。

## 在 DSH 里创建每天 05:00 的提醒

在**晨报工作目录**的会话里执行（这样技能与配置路径一致）：

```python
schedule_create(
    daily={"time": "05:00:00", "time_zone": "Asia/Shanghai"},
    title="半导体晨报",
    prompt=("跑今天的半导体晨报。先调用 skill 工具加载 morning-brief，再按其流程执行："
            "读 config.json 与 handbook → 检索 → 生成深度版 → "
            "python3 scripts/md2docx.py 转 docx → 按 delivery.mode 发邮件"
            "（正文=精简版，附件=Word）→ 发送成功后删除本地 md/docx。"),
)
```

建好后用 `schedule_list` 确认；想快速验证投递，可另建一条 `after_seconds=60` 的临时提醒，收到后 `schedule_delete`。

## 修改 / 暂停 / 恢复

| 需求 | 做法 |
|---|---|
| 改发送时间（如 6 点） | `schedule_update` 改 `daily.time`，保留同一 id |
| 暂停 | `schedule_delete` 删除提醒（skill 与规则文件保留） |
| 恢复 | 重新 `schedule_create`（上面那段） |
| 只看交易日 | 改成 `weekly`（周一至周五 05:00），节假日仍会触发，报告顶部标“休市” |
| 换收件人/内容 | 改 `config.json` 或规则文件，提醒本身不用动 |

## 运行语义（重要，别承诺做不到的事）

- 提醒依赖**宿主常驻**；到点时宿主没运行，则恢复后**只补发最近一次**错过的提醒，不会补齐中间漏掉的日子。
- 提醒触发会新建一轮对话执行整套流程；浏览器没开也能发出邮件。
- 手动“跑一份 / 补发某天”不受提醒状态影响。
- 如果用户只是问“晨报还在跑吗”，先查提醒状态（DSH：`schedule_list`），不要凭旧记忆回答。

## 非 DSH 环境

用 cron / systemd timer 调用你自己的 agent CLI（或 `scripts/md2docx.py` + `scripts/send_email.py` 处理已经写好的稿件），时间与覆盖窗口按 `config.json` 的 `timezone` / `window_start` 对齐。
