# dsh-morning-brief

> 一个可复用的「半导体行业每日晨报」技能：把隔夜的**产品/技术新闻**整理成能落到 **A 股 / 港股** 的深度晨报，自动生成 Word 并邮件送达。
>
> A reusable agent skill for a daily semiconductor-industry morning brief — product/technology news → A-share impact → Word + email.

[![CI](https://github.com/HeIIoAgain/dsh-morning-brief/actions/workflows/ci.yml/badge.svg)](https://github.com/HeIIoAgain/dsh-morning-brief/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Skill](https://img.shields.io/badge/format-SKILL.md-6f42c1.svg)

---

## 这是什么

每天早上 05:00（可配置），按固定口径检索过去 24 小时的半导体产品/技术新闻，判断对 A 股 / 港股的传导，产出一份**产品优先、盘面其次**的晨报：

| 产物 | 说明 |
|---|---|
| 邮件正文 | 精简版：3–5 条产品要点（每条 200–300 字）+ 主流看法（共识/分歧/新变量）+ 映射表 |
| Word 附件 | 深度版八章：产品与工艺进展表、A 股映射、事件日历、风险与失效信号、12 条来源 |
| 本地文件 | **不保留**：`reports/` 只是发送前的临时工作区，发送成功后即删除 |

它不是一个新闻聚合脚本，而是一套**判断口径 + 检索模板 + 交付流水线**：规则写在 Markdown 里，工具只有「Markdown → docx」和「发邮件」，剩下的检索与写作交给 agent。

## 特点

- **产品优先**：写不出型号/节点/规格/客户/时间的新闻不收；盘面、资金只作背景。
- **规则与配置分离**：`references/` 是可替换的规则文件（手册、关注清单、模板），`config.json` 只放收件人等私有设置。
- **零第三方依赖**：`scripts/md2docx.py` 直接写 OOXML，不需要 pandoc / python-docx，`python3` 标准库即可。
- **双发送通道**：优先用 DeepSeek Harness 的 `send_email` 工具；没有 DSH 时退回标准库 SMTP（支持附件）。
- **可定时**：配合宿主提醒（DSH `schedule_create`）实现每天 05:00 自动投递；技能本身不依赖调度。
- **可审计**：`scripts/validate.py` 自检结构、frontmatter、docx 冒烟测试与隐私扫描，GitHub Actions 每次提交都跑。

## 目录结构

```text
dsh-morning-brief/
├── SKILL.md                      # 技能入口：触发条件 + 执行流程
├── config.example.json           # 配置模板（复制为 config.json 后修改）
├── references/
│   ├── handbook.md               # 主流程与硬性规则（检索分组、五问、质量红线、投递）
│   ├── watchlist.md              # 示例关注清单：赛道 → 标的映射 + 产品跟踪矩阵
│   ├── report-template.md        # Word 深度版八章模板
│   ├── output-spec.md            # 邮件正文七段结构 + 交付前检查表
│   └── schedule.md               # 05:00 提醒的创建、修改、暂停与补发语义
├── scripts/
│   ├── md2docx.py                # 无依赖 Markdown → .docx
│   ├── send_email.py             # SMTP 兜底发信（附件、SSL/STARTTLS）
│   ├── validate.py               # 仓库 / 配置自检
│   └── install.sh                # 安装到 ~/.dsh/skills 或项目 .dsh/skills
├── .github/workflows/validate.yml
├── LICENSE
└── README.md / README.en.md
```

## 快速开始

### 方式一：装进 DeepSeek Harness（推荐）

```bash
git clone https://github.com/<your-name>/dsh-morning-brief.git
mkdir -p ~/.dsh/skills
cp -R dsh-morning-brief ~/.dsh/skills/morning-brief

cd ~/.dsh/skills/morning-brief
cp config.example.json config.json
$EDITOR config.json          # 至少填 recipient；路径可用 ~
python3 scripts/validate.py   # 全绿即可
```

之后在任意会话里说「跑一份晨报」「补发 10 月 9 日的晨报」，agent 会加载本技能并执行。

### 方式二：项目级技能

```bash
mkdir -p <project>/.dsh/skills
cp -R dsh-morning-brief <project>/.dsh/skills/morning-brief
```

`<project>/.dsh/skills` 的优先级高于用户目录，适合只给某个仓库用。

### 方式三：脚本安装

```bash
./scripts/install.sh              # 默认装到 ~/.dsh/skills/morning-brief
./scripts/install.sh --project .  # 装到 ./.dsh/skills/morning-brief
./scripts/install.sh --dest /path/to/skills/morning-brief
```

`install.sh` 不会覆盖已有的 `config.json`；目标已存在时需要 `--force`（会先备份）。

### 不用 DSH 时

检索与写作由你自己的 agent（或手动）完成，本仓库提供规则、模板与工具：

```bash
# 1) Markdown → Word
python3 scripts/md2docx.py references/report-template.md out.docx

# 2) 发邮件（SMTP，密码从环境变量读取）
export MORNING_BRIEF_SMTP_PASSWORD='授权码'
python3 scripts/send_email.py --config config.json \
  --subject "半导体晨报 · 2026-10-09" \
  --body-file body.txt --attach out.docx
```

## 配置

复制 `config.example.json` 为 `config.json`。所有字段：

| 字段 | 默认 | 说明 |
|---|---|---|
| `recipient` | — | 收件人邮箱（必填） |
| `subject` | `半导体晨报 · {date}` | 主题模板，`{date}` → `YYYY-MM-DD`；**不要**手动加邮件插件已有的前缀（如 `[DSH]`） |
| `docx_basename` | `半导体晨报` | Word 附件名前缀，完整名 `{docx_basename}{YYYY年M月D日}.docx`（月日不补零） |
| `report_dir` | `~/.local/share/morning-brief/reports` | 临时工作目录；发送成功后清空 |
| `timezone` | `Asia/Shanghai` | 覆盖窗口与日期口径所用时区 |
| `window_start` | `05:00` | 覆盖窗口起点：前一日 `window_start` → 当日 `window_start` |
| `handbook` | `references/handbook.md` | 主流程规则文件；可指向你自己的副本 |
| `watchlist` | `references/watchlist.md` | 关注清单；可指向你自己的股票池 |
| `template` | `references/report-template.md` | Word 八章模板 |
| `delivery.mode` | `dsh_tool` | `dsh_tool` / `smtp` / `none`（只生成文件） |
| `delivery.smtp.*` | — | `mode=smtp` 时使用：`host`、`port`、`ssl`、`from`、`username`、`password_env` |

约定：

- 相对路径按**技能目录**解析；支持 `~`。
- `config.json` 含私有信息，已被 `.gitignore` 排除，**不要提交**。
- SMTP 密码不写进文件：只写环境变量名（`password_env`），运行时再取值。

## 使用

### 手动

对 agent 说：

- 「跑一份晨报」
- 「补发 2026 年 10 月 9 日的晨报」
- 「重发昨天的」

手动与定行走同一条流水线，但**必须重新检索**，不复用旧文档。

### 定时（DSH）

```python
schedule_create(
    daily={"time": "05:00:00", "time_zone": "Asia/Shanghai"},
    title="半导体晨报",
    prompt=("跑今天的半导体晨报。先加载 morning-brief 技能：读配置与 handbook → "
            "检索 → 生成深度版 → md2docx 转 Word → 按 delivery.mode 发邮件 → "
            "成功后删除本地 md/docx。"),
)
```

改时间用 `schedule_update`，暂停用 `schedule_delete`，详见 `references/schedule.md`。

> 提醒依赖宿主常驻。若到点时服务未运行，恢复后**只补发最近一次**错过的提醒，不会补齐中间漏掉的日子。

## 自定义

| 想改什么 | 怎么做 |
|---|---|
| 关注哪些赛道/标的 | 复制 `references/watchlist.md` 改写，把 `config.watchlist` 指向它 |
| 报告结构、判断口径、检索关键词 | 复制 `references/handbook.md` 改写，把 `config.handbook` 指向它 |
| Word 版式/章节 | 复制 `references/report-template.md` 改写，把 `config.template` 指向它 |
| 收件人、主题、附件名 | 改 `config.json` |
| 发送时间 | DSH：`schedule_update`；其他环境用 cron / systemd timer 调用同一套流程 |
| 不想要邮件 | `delivery.mode = "none"`，只生成文件 |

## 输出结构

**邮件正文（精简版，1500–2500 字）**：日期与休市标注 → 一句话总览 → 3–5 条产品要点（每条 200–300 字、六要素）→ 主流看法（共识/分歧/新变量）→ 映射表 4–7 行 → 本周事件 → 附件说明与非投资建议声明。

**Word 深度版（八章）**：今日产品要点 → 产品与工艺进展（四张表）→ 主流看法 → A 股/港股映射 → 产品事件日历 → 风险与失效信号 → 来源清单（12 条，含发布时间与链接）→ 生成元信息（检索关键词、检索异常、条目统计）。

完整骨架见 `references/report-template.md`。

## 质量红线

- 产品信息必须到「型号/节点/规格」层面，禁止“发布新品”“技术领先”式空话。
- 每条事实带**来源链接 + 发布时间**；事实 / 机构预期 / 未证实传闻分开标注。
- 不编造参数、价格、客户、证券代码；不确定处写“待确认”。
- 检索失败如实写“检索异常”，不拿宏观信息凑数。
- 收件人、主题前缀、附件命名按 `config.json`，不要硬编码。

## 依赖

- **Python 3.9+**，只用标准库（`zipfile`、`smtplib`、`email`、`json`、`re`）。
- **DeepSeek Harness（可选）**：`web_search` / `web_fetch` / `send_email` 工具与 `schedule_*` 提醒；不装 DSH 也能用规则和脚本。
- **邮件**：DSH 的 `send_email` 插件，或任意 SMTP 服务。

## 安全与隐私

- 仓库**不含**任何个人邮箱、密码、本机绝对路径；`scripts/validate.py` 与 CI 会扫描常见泄露模式。
- `config.json` 不进版本库；SMTP 密码只从环境变量读。
- 生成的晨报可能含公开市场信息与个人观点，发送前请自行确认收件人。
- 报告中的证券代码仅供参考，交易前请与行情软件核对。

## 已知限制

- 检索源为公开网页，**不接行情 API**，不保证价格/财务数字实时准确；文中数字均标注来源与时间。
- 定时投递依赖宿主进程常驻；宿主停机时可能漏发（只补最近一次）。
- 邮件主题前缀由邮件插件决定（DSH 默认 `[DSH]`），本技能不会重复添加。
- 晨报是信息整理与影响分析工具，质量取决于检索源与规则文件，需要定期维护 `watchlist.md`。

## 免责声明

本项目仅用于公开信息的整理与影响分析，**不构成任何投资建议**。市场有风险，据此操作风险自担。

## License

[MIT](LICENSE) © 2026 dsh-morning-brief contributors
