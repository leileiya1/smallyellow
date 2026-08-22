#!/usr/bin/env python3
"""在 GitHub Actions 中生成《松松和绵绵》每日8图 Prompts。"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
EPISODES_DIR = ROOT / "episodes"
HISTORY_FILE = EPISODES_DIR / "index.json"
RULES_FILE = ROOT / "每日生成规则.md"
BIBLE_FILE = ROOT / "角色设定.md"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEZONE = "Asia/Shanghai"

STYLE = (
    "cute mainstream 2D chibi couple illustration, thick dark-cocoa outlines, flat matte color "
    "blocks, subtle hand-drawn paper grain, clean rounded shapes, warm low-saturation cream peach "
    "sage palette, large readable silhouettes, simple lived-in background, soft natural light, "
    "no 3D, no photorealism"
)
SONGSONG = (
    "SONGSONG, original chibi warm-caramel capybara boyfriend, rounded rectangular muzzle, tiny "
    "round ears, sleepy half-lidded black bean eyes, brick-red oval nose, exactly three dark "
    "whisker dots on each cheek, moss-green crossbody pouch, short stout body"
)
MIANMIAN = (
    "MIANMIAN, original chibi cream-white lop-eared rabbit girlfriend, pear-shaped round body, two "
    "long drooping ears with dusty-rose inner ears, left ear slightly folded inward, one small "
    "butter-yellow star hair clip on the left ear, black bean eyes, tiny W-shaped mouth, soft peach "
    "circular cheek blush, sky-blue mini tote bag"
)
NO_TEXT = (
    "[NO TEXT] absolutely no text, no letters, no numbers, no speech bubbles, no caption boxes, "
    "no logo, no watermark anywhere in the image. 1080x1350, vertical 4:5."
)

SEED_PARTS = {
    "object": [
        "一杯奶茶", "一只旧杯子", "最后一袋薯片", "情侣手机壳", "一张拍立得",
        "外卖备注", "一把备用钥匙", "一盆快蔫的薄荷", "一件缩水毛衣", "两张电影票",
        "一份早餐", "共享购物车", "一把雨伞", "一只快递盒", "冰箱里的便当",
    ],
    "place": [
        "厨房", "便利店门口", "地铁站", "小区电梯", "客厅", "阳台", "雨天公交站",
        "超市收银台", "快递柜旁", "卧室门口", "夜市摊位", "自助洗衣房",
    ],
    "conflict": [
        "说只用一下却弄坏了", "两个人都以为对方答应过", "偷偷准备惊喜却撞车",
        "嘴上说不在意其实一直记着", "为了省钱反而花了更多", "把两个人的东西拿反了",
        "想证明自己没错却拿出更糟证据", "答应补救却理解错了重点",
        "两个人同时撒了一个很容易拆穿的小谎", "本想帮忙却越帮越忙",
    ],
    "twist": [
        "陌生人意外卷入", "藏起来的证据自己掉出来", "补救品和原物只差一个字",
        "两个人同时拿出相反证据", "宠物或路人完成最后一击", "真正的问题藏在包装底下",
        "失败的补救反而解决另一个问题", "被误会的一方其实也忘了一件事",
    ],
}


def today_string() -> str:
    timezone = os.environ.get("CONTENT_TIMEZONE", DEFAULT_TIMEZONE)
    return datetime.now(ZoneInfo(timezone)).date().isoformat()


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("episodes/index.json 必须是数组")
    return data


def seed_for_day(day: str) -> dict[str, str]:
    rng = random.Random(day)
    return {name: rng.choice(values) for name, values in SEED_PARTS.items()}


def build_prompt(day: str, seed: dict[str, str], history: list[dict[str, Any]]) -> str:
    recent = history[-30:]
    return f"""
{RULES_FILE.read_text(encoding='utf-8')}

====== 固定角色与画风 ======
{BIBLE_FILE.read_text(encoding='utf-8')}

====== 今日任务 ======
日期：{day}
今日随机灵感：{json.dumps(seed, ensure_ascii=False)}
最近30条记录，必须避开：{json.dumps(recent, ensure_ascii=False)}

随机灵感只是起点，可以合理改造，但必须产出一个完整、具体、口语化的新故事。
只输出一个完整JSON对象。
""".strip()


def strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        value = "\n".join(lines).strip()
    return value


def deepseek_chat(prompt: str, api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base_url = (os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是原创情侣图片剧情生成器，只返回合法JSON。"},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0.92,
        "max_tokens": 12000,
        "stream": False,
    }
    request_data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=request_data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            return json.loads(strip_json_fence(content)), {
                "model": envelope.get("model", model),
                "usage": envelope.get("usage", {}),
                "request_id": envelope.get("id", ""),
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:600]
            last_error = RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}")
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except (
            urllib.error.URLError,
            http.client.IncompleteRead,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
        ) as exc:
            last_error = exc
        if attempt < 3:
            time.sleep(2**attempt)
    raise RuntimeError(f"DeepSeek生成失败：{last_error}")


def lock_prompts(data: dict[str, Any]) -> None:
    for panel in data.get("panels", []):
        names = {str(item) for item in panel.get("characters", [])}
        anchors = []
        if "松松" in names:
            anchors.append(SONGSONG)
        if "绵绵" in names:
            anchors.append(MIANMIAN)
        scene = str(panel.get("image_prompt_en", "")).strip()
        panel["image_prompt_en"] = ". ".join([STYLE, *anchors, scene, NO_TEXT])


def validate(data: dict[str, Any]) -> None:
    episode = data.get("episode")
    panels = data.get("panels")
    if not isinstance(episode, dict):
        raise RuntimeError("缺少episode对象")
    required_episode = {
        "title", "story_logline", "couple_conflict", "failed_fix",
        "relationship_payoff", "comment_question",
    }
    missing_episode = required_episode - set(episode)
    if missing_episode:
        raise RuntimeError("episode缺少：" + "、".join(sorted(missing_episode)))
    if not isinstance(panels, list) or len(panels) != 8:
        raise RuntimeError("panels必须恰好8项")
    for expected, panel in enumerate(panels, 1):
        if panel.get("panel_no") != expected:
            raise RuntimeError(f"第{expected}图编号错误")
        for key in ("story_action", "characters", "composition", "subtitle", "image_prompt_en"):
            if not panel.get(key):
                raise RuntimeError(f"第{expected}图缺少{key}")
        if len(str(panel["subtitle"]).replace(" ", "")) > 18:
            raise RuntimeError(f"第{expected}图字幕过长")
        prompt = str(panel["image_prompt_en"])
        for marker in ("thick dark-cocoa outlines", "[NO TEXT]", "vertical 4:5"):
            if marker not in prompt:
                raise RuntimeError(f"第{expected}图Prompt缺少{marker}")


def render_prompt_file(day: str, seed: dict[str, str], data: dict[str, Any], meta: dict[str, Any]) -> str:
    episode = data["episode"]
    parts = [
        f"# {episode['title']} · 配图 Prompts",
        "",
        f"**日期：** {day}  ",
        f"**一句话剧情：** {episode['story_logline']}  ",
        f"**具体矛盾：** {episode['couple_conflict']}  ",
        f"**失败补救：** {episode['failed_fix']}  ",
        f"**关系结果：** {episode['relationship_payoff']}  ",
        f"**评论问题：** {episode['comment_question']}  ",
        f"**生成模型：** {meta.get('model', DEFAULT_MODEL)}",
        "",
    ]
    for panel in data["panels"]:
        parts.extend(
            [
                "---",
                "",
                f"## 第{panel['panel_no']}图",
                "",
                f"**剧情：** {panel['story_action']}",
                "",
                f"**构图：** {panel['composition']}",
                "",
                f"**后期字幕：** {panel['subtitle']}",
                "",
                "```text",
                panel["image_prompt_en"],
                "```",
                "",
            ]
        )
    return "\n".join(parts).rstrip() + "\n"


def write_episode(day: str, seed: dict[str, str], data: dict[str, Any], meta: dict[str, Any]) -> Path:
    target_dir = EPISODES_DIR / day
    target = target_dir / "配图Prompts.md"
    if target.exists():
        raise FileExistsError(f"今日内容已存在，不覆盖：{target}")
    target_dir.mkdir(parents=True, exist_ok=False)
    target.write_text(render_prompt_file(day, seed, data, meta), encoding="utf-8")

    history = load_history()
    episode = data["episode"]
    history.append(
        {
            "date": day,
            "title": episode["title"],
            "story_logline": episode["story_logline"],
            "couple_conflict": episode["couple_conflict"],
            "seed": seed,
        }
    )
    HISTORY_FILE.write_text(json.dumps(history[-120:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="生成松松和绵绵每日8图 Prompts")
    parser.add_argument("--date", default=today_string(), help="YYYY-MM-DD，默认北京时间当天")
    parser.add_argument("--show-seed", action="store_true", help="只显示当天随机灵感，不调用API")
    args = parser.parse_args()
    datetime.strptime(args.date, "%Y-%m-%d")

    target = EPISODES_DIR / args.date / "配图Prompts.md"
    if target.exists():
        print(f"今日内容已存在，安全跳过：{target}")
        return 0

    seed = seed_for_day(args.date)
    if args.show_seed:
        print(json.dumps(seed, ensure_ascii=False))
        return 0

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少DEEPSEEK_API_KEY；请配置GitHub Actions Secret")

    history = load_history()
    data, meta = deepseek_chat(build_prompt(args.date, seed, history), api_key)
    lock_prompts(data)
    validate(data)
    output = write_episode(args.date, seed, data, meta)
    print(f"生成完成：{output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

