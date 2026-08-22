# 松松和绵绵 · 每日图片 Prompts

这个仓库每天由 GitHub Actions 调用 DeepSeek，生成一条原创情侣剧情和 8 张图片提示词。

生成过程完全在 GitHub 云端完成。仓库只保存最终 Prompt 和精简历史索引，不在个人电脑保存每日生成记录，也不会自动生成图片。

## 每日产物

```text
episodes/YYYY-MM-DD/配图Prompts.md
```

每份文件包含：

- 当天标题、剧情梗概和评论问题；
- 8 张图各自的剧情动作、后期字幕和英文图片 Prompt；
- 固定的松松、绵绵外貌锚点；
- 1080×1350、竖版 4:5、图片内无文字约束。

`episodes/index.json` 只记录近期标题、核心矛盾和随机种子，用于降低重复概率。

## 自动运行

工作流位于 `.github/workflows/daily-prompts.yml`，默认每天北京时间 09:00 左右触发。GitHub 的定时任务可能有少量排队延迟。

也可以在仓库的 **Actions → 每日情侣图片 Prompts → Run workflow** 手动生成。手动运行时可留空日期使用当天日期，也可以填写 `YYYY-MM-DD`。

## 仓库配置

- Actions Secret：`DEEPSEEK_API_KEY`
- 可选 Actions Variable：`DEEPSEEK_MODEL`
- 默认模型：`deepseek-v4-flash`

密钥只保存在 GitHub Actions Secret 中，禁止提交到代码、日志或 Prompt 文件。

