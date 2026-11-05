---
name: morning-brief
description: Use when the user asks to run, resend, or reschedule a daily semiconductor-industry morning brief (半导体晨报) — product/technology news from the last 24 hours, mapped to A-share/HK listed companies, delivered as a plain-text email body plus a Word (docx) deep-dive attachment. Covers manual runs ("跑一份晨报", "补发X月X日的晨报"), scheduled 05:00 delivery, and restoring or pausing the reminder.
whenToUse: 用户说“跑晨报”“补发某天的晨报”“暂停/恢复晨报”“晨报改到 X 点”；或 05:00 定时提醒到点，需要生成半导体行业晨报并邮件发送时。
---

# 半导体行业每日晨报（morning-brief）

把「关注清单 → 检索 → 深度分析 → Word → 邮件」的固定流程封装成一个可调用技能。
规则不在本文件里，而在配置指向的规则文件里——它们可能被用户改过，**每次执行前都要重新读**。

## 0. 先读配置（没有配置就停下来）

> 路径约定：下文 `$SKILL_DIR` 指本文件所在目录（宿主会给出 base directory）；`{...}` 是 `config.json` 里的值，执行时替换为实际内容，不要照抄花括号。

配置优先级：`$MORNING_BRIEF_CONFIG` → `<技能目录>/config.json`。
仓库里的 `config.example.json` 是模板；`config.json` 已被 `.gitignore` 排除，只放本机私有设置。

| 字段 | 作用 |
|---|---|
| `recipient` | 收件人邮箱 |
| `subject` | 邮件主题模板，`{date}` 会被替换为 `YYYY-MM-DD` |
| `docx_basename` | Word 附件名前缀，完整名 = `{docx_basename}{YYYY年M月D日}.docx`（月日不补零） |
| `report_dir` | 临时工作目录（发送成功后清空，本地不留副本） |
| `timezone` / `window_start` | 覆盖窗口：前一日 `window_start` → 当日 `window_start`，默认 `Asia/Shanghai` + `05:00` |
| `handbook` / `watchlist` / `template` | 规则文件路径；相对路径按技能目录解析，可用 `~`；留空则用 `references/` 里的默认版本 |
| `delivery.mode` | `dsh_tool`（默认，用 DSH 的 `send_email` 工具）、`smtp`（用 `scripts/send_email.py`）、`none`（只生成文件） |
| `delivery.smtp.*` | `mode=smtp` 时使用；密码只从环境变量读（`password_env` 指定的变量名） |

配置缺失或字段不完整：先补齐，不要凭记忆编一个收件人。

```bash
python3 "$SKILL_DIR/scripts/validate.py"     # 校验配置、规则文件、转换器
```

## 1. 读规则（唯一定义来源）

| 文件 | 作用 |
|---|---|
| `handbook`（默认 `references/handbook.md`） | **主流程与硬性规则**：核心原则、检索分组、五问分析、质量红线、投递与清理。开工前完整读一遍 |
| `watchlist`（默认 `references/watchlist.md`） | 赛道 → 代表标的映射，用于把产品新闻落到 A 股/港股 |
| `template`（默认 `references/report-template.md`） | Word 深度版的**八章**骨架，输出结构以它为准 |

规则文件与旧记忆冲突时，**以文件为准**。

## 2. 执行流程（细节以 handbook 为准）

1. **定日期与窗口**：`date` 确认时区；报告日期 = 触发当天（补发时为用户指定日期）；窗口按 `timezone` / `window_start` 回推。
2. **检索**：`web_search` 一次并发 5–6 组（先进制程/封装、存储与价格、算力芯片与终端、设备与材料、主流看法、事件日历）。目标 **8–12 条产品级信息 + 3–5 条主流看法**；关键规格/时间/客户用 `web_fetch` 核对原文，并记录发布时间与链接。
3. **分析**：每条产品新闻按五问写全——型号/节点 → 关键参数 → 进度与卡点 → 供应链影响 → A 股落点（标的+时效）。主流看法分「共识 / 分歧 / 新变量」，至少 3 家机构 + 1 个产业界口径，并回答“市场已 price in 什么”。
4. **写深度版**：`{report_dir}/{docx_basename}{YYYY年M月D日}.md`，严格按模板八章。
5. **转 Word**：
   ```bash
   python3 "$SKILL_DIR/scripts/md2docx.py" \
     "{report_dir}/{docx_basename}{YYYY年M月D日}.md" \
     "{report_dir}/{docx_basename}{YYYY年M月D日}.docx"
   ```
   转换器无第三方依赖；文件名用中文日期、月日不补零。
6. **发邮件**（正文 = 精简版纯文本，附件 = Word 深度版）：
   - `delivery.mode = dsh_tool`：调用 DSH 的 `send_email` 工具，`to=recipient`、`subject=subject`、`body=<精简版正文>`、`attachments=[docx 路径]`。
   - `delivery.mode = smtp`：
     ```bash
     python3 "$SKILL_DIR/scripts/send_email.py" --config "$CONFIG" \
       --subject "…" --body-file "$BODY" --attach "$DOCX"
     ```
   - **主题不要自己加邮件插件已有的前缀**（例如 `[DSH]`），否则会变成 `[DSH] [DSH] …`。
7. **清理**：发送成功后删除 md 与 docx（本地不留副本）；发送失败则**保留**两个文件，在会话里说明原因。
8. **回复用户**：两三句摘要 + “已发到邮箱（正文 + Word 附件）”；不要复述全文，也不要用 `present` 生成额外副本。

## 3. 硬性规则（违反即返工）

- **产品优先**：一条新闻写不出型号/节点/规格/客户/时间，就不收；禁止“发布新品”“技术领先”这类空话。
- **每条事实带来源链接 + 发布时间**；区分**已发生事实 / 机构预期 / 未证实传闻**（传闻必须标“未经证实”）。
- 不编造参数、价格、客户、证券代码；拿不准写“待确认”；检索失败如实写“检索异常”，不拿宏观凑数。
- 邮件正文每条 200–300 字、整篇 1500–2500 字；信息密度优先，禁止套话填充。
- 休市日照常发，报告顶部标注“今日休市”。
- 结尾固定附非投资建议声明（见模板）。

## 4. 定时与手动

- **手动**：用户说“跑一份晨报”“补发 X 月 X 日的晨报”“重发昨天的”。手动跑同样走完整流程，但**必须重新检索**，不能复用旧文档。
- **定时**：skill 本身不会定时；05:00 触发必须由宿主（如 DSH 的 `schedule_create`）驱动，恢复/改时间/暂停见 `references/schedule.md`。
- 如果用户只是问“晨报还在跑吗”，先查宿主提醒状态（DSH：`schedule_list`），不要凭旧记忆回答。

## 5. 参考文件

| 文件 | 内容 |
|---|---|
| `references/handbook.md` | 主流程：核心原则、检索分组、五问分析、质量红线、产出与投递 |
| `references/watchlist.md` | 示例关注清单（赛道 → 标的映射 + 产品跟踪矩阵），可整体替换 |
| `references/report-template.md` | Word 深度版八章模板 |
| `references/output-spec.md` | 邮件正文七段结构、Word 八章骨架、交付前检查表 |
| `references/schedule.md` | 05:00 提醒的创建、修改、暂停与补发语义 |
| `scripts/md2docx.py` | 无依赖 Markdown → .docx 生成器 |
| `scripts/send_email.py` | 无 DSH 时的 SMTP 发信兜底（支持附件） |
| `scripts/validate.py` | 仓库/配置自检 |
| `scripts/install.sh` | 安装到 `~/.dsh/skills` 或项目 `.dsh/skills` |

> 本技能产出为公开信息整理与影响分析，不构成投资建议。
