"""Interactive HTML/Canvas Knowledge Graph Visualizer for the Marathi Internet.

Generates a standalone, dependency-free interactive HTML application with:
- Force-directed physics canvas for network topology.
- Node sizing by PageRank/Authority score.
- Color grouping by category.
- Search, filter, inspection drawer, and metrics HUD.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from praman.crawler.db import CrawlerDB
from praman.crawler.graph import GraphMetrics, DomainNodeMetrics


CATEGORY_COLORS = {
    "News & Media": "#f59e0b",           # Amber
    "Finance & Career": "#10b981",       # Emerald
    "Agriculture": "#84cc16",            # Lime
    "Knowledge & Wiki": "#06b6d4",       # Cyan
    "Community & Literature": "#a855f7", # Purple
    "Government": "#6366f1",             # Indigo
    "Lifestyle & Cooking": "#ec4899",    # Pink
    "Blogs & Technology": "#3b82f6",     # Blue
    "Culture & History": "#f97316",      # Orange
    "General": "#94a3b8",                # Slate
}


def generate_interactive_graph_html(
    db: CrawlerDB,
    macro_metrics: GraphMetrics,
    domain_metrics: dict[str, DomainNodeMetrics],
    out_path: Path | str = "marathi_graph_view.html",
) -> Path:
    """Creates a standalone interactive HTML graph viewer."""
    out = Path(out_path)
    websites = db.get_all_websites()
    raw_edges = db.get_domain_link_matrix()

    nodes_json = []
    for w in websites:
        dom = w["domain"]
        cat = w.get("category", "General")
        dm = domain_metrics.get(dom)

        pr = dm.pagerank if dm else (w.get("pagerank") or 0.0)
        auth = dm.authority_score if dm else (w.get("authority_score") or 0.0)
        hub = dm.hub_score if dm else (w.get("hub_score") or 0.0)
        in_deg = dm.in_degree if dm else (w.get("in_degree") or 0)
        out_deg = dm.out_degree if dm else (w.get("out_degree") or 0)

        nodes_json.append({
            "id": dom,
            "label": w.get("title") or dom,
            "domain": dom,
            "category": cat,
            "color": CATEGORY_COLORS.get(cat, "#94a3b8"),
            "pagerank": pr,
            "authority": auth,
            "hub": hub,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "internal_links": w.get("internal_links_count", 0),
            "external_links": w.get("external_links_count", 0),
            "sitemap_status": w.get("sitemap_status", "unmeasured"),
            "sitemap_url": w.get("sitemap_url"),
            "sitemap_type": w.get("sitemap_type"),
            "total_sitemap_urls": w.get("total_sitemap_urls"),
            "marathi_ratio": w.get("marathi_char_ratio"),
            "language_verified": w.get("language_verified"),
        })

    edges_json = []
    for e in raw_edges:
        if not e["is_internal"] and e["source_domain"] != e["target_domain"]:
            edges_json.append({
                "source": e["source_domain"],
                "target": e["target_domain"],
                "weight": e["link_count"],
            })

    html_content = f"""<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>मराठी इंटरनेट ज्ञान आलेख (Marathi Web Knowledge Graph)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Yantramanav:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #090d16;
            --bg-surface: #111827;
            --bg-card: rgba(17, 24, 39, 0.85);
            --border-dim: rgba(255, 255, 255, 0.08);
            --border-accent: rgba(56, 189, 248, 0.3);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', 'Yantramanav', sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-dim);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .logo-badge {{
            background: linear-gradient(135deg, #06b6d4, #6366f1);
            color: #fff;
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            letter-spacing: 0.5px;
        }}
        .brand h1 {{
            font-size: 18px;
            font-weight: 700;
            color: #fff;
        }}
        .brand p {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        .hud-stats {{
            display: flex;
            gap: 20px;
        }}
        .stat-item {{
            text-align: right;
        }}
        .stat-val {{
            font-size: 16px;
            font-weight: 700;
            color: var(--accent-cyan);
        }}
        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .main-layout {{
            flex: 1;
            position: relative;
            display: flex;
        }}
        #graph-canvas {{
            width: 100%;
            height: 100%;
            cursor: grab;
            display: block;
        }}
        #graph-canvas:active {{
            cursor: grabbing;
        }}
        /* Left Control Panel */
        .control-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            width: 320px;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-dim);
            border-radius: 12px;
            padding: 16px;
            z-index: 5;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .search-box input {{
            width: 100%;
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--border-dim);
            border-radius: 8px;
            padding: 10px 14px;
            color: #fff;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box input:focus {{
            border-color: var(--accent-cyan);
        }}
        .category-filter {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            max-height: 180px;
            overflow-y: auto;
        }}
        .cat-chip {{
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 6px;
            background: rgba(255,255,255,0.06);
            color: var(--text-secondary);
            cursor: pointer;
            border: 1px solid transparent;
            user-select: none;
            transition: all 0.2s;
        }}
        .cat-chip.active {{
            border-color: var(--border-accent);
            color: #fff;
            background: rgba(6, 182, 212, 0.2);
        }}
        /* Node Details Drawer */
        .drawer {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 360px;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-dim);
            border-radius: 12px;
            padding: 20px;
            z-index: 5;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: none;
            flex-direction: column;
            gap: 14px;
            max-height: calc(100vh - 120px);
            overflow-y: auto;
        }}
        .drawer.open {{
            display: flex;
        }}
        .drawer-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border-dim);
            padding-bottom: 12px;
        }}
        .drawer-title {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
        }}
        .drawer-domain {{
            font-size: 12px;
            color: var(--accent-cyan);
            font-family: monospace;
        }}
        .close-btn {{
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 18px;
        }}
        .close-btn:hover {{ color: #fff; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .m-card {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.04);
        }}
        .m-val {{
            font-size: 15px;
            font-weight: 700;
            color: #f1f5f9;
        }}
        .m-lbl {{
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .pill-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-dim);
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            gap: 12px;
            font-size: 11px;
            color: var(--text-secondary);
            z-index: 4;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span class="logo-badge">PRAMAN GRAPH</span>
            <div>
                <h1>मराठी इंटरनेट ज्ञान आलेख (Marathi Web Graph)</h1>
                <p>Topological link structure, sitemap harvest, and authority flow</p>
            </div>
        </div>
        <div class="hud-stats">
            <div class="stat-item">
                <div class="stat-val">{macro_metrics.total_nodes}</div>
                <div class="stat-label">वेबसाइट्स (Nodes)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">{macro_metrics.total_directed_edges}</div>
                <div class="stat-label">दुवे संबंध (Edges)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">{macro_metrics.internal_edges:,}</div>
                <div class="stat-label">अंतर्गत दुवे (Internal Links)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">{macro_metrics.graph_density:.4f}</div>
                <div class="stat-label">घनता (Density)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">{macro_metrics.reciprocity*100:.1f}%</div>
                <div class="stat-label">परस्परता (Reciprocity)</div>
            </div>
        </div>
    </header>

    <div class="main-layout">
        <canvas id="graph-canvas"></canvas>

        <div class="control-panel">
            <div class="search-box">
                <input type="text" id="node-search" placeholder="शोध (Search domain / title)...">
            </div>
            <div>
                <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase;">वर्गवारी फिल्टर (Categories)</div>
                <div class="category-filter" id="cat-chips"></div>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); line-height: 1.4;">
                💡 <b>टीप:</b> नोड्सचा आकार PageRank दर्शवतो. तपशील पाहण्यासाठी कोणत्याही वेबसाइट नोडवर क्लिक करा.
            </div>
        </div>

        <div class="drawer" id="node-drawer">
            <div class="drawer-header">
                <div>
                    <div class="drawer-title" id="d-title">Title</div>
                    <div class="drawer-domain" id="d-domain">domain.com</div>
                </div>
                <button class="close-btn" id="d-close">&times;</button>
            </div>
            <div id="d-badge-container"></div>
            <div class="metric-grid">
                <div class="m-card">
                    <div class="m-val" id="d-pr">0.000</div>
                    <div class="m-lbl">PageRank</div>
                </div>
                <div class="m-card">
                    <div class="m-val" id="d-auth">0.000</div>
                    <div class="m-lbl">Authority Score (HITS)</div>
                </div>
                <div class="m-card">
                    <div class="m-val" id="d-hub">0.000</div>
                    <div class="m-lbl">Hub Score (HITS)</div>
                </div>
                <div class="m-card">
                    <div class="m-val" id="d-mr-ratio">0%</div>
                    <div class="m-lbl">मराठी मजकूर (Devanagari %)</div>
                </div>
                <div class="m-card">
                    <div class="m-val" id="d-int-links">0</div>
                    <div class="m-lbl">अंतर्गत दुवे (Internal Links)</div>
                </div>
                <div class="m-card">
                    <div class="m-val" id="d-ext-links">0</div>
                    <div class="m-lbl">बाह्य दुवे (External Citations)</div>
                </div>
            </div>
            <div class="m-card">
                <div class="m-lbl" style="margin-bottom: 4px;">साईटमॅप माहिती (Sitemap)</div>
                <div style="font-size: 12px; color: #fff;" id="d-sitemap-status">Status: found</div>
                <div style="font-size: 11px; color: var(--text-muted); word-break: break-all;" id="d-sitemap-url">-</div>
                <div style="font-size: 12px; color: var(--accent-emerald); margin-top: 4px;" id="d-sitemap-count">0 URLs indexed</div>
            </div>
        </div>

        <div class="legend">
            <div class="legend-item"><span class="dot" style="background: #f59e0b;"></span> बातम्या (News)</div>
            <div class="legend-item"><span class="dot" style="background: #10b981;"></span> अर्थ/वित्त (Finance)</div>
            <div class="legend-item"><span class="dot" style="background: #84cc16;"></span> शेती (Agri)</div>
            <div class="legend-item"><span class="dot" style="background: #06b6d4;"></span> ज्ञानकोश/विकि (Wiki)</div>
            <div class="legend-item"><span class="dot" style="background: #6366f1;"></span> शासन (Govt)</div>
            <div class="legend-item"><span class="dot" style="background: #3b82f6;"></span> ब्लॉग्स (Blogs)</div>
        </div>
    </div>

    <script>
        const graphData = {{
            nodes: {json.dumps(nodes_json, ensure_ascii=False)},
            edges: {json.dumps(edges_json, ensure_ascii=False)}
        }};

        const canvas = document.getElementById('graph-canvas');
        const ctx = canvas.getContext('2d');
        let width = canvas.width = canvas.offsetWidth;
        let height = canvas.height = canvas.offsetHeight;

        window.addEventListener('resize', () => {{
            width = canvas.width = canvas.offsetWidth;
            height = canvas.height = canvas.offsetHeight;
        }});

        // Categories setup
        const categories = [...new Set(graphData.nodes.map(n => n.category))];
        const chipsContainer = document.getElementById('cat-chips');
        let selectedCategory = null;

        categories.forEach(cat => {{
            const chip = document.createElement('div');
            chip.className = 'cat-chip';
            chip.textContent = cat;
            chip.onclick = () => {{
                if (selectedCategory === cat) {{
                    selectedCategory = null;
                    chip.classList.remove('active');
                }} else {{
                    document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
                    selectedCategory = cat;
                    chip.classList.add('active');
                }}
            }};
            chipsContainer.appendChild(chip);
        }});

        // Physics Simulation Nodes
        const nodes = graphData.nodes.map((n, i) => {{
            const angle = (i / graphData.nodes.length) * 2 * Math.PI;
            const radius = 220 + Math.random() * 120;
            return {{
                ...n,
                x: width / 2 + Math.cos(angle) * radius,
                y: height / 2 + Math.sin(angle) * radius,
                vx: 0,
                vy: 0,
                radius: Math.max(8, Math.min(28, (n.pagerank || 0.02) * 350 + 6))
            }};
        }});

        const nodeMap = new Map(nodes.map(n => [n.id, n]));
        const edges = graphData.edges
            .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
            .map(e => ({{
                source: nodeMap.get(e.source),
                target: nodeMap.get(e.target),
                weight: e.weight
            }}));

        // Camera Pan & Zoom
        let transform = {{ x: 0, y: 0, k: 1 }};
        let isDragging = false;
        let startX, startY;
        let hoveredNode = null;
        let selectedNode = null;

        canvas.addEventListener('mousedown', e => {{
            const rect = canvas.getBoundingClientRect();
            const mouseX = (e.clientX - rect.left - transform.x) / transform.k;
            const mouseY = (e.clientY - rect.top - transform.y) / transform.k;
            
            const hit = nodes.find(n => Math.hypot(n.x - mouseX, n.y - mouseY) < n.radius);
            if (hit) {{
                selectNode(hit);
            }} else {{
                isDragging = true;
                startX = e.clientX - transform.x;
                startY = e.clientY - transform.y;
            }}
        }});

        window.addEventListener('mousemove', e => {{
            if (isDragging) {{
                transform.x = e.clientX - startX;
                transform.y = e.clientY - startY;
            }} else {{
                const rect = canvas.getBoundingClientRect();
                const mouseX = (e.clientX - rect.left - transform.x) / transform.k;
                const mouseY = (e.clientY - rect.top - transform.y) / transform.k;
                hoveredNode = nodes.find(n => Math.hypot(n.x - mouseX, n.y - mouseY) < n.radius);
            }}
        }});

        window.addEventListener('mouseup', () => {{ isDragging = false; }});

        canvas.addEventListener('wheel', e => {{
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
            transform.k = Math.max(0.3, Math.min(3.5, transform.k * zoomFactor));
        }});

        // Search Filter
        let searchQuery = "";
        document.getElementById('node-search').addEventListener('input', e => {{
            searchQuery = e.target.value.toLowerCase().trim();
        }});

        function selectNode(node) {{
            selectedNode = node;
            const drawer = document.getElementById('node-drawer');
            drawer.classList.add('open');
            document.getElementById('d-title').textContent = node.label;
            document.getElementById('d-domain').textContent = node.domain;
            document.getElementById('d-pr').textContent = (node.pagerank || 0).toFixed(4);
            document.getElementById('d-auth').textContent = (node.authority || 0).toFixed(4);
            document.getElementById('d-hub').textContent = (node.hub || 0).toFixed(4);
            document.getElementById('d-mr-ratio').textContent = node.marathi_ratio != null ? Math.round(node.marathi_ratio * 100) + "%" : "मोजले नाही";
            document.getElementById('d-int-links').textContent = (node.internal_links || 0).toLocaleString();
            document.getElementById('d-ext-links').textContent = (node.external_links || 0).toLocaleString();
            document.getElementById('d-sitemap-status').textContent = "Status: " + node.sitemap_status;
            document.getElementById('d-sitemap-url').textContent = node.sitemap_url || "Direct sitemap not detected";
            document.getElementById('d-sitemap-count').textContent = (node.total_sitemap_urls || 0).toLocaleString() + " URLs discovered";

            const badgeBox = document.getElementById('d-badge-container');
            badgeBox.innerHTML = `<span class="pill-badge" style="background: ${{node.color}}22; color: ${{node.color}}; border: 1px solid ${{node.color}}55;">${{node.category}}</span>`;
        }}

        document.getElementById('d-close').onclick = () => {{
            document.getElementById('node-drawer').classList.remove('open');
            selectedNode = null;
        }};

        // Physics step
        function stepPhysics() {{
            const repulsion = 1400;
            const centerGravity = 0.015;

            // Repulsion between nodes
            for (let i = 0; i < nodes.length; i++) {{
                for (let j = i + 1; j < nodes.length; j++) {{
                    const dx = nodes[j].x - nodes[i].x;
                    const dy = nodes[j].y - nodes[i].y;
                    const dist = Math.hypot(dx, dy) || 1;
                    if (dist < 400) {{
                        const force = repulsion / (dist * dist);
                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;
                        nodes[i].vx -= fx;
                        nodes[i].vy -= fy;
                        nodes[j].vx += fx;
                        nodes[j].vy += fy;
                    }}
                }}
            }}

            // Attraction along edges
            edges.forEach(e => {{
                const dx = e.target.x - e.source.x;
                const dy = e.target.y - e.source.y;
                const dist = Math.hypot(dx, dy) || 1;
                const springForce = (dist - 140) * 0.004;
                const fx = (dx / dist) * springForce;
                const fy = (dy / dist) * springForce;
                e.source.vx += fx;
                e.source.vy += fy;
                e.target.vx -= fx;
                e.target.vy -= fy;
            }});

            // Damping & center attraction
            const cx = width / 2;
            const cy = height / 2;
            nodes.forEach(n => {{
                n.vx += (cx - n.x) * centerGravity;
                n.vy += (cy - n.y) * centerGravity;
                n.vx *= 0.88;
                n.vy *= 0.88;
                n.x += n.vx;
                n.y += n.vy;
            }});
        }}

        // Render Loop
        function render() {{
            stepPhysics();

            ctx.clearRect(0, 0, width, height);
            ctx.save();
            ctx.translate(transform.x, transform.y);
            ctx.scale(transform.k, transform.k);

            // Draw Edges
            edges.forEach(e => {{
                const isMatch = (!selectedCategory || (e.source.category === selectedCategory && e.target.category === selectedCategory));
                ctx.beginPath();
                ctx.moveTo(e.source.x, e.source.y);
                ctx.lineTo(e.target.x, e.target.y);
                ctx.strokeStyle = isMatch ? 'rgba(56, 189, 248, 0.22)' : 'rgba(255, 255, 255, 0.04)';
                ctx.lineWidth = Math.min(3, Math.max(0.5, Math.log(e.weight + 1)));
                ctx.stroke();
            }});

            // Draw Nodes
            nodes.forEach(n => {{
                const matchesCategory = !selectedCategory || n.category === selectedCategory;
                const matchesSearch = !searchQuery || n.domain.includes(searchQuery) || n.label.toLowerCase().includes(searchQuery);
                const isDimmed = !matchesCategory || !matchesSearch;

                const isSelected = selectedNode && selectedNode.id === n.id;
                const isHovered = hoveredNode && hoveredNode.id === n.id;

                ctx.beginPath();
                ctx.arc(n.x, n.y, n.radius, 0, 2 * Math.PI);
                ctx.fillStyle = isDimmed ? 'rgba(100, 116, 139, 0.2)' : n.color;
                ctx.fill();

                if (isSelected || isHovered) {{
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                }}

                // Label
                if (!isDimmed || isSelected || isHovered || transform.k > 1.2) {{
                    ctx.font = '11px "Plus Jakarta Sans", sans-serif';
                    ctx.fillStyle = isDimmed ? 'rgba(148, 163, 184, 0.4)' : '#f8fafc';
                    ctx.textAlign = 'center';
                    ctx.fillText(n.label, n.x, n.y + n.radius + 14);
                }}
            }});

            ctx.restore();
            requestAnimationFrame(render);
        }}

        render();
    </script>
</body>
</html>
"""
    out.write_text(html_content, encoding="utf-8")
    return out
