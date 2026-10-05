"""Editorial content planner: topic clustering, publishing sequence, and internal-link graph.

This module represents the product's primary moat (TECHNICAL.md §Phase 5).
Uses topic_key to unite cross-script spellings, sequences an editorial calendar,
and maps explicit internal-link anchors.
"""

from dataclasses import dataclass, field
from typing import Sequence

from praman.scoring import KeywordScore
from praman.script import topic_key


@dataclass
class TopicCluster:
    topic_id: str
    primary_title: str
    keywords: list[KeywordScore]
    cluster_demand: float
    primary_intent: str
    article_shape: str
    recommended_publish_order: int = 0


@dataclass
class InternalLink:
    source_topic: str
    target_topic: str
    anchor_text: str
    rationale: str


@dataclass
class ContentPlan:
    clusters: list[TopicCluster]
    calendar: list[TopicCluster]
    link_graph: list[InternalLink]
    orphan_topics: list[str]


def cluster_keywords(scores: Sequence[KeywordScore]) -> list[TopicCluster]:
    """Clusters keywords using consonant skeleton topic_key.

    Prevents bilingual duplicates like 'मराठी शेती' and 'marathi sheti'
    from taking separate slots on the editorial calendar.
    """
    groups: dict[str, list[KeywordScore]] = {}
    for score in scores:
        t_id = topic_key(score.seed)
        if t_id not in groups:
            groups[t_id] = []
        groups[t_id].append(score)

    clusters: list[TopicCluster] = []
    for t_id, kws in groups.items():
        # Sort keywords in cluster by demand descending
        kws_sorted = sorted(kws, key=lambda k: k.demand if k.demand is not None else -1.0, reverse=True)
        primary = kws_sorted[0]
        avg_demand = sum(k.demand or 0.0 for k in kws_sorted) / len(kws_sorted)

        clusters.append(
            TopicCluster(
                topic_id=t_id,
                primary_title=primary.seed,
                keywords=kws_sorted,
                cluster_demand=avg_demand,
                primary_intent=primary.intent.intent,
                article_shape=primary.intent.article_shape,
            )
        )

    return clusters


def generate_content_plan(scores: Sequence[KeywordScore]) -> ContentPlan:
    """Produces the complete editorial plan and internal link architecture."""
    clusters = cluster_keywords(scores)

    # Sort calendar by demand descending (prioritize high demand opportunities)
    calendar = sorted(clusters, key=lambda c: c.cluster_demand, reverse=True)
    for idx, c in enumerate(calendar, start=1):
        c.recommended_publish_order = idx

    # Build internal linking graph between related topics
    link_graph: list[InternalLink] = []
    linked_topics: set[str] = set()

    for i, source in enumerate(calendar):
        for j, target in enumerate(calendar):
            if i == j:
                continue
            # Suggest a link if topics share words or semantic intent
            source_words = set(source.primary_title.lower().split())
            target_words = set(target.primary_title.lower().split())
            common = source_words.intersection(target_words)

            source_stem = topic_key(source.primary_title)
            target_stem = topic_key(target.primary_title)
            related_cluster = bool(set(source_stem).intersection(set(target_stem))) if min(len(source_stem), len(target_stem)) >= 2 else False

            # Suggest link from broader informational/pillar to how-to or specific variant within related topics
            if common or (related_cluster and source.primary_intent == "informational" and target.primary_intent in ("howto", "freshness", "commercial")):
                anchor = target.primary_title
                link_graph.append(
                    InternalLink(
                        source_topic=source.primary_title,
                        target_topic=target.primary_title,
                        anchor_text=anchor,
                        rationale=f"Contextual link from {source.primary_intent} pillar to {target.primary_intent} target",
                    )
                )
                linked_topics.add(source.primary_title)
                linked_topics.add(target.primary_title)

    orphan_topics = [c.primary_title for c in calendar if c.primary_title not in linked_topics]

    return ContentPlan(
        clusters=clusters,
        calendar=calendar,
        link_graph=link_graph,
        orphan_topics=orphan_topics,
    )
