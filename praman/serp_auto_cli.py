"""CLI logic for serp-auto command."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Sequence

from praman.competition import (
    CSV_HEADER,
    SerpObservation,
    derive_competition_band,
    write_observation_template,
)
from praman.script import dedup_key, topic_key
from praman.serp_auto import (
    AutoSerpObservation,
    SerpAutoCache,
    auto_to_serp_observation,
    parse_serp_html,
    signals_to_observation,
)
from praman.serp_browser import CaptchaDetectedError, SerpBrowser


def _load_seeds(args) -> list[str]:
    seeds: list[str] = []
    if getattr(args, "seeds_file", None):
        with open(args.seeds_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    seeds.append(s)
    if getattr(args, "seeds", None):
        seeds.extend(args.seeds)
    return seeds


def _write_csv(out_p: Path, obs_list: list[SerpObservation], overwrite: bool = False):
    if out_p.exists() and not overwrite:
        raise FileExistsError(f"File exists: {out_p}")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for o in obs_list:
            w.writerow([o.keyword, o.top_results_stale or "", o.thin_results or "", o.weak_domains or "", o.own_sites_ranking or "", o.notes])


def _read_csv(path: Path) -> list[dict]:
    res = []
    if not path.exists():
        return res
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            res.append(row)
    return res


def run_serp_auto(args) -> int:
    seeds = _load_seeds(args)
    if not seeds:
        print("Error: No seeds provided", file=sys.stderr)
        return 1

    out_p = Path(args.out)
    if out_p.exists() and not getattr(args, "overwrite", False):
        print(f"Error: {out_p} exists. Use --overwrite", file=sys.stderr)
        return 1

    own_list = []
    if getattr(args, "own_domains", None):
        own_list = [d.strip() for d in args.own_domains.split(",") if d.strip()]

    cache = SerpAutoCache() if not getattr(args, "no_cache", False) else None
    browser = SerpBrowser(
        headless=getattr(args, "headless", False),
        min_delay=getattr(args, "min_delay", 18.0),
        max_delay=getattr(args, "max_delay", 28.0),
        close_after_each=True,
    )

    obs_list: list[SerpObservation] = []
    try:
        for i, seed in enumerate(seeds):
            try:
                if cache:
                    c = cache.get(seed, args.lang, args.region)
                    if c:
                        obs_list.append(auto_to_serp_observation(c))
                        continue
                results = browser.get_top_results(seed, num=args.num, lang=args.lang, region=args.region)
                html = ""
                try:
                    html = browser.driver.page_source if browser.driver else ""
                except Exception:
                    html = ""
                parsed = parse_serp_html(html, seed, own_domains=own_list)
                if parsed.captcha_detected:
                    raise CaptchaDetectedError(f"CAPTCHA for {seed}")
                auto = signals_to_observation(seed, parsed, own_domains=own_list)
                if cache:
                    cache.set(auto, args.lang, args.region)
                obs_list.append(auto_to_serp_observation(auto))
            except CaptchaDetectedError as e:
                print(f"CAPTCHA detected: {e}. Solve in browser if visible and retry.", file=sys.stderr)
                return 2
            except Exception as e:
                print(f"Warning: failed {seed}: {e}", file=sys.stderr)
                continue
    finally:
        browser._close_driver()

    _write_csv(out_p, obs_list, overwrite=getattr(args, "overwrite", False))
    print(f"SERP observations written to {out_p}")
    return 0
