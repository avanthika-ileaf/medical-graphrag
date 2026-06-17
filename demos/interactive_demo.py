"""
demos/interactive_demo.py

Streamlit web application for side-by-side comparison of
Standard RAG vs GraphRAG on medical queries.

Run: streamlit run demos/interactive_demo.py
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Medical GraphRAG Demo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("Medical GraphRAG")
st.sidebar.markdown("**Stack:** Neo4j · Qdrant · GPT-4 · LangChain · OWL Ontology")
st.sidebar.markdown("---")
st.sidebar.subheader("Preset Queries")

PRESET_QUERIES = [
    "Which patients with Type 2 Diabetes are on 3+ medications that interact dangerously?",
    "Which patients with Chronic Kidney Disease are taking contraindicated drugs?",
    "Show the drug interaction chain from Warfarin (2 hops).",
    "Find patients sharing a doctor who have overlapping conditions and interacting drugs.",
    "Which patients are at risk for serotonin syndrome from their medications?",
]

selected_preset = st.sidebar.selectbox(
    "Choose a preset query:",
    options=["(custom)"] + PRESET_QUERIES,
    index=0,
)

# ─── Main UI ──────────────────────────────────────────────────────────────────
st.title("🏥 Medical Knowledge GraphRAG")
st.markdown(
    "Compare **Standard RAG** (vector-only) vs **GraphRAG** (vector + Neo4j graph) "
    "on complex medical queries that require multi-hop reasoning."
)

if selected_preset != "(custom)":
    query_input = st.text_area("Medical Query:", value=selected_preset, height=80)
else:
    query_input = st.text_area(
        "Medical Query:",
        placeholder="e.g. Which patients with diabetes are on interacting medications?",
        height=80,
    )

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_btn = st.button("Run Comparison", type="primary")
with col_clear:
    if st.button("Clear"):
        st.rerun()

# ─── Run ──────────────────────────────────────────────────────────────────────
if run_btn and query_input.strip():
    with st.spinner("Running retrieval pipelines..."):
        try:
            from evaluation.compare_rag_systems import StandardRAG
            from src.graphrag.medical_graphrag import MedicalGraphRAG

            # Standard RAG
            t0 = time.perf_counter()
            standard = StandardRAG()
            std_result = standard.query(query_input)
            std_latency = (time.perf_counter() - t0) * 1000

            # GraphRAG
            t0 = time.perf_counter()
            graph_rag = MedicalGraphRAG()
            gr_result = graph_rag.query(query_input)
            gr_latency = (time.perf_counter() - t0) * 1000
            graph_rag.close()

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

    st.success("Retrieval complete!")
    st.markdown("---")

    # ─── Results columns ──────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Standard RAG (Vector Only)")
        st.metric("Latency", f"{std_latency:.0f} ms")
        st.metric("Confidence", f"{std_result.get('confidence', 0):.0%}")
        st.markdown("**Answer:**")
        st.info(std_result.get("answer", "No answer"))
        st.caption("Sources: Qdrant semantic search only")

    with col2:
        st.subheader("GraphRAG (Vector + Neo4j)")
        st.metric("Latency", f"{gr_latency:.0f} ms")
        st.metric("Confidence", f"{gr_result.get('confidence', 0):.0%}")
        st.markdown("**Answer:**")
        st.success(gr_result.get("answer", "No answer"))

        provenance = gr_result.get("provenance", {})
        st.caption(
            f"Sources: Neo4j graph ({len(provenance.get('graph_only', []))} unique) "
            f"+ Qdrant ({len(provenance.get('vector_only', []))} unique) "
            f"| Confirmed by both: {len(provenance.get('confirmed', []))}"
        )

    # ─── Graph results ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Graph Traversal Results")

    graph_hits = gr_result.get("graph_hits", [])
    if graph_hits:
        import pandas as pd
        try:
            df = pd.DataFrame(graph_hits[:10])
            # Format any list/dict columns into readable strings
            for col in df.columns:
                if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                    def _fmt(v):
                        if isinstance(v, list):
                            if v and isinstance(v[0], dict):
                                # e.g. interactions: [{drug1, drug2, severity}]
                                return "; ".join(
                                    f"{d.get('drug1','?')} ↔ {d.get('drug2','?')} (sev {d.get('severity','?')})"
                                    if 'drug1' in d else str(d)
                                    for d in v
                                )
                            return ", ".join(str(x) for x in v) if v else "—"
                        if isinstance(v, dict):
                            return str(v)
                        return v
                    df[col] = df[col].apply(_fmt)
            st.dataframe(df, use_container_width=True)
        except Exception:
            st.json(graph_hits[:5])
    else:
        st.info("No graph results (is Neo4j running and populated?)")

    # ─── Patient relationship path visualizer ─────────────────────────────────
    st.markdown("---")
    st.subheader("🔗 Patient Relationship Path Visualizer")
    st.markdown(
        "Select a patient from the graph results to see their **full node traversal path** "
        "— from the patient node through all connected relationships to the final result entities."
    )

    # Collect patient IDs from graph_hits
    patient_ids = [
        h.get("patientID") or h.get("patient1")
        for h in graph_hits
        if h.get("patientID") or h.get("patient1")
    ]
    # Also add patient2 from cohort queries
    for h in graph_hits:
        if h.get("patient2") and h["patient2"] not in patient_ids:
            patient_ids.append(h["patient2"])

    patient_ids = list(dict.fromkeys(patient_ids))  # deduplicate, preserve order

    if patient_ids:
        selected_patient = st.selectbox(
            "Choose a patient to visualise their graph path:",
            options=patient_ids,
        )

        if selected_patient:
            try:
                from src.graphrag.retrievers.graph_retriever import GraphRetriever

                _gr = GraphRetriever()
                path_data = _gr.get_patient_graph_paths(selected_patient)
                _gr.close()

                nodes = path_data["nodes"]
                edges = path_data["edges"]

                if not nodes:
                    st.warning(f"No graph path found for patient {selected_patient}.")
                else:
                    # ── Build Plotly network layout ──────────────────────────
                    import math

                    # Assign positions: patient at center, others in arcs by type
                    TYPE_COLORS = {
                        "Patient":   "#3498db",
                        "Drug":      "#e67e22",
                        "Condition": "#2ecc71",
                        "Provider":  "#9b59b6",
                    }
                    TYPE_SYMBOLS = {
                        "Patient":   "circle",
                        "Drug":      "diamond",
                        "Condition": "square",
                        "Provider":  "star",
                    }

                    # Group non-patient nodes by type
                    from collections import defaultdict
                    type_groups: dict[str, list] = defaultdict(list)
                    pos: dict[str, tuple] = {}

                    for node in nodes:
                        if node["type"] == "Patient":
                            pos[node["id"]] = (0.0, 0.0)
                        else:
                            type_groups[node["type"]].append(node)

                    # Arrange each type group in an arc
                    arc_angles = {"Drug": 0, "Condition": 120, "Provider": 240}
                    radius = 2.0
                    arc_spread = 60  # degrees around the center angle per group

                    for ntype, group in type_groups.items():
                        center_angle = arc_angles.get(ntype, 180)
                        n = len(group)
                        for i, node in enumerate(group):
                            if n == 1:
                                angle_deg = center_angle
                            else:
                                angle_deg = center_angle - arc_spread / 2 + i * arc_spread / (n - 1)
                            angle_rad = math.radians(angle_deg)
                            pos[node["id"]] = (
                                radius * math.cos(angle_rad),
                                radius * math.sin(angle_rad),
                            )

                    # Build edge traces
                    edge_traces = []
                    for edge in edges:
                        x0, y0 = pos.get(edge["from"], (0, 0))
                        x1, y1 = pos.get(edge["to"], (0, 0))
                        sev = edge.get("severity")
                        color = "#e74c3c" if sev and sev >= 0.7 else "#95a5a6"
                        width = 3 if sev and sev >= 0.7 else 1.5

                        # Edge line
                        edge_traces.append(go.Scatter(
                            x=[x0, x1, None],
                            y=[y0, y1, None],
                            mode="lines",
                            line=dict(width=width, color=color),
                            hoverinfo="none",
                            showlegend=False,
                        ))

                        # Edge label at midpoint
                        edge_traces.append(go.Scatter(
                            x=[(x0 + x1) / 2],
                            y=[(y0 + y1) / 2],
                            mode="text",
                            text=[edge["label"]],
                            textfont=dict(size=9, color=color),
                            hoverinfo="none",
                            showlegend=False,
                        ))

                    # Build node traces (one per type for legend)
                    node_traces = []
                    for ntype, color in TYPE_COLORS.items():
                        type_nodes = [n for n in nodes if n["type"] == ntype]
                        if not type_nodes:
                            continue
                        xs = [pos[n["id"]][0] for n in type_nodes]
                        ys = [pos[n["id"]][1] for n in type_nodes]
                        labels = [n["label"] for n in type_nodes]
                        node_traces.append(go.Scatter(
                            x=xs,
                            y=ys,
                            mode="markers+text",
                            marker=dict(
                                size=22 if ntype == "Patient" else 16,
                                color=color,
                                symbol=TYPE_SYMBOLS[ntype],
                                line=dict(width=2, color="white"),
                            ),
                            text=labels,
                            textposition="top center",
                            textfont=dict(size=10),
                            name=ntype,
                            hovertext=labels,
                            hoverinfo="text",
                        ))

                    fig_path = go.Figure(
                        data=edge_traces + node_traces,
                        layout=go.Layout(
                            title=dict(
                                text=f"Relationship Path — Patient {selected_patient}",
                                font=dict(size=16),
                            ),
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            plot_bgcolor="rgba(15,17,22,1)",
                            paper_bgcolor="rgba(15,17,22,1)",
                            font=dict(color="white"),
                            height=550,
                            margin=dict(l=20, r=20, t=60, b=20),
                        ),
                    )
                    st.plotly_chart(fig_path, use_container_width=True)

                    # ── Path legend / summary ────────────────────────────────
                    with st.expander("Path Summary — Nodes & Relationships"):
                        col_n, col_e = st.columns(2)
                        with col_n:
                            st.markdown("**Nodes**")
                            for n in nodes:
                                badge_color = TYPE_COLORS.get(n["type"], "#888")
                                st.markdown(
                                    f"<span style='background:{badge_color};color:#fff;"
                                    f"padding:2px 8px;border-radius:4px;font-size:12px'>"
                                    f"{n['type']}</span> &nbsp; {n['label']}",
                                    unsafe_allow_html=True,
                                )
                        with col_e:
                            st.markdown("**Relationships (edges)**")
                            for e in edges:
                                sev = e.get("severity")
                                sev_str = f" — severity **{sev:.2f}**" if sev else ""
                                src_label = next((n["label"] for n in nodes if n["id"] == e["from"]), e["from"])
                                tgt_label = next((n["label"] for n in nodes if n["id"] == e["to"]),   e["to"])
                                st.markdown(
                                    f"`{src_label}` → **{e['label']}** → `{tgt_label}`{sev_str}"
                                )

            except Exception as exc:
                st.error(f"Could not load relationship path: {exc}")
    else:
        st.info("Run a query with patient results to enable path visualisation.")

    # ─── arXiv research papers ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Related Research Papers (arXiv)")
    st.markdown(
        "Papers retrieved live from arXiv and semantically cached in Qdrant "
        "matching your medical query."
    )

    with st.spinner("Fetching arXiv papers..."):
        try:
            from src.graphrag.retrievers.arxiv_retriever import ArxivRetriever
            _arxiv = ArxivRetriever()
            arxiv_papers = _arxiv.search(query_input)
        except Exception as arxiv_err:
            arxiv_papers = []
            st.warning(f"arXiv retrieval error: {arxiv_err}")

    if arxiv_papers:
        for paper in arxiv_papers:
            with st.expander(
                f"[{paper.get('published', '')}] {paper.get('title', 'Untitled')}  "
                f"— {', '.join(paper.get('authors', [])[:2])}"
                + (" et al." if len(paper.get("authors", [])) > 2 else "")
            ):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Summary:** {paper.get('summary', '')}")
                    st.markdown(
                        f"**Authors:** {', '.join(paper.get('authors', []))}"
                    )
                    st.markdown(
                        "**Topics:** "
                        + "  ".join(
                            f"`{t}`" for t in paper.get("topics", [])
                        )
                    )
                with col_b:
                    st.markdown(f"**Published:** {paper.get('published', 'N/A')}")
                    st.markdown(
                        f"**Source:** `{paper.get('source', 'arxiv_api')}`"
                    )
                    url = paper.get("url", "")
                    if url:
                        st.markdown(f"[Open on arXiv]({url})")
    else:
        st.info("No arXiv papers found for this query.")

    # ─── Latency chart ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Latency Comparison")
    fig = go.Figure(
        data=[
            go.Bar(name="Standard RAG", x=["This Query"], y=[std_latency], marker_color="#e74c3c"),
            go.Bar(name="GraphRAG",     x=["This Query"], y=[gr_latency],  marker_color="#2ecc71"),
        ]
    )
    fig.add_hline(y=2000, line_dash="dash", line_color="red",
                  annotation_text="2s target", annotation_position="bottom right")
    fig.update_layout(
        barmode="group",
        yaxis_title="Latency (ms)",
        title="Query Latency: Standard RAG vs GraphRAG",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ─── Why GraphRAG wins ────────────────────────────────────────────────────
    with st.expander("Why does GraphRAG outperform Standard RAG for this query type?"):
        from demos.impossible_queries import DEMO_QUERIES
        for demo in DEMO_QUERIES:
            if any(kw in query_input.lower() for kw in demo["query"].lower().split()[:4]):
                st.markdown(f"**Category:** `{demo['category']}`")
                st.markdown(f"**Why vector fails:** {demo['why_vector_fails']}")
                st.code(demo["graph_cypher"], language="cypher")
                break
        else:
            st.markdown(
                "Graph traversal provides verified, structured relationship data with "
                "explicit provenance. Vector search alone cannot guarantee multi-hop "
                "relationship correctness — it finds semantically similar text but "
                "cannot guarantee that the actual patient-drug-condition connections exist."
            )

# ─── Graph statistics sidebar ─────────────────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("Show Graph Statistics"):
    try:
        from src.graphrag.retrievers.graph_retriever import GraphRetriever
        gr = GraphRetriever()
        stats = gr.get_graph_statistics()
        gr.close()
        st.sidebar.markdown("**Node Counts:**")
        for label, count in stats["nodes"].items():
            st.sidebar.markdown(f"- {label}: {count}")
        st.sidebar.markdown("**Relationship Counts:**")
        for rel, count in stats["relationships"].items():
            st.sidebar.markdown(f"- {rel}: {count}")
    except Exception as e:
        st.sidebar.error(f"Neo4j error: {e}")
