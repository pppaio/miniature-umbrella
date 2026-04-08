#!/usr/bin/env python3
"""
ZZZ Daily Assistant (Image Recognition based)

A small automation framework that uses template matching + optional OCR
for assisting repetitive daily tasks in Zenless Zone Zero (ZZZ).

DISCLAIMER:
- For educational/personal use only.
- Automating gameplay may violate game Terms of Service. Use at your own risk.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import mss
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Please install dependencies: pip install -r requirements.txt") from exc


LOGGER = logging.getLogger("zzz_assistant")


@dataclasses.dataclass
class TemplateTarget:
    name: str
    path: str
    threshold: float = 0.88
    click_offset: Tuple[int, int] = (0, 0)


@dataclasses.dataclass
class StepAction:
    id: str
    find: Optional[TemplateTarget] = None
    wait_seconds: float = 0.8
    click: bool = False
    confidence: float = 0.0


class ScreenCapture:
    def __init__(self, monitor_index: int = 1):
        self.monitor_index = monitor_index

    def shot(self) -> np.ndarray:
        with mss.mss() as sct:
            monitor = sct.monitors[self.monitor_index]
            frame = np.array(sct.grab(monitor))
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


class VisionEngine:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.cache: Dict[str, np.ndarray] = {}

    def _load(self, rel_path: str) -> np.ndarray:
        if rel_path in self.cache:
            return self.cache[rel_path]

        target_path = self.assets_dir / rel_path
        image = cv2.imread(str(target_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Template not found: {target_path}")
        self.cache[rel_path] = image
        return image

    def locate(self, frame: np.ndarray, target: TemplateTarget) -> Tuple[Optional[Tuple[int, int]], float]:
        template = self._load(target.path)
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < target.threshold:
            return None, float(max_val)

        th, tw = template.shape[:2]
        center = (max_loc[0] + tw // 2 + target.click_offset[0], max_loc[1] + th // 2 + target.click_offset[1])
        return center, float(max_val)


class InputController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def click(self, point: Tuple[int, int]) -> None:
        if self.dry_run:
            LOGGER.info("[DRY-RUN] click at %s", point)
            return

        import pyautogui  # lazy import to avoid requirement when dry-run

        jitter = (random.randint(-2, 2), random.randint(-2, 2))
        pyautogui.moveTo(point[0] + jitter[0], point[1] + jitter[1], duration=random.uniform(0.08, 0.20))
        pyautogui.click()
        LOGGER.info("clicked at %s", point)


class DailyRunner:
    def __init__(self, capture: ScreenCapture, vision: VisionEngine, control: InputController):
        self.capture = capture
        self.vision = vision
        self.control = control

    def run(self, plan: List[StepAction], timeout_each: float = 12.0) -> None:
        for step in plan:
            LOGGER.info("Step: %s", step.id)
            deadline = time.time() + timeout_each

            if step.find is None:
                time.sleep(step.wait_seconds)
                continue

            matched = False
            while time.time() < deadline:
                frame = self.capture.shot()
                point, conf = self.vision.locate(frame, step.find)
                step.confidence = conf
                if point:
                    LOGGER.info("matched '%s' confidence=%.3f", step.find.name, conf)
                    if step.click:
                        self.control.click(point)
                    matched = True
                    break
                time.sleep(0.25)

            if not matched:
                LOGGER.warning("step '%s' skipped (not found). best_conf=%.3f", step.id, step.confidence)
            time.sleep(step.wait_seconds)


def load_plan(config_path: Path) -> List[StepAction]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    steps: List[StepAction] = []
    for row in data.get("steps", []):
        target = None
        if "find" in row:
            f = row["find"]
            target = TemplateTarget(
                name=f["name"],
                path=f["path"],
                threshold=float(f.get("threshold", 0.88)),
                click_offset=tuple(f.get("click_offset", [0, 0])),
            )
        steps.append(
            StepAction(
                id=row["id"],
                find=target,
                wait_seconds=float(row.get("wait_seconds", 0.8)),
                click=bool(row.get("click", False)),
            )
        )
    return steps


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ZZZ image-recognition daily assistant")
    p.add_argument("--config", default="configs/daily_plan.example.json", help="Path to plan JSON")
    p.add_argument("--assets", default="assets", help="Path to template assets directory")
    p.add_argument("--monitor", type=int, default=1, help="Monitor index for mss")
    p.add_argument("--dry-run", action="store_true", help="Only detect and print actions without clicking")
    p.add_argument("--timeout-each", type=float, default=12.0, help="Timeout per step (seconds)")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")

    plan = load_plan(Path(args.config))
    capture = ScreenCapture(monitor_index=args.monitor)
    vision = VisionEngine(Path(args.assets))
    control = InputController(dry_run=args.dry_run)
    runner = DailyRunner(capture, vision, control)

    LOGGER.info("Loaded %d steps from %s", len(plan), args.config)
    runner.run(plan, timeout_each=args.timeout_each)


if __name__ == "__main__":
    main()
