# 竹影 · Shadow of the Bamboo

原创竹林忍者游戏，支持浏览器游玩、触屏控制，以及 TypeSafe Jev AI 的结构化决策测试。

**在线体验：** https://shadow-ninja-jev-lab.sjialu115.chatgpt.site

## 玩法

收集竹台上的三枚卷轴，再到森林最右侧的朱红鸟居完成救援。五点生命，近身刀击可以挡住敌方飞镖。

| 操作 | 键盘 |
| --- | --- |
| 左右移动 | A / D 或方向键 |
| 大跳跃 | Space / W / 上键 |
| 投掷飞镖 | J |
| 挥刀 / 挡镖 | K |
| 手动 / 规则演示 / Jev | 1 / 2 / 3 |
| 重新开始 / 暂停 | R / P |

移动设备使用游戏下方的触屏按钮。规则演示可以通关，不调用任何 AI 接口。

## Jev AI 模式

点击 **Jev AI**，输入 TypeSafe 官方 API Key（`apikey_` 开头）。每位体验者使用自己的账户和额度，不提供公共密钥。Vercel Key 不适用。

- Key 仅存于当前页面内存，经本站的 `/api/jev` 转发给固定的 TypeSafe 官方端点；应用不持久化密钥，也不记录请求正文或鉴权头。
- 关闭或刷新页面会清除 Key。请勿把 Key 写入源码、截图或 GitHub Issues。
- Jev 读取玩家坐标、速度、生命、平台、敌人、飞镖、卷轴等结构化状态，并选择一个动作。
- 每次动作执行 18 帧游戏时间，推理期间暂停模拟，浏览器界面仍可交互。这是分步决策实验，不是实时控制延迟基准。
- 请求超时、认证失败、余额不足或限流时暂停，不自动重试、不回退为规则 AI。
- 当前页面默认最多 200 次请求，可以主动选择提高到 500 / 1000。该上限不是账户余额；重开关卡不重置计数。
- 取消或重开会忽略旧回复，但已经提交给服务方的请求仍可能计费。

## 本地运行浏览器版

Node.js 22.13+（测试使用 Node 24）：

```sh
npm ci
npm run dev
```

构建：`npm run build`。代码基于 React / Vinext，生产输出为 Cloudflare Workers 兼容服务，`app/api/jev/route.ts` 提供同源 API 转发。发布配置位于 `.openai/hosting.json`，部署资源由 Sites 管理。

## Python 桌面版

原始 Pygame 实现保存在 `desktop/`，不依赖网页服务：

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r desktop/requirements.txt
.venv/bin/python desktop/game.py
# 官方 AI，或者启动后按 3 在窗口中粘贴 Key
.venv/bin/python desktop/game.py --mode ai --ask-key
```

## 验证

```sh
node --test tests/game.test.mjs
npx tsc --noEmit
# 桌面版（需额外安装 pytest）
.venv/bin/python -m pytest -q desktop/test_game.py
```

所有角色、竹林、卷轴与场景均由程序绘制，不包含商业游戏 ROM 或原版素材。
