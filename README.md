# miniature-umbrella

基于图像识别的 **ZZZ（日常辅助）** 示例程序。

> ⚠️ 说明：自动化游戏操作可能违反游戏服务条款（ToS）。本项目仅用于学习图像识别与自动化流程设计，请自行评估风险。

## 功能概览

- 屏幕截图（`mss`）
- 模板匹配（OpenCV `matchTemplate`）
- 可配置任务流（JSON）
- 支持 `--dry-run`（只识别不点击）

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

准备模板图：

- 在 `assets/` 下放置按钮截图，例如：
  - `assets/dailies_button.png`
  - `assets/claim_button.png`

运行：

```bash
python zzz_daily_assistant.py --dry-run --config configs/daily_plan.example.json
```

确认识别稳定后，去掉 `--dry-run` 执行真实点击：

```bash
python zzz_daily_assistant.py --config configs/daily_plan.example.json
```

## 配置文件说明

参考 `configs/daily_plan.example.json`：

- `steps`: 步骤列表
- `id`: 步骤名
- `find`: 要查找的模板
  - `name`: 名称（日志用）
  - `path`: 模板图片相对 `assets/` 的路径
  - `threshold`: 匹配阈值（建议 0.85 ~ 0.95）
- `click`: 找到后是否点击
- `wait_seconds`: 步骤后等待时间

## 实战建议

1. 使用固定分辨率与窗口位置。
2. 模板截图要小而清晰（只截按钮主体）。
3. 先 `--dry-run` 观察日志中的置信度。
4. 点击动作已加入少量随机抖动，降低机械性轨迹。
5. 为异常流程（弹窗、网络波动）增加额外步骤与超时策略。

## 后续可扩展

- 接入 OCR（如 `pytesseract`）判断数字/文本状态。
- 增加多模板候选与区域裁剪，加快匹配速度。
- 增加“安全停机热键”与前台窗口校验，避免误点。
