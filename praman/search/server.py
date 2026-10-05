"""Local HTTP Search Server and Web Application for Marathi Search & Directory.

Light Sepia & Royal Saffron Theme.
Adheres strictly to METHODOLOGY.md and MATH.md principles.

Zero external dependencies: uses Python standard library http.server.
Serves:
- /                  -> Interactive Light Sepia & Saffron Marathi Search & Directory Portal
- /api/search?q=...  -> JSON search results with hybrid ranking, intent, freshness & coverage
- /api/suggest?q=... -> Live autocomplete suggestions
- /api/directory     -> Curated categorized directory of the Marathi web
"""

from __future__ import annotations
import http.server
import json
import socketserver
import urllib.parse
from pathlib import Path
from typing import Any

from praman.crawler.db import CrawlerDB
from praman.crawler.freshness_crawler import FreshnessCrawler
from praman.search.engine import MarathiSearchEngine
from praman.search.directory import MarathiDirectory
from praman.search.discover import MarathiDiscoverService
from praman.search.indexer import SearchIndexer


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>तात्या — मराठी इंटरनेटचा आपला शोध | स्वतंत्र मराठी शोधयंत्र</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Yantramanav:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Light Sepia & Parchment Palette */
            --bg-base: #FAF6EE;
            --bg-surface: #FFFFFF;
            --bg-card: #FFFDF9;
            --bg-card-hover: #FEF8ED;
            --border-subtle: #E8DFD1;
            --border-focus: #E65100;
            
            /* Typography in Deep Sepia */
            --text-primary: #2B2118;
            --text-secondary: #5C4B3E;
            --text-muted: #8A7A6D;
            
            /* Royal Saffron & Warm Accents */
            --saffron-primary: #E65100;
            --saffron-bright: #FF6F00;
            --saffron-gradient: linear-gradient(135deg, #FF6F00 0%, #D84315 100%);
            --saffron-soft: rgba(230, 81, 0, 0.08);
            --saffron-border: rgba(230, 81, 0, 0.25);
            --amber-gold: #D97706;
            --emerald-green: #15803D;
            --emerald-soft: rgba(21, 128, 61, 0.08);
            
            /* Shadows & Transitions */
            --shadow-subtle: 0 4px 16px rgba(74, 53, 34, 0.06);
            --shadow-float: 0 10px 30px rgba(74, 53, 34, 0.10);
            --shadow-glow: 0 0 0 3px rgba(255, 111, 0, 0.20);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Plus Jakarta Sans', 'Yantramanav', sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.6;
        }

        /* Top Header */
        header {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border-subtle);
            padding: 14px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 50;
            box-shadow: 0 2px 10px rgba(74, 53, 34, 0.04);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
            text-decoration: none;
            color: inherit;
        }

        .logo-box {
            background: var(--saffron-gradient);
            color: #FFFFFF;
            font-weight: 900;
            font-size: 17px;
            padding: 7px 14px;
            border-radius: 9px;
            box-shadow: 0 4px 14px rgba(230, 81, 0, 0.35);
            display: flex;
            align-items: center;
            gap: 6px;
            letter-spacing: 0.5px;
        }

        .brand-text h1 {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 20px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.3px;
        }

        .brand-text span {
            font-size: 11px;
            color: var(--saffron-primary);
            font-weight: 600;
            display: block;
            margin-top: -2px;
        }

        .nav-tabs {
            display: flex;
            gap: 6px;
            background: var(--bg-base);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border-subtle);
        }

        .nav-tab {
            padding: 7px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            background: transparent;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .nav-tab:hover {
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        .nav-tab.active {
            background: var(--saffron-primary);
            color: #FFFFFF;
            box-shadow: 0 2px 8px rgba(230, 81, 0, 0.25);
        }

        /* Container */
        .container {
            max-width: 960px;
            width: 100%;
            margin: 0 auto;
            padding: 32px 20px;
            flex: 1;
        }

        /* Hero */
        .hero {
            text-align: center;
            margin: 36px 0 28px 0;
            transition: all 0.3s;
        }

        .hero.compact {
            margin: 10px 0 18px 0;
        }

        .hero h2 {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 8px;
            color: var(--text-primary);
            letter-spacing: -0.5px;
        }

        .hero h2 span {
            color: var(--saffron-primary);
        }

        .hero p {
            font-size: 15px;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0 auto;
        }

        /* Search Form */
        .search-container {
            position: relative;
            margin-bottom: 20px;
        }

        .search-bar-wrap {
            position: relative;
            display: flex;
            align-items: center;
            background: #FFFFFF;
            border: 2px solid var(--border-subtle);
            border-radius: 14px;
            box-shadow: var(--shadow-subtle);
            transition: all 0.2s ease;
        }

        .search-bar-wrap:focus-within {
            border-color: var(--border-focus);
            box-shadow: var(--shadow-glow);
        }

        .search-icon {
            position: absolute;
            left: 18px;
            font-size: 19px;
            color: var(--saffron-primary);
            pointer-events: none;
        }

        .search-bar {
            width: 100%;
            background: transparent;
            border: none;
            padding: 16px 110px 16px 50px;
            font-size: 17px;
            color: var(--text-primary);
            outline: none;
            font-family: inherit;
        }

        .search-bar::placeholder {
            color: var(--text-muted);
            font-weight: 400;
        }

        .search-submit-btn {
            position: absolute;
            right: 8px;
            background: var(--saffron-gradient);
            color: #FFFFFF;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(230, 81, 0, 0.25);
        }

        .search-submit-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(230, 81, 0, 0.35);
        }

        /* Autocomplete Suggestions */
        .suggestions-dropdown {
            position: absolute;
            top: calc(100% + 6px);
            left: 0;
            right: 0;
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            box-shadow: var(--shadow-float);
            max-height: 280px;
            overflow-y: auto;
            z-index: 40;
            display: none;
        }

        .suggestion-item {
            padding: 12px 18px;
            font-size: 14px;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid rgba(232, 223, 209, 0.4);
            transition: background 0.15s;
        }

        .suggestion-item:last-child { border-bottom: none; }
        .suggestion-item:hover {
            background: var(--bg-card-hover);
            color: var(--saffron-primary);
        }

        /* Filter Controls */
        .controls-panel {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 24px;
        }

        /* Category Filter Pills */
        .category-pills {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
            scrollbar-width: thin;
        }

        .cat-pill {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
        }

        .cat-pill:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
        }

        .cat-pill.active {
            background: var(--saffron-primary);
            color: #FFFFFF;
            border-color: var(--saffron-primary);
            box-shadow: 0 2px 8px rgba(230, 81, 0, 0.25);
        }

        /* Secondary Filter Row (Freshness & Sorting) */
        .filter-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            font-size: 13px;
            padding: 8px 12px;
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
        }

        .freshness-group {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .fresh-label {
            font-weight: 600;
            color: var(--text-muted);
            margin-right: 4px;
        }

        .fresh-btn {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            background: transparent;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.15s;
        }

        .fresh-btn:hover {
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        .fresh-btn.active {
            background: var(--saffron-soft);
            color: var(--saffron-primary);
            border-color: var(--saffron-border);
            font-weight: 700;
        }

        .sort-select {
            background: var(--bg-base);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            outline: none;
            cursor: pointer;
        }

        .sort-select:focus {
            border-color: var(--saffron-primary);
        }

        /* Intent Guidance Banner (METHODOLOGY.md §6) */
        .intent-banner {
            display: none;
            background: linear-gradient(135deg, rgba(255, 111, 0, 0.08) 0%, rgba(217, 119, 6, 0.05) 100%);
            border: 1px solid var(--saffron-border);
            border-left: 4px solid var(--saffron-primary);
            border-radius: 10px;
            padding: 12px 18px;
            margin-bottom: 20px;
            font-size: 13px;
            color: var(--text-primary);
        }

        .intent-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 700;
            color: var(--saffron-primary);
            margin-bottom: 4px;
        }

        .intent-shape {
            color: var(--text-secondary);
        }

        /* Results Meta */
        .results-meta {
            font-size: 13.5px;
            color: var(--text-muted);
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }

        /* Result Cards */
        .result-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-subtle);
            transition: all 0.2s ease;
        }

        .result-card:hover {
            border-color: rgba(230, 81, 0, 0.4);
            box-shadow: var(--shadow-float);
            background: var(--bg-card-hover);
        }

        .result-meta-top {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 8px;
            font-size: 12px;
        }

        .domain-tag {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
        }

        .cat-tag {
            background: rgba(217, 119, 6, 0.1);
            color: var(--amber-gold);
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
        }

        .date-badge {
            background: var(--saffron-soft);
            color: var(--saffron-primary);
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .recent-tag {
            background: #E65100;
            color: #FFFFFF;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 11px;
        }

        .mr-badge {
            background: var(--emerald-soft);
            color: var(--emerald-green);
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
        }

        .result-title {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 18.5px;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 6px;
        }

        .result-title a {
            color: var(--text-primary);
            text-decoration: none;
            transition: color 0.15s;
        }

        .result-title a:hover {
            color: var(--saffron-primary);
            text-decoration: underline;
        }

        .result-url {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 8px;
            word-break: break-all;
        }

        .result-snippet {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 14px;
        }

        /* Result Footer & Breakdown */
        .result-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            padding-top: 12px;
            border-top: 1px solid rgba(232, 223, 209, 0.6);
            font-size: 12px;
        }

        .result-breakdown {
            color: var(--text-muted);
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .result-breakdown b {
            color: var(--text-primary);
        }

        .action-btns {
            display: flex;
            gap: 8px;
        }

        .action-btn {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .action-btn:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        /* Related Queries Section */
        .related-box {
            display: none;
            margin-top: 32px;
            padding: 20px;
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            box-shadow: var(--shadow-subtle);
        }

        .related-title {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 15px;
            font-weight: 700;
            color: var(--saffron-primary);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .related-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .related-tag {
            background: var(--bg-base);
            border: 1px solid var(--border-subtle);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            color: var(--text-primary);
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
        }

        .related-tag:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 50px 20px;
            background: #FFFFFF;
            border: 1px dashed var(--border-subtle);
            border-radius: 14px;
            color: var(--text-muted);
        }

        .empty-state h3 {
            font-size: 18px;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        /* Directory Section */
        .dir-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .site-card {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-subtle);
        }

        .site-card:hover {
            border-color: var(--saffron-primary);
            transform: translateY(-2px);
            box-shadow: var(--shadow-float);
        }

        .site-name {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .site-domain {
            font-size: 12px;
            color: var(--saffron-primary);
            font-weight: 600;
            margin-bottom: 8px;
        }

        .site-desc {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 14px;
        }

        .site-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 10px;
            border-top: 1px solid rgba(232, 223, 209, 0.6);
            font-size: 11.5px;
        }

        .visit-link {
            color: var(--saffron-primary);
            font-weight: 700;
            text-decoration: none;
        }

        .visit-link:hover {
            text-decoration: underline;
        }

        /* Footer */
        footer {
            border-top: 1px solid var(--border-subtle);
            padding: 24px 32px;
            text-align: center;
            font-size: 13px;
            color: var(--text-muted);
            background: #FFFFFF;
            margin-top: 40px;
        }

        footer b { color: var(--saffron-primary); }

        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--text-primary);
            color: #FFFFFF;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 4px 14px rgba(0,0,0,0.2);
            display: none;
            z-index: 100;
        }

        /* Discover Feed Styling */
        .discover-header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 14px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .discover-title-wrap h2 {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 24px;
            font-weight: 800;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .discover-title-wrap p {
            font-size: 13.5px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .pulse-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(21, 128, 61, 0.09);
            color: var(--emerald-green);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11.5px;
            font-weight: 700;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--emerald-green);
            box-shadow: 0 0 0 0 rgba(21, 128, 61, 0.7);
            animation: pulse-ring 1.8s infinite;
        }

        @keyframes pulse-ring {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(21, 128, 61, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(21, 128, 61, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(21, 128, 61, 0); }
        }

        .sync-crawler-btn {
            background: #FFFFFF;
            border: 1.5px solid var(--saffron-primary);
            color: var(--saffron-primary);
            font-size: 13px;
            font-weight: 700;
            padding: 8px 18px;
            border-radius: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(230, 81, 0, 0.1);
        }

        .sync-crawler-btn:hover {
            background: var(--saffron-primary);
            color: #FFFFFF;
            box-shadow: 0 4px 14px rgba(230, 81, 0, 0.25);
            transform: translateY(-1px);
        }

        .sync-crawler-btn.spinning .sync-icon {
            display: inline-block;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            100% { transform: rotate(360deg); }
        }

        .discover-topic-chips {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 8px;
            margin-bottom: 24px;
            scrollbar-width: thin;
        }

        .topic-chip {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            font-size: 13px;
            font-weight: 600;
            padding: 7px 16px;
            border-radius: 20px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s;
        }

        .topic-chip:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        .topic-chip.active {
            background: var(--saffron-primary);
            color: #FFFFFF;
            border-color: var(--saffron-primary);
            box-shadow: 0 2px 8px rgba(230, 81, 0, 0.25);
        }

        /* Hero Featured Card */
        .featured-card {
            background: linear-gradient(135deg, #FFFDF9 0%, #FEF5E7 100%);
            border: 1.5px solid rgba(230, 81, 0, 0.35);
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-float);
            position: relative;
            overflow: hidden;
            transition: all 0.2s;
        }

        .featured-card:hover {
            border-color: var(--saffron-primary);
            box-shadow: 0 14px 34px rgba(230, 81, 0, 0.15);
        }

        .featured-badge-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .featured-badge {
            background: var(--saffron-gradient);
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 4px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .featured-headline {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 23px;
            font-weight: 800;
            line-height: 1.35;
            color: var(--text-primary);
            margin-bottom: 12px;
        }

        .featured-headline a {
            color: inherit;
            text-decoration: none;
        }

        .featured-headline a:hover {
            color: var(--saffron-primary);
            text-decoration: underline;
        }

        /* Discover Grid */
        .discover-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }

        .discover-card {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: var(--shadow-subtle);
            position: relative;
        }

        .discover-card:hover {
            border-color: var(--saffron-primary);
            transform: translateY(-3px);
            box-shadow: var(--shadow-float);
        }

        .discover-meta-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 12px;
        }

        .pub-badge {
            font-weight: 700;
            color: var(--saffron-primary);
            background: var(--saffron-soft);
            padding: 3px 9px;
            border-radius: 6px;
        }

        .time-ago {
            color: var(--text-muted);
            font-size: 11.5px;
            font-weight: 600;
        }

        .discover-headline {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 17px;
            font-weight: 700;
            line-height: 1.45;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .discover-headline a {
            color: inherit;
            text-decoration: none;
        }

        .discover-headline a:hover {
            color: var(--saffron-primary);
            text-decoration: underline;
        }

        .discover-tag {
            color: var(--amber-gold);
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 10px;
            display: inline-block;
        }

        .discover-snippet {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 14px;
            flex-grow: 1;
        }

        .discover-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(232, 223, 209, 0.6);
            padding-top: 10px;
            font-size: 11.5px;
            color: var(--text-muted);
        }

        .load-more-wrap {
            text-align: center;
            margin: 20px 0 40px 0;
        }

        .load-more-btn {
            background: #FFFFFF;
            border: 1.5px solid var(--border-subtle);
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 700;
            padding: 10px 28px;
            border-radius: 24px;
            cursor: pointer;
            transition: all 0.15s;
            box-shadow: var(--shadow-subtle);
        }

        .load-more-btn:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
        }

        /* Mode Strip Styling (Phase 1: Aspirant & Newsroom) */
        .mode-strip {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border-subtle);
            padding: 8px 32px;
            box-shadow: 0 1px 4px rgba(74, 53, 34, 0.03);
            position: sticky;
            top: 61px;
            z-index: 40;
        }

        .mode-strip-inner {
            max-width: 960px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            overflow-x: auto;
            scrollbar-width: none;
            -webkit-overflow-scrolling: touch;
        }
        .mode-strip-inner::-webkit-scrollbar { display: none; }

        .mode-label-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }

        .mode-label {
            font-size: 11.5px;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        .mode-buttons {
            display: flex;
            gap: 8px;
            align-items: center;
            overflow-x: auto;
            scrollbar-width: none;
            -webkit-overflow-scrolling: touch;
        }
        .mode-buttons::-webkit-scrollbar { display: none; }

        .mode-btn {
            background: var(--bg-base);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            padding: 5px 13px;
            font-size: 12.5px;
            font-weight: 700;
            color: var(--text-secondary);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
            transition: all 0.2s ease;
        }

        .mode-btn:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
            transform: translateY(-1px);
        }

        .mode-btn.active {
            color: #FFFFFF !important;
        }

        #btn-mode-general.active,
        .mode-btn.general-mode.active {
            background: linear-gradient(135deg, #E65100, #F57C00) !important;
            border-color: #E65100 !important;
            box-shadow: 0 3px 10px rgba(230, 81, 0, 0.35) !important;
        }

        #btn-mode-mpsc.active,
        .mode-btn.mpsc-mode.active {
            background: linear-gradient(135deg, #15803D, #16A34A) !important;
            border-color: #15803D !important;
            box-shadow: 0 3px 10px rgba(21, 128, 61, 0.4) !important;
        }

        #btn-mode-reporter.active,
        .mode-btn.reporter-mode.active {
            background: linear-gradient(135deg, #DC2626, #EF4444) !important;
            border-color: #B91C1C !important;
            box-shadow: 0 3px 10px rgba(220, 38, 38, 0.4) !important;
        }

        .m-tag {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            background: rgba(21, 128, 61, 0.12);
            color: #15803D;
            font-weight: 800;
        }

        .m-tag.red {
            background: rgba(185, 28, 28, 0.12);
            color: #B91C1C;
        }

        .mode-btn.active .m-tag {
            background: rgba(255, 255, 255, 0.3) !important;
            color: #FFFFFF !important;
        }

        /* Persona Quick Hub */
        .persona-quick-hub {
            background: #FFFFFF;
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 10px 16px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            box-shadow: var(--shadow-subtle);
        }

        .pq-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 700;
            font-size: 13px;
            color: var(--text-primary);
            white-space: nowrap;
        }

        .pq-chips {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .pq-chip {
            background: var(--bg-base);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 4px 11px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
        }

        .pq-chip:hover {
            border-color: var(--saffron-primary);
            color: var(--saffron-primary);
            background: var(--saffron-soft);
            transform: translateY(-1px);
        }

        /* Persona Live Section in Search View */
        .persona-live-section {
            margin-top: 24px;
            margin-bottom: 32px;
        }

        .pls-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--saffron-primary);
            padding-bottom: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 10px;
        }

        .pls-title-wrap h3 {
            font-family: 'Noto Serif Devanagari', serif;
            font-size: 18.5px;
            color: var(--text-primary);
            margin: 0;
        }

        .pls-title-wrap p {
            font-size: 12.5px;
            color: var(--text-muted);
            margin: 2px 0 0 0;
        }

        .pls-switch-btn {
            background: var(--saffron-soft);
            color: var(--saffron-primary);
            border: 1px solid rgba(230, 81, 0, 0.25);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .pls-switch-btn:hover {
            background: var(--saffron-primary);
            color: #FFFFFF;
        }

        /* Responsive Mobile Layout Rules */
        @media (max-width: 768px) {
            header {
                padding: 10px 14px;
                flex-direction: column;
                gap: 10px;
                align-items: stretch;
            }

            .brand {
                justify-content: flex-start;
                gap: 10px;
            }

            .logo-box {
                font-size: 14.5px;
                padding: 5px 10px;
            }

            .brand-text h1 {
                font-size: 16.5px;
            }

            .brand-text span {
                font-size: 10.5px;
            }

            .nav-tabs {
                overflow-x: auto;
                white-space: nowrap;
                padding: 3px;
                justify-content: flex-start;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }
            .nav-tabs::-webkit-scrollbar { display: none; }

            .nav-tab {
                padding: 6px 12px;
                font-size: 12px;
                flex-shrink: 0;
            }

            .mode-strip {
                padding: 6px 12px;
                position: static;
            }

            .mode-strip-inner {
                flex-direction: column;
                align-items: flex-start;
                gap: 6px;
            }

            .mode-buttons {
                width: 100%;
                overflow-x: auto;
                padding-bottom: 3px;
                -webkit-overflow-scrolling: touch;
            }

            .mode-btn {
                padding: 7px 12px;
                font-size: 12px;
                flex-shrink: 0;
                min-height: 36px;
            }

            .container {
                padding: 16px 12px;
            }

            .hero {
                margin: 18px 0 16px 0;
            }

            .hero h2 {
                font-size: 23px;
                line-height: 1.3;
            }

            .hero p {
                font-size: 13px;
            }

            .search-bar {
                padding: 13px 70px 13px 40px;
                font-size: 15px;
            }

            .search-icon {
                left: 14px;
                font-size: 17px;
            }

            .search-submit-btn {
                padding: 8px 14px;
                font-size: 13px;
                right: 6px;
            }

            .controls-panel {
                margin-bottom: 16px;
            }

            .category-pills, .discover-topic-chips {
                gap: 6px;
                padding-bottom: 6px;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }
            .category-pills::-webkit-scrollbar,
            .discover-topic-chips::-webkit-scrollbar { display: none; }

            .cat-pill, .topic-chip {
                padding: 6px 13px;
                font-size: 12px;
                flex-shrink: 0;
                min-height: 34px;
            }

            .filter-row {
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
            }

            .freshness-group {
                overflow-x: auto;
                white-space: nowrap;
                scrollbar-width: none;
                padding-bottom: 2px;
                display: flex;
                align-items: center;
                gap: 6px;
                -webkit-overflow-scrolling: touch;
            }
            .freshness-group::-webkit-scrollbar { display: none; }

            .fresh-btn {
                padding: 5px 10px;
                font-size: 12px;
                flex-shrink: 0;
                min-height: 32px;
            }

            .sort-select {
                width: 100%;
                font-size: 12.5px;
            }

            .featured-card {
                padding: 16px;
                border-radius: 12px;
                margin-bottom: 16px;
            }

            .featured-headline {
                font-size: 18px;
                line-height: 1.35;
            }

            .discover-grid {
                grid-template-columns: 1fr;
                gap: 14px;
                margin-bottom: 20px;
            }

            .discover-header-bar {
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
            }

            .sync-crawler-btn {
                justify-content: center;
                width: 100%;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
            }

            .result-card, .discover-card {
                padding: 14px;
                border-radius: 12px;
            }

            .result-title {
                font-size: 16.5px;
            }

            .result-footer, .discover-footer {
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
            }

            .action-btns {
                width: 100%;
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
            }

            .action-btn {
                flex: 1;
                min-width: 68px;
                justify-content: center;
                padding: 8px 6px;
                font-size: 11.5px;
                min-height: 38px;
                touch-action: manipulation;
            }

            .toast {
                left: 12px;
                right: 12px;
                bottom: 12px;
                text-align: center;
                font-size: 12.5px;
                padding: 9px 14px;
            }
        }
    </style>
</head>
<body>

    <header>
        <a href="/" class="brand">
            <div class="logo-box">🚩 तात्या</div>
            <div class="brand-text">
                <h1>तात्या</h1>
                <span>मराठी इंटरनेटचा आपला शोध</span>
            </div>
        </a>
        <nav class="nav-tabs">
            <button class="nav-tab active" id="tab-search" onclick="switchTab('search')">🔍 शोधयंत्र</button>
            <button class="nav-tab" id="tab-discover" onclick="switchTab('discover')">✨ डिस्कव्हर (Discover)</button>
            <button class="nav-tab" id="tab-dir" onclick="switchTab('directory')">📂 निर्देशिका</button>
            <a href="/graph" target="_blank" class="nav-tab">🌐 ज्ञान आलेख</a>
        </nav>
    </header>

    <!-- Mode Selector Strip (Phase 1) -->
    <div class="mode-strip">
        <div class="mode-strip-inner">
            <div class="mode-label-wrap">
                <span class="mode-label">⚡ कार्यप्रणाली (Mode):</span>
            </div>
            <div class="mode-buttons">
                <button type="button" class="mode-btn general-mode active" id="btn-mode-general" onclick="setAppMode('general')">
                    <span>🌐</span>
                    <span>सर्वसाधारण</span>
                </button>
                <button type="button" class="mode-btn mpsc-mode" id="btn-mode-mpsc" onclick="setAppMode('mpsc')">
                    <span>🎓</span>
                    <span>स्पर्धा परीक्षा (MPSC)</span>
                    <span class="m-tag">अभ्यासक</span>
                </button>
                <button type="button" class="mode-btn reporter-mode" id="btn-mode-reporter" onclick="setAppMode('reporter')">
                    <span>📰</span>
                    <span>पत्रकार कक्ष (Newsroom)</span>
                    <span class="m-tag red">लाइव्ह वायर</span>
                </button>
            </div>
        </div>
    </div>

    <main class="container">
        <!-- Search View -->
        <section id="search-view">
            <div class="hero" id="hero-box">
                <h2>तात्या — <span>मराठी इंटरनेटचा आपला शोध</span></h2>
                <p>मराठी इंटरनेटसाठी स्वतंत्र शोधयंत्र • ५०,०००+ अस्सल वेबपेजेस</p>
            </div>

            <div class="search-container">
                <form id="search-form" onsubmit="event.preventDefault(); doSearch();">
                    <div class="search-bar-wrap">
                        <span class="search-icon">🔍</span>
                        <input 
                            type="text" 
                            id="search-input" 
                            class="search-bar" 
                            placeholder="तात्यांवर मराठीत काय शोधायचे आहे? (उदा. शेतकऱ्यांना कर्जमाफी, कांदा भाव, लाडकी बहीण योजना)..." 
                            autocomplete="off"
                            autofocus
                        >
                        <button type="submit" class="search-submit-btn">शोधा</button>
                    </div>
                </form>
                <div id="suggestions" class="suggestions-dropdown"></div>
            </div>

            <!-- Persona Quick Hub (Syllabus/Beat tags) -->
            <div id="persona-quick-hub" class="persona-quick-hub">
                <div class="pq-header">
                    <span class="pq-icon" id="pq-icon">💡</span>
                    <span class="pq-title" id="pq-title">लोकप्रिय शोध:</span>
                </div>
                <div class="pq-chips" id="pq-chips"></div>
            </div>

            <!-- Live Persona Feed in Search View (Activated on Mode Click) -->
            <div id="persona-live-section" class="persona-live-section" style="display: none;">
                <div class="pls-header">
                    <div class="pls-title-wrap">
                        <h3 id="pls-title">🔥 आजच्या महत्त्वाच्या घडामोडी</h3>
                        <p id="pls-subtitle">थेट ताज्या बातम्या व पडताळणी</p>
                    </div>
                    <button type="button" class="pls-switch-btn" onclick="switchTab('discover')">
                        सविस्तर डिस्कव्हर डेस्क पहा &rarr;
                    </button>
                </div>
                <div id="pls-grid" class="discover-grid"></div>
            </div>

            <!-- Controls Panel: Categories & Freshness -->
            <div class="controls-panel">
                <div class="category-pills">
                    <button class="cat-pill active" onclick="setCategory('all', this)">सर्व वर्गवारी</button>
                    <button class="cat-pill" onclick="setCategory('Agriculture', this)">🌾 शेती व कृषी</button>
                    <button class="cat-pill" onclick="setCategory('News & Media', this)">📰 बातम्या व घडामोडी</button>
                    <button class="cat-pill" onclick="setCategory('Finance & Banking', this)">💰 अर्थ व वित्त</button>
                    <button class="cat-pill" onclick="setCategory('Education & Exams', this)">📚 शिक्षण व परीक्षा</button>
                    <button class="cat-pill" onclick="setCategory('Literature & Culture', this)">✍️ साहित्य व संस्कृती</button>
                    <button class="cat-pill" onclick="setCategory('Cuisine & Recipes', this)">🍲 पाककृती</button>
                </div>

                <div class="filter-row">
                    <div class="freshness-group">
                        <span class="fresh-label">कालानुरूपता (Freshness):</span>
                        <button class="fresh-btn active" onclick="setFreshness('all', this)">सर्व काळ</button>
                        <button class="fresh-btn" onclick="setFreshness('24h', this)">🔥 २४ तास</button>
                        <button class="fresh-btn" onclick="setFreshness('week', this)">📅 या आठवड्यात</button>
                        <button class="fresh-btn" onclick="setFreshness('month', this)">🗓️ या महिन्यात</button>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 600; color: var(--text-muted);">क्रमवारी:</span>
                        <select id="sort-select" class="sort-select" onchange="doSearch()">
                            <option value="relevance">📊 सर्वोत्तम प्रासंगिकता (Relevance)</option>
                            <option value="date">🕒 नवीनतम तारखेनुसार (Latest Date)</option>
                            <option value="pagerank">⭐ संकेतस्थळ प्रतिष्ठा (PageRank)</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Intent Guidance Banner (METHODOLOGY.md §6) -->
            <div id="intent-banner" class="intent-banner">
                <div class="intent-header">
                    <span id="intent-label"></span>
                    <span style="font-size: 11.5px; opacity: 0.9;">METHODOLOGY.md §6 करार</span>
                </div>
                <div class="intent-shape" id="intent-shape"></div>
            </div>

            <!-- Results Meta Info -->
            <div id="results-meta" class="results-meta"></div>

            <!-- Search Results List -->
            <div id="results-box"></div>

            <!-- Related Searches (हे पण शोधा) -->
            <div id="related-box" class="related-box">
                <div class="related-title">💡 हे पण शोधा (संबंधित विषय):</div>
                <div id="related-tags" class="related-tags"></div>
            </div>
        </section>

        <!-- Directory View -->
        <section id="directory-view" style="display: none;">
            <div class="hero">
                <h2>तात्या मराठी <span>निर्देशिका (Directory)</span></h2>
                <p>मराठी भाषेतील विश्वासार्ह, प्रमाणित आणि दर्जेदार संकेतस्थळांची निवडक सूची</p>
            </div>
            <div id="directory-content"></div>
        </section>

        <!-- Discover View (Google Discover for Marathi) -->
        <section id="discover-view" style="display: none;">
            <div class="discover-header-bar">
                <div class="discover-title-wrap">
                    <h2>
                        <span id="discover-title-text">✨ तात्या डिस्कव्हर (Discover)</span>
                        <span class="pulse-live">
                            <span class="pulse-dot"></span> थेट प्रवाह (Live Feed)
                        </span>
                    </h2>
                    <p id="discover-subtitle-text">मराठी विश्वातील ताज्या घडामोडी, महत्त्वाचे लेख आणि ट्रेंडिंग विषय एकाच ठिकाणी</p>
                </div>
                <button class="sync-crawler-btn" id="sync-crawler-btn" onclick="triggerCrawlerSync()">
                    <span class="sync-icon">🔄</span> ताज्या बातम्या क्रॉल करा (Live Sync)
                </button>
            </div>

            <!-- Discover Topic Chips -->
            <div class="discover-topic-chips" id="discover-chips-container">
                <button class="topic-chip active" onclick="setDiscoverTopic('all', this)">🌟 सर्व ताज्या बातम्या</button>
                <button class="topic-chip" onclick="setDiscoverTopic('agriculture', this)">🌾 शेती व कृषी</button>
                <button class="topic-chip" onclick="setDiscoverTopic('news', this)">📰 महाराष्ट्र राजकारण</button>
                <button class="topic-chip" onclick="setDiscoverTopic('finance', this)">💰 अर्थ व वित्त</button>
                <button class="topic-chip" onclick="setDiscoverTopic('tech', this)">⚡ तंत्रज्ञान</button>
                <button class="topic-chip" onclick="setDiscoverTopic('culture', this)">✍️ साहित्य व संस्कृती</button>
            </div>

            <!-- Featured Top Story -->
            <div id="featured-story-wrap"></div>

            <!-- Discover Story Grid -->
            <div id="discover-grid" class="discover-grid"></div>

            <!-- Load More Button -->
            <div class="load-more-wrap">
                <button class="load-more-btn" id="load-more-btn" onclick="loadMoreDiscover()">
                    आणखी ताज्या बातम्या दाखवा &darr;
                </button>
            </div>
        </section>
    </main>

    <footer>
        <p><b>तात्या (Tatya)</b> — मराठी इंटरनेटसाठी स्वतंत्र शोधयंत्र • <span>मराठी इंटरनेटचा आपला शोध.</span></p>
        <p style="margin-top: 4px; font-size: 12px; color: var(--text-muted);">अंमलबजावणी: METHODOLOGY.md व MATH.md प्रमाणबद्ध अल्गोरिदम • तंत्रज्ञान: SQLite FTS5 + PageRank + HITS</p>
    </footer>

    <div id="toast" class="toast"></div>

    <script>
        // DOM Elements
        const toast = document.getElementById('toast');
        const searchInput = document.getElementById('search-input');
        const suggestionsBox = document.getElementById('suggestions');
        const resultsBox = document.getElementById('results-box');
        const resultsMeta = document.getElementById('results-meta');
        const heroBox = document.getElementById('hero-box');
        const intentBanner = document.getElementById('intent-banner');
        const intentLabel = document.getElementById('intent-label');
        const intentShape = document.getElementById('intent-shape');
        const relatedBox = document.getElementById('related-box');
        const relatedTags = document.getElementById('related-tags');

        let appMode = 'general';
        let currentCategory = 'all';
        let currentFreshness = 'all';
        let currentDiscoverTopic = 'all';
        let discoverOffset = 0;
        let isDiscoverLoading = false;

        function showToast(msg) {
            if (!toast) return;
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 2400);
        }

        const CHIPS_CONFIG = {
            'general': [
                { id: 'all', label: '🌟 सर्व ताज्या बातम्या' },
                { id: 'agriculture', label: '🌾 शेती व कृषी' },
                { id: 'news', label: '📰 महाराष्ट्र राजकारण' },
                { id: 'finance', label: '💰 अर्थ व वित्त' },
                { id: 'tech', label: '⚡ तंत्रज्ञान' },
                { id: 'culture', label: '✍️ साहित्य व संस्कृती' }
            ],
            'mpsc': [
                { id: 'all', label: '🌟 सर्व चालू घडामोडी' },
                { id: 'gs2', label: '📜 GS-2: शासन निर्णय व योजना' },
                { id: 'gs3', label: '🌾 GS-3: कृषी व अर्थव्यवस्था' },
                { id: 'gs1', label: '🏛️ GS-1: इतिहास व भूगोल' },
                { id: 'tech', label: '⚡ GS-3: विज्ञान व तंत्रज्ञान' }
            ],
            'reporter': [
                { id: 'all', label: '🚨 सर्व ब्रेकिंग वायर' },
                { id: 'politics', label: '🏛️ मंत्रालय व राजकारण' },
                { id: 'rural', label: '🚜 कृषी व ग्रामीण वार्ता' },
                { id: 'crime', label: '⚖️ कायदेशीर व क्राईम' },
                { id: 'regional', label: '📍 प्रादेशिक जिल्हा रडार' }
            ]
        };

        const QUICK_HUB_CONFIG = {
            'general': {
                icon: '💡',
                title: 'लोकप्रिय शोध:',
                chips: [
                    'शेतकऱ्यांना कर्जमाफी शासन निर्णय',
                    'कांदा बाजारभाव थेट भाव',
                    'शेअर बाजार म्युच्युअल फंड',
                    'मान्सून पाऊस हवामान अंदाज',
                    'लाडकी बहीण योजना'
                ]
            },
            'mpsc': {
                icon: '🎓',
                title: 'MPSC अभ्यासक्रम घटक (Quick Syllabus Filters):',
                chips: [
                    'लाडकी बहीण योजना शासन निर्णय',
                    'राज्यपाल अधिकार घटनात्मक तरतुदी',
                    'शेतकरी कर्जमाफी शासन निर्णय',
                    'सह्याद्री व्याघ्र प्रकल्प भूगोल',
                    'महाराष्ट्र अर्थसंकल्प २०२६'
                ]
            },
            'reporter': {
                icon: '🚨',
                title: 'पत्रकार बीट्स व लीड्स (Newsroom Beats):',
                chips: [
                    'मंत्रिमंडळ निर्णय थेट',
                    'कांदा बाजारभाव थेट भाव',
                    'पोलीस तपास गुन्हा',
                    'पुणे नाशिक जिल्हा परिषद निकाल',
                    'दुष्काळ जाहीर परिपत्रक'
                ]
            }
        };

        function renderPersonaQuickHub(mode) {
            const config = QUICK_HUB_CONFIG[mode] || QUICK_HUB_CONFIG['general'];
            const iconEl = document.getElementById('pq-icon');
            const titleEl = document.getElementById('pq-title');
            const chipsEl = document.getElementById('pq-chips');
            if (iconEl) iconEl.textContent = config.icon;
            if (titleEl) titleEl.textContent = config.title;
            if (chipsEl) {
                chipsEl.innerHTML = config.chips.map(chip => `
                    <button type="button" class="pq-chip" onclick="doSearch('${escapeJsString(chip)}')">
                        ${chip}
                    </button>
                `).join('');
            }
        }

        async function loadPersonaLiveFeed(mode) {
            const section = document.getElementById('persona-live-section');
            const grid = document.getElementById('pls-grid');
            const titleEl = document.getElementById('pls-title');
            const subtitleEl = document.getElementById('pls-subtitle');
            if (!section || !grid) return;

            // Only show if not currently displaying search results
            if (resultsBox && resultsBox.children.length > 0 && searchInput && searchInput.value.trim().length > 0) {
                section.style.display = 'none';
                return;
            }

            if (mode === 'mpsc') {
                titleEl.textContent = '🎓 MPSC / UPSC चालू घडामोडी थेट प्रवाह';
                subtitleEl.textContent = 'अभ्यासक्रमावर आधारित प्रमाणित चालू घडामोडी (GS-1, GS-2, GS-3)';
                section.style.display = 'block';
            } else if (mode === 'reporter') {
                titleEl.textContent = '📰 पत्रकार कक्ष: थेट बातमी वायर व लीड्स';
                subtitleEl.textContent = '२४/७ डिजिटल वार्ताहर रडार, थेट ब्रेकिंग फीड व अधिकृत परिपत्रके';
                section.style.display = 'block';
            } else {
                section.style.display = 'none';
                return;
            }

            grid.innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 24px;'>थेट प्रवाह लोड होत आहे...</p>";

            try {
                const resp = await fetch(`/api/discover?mode=${encodeURIComponent(mode)}&topic=all&limit=6`);
                const data = await resp.json();
                const cards = data.cards || [];
                if (cards.length === 0) {
                    grid.innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: var(--text-muted);'>सध्या ताज्या नोंदी उपलब्ध नाहीत.</p>";
                    return;
                }

                grid.innerHTML = cards.map(c => `
                    <article class="discover-card">
                        <div>
                            <div class="discover-meta-row">
                                <span class="pub-badge">${c.publisher_mr}</span>
                                <span class="time-ago">🕒 ${c.relative_time_mr}</span>
                            </div>
                            <h4 class="discover-headline">
                                <a href="${c.url}" target="_blank" rel="noopener">${c.title}</a>
                            </h4>
                            <span class="discover-tag">${c.topic_tag}</span>
                            <p class="discover-snippet">${c.snippet}</p>
                        </div>
                        <div class="discover-footer">
                            <span>📖 ${c.reading_time_mr}</span>
                            <div class="action-btns">
                                ${renderActionsHtml(c.title, c.publisher_mr, c.url, c.topic_tag)}
                                <a href="${c.url}" target="_blank" rel="noopener" class="visit-link" style="font-size: 12px; margin-left: 4px;">
                                    वाचा &rarr;
                                </a>
                            </div>
                        </div>
                    </article>
                `).join('');
            } catch(e) {
                grid.innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: var(--text-muted);'>लोड करताना त्रुटी आली.</p>";
            }
        }

        function setAppMode(mode) {
            appMode = mode;
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            const btn = document.getElementById('btn-mode-' + mode);
            if (btn) btn.classList.add('active');

            const dTitle = document.getElementById('discover-title-text');
            const dSub = document.getElementById('discover-subtitle-text');
            const heroH2 = document.querySelector('#hero-box h2');
            const heroP = document.querySelector('#hero-box p');
            const sInput = document.getElementById('search-input');

            if (mode === 'mpsc') {
                if (heroH2) heroH2.innerHTML = 'तात्या अभ्यासक — <span>स्पर्धा परीक्षा व शासन निर्णय</span>';
                if (heroP) heroP.textContent = 'MPSC, UPSC व सरळसेवा चालू घडामोडी, GS अभ्यासक्रम, सरकारी योजना व अधिकृत माहिती';
                if (sInput) sInput.placeholder = 'तात्यांवर स्पर्धा परीक्षा संदर्भ शोधा (उदा. राज्यपाल अधिकार, लाडकी बहीण योजना, अर्थसंकल्प)...';
                if (dTitle) dTitle.textContent = '🎓 तात्या MPSC / UPSC चालू घडामोडी डेस्क';
                if (dSub) dSub.textContent = 'अभ्यासक्रमावर आधारित प्रमाणित घडामोडी (GS-1, GS-2, GS-3) व शासन निर्णय (GR)';
                showToast("🎓 तात्या अभ्यासक (MPSC) मोड सक्रिय!");
            } else if (mode === 'reporter') {
                if (heroH2) heroH2.innerHTML = 'तात्या न्यूजरूम — <span>लाइव्ह वायर व लीड रडार</span>';
                if (heroP) heroP.textContent = 'मंत्रालय, जिल्हा वार्ता, अधिकृत परिपत्रके आणि थेट बातम्यांची पडताळणी';
                if (sInput) sInput.placeholder = 'तात्यांवर पत्रकार संदर्भ शोधा (उदा. मंत्रिमंडळ निर्णय, दुष्काळ जाहीर, जिल्हा परिषद निकाल)...';
                if (dTitle) dTitle.textContent = '📰 तात्या पत्रकार कक्ष: थेट बातमी वायर';
                if (dSub) dSub.textContent = '२४/७ डिजिटल वार्ताहर रडार, थेट ब्रेकिंग फीड, कोट कॉपी आणि स्रोत दुवे';
                showToast("📰 तात्या न्यूजरूम (Live Wire) मोड सक्रिय!");
            } else {
                if (heroH2) heroH2.innerHTML = 'तात्या — <span>मराठी इंटरनेटचा आपला शोध</span>';
                if (heroP) heroP.textContent = 'मराठी इंटरनेटसाठी स्वतंत्र शोधयंत्र • ५०,०००+ अस्सल वेबपेजेस';
                if (sInput) sInput.placeholder = 'तात्यांवर मराठीत काय शोधायचे आहे? (उदा. शेतकऱ्यांना कर्जमाफी, कांदा भाव, लाडकी बहीण योजना)...';
                if (dTitle) dTitle.textContent = '✨ तात्या डिस्कव्हर (Discover)';
                if (dSub) dSub.textContent = 'मराठी विश्वातील ताज्या घडामोडी, महत्त्वाचे लेख आणि ट्रेंडिंग विषय एकाच ठिकाणी';
                showToast("🌐 तात्या: सर्वसाधारण शोध सक्रिय!");
            }

            renderPersonaQuickHub(mode);

            currentDiscoverTopic = 'all';
            const chips = CHIPS_CONFIG[mode] || CHIPS_CONFIG['general'];
            const chipsContainer = document.getElementById('discover-chips-container');
            if (chipsContainer) {
                chipsContainer.innerHTML = chips.map((c, idx) => `
                    <button type="button" class="topic-chip ${idx === 0 ? 'active' : ''}" onclick="setDiscoverTopic('${c.id}', this)">
                        ${c.label}
                    </button>
                `).join('');
            }

            if (document.getElementById('discover-view').style.display !== 'none') {
                loadDiscoverFeed(true);
            } else if (searchInput && searchInput.value.trim().length > 0) {
                doSearch();
            } else {
                loadPersonaLiveFeed(mode);
            }
        }

        function escapeJsString(str) {
            if (!str) return '';
            return String(str)
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#39;');
        }

        function copyMpscNotes(title, publisher, url, tag) {
            const today = new Date().toLocaleDateString('mr-IN', { year: 'numeric', month: 'long', day: 'numeric' });
            const note = [
                '📌 [MPSC चालू घडामोडी नोंद]',
                '• विषय/घटक: ' + (tag || 'चालू घडामोडी'),
                '• शीर्षक: ' + title,
                '• संदर्भ/स्रोत: ' + publisher,
                '• तारीख: ' + today,
                '• संदर्भ दुवा: ' + url
            ].join(String.fromCharCode(10));
            navigator.clipboard.writeText(note).then(() => {
                showToast("📝 MPSC अभ्यास नोंद क्लिपबोर्डवर सेव्ह झाली!");
            }).catch(() => {
                showToast("नोंद सेव्ह करणे अयशस्वी.");
            });
        }

        function copyReporterLead(title, publisher, url) {
            const lead = [
                '📰 [डिजिटल बातमी लीड / कोट]',
                '"' + title + '"',
                '(स्रोत: ' + publisher + ' | ' + url + ')'
            ].join(String.fromCharCode(10));
            navigator.clipboard.writeText(lead).then(() => {
                showToast("📋 बातमी लीड व कोट कॉपी झाले!");
            }).catch(() => {
                showToast("कॉपी अयशस्वी.");
            });
        }

        function copyCitation(publisher, url) {
            const cite = '(सौजन्य: ' + publisher + ', ' + url + ')';
            navigator.clipboard.writeText(cite).then(() => {
                showToast("📎 बातमी श्रेय (Citation) कॉपी झाले!");
            }).catch(() => {
                showToast("कॉपी अयशस्वी.");
            });
        }

        function renderActionsHtml(title, publisher, url, tag) {
            const escT = escapeJsString(title);
            const escP = escapeJsString(publisher);
            const escU = escapeJsString(url);
            const escTag = escapeJsString(tag);

            if (appMode === 'mpsc') {
                return `
                    <button type="button" class="action-btn" onclick="copyMpscNotes('${escT}', '${escP}', '${escU}', '${escTag}')" title="MPSC अभ्यास नोंद वहीत सेव्ह करा">
                        📝 नोंदवा
                    </button>
                    <button type="button" class="action-btn" onclick="speakMarathi('${escT}')" title="मराठीत ऑडिओ रिव्हिजन">
                        🔊 उजळणी
                    </button>
                    <button type="button" class="action-btn" onclick="copyLink('${escU}')" title="दुवा कॉपी करा">
                        🔗 लिंक
                    </button>
                `;
            } else if (appMode === 'reporter') {
                return `
                    <button type="button" class="action-btn" onclick="copyReporterLead('${escT}', '${escP}', '${escU}')" title="बातमी लीड आणि कोट कॉपी करा">
                        📋 कोट कॉपी
                    </button>
                    <button type="button" class="action-btn" onclick="copyCitation('${escP}', '${escU}')" title="बातम्यांसाठी श्रेय दुवा कॉपी करा">
                        📎 श्रेय
                    </button>
                    <button type="button" class="action-btn" onclick="speakMarathi('${escT}')" title="शीर्षक ऐका">
                        🔊 ऐका
                    </button>
                `;
            } else {
                return `
                    <button type="button" class="action-btn" onclick="speakMarathi('${escT}')" title="शीर्षक ऐका">
                        🔊 ऐका
                    </button>
                    <button type="button" class="action-btn" onclick="copyLink('${escU}')" title="URL कॉपी करा">
                        🔗 कॉपी
                    </button>
                `;
            }
        }

        function switchTab(tab) {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            if (tab === 'search') {
                document.getElementById('tab-search').classList.add('active');
                document.getElementById('search-view').style.display = 'block';
                document.getElementById('directory-view').style.display = 'none';
                document.getElementById('discover-view').style.display = 'none';
            } else if (tab === 'discover') {
                document.getElementById('tab-discover').classList.add('active');
                document.getElementById('search-view').style.display = 'none';
                document.getElementById('directory-view').style.display = 'none';
                document.getElementById('discover-view').style.display = 'block';
                loadDiscoverFeed(true);
            } else {
                document.getElementById('tab-dir').classList.add('active');
                document.getElementById('search-view').style.display = 'none';
                document.getElementById('directory-view').style.display = 'block';
                document.getElementById('discover-view').style.display = 'none';
                loadDirectory();
            }
        }

        function setCategory(cat, el) {
            currentCategory = cat;
            document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
            el.classList.add('active');
            doSearch();
        }

        function setFreshness(fresh, el) {
            currentFreshness = fresh;
            document.querySelectorAll('.fresh-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            doSearch();
        }

        // Live Suggestions
        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const val = searchInput.value.trim();
            if (val.length < 2) {
                suggestionsBox.style.display = 'none';
                return;
            }
            debounceTimer = setTimeout(async () => {
                try {
                    const resp = await fetch(`/api/suggest?q=${encodeURIComponent(val)}`);
                    const data = await resp.json();
                    if (data.suggestions && data.suggestions.length > 0) {
                        suggestionsBox.innerHTML = data.suggestions.map(s => `
                            <div class="suggestion-item" onclick="pickSuggestion('${escapeJsString(s)}')">
                                <span style="color: var(--saffron-primary);">🔍</span>
                                <span>${s}</span>
                            </div>
                        `).join('');
                        suggestionsBox.style.display = 'block';
                    } else {
                        suggestionsBox.style.display = 'none';
                    }
                } catch(e) {
                    suggestionsBox.style.display = 'none';
                }
            }, 180);
        });

        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.style.display = 'none';
            }
        });

        function pickSuggestion(term) {
            searchInput.value = term;
            suggestionsBox.style.display = 'none';
            doSearch();
        }

        // Main Search Function
        async function doSearch(overrideQuery) {
            const query = (overrideQuery !== undefined ? overrideQuery : searchInput.value).trim();
            if (!query) return;

            if (overrideQuery !== undefined) {
                searchInput.value = overrideQuery;
            }

            heroBox.classList.add('compact');
            resultsMeta.innerHTML = "शोधत आहे...";
            resultsBox.innerHTML = "";
            intentBanner.style.display = 'none';
            relatedBox.style.display = 'none';
            suggestionsBox.style.display = 'none';
            const pls = document.getElementById('persona-live-section');
            if (pls) pls.style.display = 'none';

            const sortBy = document.getElementById('sort-select').value;

            try {
                const url = `/api/search?q=${encodeURIComponent(query)}&category=${encodeURIComponent(currentCategory)}&freshness=${encodeURIComponent(currentFreshness)}&sort_by=${encodeURIComponent(sortBy)}`;
                const resp = await fetch(url);
                const data = await resp.json();

                // Intent Banner
                if (data.intent && data.intent !== 'unclear') {
                    intentLabel.textContent = data.intent_label_mr || data.intent;
                    intentShape.textContent = `अपेक्षित पृष्ठ स्वरूप: ${data.article_shape_mr || data.article_shape}`;
                    intentBanner.style.display = 'block';
                }

                // Results Meta
                let metaHtml = `<span>"${query}" साठी <b>${data.total}</b> अस्सल मराठी निकाल सापडले (${data.time_ms} ms)</span>`;
                metaHtml += `<span>पद्धती: <b>${data.tier_used === 'exact' ? 'अचूक संकल्पना जुळणी (Conjunction)' : 'विस्तारित जुळणी (Relaxed OR)'}</b></span>`;
                resultsMeta.innerHTML = metaHtml;

                if (data.results.length === 0) {
                    resultsBox.innerHTML = `
                        <div class="empty-state">
                            <h3>कोणतेही निकाल आढळले नाहीत</h3>
                            <p style="margin-top: 6px;">वेगळ्या मराठी शब्दाने शोधून पहा किंवा कालानुरूपता व वर्गवारी 'सर्व' ठेवा.</p>
                        </div>
                    `;
                    return;
                }

                // Render Result Cards
                resultsBox.innerHTML = data.results.map((r, idx) => `
                    <article class="result-card">
                        <div class="result-meta-top">
                            <span class="domain-tag">${r.domain}</span>
                            <span class="cat-tag">${r.category}</span>
                            <span class="mr-badge">अस्सल मराठी: ${r.marathi_char_ratio}%</span>
                            ${r.formatted_date ? `
                                <span class="date-badge">
                                    📅 ${r.formatted_date}
                                </span>
                            ` : ''}
                            ${r.is_recent ? '<span class="recent-tag">🔥 ताजी बातमी</span>' : ''}
                        </div>

                        <h3 class="result-title">
                            <a href="${r.url}" target="_blank" rel="noopener">${r.title}</a>
                        </h3>
                        <div class="result-url">${r.url}</div>
                        <p class="result-snippet">${r.snippet}</p>

                        <div class="result-footer">
                            <div class="result-breakdown" title="${r.why_matched}">
                                <span>प्रतिष्ठा (PageRank): <b>${r.pagerank}</b></span>
                                <span>संकल्पना व्याप्ती: <b>${Math.round(r.coverage * 100)}%</b></span>
                                <span>एकूण स्कोअर: <b>${r.relevance_score}</b></span>
                            </div>
                            <div class="action-btns">
                                ${renderActionsHtml(r.title, r.domain, r.url, r.category)}
                            </div>
                        </div>
                    </article>
                `).join('');

                // Render Related Searches
                if (data.related_queries && data.related_queries.length > 0) {
                    relatedTags.innerHTML = data.related_queries.map(q => `
                        <button class="related-tag" onclick="doSearch('${escapeJsString(q)}')">
                            ${q}
                        </button>
                    `).join('');
                    relatedBox.style.display = 'block';
                }

            } catch (err) {
                resultsMeta.textContent = "शोध करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.";
            }
        }

        // Web Speech API for Marathi
        function speakMarathi(text) {
            if (!('speechSynthesis' in window)) {
                showToast("आपल्या ब्राउझरमध्ये ऑडिओ सपोर्ट उपलब्ध नाही.");
                return;
            }
            window.speechSynthesis.cancel();
            const cleanText = String(text).split('|')[0].trim();
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'mr-IN';
            utterance.rate = 0.95;
            window.speechSynthesis.speak(utterance);
            showToast("मराठीत उच्चार वाचन सुरू...");
        }

        function copyLink(url) {
            navigator.clipboard.writeText(url).then(() => {
                showToast("लिंक कॉपी झाली!");
            }).catch(() => {
                showToast("कॉपी करणे अयशस्वी.");
            });
        }

        // Load Directory
        async function loadDirectory() {
            const container = document.getElementById('directory-content');
            if (container.children.length > 0) return;
            container.innerHTML = "<p style='color: var(--text-muted); text-align: center; padding: 40px;'>निर्देशिका लोड होत आहे...</p>";

            try {
                const resp = await fetch('/api/directory');
                const data = await resp.json();
                
                container.innerHTML = data.categories.map(c => `
                    <div style="margin-bottom: 36px;">
                        <div style="margin-bottom: 12px; border-bottom: 2px solid var(--saffron-primary); padding-bottom: 6px;">
                            <h3 style="font-family: 'Noto Serif Devanagari', serif; font-size: 20px; color: var(--text-primary);">
                                ${c.icon} ${c.title_mr} <span style="font-size: 14px; color: var(--text-muted); font-weight: normal;">(${c.title_en})</span>
                            </h3>
                            <p style="font-size: 13px; color: var(--text-muted);">${c.description_mr}</p>
                        </div>
                        <div class="dir-grid">
                            ${c.entries.map(e => `
                                <div class="site-card">
                                    <div>
                                        <div class="site-name">${e.title}</div>
                                        <div class="site-domain">${e.domain}</div>
                                        <div class="site-desc">${e.description}</div>
                                    </div>
                                    <div class="site-footer">
                                        <span style="color: var(--emerald-green); font-weight: 600;">मराठी: ${e.marathi_ratio}%</span>
                                        <span style="color: var(--text-muted);">${e.total_urls.toLocaleString()} पेजेस</span>
                                        <a href="https://${e.domain}/" target="_blank" rel="noopener" class="visit-link">भेट द्या &rarr;</a>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            } catch(e) {
                container.innerHTML = "<p style='text-align: center;'>निर्देशिका लोड करताना त्रुटी आली.</p>";
            }
        }

        // Discover Feed Logic (Google Discover for Marathi)
        function setDiscoverTopic(topic, el) {
            currentDiscoverTopic = topic;
            document.querySelectorAll('.topic-chip').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            loadDiscoverFeed(true);
        }

        async function triggerCrawlerSync() {
            const btn = document.getElementById('sync-crawler-btn');
            btn.classList.add('spinning');
            btn.disabled = true;
            btn.innerHTML = '<span class="sync-icon">🔄</span> क्रॉलिंग सुरू आहे...';
            showToast("नवीन मराठी बातम्या व RSS फीड तपासत आहे...");

            try {
                const resp = await fetch('/api/crawler/refresh');
                const data = await resp.json();
                showToast(data.message || "क्रॉल पूर्ण!");
                loadDiscoverFeed(true);
            } catch(e) {
                showToast("क्रॉल करताना त्रुटी आली.");
            } finally {
                btn.classList.remove('spinning');
                btn.disabled = false;
                btn.innerHTML = '<span class="sync-icon">🔄</span> ताज्या बातम्या क्रॉल करा (Live Sync)';
            }
        }

        async function loadDiscoverFeed(reset = false) {
            if (reset) {
                discoverOffset = 0;
                document.getElementById('featured-story-wrap').innerHTML = "";
                document.getElementById('discover-grid').innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;'>ताज्या घडामोडी लोड होत आहेत...</p>";
            }

            if (isDiscoverLoading) return;
            isDiscoverLoading = true;

            try {
                const url = `/api/discover?topic=${encodeURIComponent(currentDiscoverTopic)}&mode=${encodeURIComponent(appMode)}&limit=24&offset=${discoverOffset}`;
                const resp = await fetch(url);
                const data = await resp.json();
                const cards = data.cards || [];

                const grid = document.getElementById('discover-grid');
                const featuredWrap = document.getElementById('featured-story-wrap');

                if (reset) {
                    grid.innerHTML = "";
                    if (cards.length > 0 && cards[0].is_featured) {
                        const top = cards[0];
                        featuredWrap.innerHTML = `
                            <article class="featured-card">
                                <div class="featured-badge-bar">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span class="featured-badge">🔥 अग्रगण्य बातमी</span>
                                        <span class="pub-badge">${top.publisher_mr}</span>
                                        <span class="time-ago">🕒 ${top.relative_time_mr}</span>
                                    </div>
                                    <span style="font-size: 12px; color: var(--saffron-primary); font-weight: 700;">${top.reading_time_mr}</span>
                                </div>
                                <h3 class="featured-headline">
                                    <a href="${top.url}" target="_blank" rel="noopener">${top.title}</a>
                                </h3>
                                <div class="discover-tag">${top.topic_tag}</div>
                                <p style="font-size: 14.5px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
                                    ${top.snippet}
                                </p>
                                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                                    <div class="action-btns">
                                        ${renderActionsHtml(top.title, top.publisher_mr, top.url, top.topic_tag)}
                                    </div>
                                    <a href="${top.url}" target="_blank" rel="noopener" class="visit-link" style="font-size: 13.5px;">
                                        सविस्तर बातमी वाचा &rarr;
                                    </a>
                                </div>
                            </article>
                        `;
                        cards.shift();
                    }
                }

                if (cards.length === 0 && reset) {
                    grid.innerHTML = `
                        <div class="empty-state" style="grid-column: 1/-1;">
                            <h3>या वर्गवारीत सध्या ताज्या बातम्या उपलब्ध नाहीत</h3>
                            <p style="margin-top: 6px;">'सर्व ताज्या बातम्या' निवडा किंवा 'Live Sync' बटणावर क्लिक करून थेट ताज्या बातम्या आणा.</p>
                        </div>
                    `;
                    document.getElementById('load-more-btn').style.display = 'none';
                    return;
                }

                const cardsHtml = cards.map(c => `
                    <article class="discover-card">
                        <div>
                            <div class="discover-meta-row">
                                <span class="pub-badge">${c.publisher_mr}</span>
                                <span class="time-ago">🕒 ${c.relative_time_mr}</span>
                            </div>
                            <h4 class="discover-headline">
                                <a href="${c.url}" target="_blank" rel="noopener">${c.title}</a>
                            </h4>
                            <span class="discover-tag">${c.topic_tag}</span>
                            <p class="discover-snippet">${c.snippet}</p>
                        </div>
                        <div class="discover-footer">
                            <span>📖 ${c.reading_time_mr}</span>
                            <div class="action-btns">
                                ${renderActionsHtml(c.title, c.publisher_mr, c.url, c.topic_tag)}
                                <a href="${c.url}" target="_blank" rel="noopener" class="visit-link" style="font-size: 12px; margin-left: 4px;">
                                    वाचा &rarr;
                                </a>
                            </div>
                        </div>
                    </article>
                `).join('');

                if (reset) {
                    grid.innerHTML = cardsHtml;
                } else {
                    grid.insertAdjacentHTML('beforeend', cardsHtml);
                }

                discoverOffset += cards.length;
                document.getElementById('load-more-btn').style.display = cards.length < 15 ? 'none' : 'inline-block';

            } catch(e) {
                if (reset) {
                    document.getElementById('discover-grid').innerHTML = "<p style='grid-column: 1/-1; text-align: center;'>बातम्या लोड करताना त्रुटी आली.</p>";
                }
            } finally {
                isDiscoverLoading = false;
            }
        }

        function loadMoreDiscover() {
            loadDiscoverFeed(false);
        }

        // Initialize Persona Quick Hub on load
        renderPersonaQuickHub('general');
    </script>
</body>
</html>
"""


class SearchRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handles HTTP requests for Marathi Search Engine, API and Directory."""

    engine: MarathiSearchEngine
    dir_service: MarathiDirectory
    discover_service: MarathiDiscoverService
    crawler: FreshnessCrawler
    graph_html_path: Path

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif path == "/graph":
            if self.graph_html_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(self.graph_html_path.read_bytes())
            else:
                self.send_error(404, "Knowledge Graph file not generated yet")

        elif path == "/api/search":
            q = qs.get("q", [""])[0]
            cat = qs.get("category", ["all"])[0]
            freshness = qs.get("freshness", ["all"])[0]
            sort_by = qs.get("sort_by", ["relevance"])[0]

            resp = self.engine.search_full(
                q, 
                category=cat, 
                freshness=freshness,
                sort_by=sort_by
            )

            data = {
                "query": resp.query,
                "category": cat,
                "freshness": freshness,
                "sort_by": sort_by,
                "total": resp.total_found,
                "time_ms": resp.execution_time_ms,
                "intent": resp.intent,
                "intent_label_mr": resp.intent_label_mr,
                "article_shape": resp.article_shape,
                "article_shape_mr": resp.article_shape_mr,
                "tier_used": resp.tier_used,
                "measured": resp.measured,
                "related_queries": resp.related_queries,
                "results": [
                    {
                        "url": r.url,
                        "title": r.title,
                        "domain": r.domain,
                        "category": r.category,
                        "snippet": r.snippet,
                        "marathi_char_ratio": r.marathi_char_ratio,
                        "pagerank": r.pagerank,
                        "authority_score": r.authority_score,
                        "relevance_score": r.relevance_score,
                        "coverage": r.coverage,
                        "tier": r.tier,
                        "partial_match": r.partial_match,
                        "formatted_date": r.formatted_date,
                        "is_recent": r.is_recent,
                        "why_matched": r.why_matched,
                    }
                    for r in resp.results
                ],
            }
            self._send_json(data)

        elif path == "/api/suggest":
            q = qs.get("q", [""])[0]
            suggs = self.engine.suggest(q)
            self._send_json({"prefix": q, "suggestions": suggs})

        elif path == "/api/discover":
            topic = qs.get("topic", ["all"])[0]
            mode = qs.get("mode", ["general"])[0]
            try:
                limit = int(qs.get("limit", ["24"])[0])
            except ValueError:
                limit = 24
            try:
                offset = int(qs.get("offset", ["0"])[0])
            except ValueError:
                offset = 0

            cards = self.discover_service.get_discover_feed(
                topic=topic,
                mode=mode,
                limit=limit,
                offset=offset,
            )
            data = {
                "topic": topic,
                "mode": mode,
                "limit": limit,
                "offset": offset,
                "count": len(cards),
                "cards": [
                    {
                        "id": c.id,
                        "url": c.url,
                        "title": c.title,
                        "domain": c.domain,
                        "publisher_mr": c.publisher_mr,
                        "category": c.category,
                        "snippet": c.snippet,
                        "published_at": c.published_at,
                        "relative_time_mr": c.relative_time_mr,
                        "reading_time_mr": c.reading_time_mr,
                        "pagerank": c.pagerank,
                        "topic_tag": c.topic_tag,
                        "is_featured": c.is_featured,
                    }
                    for c in cards
                ]
            }
            self._send_json(data)

        elif path == "/api/crawler/refresh":
            new_indexed = self.crawler.crawl_once()
            data = {
                "success": True,
                "new_indexed": new_indexed,
                "message": f"ताज्या बातम्यांचे संकलन पूर्ण! {new_indexed} नवीन लेख जोडले गेले."
            }
            self._send_json(data)

        elif path == "/api/directory":
            cats = self.dir_service.get_full_directory()
            data = {
                "categories": [
                    {
                        "id": c.id,
                        "title_mr": c.title_mr,
                        "title_en": c.title_en,
                        "icon": c.icon,
                        "description_mr": c.description_mr,
                        "entries": [
                            {
                                "domain": e.domain,
                                "title": e.title,
                                "description": e.description,
                                "total_urls": e.total_urls,
                                "marathi_ratio": e.marathi_ratio,
                                "pagerank": e.pagerank,
                            }
                            for e in c.entries
                        ],
                    }
                    for c in cats
                ]
            }
            self._send_json(data)

        elif path in ("/config", "/health"):
            self._send_json({"status": "ok", "app": "tatya", "version": "1.0", "name": "तात्या"})

        else:
            self.send_error(404, "Page Not Found")

    def _send_json(self, data: dict[str, Any]) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine GET logging for crisp terminal output
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server(
    db_or_path: str | CrawlerDB = "marathi_web.db", 
    port: int = 8085, 
    graph_path: Any = None
) -> None:
    """Starts the multi-threaded Marathi Search Server."""
    if isinstance(db_or_path, CrawlerDB):
        db = db_or_path
    else:
        p = Path(db_or_path)
        gz_path = Path(str(db_or_path) + ".gz") if not str(db_or_path).endswith(".gz") else Path(db_or_path)
        if not p.exists() and gz_path.exists():
            print(f"📦 Extracting {gz_path} -> {p}...")
            import gzip, shutil
            with gzip.open(gz_path, "rb") as f_in, open(p, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            print("✅ Database extracted successfully.")
        db = CrawlerDB(str(p))
    
    # Ensure index exists
    print("⚡ Ensuring FTS5 Full-Text Index is ready...")
    indexer = SearchIndexer(db)
    indexed = indexer.build_index()
    print(f"✅ Indexed {indexed:,} Marathi pages in Full-Text Search index.")

    engine = MarathiSearchEngine(db)
    dir_service = MarathiDirectory(db)
    discover_service = MarathiDiscoverService(db)
    crawler = FreshnessCrawler(db)
    
    if graph_path:
        graph_html_path = Path(graph_path)
    else:
        graph_html_path = Path("marathi_graph_view.html")

    # Inject shared services into request handler
    SearchRequestHandler.engine = engine
    SearchRequestHandler.dir_service = dir_service
    SearchRequestHandler.discover_service = discover_service
    SearchRequestHandler.crawler = crawler
    SearchRequestHandler.graph_html_path = graph_html_path

    server = ThreadedHTTPServer(("0.0.0.0", port), SearchRequestHandler)
    print("\n" + "=" * 65)
    print("🚩 तात्या (TATYA) — मराठी इंटरनेटचा आपला शोध IS LIVE!")
    print("   तात्या — मराठी इंटरनेटसाठी स्वतंत्र शोधयंत्र")
    print("=" * 65)
    print(f"• URL:        http://localhost:{port}/")
    print(f"• Directory:  http://localhost:{port}/#directory")
    print(f"• Graph UI:   http://localhost:{port}/graph")
    print(f"• API:        http://localhost:{port}/api/search?q=शेतकऱ्यांना+कर्जमाफी")
    print("=" * 65 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()


serve_search_portal = start_server


if __name__ == "__main__":
    start_server()
