# 江陈记茶业 · 小红书多账号自动发布系统

为江陈记茶业搭建的「素材整理 → 拼图配字 → 文案生成 → 多账号定时发布 → 风控防护」全自动内容流水线。
支持 12~15 个账号每天定时各发 1 条笔记。

## 目录结构

```
jcs_auto/
├── config/
│   ├── config.example.json      # 主配置（账号/时段/频率/素材策略）
│   └── copy_templates.json      # 文案模板库（标题公式/正文模板）
├── src/
│   ├── asset_lib.py             # 素材库：树状目录、图片指纹、已用图去重
│   ├── image_pipeline.py        # 拼图配字引擎：四宫格/九宫格/单图大字/系列化拼图（series_grid）
│   ├── copy_engine.py           # 文案引擎：标题公式+5段式正文+差异化+敏感词过滤
│   ├── risk_control.py          # 风控引擎：频率/去重/相似度/熔断
│   ├── scheduler.py             # 每日队列调度（错峰≥30分钟）
│   ├── publisher.py             # 发布器框架（Playwright 独立环境）
│   └── main.py                  # 主入口（--dry-run 预演 / --wait 定时到点发布 / 立即发布）
├── assets/                      # 素材库（树状，首次运行自动创建）
├── output/                      # 成图 + 日志 + 状态
└── tests/                       # 单元测试
```

## 快速开始

### 1. 安装依赖（本机已验证 Python 3.13 + Pillow 13）

```powershell
pip install Pillow
# 正式发布还需：
pip install playwright
playwright install chromium
```

### 2. 预演（不需要真实账号/素材，纯本地验证）

```powershell
cd C:\Users\Lenovo\Doubao\chats\2026-10-26\new-chat\jcs_auto
python src\main.py --dry-run
```

预演会：扫描素材 → 为当日队列每账号生成封面+文案 → 输出待发包清单（不发布）。
素材为空时预演不会产生包，先用样例验证各模块：

```powershell
python src\image_pipeline.py   # 生成 3 张模板示例图到 output\demo
python src\copy_engine.py      # 生成 4 场景示例文案
python src\risk_control.py     # 自检风控逻辑
```

### 3. 配置（商家部署时）

1. 复制 `config\config.example.json` 为 `config\config.json`，填 15 个账号：
   - `id`：账号标识；`name`：备注名
   - `proxy`：每账号独立代理IP（住宅IP最佳），防连坐
   - `env`：每账号独立 user_data_dir（浏览器指纹隔离）
2. 素材按树状目录放入 `assets\01_产品线` / `assets\02_场景`（子目录见 asset_lib.TREE）
3. 改 `config\copy_templates.json` 可调文案模板，无需改代码

### 4. 首次登录（每账号一次，人工步骤）

正式发布前，每个账号环境需人工扫码登录一次：
运行 `python src\publisher.py` 的用法提示，或用浏览器打开该账号 env 目录完成登录，
登录态保存在独立 user_data_dir，后续自动复用。

### 5. 正式发布（定时模式 / 立即模式二选一）

定时模式（长驻等待，按排期到点发布，30 秒轮询）：

```powershell
python src\main.py --wait
```

立即模式（生成完即逐个发布，适合配合系统定时任务每天跑一次）：

```powershell
python src\main.py
```

Windows 计划任务（每 10 分钟跑一次立即模式，只发到点任务）：

```powershell
schtasks /create /tn "jcs_auto" /tr "python D:\jcs_auto\src\main.py" /sc minute /mo 10
```

Linux crontab：`*/10 * * * * cd /opt/jcs_auto && python3 src/main.py >> output/logs/cron.log 2>&1`

发布器内置幂等保护：已发布账号当天不再重复发（state.json 记录）。

## 风控规则（已内置，不可绕过）

| 规则 | 实现 |
|------|------|
| 每账号每日 ≤1 条 | risk_control.check_frequency |
| 相邻账号间隔 ≥30 分钟 | scheduler + check_interval |
| 发布时段 9:00-22:00 | check_frequency |
| 图片已用过拦截 | asset_lib.is_used（hash） |
| 文案相似度 ≥60% 拦截 | check_copy（SequenceMatcher） |
| 验证码/违规/失败率≥20% 熔断 3 小时 | suspend + record_result |
| 素材树状管理+已用图标记 | asset_lib.mark_used |

## 部署清单（商家侧）

- [ ] 指纹浏览器环境 ×15（或自建 user_data_dir + 独立代理IP）
- [ ] 住宅代理IP ×15
- [ ] 常开电脑/服务器
- [ ] 素材原图按树状目录归置
- [ ] 15 账号逐一扫码登录一次
- [ ] 试运行：1 账号 3 天 → 每周 +3 账号扩容

## 风险提示（务必知悉）

1. 批量多账号营销是平台红线，即使按上述风控执行仍非零封号风险
2. 登录态过期需人工重登（无法全自动化）
3. 广告法敏感词已内置过滤（最/第一/顶级/治病等），文案引擎自动替换
