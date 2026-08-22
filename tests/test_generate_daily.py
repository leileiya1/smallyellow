import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_daily


def sample_data():
    return {
        "episode": {
            "title": "奶茶拿错了",
            "story_logline": "松松拿错奶茶后越解释越乱",
            "couple_conflict": "绵绵以为松松偷喝",
            "failed_fix": "补买成了超辣口味",
            "relationship_payoff": "两人一起寻找失主",
            "comment_question": "拿错奶茶要重买吗？",
        },
        "panels": [
            {
                "panel_no": number,
                "story_action": "松松和绵绵看着奶茶",
                "characters": ["松松", "绵绵"],
                "emotion": "尴尬",
                "composition": "中景，上方留白",
                "subtitle": "这杯是谁的？",
                "image_prompt_en": "SONGSONG and MIANMIAN looking at one milk tea, medium shot",
            }
            for number in range(1, 9)
        ],
    }


class DailyGeneratorTests(unittest.TestCase):
    def test_daily_seed_is_deterministic(self):
        self.assertEqual(generate_daily.seed_for_day("2026-08-22"), generate_daily.seed_for_day("2026-08-22"))

    def test_prompt_lock_adds_anchors_and_no_text(self):
        data = sample_data()
        generate_daily.lock_prompts(data)
        prompt_text = data["panels"][0]["image_prompt_en"]
        self.assertIn("SONGSONG", prompt_text)
        self.assertIn("MIANMIAN", prompt_text)
        self.assertIn("[NO TEXT]", prompt_text)
        self.assertIn("vertical 4:5", prompt_text)

    def test_valid_eight_panel_contract(self):
        data = sample_data()
        generate_daily.lock_prompts(data)
        generate_daily.validate(data)

    def test_existing_day_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            episode_dir = root / "episodes" / "2026-08-22"
            episode_dir.mkdir(parents=True)
            target = episode_dir / "配图Prompts.md"
            target.write_text("original", encoding="utf-8")
            with patch.object(generate_daily, "EPISODES_DIR", root / "episodes"), patch.object(
                generate_daily, "HISTORY_FILE", root / "episodes" / "index.json"
            ):
                with self.assertRaises(FileExistsError):
                    generate_daily.write_episode(
                        "2026-08-22", generate_daily.seed_for_day("2026-08-22"), sample_data(), {"model": "test"}
                    )
            self.assertEqual(target.read_text(encoding="utf-8"), "original")


if __name__ == "__main__":
    unittest.main()

