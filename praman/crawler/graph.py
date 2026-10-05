"""Knowledge Graph Analytics and Measurements for the Marathi Internet.

Computes:
- Directed Adjacency Matrix of domains and internal link densities.
- Google PageRank (power iteration with dangling node redistribution).
- Kleinberg HITS (Hubs and Authorities).
- Graph Reciprocity, Density, and Component Connectivity.
- Cross-Domain Link Flow across Categories (News, Finance, Agri, Wiki, Govt, Blogs).
"""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from praman.crawler.db import CrawlerDB


@dataclass
class DomainNodeMetrics:
    domain: str
    category: str
    in_degree: int
    out_degree: int
    internal_links: int
    external_links: int
    pagerank: float
    hub_score: float
    authority_score: float
    marathi_ratio: Optional[float]
    title: Optional[str] = None


@dataclass
class GraphMetrics:
    total_nodes: int
    total_directed_edges: int
    cross_domain_edges: int
    internal_edges: int
    graph_density: float
    reciprocity: float
    top_authorities: list[tuple[str, float, str]]  # (domain, authority_score, category)
    top_hubs: list[tuple[str, float, str]]         # (domain, hub_score, category)
    top_pagerank: list[tuple[str, float, str]]     # (domain, pagerank, category)
    category_flows: dict[str, dict[str, int]]      # source_cat -> target_cat -> link_count


class GraphAnalyzer:
    """Analyzes the Marathi Web Knowledge Graph from CrawlerDB."""

    def __init__(self, db: CrawlerDB):
        self.db = db

    def compute_all_metrics(self) -> tuple[GraphMetrics, dict[str, DomainNodeMetrics]]:
        """Extracts link matrix, runs PageRank and HITS, and persists scores into CrawlerDB."""
        websites = {w["domain"]: w for w in self.db.get_all_websites()}
        all_domains = sorted(list(websites.keys()))
        N = len(all_domains)

        if N == 0:
            empty_metrics = GraphMetrics(0, 0, 0, 0, 0.0, 0.0, [], [], [], {})
            return empty_metrics, {}

        dom_to_idx = {d: i for i, d in enumerate(all_domains)}
        idx_to_dom = {i: d for i, d in enumerate(all_domains)}

        # Fetch aggregated link matrix from database
        raw_edges = self.db.get_domain_link_matrix()

        # Build adjacency structures
        # out_adj[u] = {v: weight}
        # in_adj[v] = {u: weight}
        out_adj: dict[int, dict[int, int]] = {i: {} for i in range(N)}
        in_adj: dict[int, dict[int, int]] = {i: {} for i in range(N)}
        
        internal_links_count: dict[str, int] = {d: 0 for d in all_domains}
        external_out_count: dict[str, int] = {d: 0 for d in all_domains}
        external_in_count: dict[str, int] = {d: 0 for d in all_domains}

        total_internal_links = 0
        total_external_links = 0
        cross_domain_edge_set: set[tuple[int, int]] = set()
        category_flows: dict[str, dict[str, int]] = {}

        for edge in raw_edges:
            s_dom = edge["source_domain"]
            t_dom = edge["target_domain"]
            count = edge["link_count"]
            is_int = edge["is_internal"]

            if is_int or s_dom == t_dom:
                internal_links_count[s_dom] = internal_links_count.get(s_dom, 0) + count
                total_internal_links += count
            else:
                total_external_links += count
                external_out_count[s_dom] = external_out_count.get(s_dom, 0) + count
                external_in_count[t_dom] = external_in_count.get(t_dom, 0) + count

                s_cat = websites.get(s_dom, {}).get("category", "Unclassified")
                t_cat = websites.get(t_dom, {}).get("category", "Unclassified")
                if s_cat not in category_flows:
                    category_flows[s_cat] = {}
                category_flows[s_cat][t_cat] = category_flows[s_cat].get(t_cat, 0) + count

                if s_dom in dom_to_idx and t_dom in dom_to_idx:
                    u = dom_to_idx[s_dom]
                    v = dom_to_idx[t_dom]
                    out_adj[u][v] = out_adj[u].get(v, 0) + count
                    in_adj[v][u] = in_adj[v].get(u, 0) + count
                    cross_domain_edge_set.add((u, v))

        # 1. PageRank Calculation (Power iteration, d = 0.85)
        pageranks = self._compute_pagerank(N, out_adj)

        # 2. Kleinberg HITS (Hubs and Authorities)
        hubs, authorities = self._compute_hits(N, out_adj, in_adj)

        # 3. Reciprocity
        mutual_edges = 0
        for (u, v) in cross_domain_edge_set:
            if (v, u) in cross_domain_edge_set:
                mutual_edges += 1
        reciprocity = round(mutual_edges / len(cross_domain_edge_set), 4) if cross_domain_edge_set else 0.0

        # 4. Graph Density
        possible_edges = N * (N - 1) if N > 1 else 1
        graph_density = round(len(cross_domain_edge_set) / possible_edges, 6)

        # Build Domain Node Metrics
        domain_metrics: dict[str, DomainNodeMetrics] = {}
        db_scores_update: dict[str, dict[str, Any]] = {}

        for i, dom in enumerate(all_domains):
            site_info = websites[dom]
            in_deg = len(in_adj[i])
            out_deg = len(out_adj[i])
            pr = round(pageranks[i], 6)
            h_score = round(hubs[i], 6)
            a_score = round(authorities[i], 6)

            dnm = DomainNodeMetrics(
                domain=dom,
                category=site_info.get("category", "General"),
                in_degree=in_deg,
                out_degree=out_deg,
                internal_links=internal_links_count.get(dom, 0),
                external_links=external_out_count.get(dom, 0),
                pagerank=pr,
                hub_score=h_score,
                authority_score=a_score,
                marathi_ratio=site_info.get("marathi_char_ratio"),
                title=site_info.get("title"),
            )
            domain_metrics[dom] = dnm

            db_scores_update[dom] = {
                "in_degree": in_deg,
                "out_degree": out_deg,
                "pagerank": pr,
                "hub_score": h_score,
                "authority_score": a_score,
                "internal_links": internal_links_count.get(dom, 0),
                "external_links": external_out_count.get(dom, 0),
            }

        # Update scores in SQLite DB
        self.db.update_graph_scores(db_scores_update)

        # Top ranked domains
        sorted_by_pr = sorted(domain_metrics.values(), key=lambda x: x.pagerank, reverse=True)
        sorted_by_auth = sorted(domain_metrics.values(), key=lambda x: x.authority_score, reverse=True)
        sorted_by_hub = sorted(domain_metrics.values(), key=lambda x: x.hub_score, reverse=True)

        top_pr = [(m.domain, m.pagerank, m.category) for m in sorted_by_pr[:10]]
        top_auth = [(m.domain, m.authority_score, m.category) for m in sorted_by_auth[:10]]
        top_hubs = [(m.domain, m.hub_score, m.category) for m in sorted_by_hub[:10]]

        macro_metrics = GraphMetrics(
            total_nodes=N,
            total_directed_edges=len(cross_domain_edge_set),
            cross_domain_edges=total_external_links,
            internal_edges=total_internal_links,
            graph_density=graph_density,
            reciprocity=reciprocity,
            top_authorities=top_auth,
            top_hubs=top_hubs,
            top_pagerank=top_pr,
            category_flows=category_flows,
        )

        # Persist graph snapshot
        self.db.record_graph_snapshot({
            "total_domains": N,
            "total_pages": sum(w.get("pages_crawled", 0) for w in websites.values()),
            "total_sitemaps": len(all_domains),
            "total_internal_links": total_internal_links,
            "total_external_links": total_external_links,
            "cross_domain_edges": len(cross_domain_edge_set),
            "graph_density": graph_density,
            "reciprocity": reciprocity,
            "top_authorities_json": json.dumps(top_auth),
            "top_hubs_json": json.dumps(top_hubs),
            "category_distribution_json": json.dumps(category_flows),
        })

        return macro_metrics, domain_metrics

    def _compute_pagerank(
        self,
        N: int,
        out_adj: dict[int, dict[int, int]],
        d: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> list[float]:
        """Calculates PageRank with dangling node redistribution."""
        if N == 0:
            return []
        
        pr = [1.0 / N] * N
        out_totals = [sum(out_adj[i].values()) for i in range(N)]

        for _ in range(max_iter):
            new_pr = [(1.0 - d) / N] * N
            dangling_sum = sum(pr[i] for i in range(N) if out_totals[i] == 0)

            for i in range(N):
                if out_totals[i] > 0:
                    weight_factor = pr[i] / out_totals[i]
                    for j, weight in out_adj[i].items():
                        new_pr[j] += d * weight * weight_factor
                else:
                    # Dangling contribution is distributed equally
                    pass

            dangling_contrib = (d * dangling_sum) / N
            for j in range(N):
                new_pr[j] += dangling_contrib

            diff = sum(abs(new_pr[i] - pr[i]) for i in range(N))
            pr = new_pr
            if diff < tol:
                break

        return pr

    def _compute_hits(
        self,
        N: int,
        out_adj: dict[int, dict[int, int]],
        in_adj: dict[int, dict[int, int]],
        max_iter: int = 40,
        tol: float = 1e-5,
    ) -> tuple[list[float], list[float]]:
        """Kleinberg's HITS Algorithm for Hubs and Authorities."""
        if N == 0:
            return [], []

        hubs = [1.0] * N
        authorities = [1.0] * N

        for _ in range(max_iter):
            new_auth = [0.0] * N
            new_hubs = [0.0] * N

            # Update authorities from incoming hubs
            for i in range(N):
                for j in in_adj[i]:
                    new_auth[i] += hubs[j]

            # Update hubs from outgoing authorities
            for i in range(N):
                for j in out_adj[i]:
                    new_hubs[i] += authorities[j]

            # Normalize with L2 norm
            auth_norm = math.sqrt(sum(a * a for a in new_auth)) or 1.0
            hub_norm = math.sqrt(sum(h * h for h in new_hubs)) or 1.0

            new_auth = [a / auth_norm for a in new_auth]
            new_hubs = [h / hub_norm for h in new_hubs]

            diff = sum(abs(new_auth[i] - authorities[i]) + abs(new_hubs[i] - hubs[i]) for i in range(N))
            authorities = new_auth
            hubs = new_hubs
            if diff < tol:
                break

        return hubs, authorities
