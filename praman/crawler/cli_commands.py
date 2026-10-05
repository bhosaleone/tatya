"""CLI Command Handlers for Marathi Web Crawler and Knowledge Graph."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from praman.crawler.db import CrawlerDB
from praman.crawler.engine import CrawlerEngine, CrawlerConfig
from praman.crawler.graph import GraphAnalyzer
from praman.crawler.seeds import MARATHI_SEEDS, SeedDomain
from praman.crawler.visualizer import generate_interactive_graph_html


def run_crawl(args: argparse.Namespace) -> int:
    """Executes high-concurrency crawler bots across Marathi seeds."""
    db_path = Path(args.db) if args.db else Path("marathi_web.db")
    db = CrawlerDB(db_path)

    # Determine seed list
    seeds = list(MARATHI_SEEDS)
    if args.domain:
        # User specified specific domains
        target_domains = [d.strip().lower() for d in args.domain.split(",")]
        seeds = [s for s in seeds if s.domain in target_domains]
        # If user passed custom domains not in default seeds
        for td in target_domains:
            if not any(s.domain == td for s in seeds):
                seeds.append(SeedDomain(
                    domain=td,
                    root_url=f"https://{td}/",
                    category="Custom",
                    title_mr=td,
                ))

    if args.limit and args.limit > 0:
        seeds = seeds[:args.limit]

    config = CrawlerConfig(
        num_workers=args.workers,
        per_domain_delay=args.delay,
        request_timeout=args.timeout,
        max_sitemaps_per_domain=args.max_sitemaps,
        max_pages_per_domain=args.max_pages,
    )

    engine = CrawlerEngine(db, config)
    print(f"\n=======================================================")
    print(f"🚀 PRAMAN MARATHI WEB CRAWLER & SITEMAP ENGINE")
    print(f"=======================================================")
    print(f"• Concurrency Bots:  {config.num_workers}")
    print(f"• Target Domains:    {len(seeds)}")
    print(f"• Database Path:     {db_path.resolve()}")
    print(f"• Max Sitemaps/Dom:  {config.max_sitemaps_per_domain}")
    print(f"• Max Pages/Dom:     {config.max_pages_per_domain}")
    print(f"=======================================================\n")

    results = engine.run_crawler_pool(seeds)

    # If recursive discovery flag is set, auto-discover new Marathi sites from links
    if getattr(args, "recursive", False):
        max_cands = getattr(args, "max_candidates", 100) or 100
        engine.run_recursive_discovery(max_candidates=max_cands)

    # Run Graph Analysis on the freshly crawled data
    print("\n📊 Computing Graph Topology, PageRank, and Kleinberg HITS...")
    analyzer = GraphAnalyzer(db)
    macro, domain_metrics = analyzer.compute_all_metrics()

    # Generate interactive visualization
    viz_file = Path(args.viz_out) if args.viz_out else Path("marathi_graph_view.html")
    generate_interactive_graph_html(db, macro, domain_metrics, viz_file)

    stats = db.get_summary_stats()
    print(f"\n=======================================================")
    print(f"✅ CRAWL & GRAPH GENERATION COMPLETE")
    print(f"=======================================================")
    print(f"• Total Domains in DB:         {stats['total_domains']}")
    print(f"• Verified Marathi Domains:    {stats['verified_marathi_domains']}")
    print(f"• Domains with Sitemaps:       {stats['domains_with_sitemaps']}")
    print(f"• Sitemaps Indexed:            {stats['total_sitemaps_indexed']}")
    print(f"• Total Sitemap URLs Found:    {stats['total_sitemap_urls_discovered']:,}")
    print(f"• Pages Stored:                {stats['total_pages_stored']}")
    print(f"• Internal Navigation Links:   {stats['internal_links']:,}")
    print(f"• Cross-Domain External Links: {stats['external_links']:,}")
    print(f"• Interactive Visual Graph:    {viz_file.resolve()}")
    print(f"=======================================================\n")

    return 0


def run_sitemaps_list(args: argparse.Namespace) -> int:
    """Lists all discovered sitemaps and their status."""
    db_path = Path(args.db) if args.db else Path("marathi_web.db")
    if not db_path.exists():
        print(f"Error: Database {db_path} does not exist. Run crawl first.", file=sys.stderr)
        return 1

    db = CrawlerDB(db_path)
    websites = db.get_all_websites()

    print(f"\n{'Domain':<26} | {'Sitemap Status':<14} | {'Type':<12} | {'URLs Discovered':<16} | {'Sitemap URL'}")
    print("-" * 100)
    for w in websites:
        st = w.get("sitemap_status") or "unmeasured"
        st_type = w.get("sitemap_type") or "-"
        urls = str(w.get("total_sitemap_urls") or 0)
        s_url = w.get("sitemap_url") or "-"
        print(f"{w['domain']:<26} | {st:<14} | {st_type:<12} | {urls:<16} | {s_url}")
    print("-" * 100)
    return 0


def run_graph_analytics(args: argparse.Namespace) -> int:
    """Computes and prints Knowledge Graph analytics (PageRank, HITS, density)."""
    db_path = Path(args.db) if args.db else Path("marathi_web.db")
    if not db_path.exists():
        print(f"Error: Database {db_path} does not exist. Run crawl first.", file=sys.stderr)
        return 1

    db = CrawlerDB(db_path)
    analyzer = GraphAnalyzer(db)
    macro, domain_metrics = analyzer.compute_all_metrics()

    print(f"\n=======================================================")
    print(f"🌐 MARATHI INTERNET KNOWLEDGE GRAPH MEASUREMENTS")
    print(f"=======================================================")
    print(f"• Total Domains (Nodes):       {macro.total_nodes}")
    print(f"• Cross-Domain Edges:          {macro.total_directed_edges}")
    print(f"• Total Internal Links:        {macro.internal_edges:,}")
    print(f"• Graph Density:               {macro.graph_density:.6f}")
    print(f"• Reciprocity:                 {macro.reciprocity*100:.2f}%")
    print(f"=======================================================\n")

    print("🏆 Top 10 Marathi Domains by PageRank:")
    print(f"{'Rank':<6} | {'Domain':<28} | {'Category':<22} | {'PageRank'}")
    print("-" * 75)
    for rank, (dom, pr, cat) in enumerate(macro.top_pagerank, 1):
        print(f"#{rank:<5} | {dom:<28} | {cat:<22} | {pr:.4f}")

    print("\n🏛️ Top 10 Marathi Authorities (Kleinberg HITS - Most Cited/Referenced):")
    print(f"{'Rank':<6} | {'Domain':<28} | {'Category':<22} | {'Authority Score'}")
    print("-" * 75)
    for rank, (dom, auth, cat) in enumerate(macro.top_authorities, 1):
        print(f"#{rank:<5} | {dom:<28} | {cat:<22} | {auth:.4f}")

    print("\n🧭 Top 10 Marathi Hubs (Kleinberg HITS - Best Navigators/Outlinkers):")
    print(f"{'Rank':<6} | {'Domain':<28} | {'Category':<22} | {'Hub Score'}")
    print("-" * 75)
    for rank, (dom, hub, cat) in enumerate(macro.top_hubs, 1):
        print(f"#{rank:<5} | {dom:<28} | {cat:<22} | {hub:.4f}")

    if args.viz:
        viz_p = Path(args.viz_out) if args.viz_out else Path("marathi_graph_view.html")
        generate_interactive_graph_html(db, macro, domain_metrics, viz_p)
        print(f"\n🎨 Interactive Knowledge Graph saved to: {viz_p.resolve()}")

    return 0


def run_export_graph(args: argparse.Namespace) -> int:
    """Exports graph nodes and edges to JSON."""
    db_path = Path(args.db) if args.db else Path("marathi_web.db")
    if not db_path.exists():
        print(f"Error: Database {db_path} does not exist.", file=sys.stderr)
        return 1

    db = CrawlerDB(db_path)
    websites = db.get_all_websites()
    edges = db.get_domain_link_matrix()

    data = {
        "nodes": websites,
        "edges": edges,
    }

    out_file = Path(args.out) if args.out else Path("marathi_web_graph.json")
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported graph ({len(websites)} nodes, {len(edges)} edges) to {out_file.resolve()}")
    return 0
