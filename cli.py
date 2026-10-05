#!/usr/bin/env python3
"""Praman CLI: Evidence-first Indic keyword demand research & content planning."""

import argparse
import os
from pathlib import Path
import sys

from praman.competition import CompetitionIndex, write_observation_template
from praman.config import Mode, Settings, Weights
from praman.pipeline import run_research
from praman.planner import generate_content_plan
from praman.report import render_csv_report, render_json_report, render_markdown_report


def cmd_research(args: argparse.Namespace) -> int:
    seeds: list[str] = []
    if args.seeds_file:
        with open(args.seeds_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    seeds.append(stripped)
    if args.seeds:
        seeds.extend(args.seeds)

    if not seeds:
        print("Error: No seeds provided. Specify seeds as arguments or via --seeds-file.", file=sys.stderr)
        return 1

    settings = Settings(
        language=args.lang,
        region=args.region,
        mode=Mode(args.mode),
        max_seeds=args.max_seeds,
        max_queries=args.max_queries,
        latin_expansion=args.latin_expansion,
        commercial_expansion=args.commercial_expansion,
        recorded_file=Path(args.recorded) if args.recorded else None,
    )

    comp_idx = None
    if args.serp:
        comp_path = Path(args.serp)
        if comp_path.exists():
            comp_idx = CompetitionIndex.from_csv(comp_path)
        else:
            print(f"Warning: SERP file '{args.serp}' not found; proceeding without competition data.", file=sys.stderr)

    result = run_research(seeds, settings, comp_idx)

    # Format output
    if args.format == "csv":
        output = render_csv_report(result)
    elif args.format == "json":
        output = render_json_report(result, settings.mode)
    else:
        output = render_markdown_report(result, settings.mode)

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to {args.out}")
    else:
        print(output)

    return 0


def cmd_serp(args: argparse.Namespace) -> int:
    seeds: list[str] = []
    if args.seeds_file:
        with open(args.seeds_file, "r", encoding="utf-8") as f:
            seeds.extend([l.strip() for l in f if l.strip() and not l.startswith("#")])
    if args.seeds:
        seeds.extend(args.seeds)

    if not seeds:
        print("Error: No seeds specified for SERP template.", file=sys.stderr)
        return 1

    out_p = Path(args.out)
    try:
        write_observation_template(seeds, out_p, overwrite=args.overwrite)
        print(f"SERP observation template written to {out_p}")
        print("Columns: keyword, top_results_stale, thin_results, weak_domains, own_sites_ranking, notes")
        print("Values: 'yes', 'no', or leave blank for unrecorded.")
    except FileExistsError as e:
        print(f"Error: {e} Use --overwrite to replace existing file.", file=sys.stderr)
        return 1
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    seeds: list[str] = []
    if args.seeds_file:
        with open(args.seeds_file, "r", encoding="utf-8") as f:
            seeds.extend([l.strip() for l in f if l.strip() and not l.startswith("#")])
    if args.seeds:
        seeds.extend(args.seeds)

    if not seeds:
        print("Error: No seeds provided for planning.", file=sys.stderr)
        return 1

    settings = Settings(
        language=args.lang,
        mode=Mode(args.mode),
        latin_expansion=args.latin_expansion,
        commercial_expansion=args.commercial_expansion,
        recorded_file=Path(args.recorded) if args.recorded else None,
    )

    result = run_research(seeds, settings)
    plan = generate_content_plan(result.scores)

    # Format editorial plan as Markdown
    lines = [
        f"# Praman Editorial Content Plan — Language: {args.lang.upper()}",
        f"Analyzed {len(result.scores)} keywords into {len(plan.clusters)} topic clusters.",
        "",
        "## Recommended Publishing Calendar",
        "| Order | Topic / Title | Cluster Demand | Primary Intent | Recommended Article Shape |",
        "|---|---|---|---|---|",
    ]

    for c in plan.calendar:
        lines.append(
            f"| #{c.recommended_publish_order} | **{c.primary_title}** | {c.cluster_demand:.3f} | `{c.primary_intent}` | {c.article_shape} |"
        )

    lines.extend([
        "",
        "## Internal Link Architecture",
        "| Source Topic | Target Topic | Suggested Anchor Text | Strategic Rationale |",
        "|---|---|---|---|",
    ])

    for link in plan.link_graph:
        lines.append(
            f"| {link.source_topic} | {link.target_topic} | **`{link.anchor_text}`** | {link.rationale} |"
        )

    if plan.orphan_topics:
        lines.extend([
            "",
            "## Standalone / Pillar Topics (No Inbound Links Suggested)",
        ])
        for o in plan.orphan_topics:
            lines.append(f"- `{o}`")

    output = "\n".join(lines)
    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Content plan written to {args.out}")
    else:
        print(output)

    return 0


def cmd_weights(args: argparse.Namespace) -> int:
    w = Weights()
    print("Praman Pinned Demand Voice Weights (MATH.md §6):")
    print(f"  • Breadth (Expansion Breadth):  {w.breadth:.2f} (50%)")
    print(f"  • Coverage (Head Presence):     {w.coverage:.2f} (25%)")
    print(f"  • Density (Question Density):   {w.density:.2f} (15%)")
    print(f"  • Depth (Rank Depth):           {w.depth:.2f} (10%)")
    print("\nInvariants:")
    print("  1. Weights sum strictly to 1.0.")
    print("  2. If any voice is unmeasured, surviving weights do NOT renormalize.")
    print("  3. The score is capped below 1.0 and flagged partial (MATH.md Theorem 2).")
    return 0


def cmd_serp_auto(args: argparse.Namespace) -> int:
    from praman import serp_auto_cli

    return serp_auto_cli.run_serp_auto(args)


def cmd_serp_dates(args: argparse.Namespace) -> int:
    from praman import serp_dates_cli

    rows = serp_dates_cli.run_serp_dates(
        query=args.query,
        num=args.num,
        lang=args.lang,
        region=args.region,
        use_selenium=not args.no_selenium,
        headless=args.headless,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        out=Path(args.out) if args.out else None,
        cache=not args.no_cache,
    )
    if not args.out:
        import json

        print(json.dumps([r.to_dict() for r in rows], ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="praman",
        description="Evidence-first keyword demand research and content planning for Indian regional languages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: research
    p_research = subparsers.add_parser("research", help="Run keyword demand research on seeds")
    p_research.add_argument("seeds", nargs="*", help="Seed keywords to evaluate")
    p_research.add_argument("--seeds-file", help="File with seed keywords (one per line)")
    p_research.add_argument("--lang", default="mr", help="Target language code (e.g. mr, hi, ta, te, bn, gu, kn)")
    p_research.add_argument("--region", default="IN", help="Region code (default: IN)")
    p_research.add_argument("--mode", choices=["fixture", "recorded", "live"], default="fixture", help="Execution mode")
    p_research.add_argument("--recorded", help="Path to recorded.json when mode=recorded")
    p_research.add_argument("--serp", help="Path to human SERP observations CSV")
    p_research.add_argument("--max-seeds", type=int, help="Seed count ceiling")
    p_research.add_argument("--max-queries", type=int, help="Total query count ceiling")
    p_research.add_argument("--latin-expansion", action="store_true", help="Include A-Z alphabet expansion")
    p_research.add_argument("--commercial-expansion", action="store_true", help="Include Indian commercial & affiliate modifier probes")
    p_research.add_argument("--format", choices=["md", "csv", "json"], default="md", help="Output format")
    p_research.add_argument("-o", "--out", help="Output file path")
    p_research.set_defaults(func=cmd_research)

    # Subcommand: serp
    p_serp = subparsers.add_parser("serp", help="Generate human SERP observation template CSV")
    p_serp.add_argument("seeds", nargs="*", help="Seed keywords")
    p_serp.add_argument("--seeds-file", help="File with seed keywords")
    p_serp.add_argument("-o", "--out", required=True, help="Output CSV path")
    p_serp.add_argument("--overwrite", action="store_true", help="Overwrite if output file exists")
    p_serp.set_defaults(func=cmd_serp)

    # Subcommand: plan
    p_plan = subparsers.add_parser("plan", help="Generate editorial publishing calendar and link graph")
    p_plan.add_argument("seeds", nargs="*", help="Seed keywords")
    p_plan.add_argument("--seeds-file", help="File with seed keywords")
    p_plan.add_argument("--lang", default="mr", help="Target language code")
    p_plan.add_argument("--mode", choices=["fixture", "recorded", "live"], default="fixture", help="Execution mode")
    p_plan.add_argument("--recorded", help="Path to recorded.json")
    p_plan.add_argument("--latin-expansion", action="store_true", help="Include A-Z alphabet expansion")
    p_plan.add_argument("--commercial-expansion", action="store_true", help="Include Indian commercial & affiliate modifier probes")
    p_plan.add_argument("-o", "--out", help="Output markdown file path")
    p_plan.set_defaults(func=cmd_plan)

    # Subcommand: weights
    p_weights = subparsers.add_parser("weights", help="Display pinned demand weights and algebraic rules")
    p_weights.set_defaults(func=cmd_weights)

    # Subcommand: serp-auto (automated SERP competition)
    p_serp_auto = subparsers.add_parser("serp-auto", help="Auto-generate SERP competition observations via browser")
    p_serp_auto.add_argument("seeds", nargs="*", help="Seed keywords")
    p_serp_auto.add_argument("--seeds-file", help="File with seed keywords")
    p_serp_auto.add_argument("-o", "--out", required=True, help="Output CSV path")
    p_serp_auto.add_argument("--overwrite", action="store_true", help="Overwrite if output file exists")
    p_serp_auto.add_argument("--lang", default="mr", help="Target language code")
    p_serp_auto.add_argument("--region", default="IN", help="Region code")
    p_serp_auto.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    p_serp_auto.add_argument("--min-delay", type=float, default=18.0, help="Min delay between searches (seconds)")
    p_serp_auto.add_argument("--max-delay", type=float, default=28.0, help="Max delay between searches (seconds)")
    p_serp_auto.add_argument("--num", type=int, default=10, help="Results per search")
    p_serp_auto.add_argument("--own-domains", help="Comma-separated own domains to detect (e.g. example.com,site.in)")
    p_serp_auto.add_argument("--fill-blanks", action="store_true", help="Fill only blank cells from existing CSV")
    p_serp_auto.add_argument("--serp", help="Existing SERP CSV to update when using --fill-blanks")
    p_serp_auto.add_argument("--no-cache", action="store_true", help="Disable SERP parsing cache")
    p_serp_auto.set_defaults(func=cmd_serp_auto)

    # Subcommand: serp-dates (extract published dates)
    p_serp_dates = subparsers.add_parser("serp-dates", help="Extract published/modified dates for Google top results")
    p_serp_dates.add_argument("query", help="Search query")
    p_serp_dates.add_argument("-o", "--out", help="Output CSV or JSON path")
    p_serp_dates.add_argument("--num", type=int, default=10, help="Number of results")
    p_serp_dates.add_argument("--lang", default="mr", help="Language")
    p_serp_dates.add_argument("--region", default="IN", help="Region")
    p_serp_dates.add_argument("--no-selenium", action="store_true", help="Do not use Selenium (lightweight HTTP)")
    p_serp_dates.add_argument("--headless", action="store_true", help="Headless browser")
    p_serp_dates.add_argument("--min-delay", type=float, default=18.0, help="Min delay")
    p_serp_dates.add_argument("--max-delay", type=float, default=28.0, help="Max delay")
    p_serp_dates.add_argument("--no-cache", action="store_true", help="Disable cache")
    p_serp_dates.set_defaults(func=cmd_serp_dates)

    # Subcommand: crawl (high-concurrency crawler bots)
    p_crawl = subparsers.add_parser("crawl", help="Run high-concurrency crawler bots to map Marathi websites and sitemaps")
    p_crawl.add_argument("--domain", help="Specific domain(s) to crawl (comma-separated, e.g. 'loksatta.com,paisamarg.com')")
    p_crawl.add_argument("--workers", type=int, default=24, help="Number of concurrent crawler worker bots (default: 24)")
    p_crawl.add_argument("--db", default="marathi_web.db", help="SQLite database path (default: marathi_web.db)")
    p_crawl.add_argument("--limit", type=int, help="Limit number of seed domains to crawl")
    p_crawl.add_argument("--delay", type=float, default=0.3, help="Per-domain polite delay in seconds (default: 0.3)")
    p_crawl.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout (seconds)")
    p_crawl.add_argument("--max-sitemaps", type=int, default=5, help="Max child sitemaps to resolve per domain (default: 5)")
    p_crawl.add_argument("--max-pages", type=int, default=20, help="Max pages to crawl per domain for link extraction (default: 20)")
    p_crawl.add_argument("--recursive", action="store_true", help="Auto-discover and crawl new Marathi sites from cross-domain links")
    p_crawl.add_argument("--max-candidates", type=int, default=100, help="Max candidate external domains to probe in recursive mode")
    p_crawl.add_argument("--viz-out", default="marathi_graph_view.html", help="Path to write interactive HTML graph visualization")
    p_crawl.set_defaults(func=lambda args: __import__("praman.crawler.cli_commands", fromlist=["run_crawl"]).run_crawl(args))

    # Subcommand: sitemaps (list discovered sitemaps)
    p_sitemaps = subparsers.add_parser("sitemaps", help="List discovered sitemaps and status for all domains")
    p_sitemaps.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    p_sitemaps.set_defaults(func=lambda args: __import__("praman.crawler.cli_commands", fromlist=["run_sitemaps_list"]).run_sitemaps_list(args))

    # Subcommand: graph (Knowledge Graph analysis & metrics)
    p_graph = subparsers.add_parser("graph", help="Compute Marathi Web Knowledge Graph metrics (PageRank, HITS, density)")
    p_graph.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    p_graph.add_argument("--viz", action="store_true", default=True, help="Generate interactive HTML visualizer")
    p_graph.add_argument("--viz-out", default="marathi_graph_view.html", help="Path for interactive HTML visualizer")
    p_graph.set_defaults(func=lambda args: __import__("praman.crawler.cli_commands", fromlist=["run_graph_analytics"]).run_graph_analytics(args))

    # Subcommand: search (Marathi-First Full-Text Search)
    p_search = subparsers.add_parser("search", help="Search the Marathi web index with BM25 and PageRank ranking")
    p_search.add_argument("query", help="Search query (Devanagari or Romanized Marathi)")
    p_search.add_argument("--category", default="all", help="Category filter (e.g. News, Finance, Agriculture, Wiki)")
    p_search.add_argument("--limit", type=int, default=15, help="Max results to display")
    p_search.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    def _cmd_search(args: argparse.Namespace) -> int:
        from praman.crawler.db import CrawlerDB
        from praman.search.engine import MarathiSearchEngine
        from praman.search.indexer import SearchIndexer
        db = CrawlerDB(args.db)
        indexer = SearchIndexer(db)
        indexer.build_index()
        engine = MarathiSearchEngine(db)
        resp = engine.search_full(args.query, category=args.category, limit=args.limit)
        print(f"\n🔍 '{args.query}' साठी {resp.total_found} निकाल सापडले ({resp.execution_time_ms} ms)")
        print(f"📌 पद्धती (Tier): {resp.tier_used.upper()} | शोध हेतू (Intent): {resp.intent} | अपेक्षित स्वरूप: {resp.article_shape}")
        print("=" * 80)
        for i, r in enumerate(resp.results, 1):
            print(f"#{i} [{r.domain} / {r.category}] {r.title}")
            print(f"   🔗 {r.url}")
            print(f"   📊 PageRank: {r.pagerank:.4f} | संकल्पना व्याप्ती (Coverage): {r.coverage*100:.0f}% | मराठी: {r.marathi_char_ratio}% | Score: {r.relevance_score:.4f}")
            print(f"   📝 {r.snippet}")
            print("-" * 80)
        return 0
    p_search.set_defaults(func=_cmd_search)

    # Subcommand: directory (Categorized Marathi Web Directory)
    p_directory = subparsers.add_parser("directory", help="Display the curated directory of the Marathi web")
    p_directory.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    def _cmd_directory(args: argparse.Namespace) -> int:
        from praman.crawler.db import CrawlerDB
        from praman.search.directory import MarathiDirectory
        db = CrawlerDB(args.db)
        dir_mgr = MarathiDirectory(db)
        categories = dir_mgr.get_full_directory()
        print("\n=======================================================")
        print("📂 मराठी इंटरनेट अधिकृत निर्देशिका (MARATHI WEB DIRECTORY)")
        print("=======================================================")
        for c in categories:
            print(f"\n{c.icon} {c.title_mr} ({c.title_en}) — {len(c.entries)} संकेतस्थळे")
            print(f"   वर्णन: {c.description_mr}")
            print(f"   {'-'*70}")
            for e in c.entries[:8]:
                print(f"   • {e.title:<24} | {e.domain:<28} | PR: {e.pagerank:.4f} | {e.total_urls:,} पेजेस")
        print("\n=======================================================\n")
        return 0
    p_directory.set_defaults(func=_cmd_directory)

    # Subcommand: serve (Interactive Marathi Search & Directory Web Portal)
    p_serve = subparsers.add_parser("serve", help="Launch the local interactive Marathi Search Engine & Directory Web Portal")
    default_port = int(os.environ.get("PORT", "8080"))
    p_serve.add_argument("--port", type=int, default=default_port, help=f"Port to serve on (default: {default_port})")
    p_serve.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    p_serve.add_argument("--viz", default="marathi_graph_view.html", help="Path to interactive graph HTML")
    def _cmd_serve(args: argparse.Namespace) -> int:
        from pathlib import Path
        import gzip
        import shutil
        db_path = Path(args.db)
        gz_path = Path(str(args.db) + ".gz") if not str(args.db).endswith(".gz") else Path(args.db)
        
        # If DB doesn't exist or is an empty/stub file (< 1MB) and .gz exists, extract it!
        if gz_path.exists() and (not db_path.exists() or db_path.stat().st_size < 1_000_000):
            print(f"📦 Extracting {gz_path} -> {db_path} ({gz_path.stat().st_size / (1024*1024):.1f} MB)...")
            with gzip.open(gz_path, "rb") as f_in, open(db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            print(f"✅ Extracted database: {db_path.stat().st_size / (1024*1024):.1f} MB.")
            
        from praman.crawler.db import CrawlerDB
        from praman.search.server import serve_search_portal
        db = CrawlerDB(args.db)
        serve_search_portal(db, port=args.port, graph_path=args.viz)
        return 0
    p_serve.set_defaults(func=_cmd_serve)

    # Subcommand: live-crawler (Continuous Fresh Link Crawler)
    p_live = subparsers.add_parser("live-crawler", help="Run background crawler monitoring fresh Marathi RSS feeds and sitemaps")
    p_live.add_argument("--interval", type=int, default=300, help="Interval in seconds between crawl sweeps (default: 300)")
    p_live.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    def _cmd_live(args: argparse.Namespace) -> int:
        from praman.crawler.db import CrawlerDB
        from praman.crawler.freshness_crawler import FreshnessCrawler
        db = CrawlerDB(args.db)
        crawler = FreshnessCrawler(db)
        crawler.run_daemon(interval_seconds=args.interval)
        return 0
    p_live.set_defaults(func=_cmd_live)

    # Subcommand: refresh-news (One-shot poll of fresh feeds)
    p_refresh = subparsers.add_parser("refresh-news", help="Poll live Marathi feeds once and index newly published links")
    p_refresh.add_argument("--db", default="marathi_web.db", help="SQLite database path")
    def _cmd_refresh(args: argparse.Namespace) -> int:
        from praman.crawler.db import CrawlerDB
        from praman.crawler.freshness_crawler import FreshnessCrawler
        db = CrawlerDB(args.db)
        crawler = FreshnessCrawler(db)
        print("🔄 Checking live Marathi feeds for newly published links...")
        count = crawler.crawl_once()
        print(f"✅ Finished! Added and indexed {count} newly published Marathi articles.")
        return 0
    p_refresh.set_defaults(func=_cmd_refresh)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()


