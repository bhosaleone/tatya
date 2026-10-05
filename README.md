---
title: Tatya - Marathi Search Engine
emoji: 🚩
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# 🚩 तात्या (Tatya) — मराठी इंटरनेटचा आपला शोध

> **मराठी इंटरनेटसाठी स्वतंत्र शोधयंत्र.**  
> *Zero external dependencies. Pure Python Standard Library + SQLite FTS5.*

---

# Praman CLI (प्रमाण)

> **Evidence-First Keyword Demand Research & Content Planning for Indian Regional Languages & English.**  
> *Zero external dependencies. Pure Python Standard Library. Refusing to fake search volume.*

---

## Overview

**Praman CLI** is a standalone, deterministic command-line keyword demand research and content planning engine. It replaces inaccurate clickstream scraping tools with a mathematically sound, reproducible demand index ($0.0 \le \text{demand}(s) \le 1.0$) built on Google's autocomplete protocol.

### Why Praman CLI?
1. **Zero External Dependencies**: Runs entirely on Python 3.10+ standard library (`urllib`, `json`, `re`, `unicodedata`, `argparse`). No heavy binaries, no paid API keys required.
2. **Grammatically Aware for Indic Scripts**: Built specifically for Brahmic combining characters (matras, halant, anusvara) and Subject-Object-Verb (SOV) question patterns across 10 Indian languages.
3. **Strict Mathematical Invariants**: Missing measurements are never treated as zero ($V = \mathbb{R} \cup \{\bot\}$). Unmeasured axes never distort surviving weights.
4. **Actionable Editorial Outputs**: Generates full publication calendars, semantic cluster mappings, and contextual internal linking graphs with exact anchor text recommendations.
5. **Human SERP Integration**: Allows human search evaluation data (`thin_results`, `weak_domains`, `top_results_stale`) to blend directly into the priority formula.

---

## Directory Structure

```
praman_cli/
├── cli.py                     # Main CLI executable entry point
├── pyproject.toml             # Standard packaging specification
├── setup.py                   # Traditional setuptools packaging
├── requirements.txt           # Dependency notes (zero dependencies required)
├── README.md                  # This documentation
├── praman/                    # Core research & algorithmic engine
│   ├── __init__.py
│   ├── autocomplete.py        # HTTP autocomplete fetcher & rate-limit handler
│   ├── cache.py               # Deterministic disk caching engine
│   ├── competition.py         # Human SERP observation & competition index
│   ├── config.py              # Configuration, modes, weights, and settings
│   ├── errors.py              # Strict domain error types
│   ├── expand.py              # Alphabetical & commercial modifier expansion
│   ├── fixtures.py            # Offline synthetic hash-deterministic fixtures
│   ├── intent.py              # Indic grammatical intent classification
│   ├── languages.py           # Language definitions & SOV interrogative rules
│   ├── pipeline.py            # Core research pipeline orchestration
│   ├── planner.py             # Topological editorial calendar & link graph generator
│   ├── report.py              # Markdown, CSV, and JSON report renderers
│   ├── scoring.py             # Pinned 4-voice demand calculation
│   ├── script.py              # Unicode script classification & normalization
│   ├── signals.py             # Signals and metrics extraction
│   └── ai.py                  # Optional LLM-assisted brief generation
├── docs/                      # Comprehensive theoretical & operational documentation
│   ├── USER_MANUAL.md         # Full operational user manual
│   ├── KEYWORD_RESEARCH_AND_BLOG_TAXONOMY_MANUAL.md # Content clustering & taxonomy guide
│   ├── MATH.md                # Mathematical proofs & formula definitions
│   ├── METHODOLOGY.md         # Scientific demand measurement methodology
│   ├── PRIOR_ART_KD_FORMULAS.md # Critique of legacy KD formulas
│   └── NO_API.md              # Zero-API key protocol specification
├── examples/                  # Sample data & demo scripts
│   ├── seeds_sample.txt       # Multi-niche sample seeds (Marathi, Hindi, English)
│   └── run_demo.sh            # 1-click comprehensive demonstration script
└── tests/                     # 37-test automated verification suite
    ├── test_affiliate.py
    ├── test_ai.py
    ├── test_candidate_filter.py
    ├── test_expand.py
    ├── test_intent_competition.py
    ├── test_planner.py
    ├── test_scoring.py
    └── test_script.py
```

---

## Installation & Setup

### Option 1: Direct Execution (No Install Needed)
Clone or unzip `praman_cli` and run directly using Python 3:
```bash
python3 cli.py --help
```

### Option 2: Install as a System/Virtualenv CLI Command
```bash
pip install -e .
praman --help
```

---

## Quickstart & Common Workflows

### 1. View Pinned Demand Weights & Invariants
```bash
python3 cli.py weights
```

### 2. Run Keyword Demand Research
#### Offline Fixture Mode (Instant demo without internet)
```bash
python3 cli.py research "शेती" "हवामान" --lang mr --mode fixture
```

#### Live Mode (Real-time Google Autocomplete)
```bash
# Research Marathi agriculture & finance seeds
python3 cli.py research "शेअर बाजार" "म्युच्युअल फंड" --lang mr --mode live --format md -o report.md

# Research Hindi seeds with commercial expansion
python3 cli.py research "क्रेडिट कार्ड" "होम लोन" --lang hi --mode live --commercial-expansion -o hindi_finance.md
```

#### Batch Research from File
```bash
python3 cli.py research --seeds-file examples/seeds_sample.txt --lang mr --mode live --format csv -o batch_output.csv
```

---

### 3. Human SERP Review Workflow
Praman separates autocomplete demand from search page competition. Use this workflow to blend human SERP observation with demand:

```bash
# Step 1: Generate human observation template
python3 cli.py serp --seeds-file examples/seeds_sample.txt -o observations.csv

# Step 2: Open observations.csv in Excel/Sheets, inspect SERPs, and fill in 'yes' or 'no'
# Columns: keyword, top_results_stale, thin_results, weak_domains, own_sites_ranking, notes

# Step 3: Run research with SERP data blended in
python3 cli.py research --seeds-file examples/seeds_sample.txt --serp observations.csv --lang mr --mode live -o final_report.md
```

---

### 4. Generate Editorial Calendar & Internal Link Graph
Generate a topological publication order and interlinking graph that prioritizes high-demand, low-competition pillar topics:

```bash
python3 cli.py plan "शेअर बाजार" "म्युच्युअल फंड" "एसआयपी" "डीमॅट" --lang mr --mode live -o editorial_plan.md
```

---

## CLI Reference & Flags

### Global Options
- `-h, --help`: Show help message.

### `praman research`
| Flag | Default | Description |
|---|---|---|
| `seeds` | `[]` | Positional seed keyword(s) to evaluate. |
| `--seeds-file` | `None` | Path to text file containing seed keywords (one per line). |
| `--lang` | `mr` | Target language code (`mr`, `hi`, `ta`, `te`, `bn`, `gu`, `kn`, `ml`, `pa`, `or`, `en`). |
| `--region` | `IN` | Search region (default: `IN`). |
| `--mode` | `fixture` | Execution mode: `live`, `fixture`, or `recorded`. |
| `--recorded` | `None` | Path to recorded session JSON file (when `--mode recorded`). |
| `--serp` | `None` | Path to human SERP evaluation CSV file. |
| `--latin-expansion` | `False` | Probe alphabet combinations A–Z. |
| `--commercial-expansion`| `False` | Probe Indian commercial modifiers (दर, फी, पात्रता, नियम, चार्ज, ऑनलाइन). |
| `--format` | `md` | Output format: `md` (Markdown), `csv`, or `json`. |
| `-o, --out` | `None` | Path to write the output report (default: stdout). |

### `praman serp`
| Flag | Default | Description |
|---|---|---|
| `seeds` | `[]` | Positional seed keyword(s). |
| `--seeds-file` | `None` | Path to file with seed keywords. |
| `-o, --out` | Required | Output CSV path for the template. |
| `--overwrite` | `False` | Overwrite existing template file. |

### `praman plan`
| Flag | Default | Description |
|---|---|---|
| `seeds` | `[]` | Seed keywords to cluster and plan. |
| `--lang` | `mr` | Target language code. |
| `--mode` | `fixture` | Execution mode (`live`, `fixture`, `recorded`). |
| `-o, --out` | `None` | Output Markdown path for the content plan. |

---

## The Mathematical Demand Model

Praman calculates a composite demand score:
$$\text{demand}(s) = 0.50 \cdot \text{breadth}(s) + 0.25 \cdot \text{coverage}(s) + 0.15 \cdot \text{density}(s) + 0.10 \cdot \text{depth}(s)$$

- **Breadth ($0.50$)**: Normalized count of alphabet/modifier branches returning suggestions.
- **Coverage ($0.25$)**: Frequency of the seed appearing at the head of root query suggestions.
- **Density ($0.15$)**: Ratio of discovered queries containing SOV interrogative tokens.
- **Depth ($0.10$)**: Positional prominence across suggestion dropdown ranks.

### Fundamental Invariants
1. **Weights strictly sum to 1.0.**
2. **Missing measurement is never zero**: If rate-limited or unmeasured, weights never renormalize; the score is capped and flagged `partial`.

---

## Running the Automated Test Suite

Praman CLI includes a comprehensive unit test suite:
```bash
python3 -m unittest discover tests
```
All 37 test cases run in **< 0.1 seconds** using the standard library.

---

## License & Credits
- **License**: MIT
- **Architecture**: Mathematical Demand Modeling & Indic SOV Autocomplete Pipeline
