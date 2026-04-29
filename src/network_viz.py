import numpy as np
import networkx as nx
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from typing import Dict, List, Tuple, Any, Optional
from loguru import logger

_CLUSTER_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860"]


def _parse_sender_name(sender: str) -> str:
    if "<" in sender:
        name = sender.split("<")[0].strip().strip('"').strip("'")
        return name if name else sender.split("<")[1].split("@")[0]
    return sender.split("@")[0] if "@" in sender else sender


def _hex_to_rgba(hex_color: str, alpha: float = 0.55) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def build_and_render_network(
    sender_docs: Dict[str, List[Dict[str, Any]]],
    tfidf_keywords: Dict[str, List[Tuple[str, float]]],
    sender_sim_threshold: float = 0.35,
    pdf_sim_threshold: float = 0.50,
) -> Optional[go.Figure]:
    """
    sender_docs : {sender_str: [{file, text, email_subject, email_date}, ...]}
    tfidf_keywords : {doc_key: [(word, score), ...]}  — extract_tfidf_keywords 결과
    """
    from src.embedder import embed_texts, cosine_sim_matrix

    senders = list(sender_docs.keys())
    if not senders:
        return None

    # PDF 목록 평탄화
    pdf_info: List[Dict] = []
    for sender in senders:
        for doc in sender_docs[sender]:
            pdf_info.append({"sender": sender, **doc})

    if not pdf_info:
        return None

    # --- 임베딩 계산 ---
    logger.info(f"PDF {len(pdf_info)}개 임베딩 계산 중...")
    pdf_vecs = embed_texts([p["text"] for p in pdf_info])
    pdf_sim = cosine_sim_matrix(pdf_vecs)

    # 발신자 임베딩 = 해당 발신자의 PDF 벡터 평균
    sender_vecs = np.array([
        pdf_vecs[[i for i, p in enumerate(pdf_info) if p["sender"] == s]].mean(axis=0)
        for s in senders
    ])
    sender_sim = cosine_sim_matrix(sender_vecs)

    # --- 발신자 클러스터링 ---
    n_clusters = max(1, min(len(senders), len(_CLUSTER_COLORS)))
    if n_clusters > 1:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        cluster_ids = kmeans.fit_predict(sender_vecs).tolist()
    else:
        cluster_ids = [0] * len(senders)

    # --- 그래프 구성 ---
    G = nx.Graph()

    for i, sender in enumerate(senders):
        G.add_node(f"s_{i}", ntype="sender", label=_parse_sender_name(sender),
                   full=sender, count=len(sender_docs[sender]), cluster=cluster_ids[i])

    for j, p in enumerate(pdf_info):
        si = senders.index(p["sender"])
        doc_key = f"{p['email_subject'][:25]} / {p['file']}"
        kws = ", ".join(w for w, _ in tfidf_keywords.get(doc_key, [])[:5]) or "—"
        G.add_node(f"p_{j}", ntype="pdf", label=p["file"][:18], full=p["file"],
                   sender=_parse_sender_name(p["sender"]),
                   date=p.get("email_date", ""), keywords=kws, cluster=cluster_ids[si])
        G.add_edge(f"s_{si}", f"p_{j}", etype="sent")

    for i in range(len(senders)):
        for j in range(i + 1, len(senders)):
            sim = float(sender_sim[i, j])
            if sim >= sender_sim_threshold:
                G.add_edge(f"s_{i}", f"s_{j}", etype="sender_sim", sim=round(sim, 2))

    for i in range(len(pdf_info)):
        for j in range(i + 1, len(pdf_info)):
            if pdf_info[i]["sender"] == pdf_info[j]["sender"]:
                continue
            sim = float(pdf_sim[i, j])
            if sim >= pdf_sim_threshold:
                G.add_edge(f"p_{i}", f"p_{j}", etype="pdf_sim", sim=round(sim, 2))

    # --- 레이아웃 ---
    pos = nx.spring_layout(G, k=2.2, iterations=100, seed=42)

    # --- Plotly 트레이스 ---
    traces: List[go.BaseTraceType] = []

    def _batch_edges(etype: str):
        xs, ys = [], []
        for u, v, d in G.edges(data=True):
            if d.get("etype") != etype:
                continue
            x0, y0 = pos[u]; x1, y1 = pos[v]
            xs += [x0, x1, None]; ys += [y0, y1, None]
        return xs, ys

    # 실선: 첨부 관계
    ex, ey = _batch_edges("sent")
    if ex:
        traces.append(go.Scatter(x=ex, y=ey, mode="lines",
                                 line=dict(color="#C0C0C0", width=1.5),
                                 hoverinfo="none", name="첨부 관계"))

    # 점선: 발신자 유사
    ex, ey = _batch_edges("sender_sim")
    if ex:
        traces.append(go.Scatter(x=ex, y=ey, mode="lines",
                                 line=dict(color="#E8735A", width=2.5, dash="dash"),
                                 hoverinfo="none", name="발신자 유사"))

    # 점선: 문서 유사
    ex, ey = _batch_edges("pdf_sim")
    if ex:
        traces.append(go.Scatter(x=ex, y=ey, mode="lines",
                                 line=dict(color="#7DB8D8", width=1.5, dash="dot"),
                                 hoverinfo="none", name="문서 유사"))

    # 엣지 중간점 — 유사도 수치 항상 표시 + hover 상세 정보
    sx, sy, stxt, shtml = [], [], [], []  # sender_sim
    px, py, ptxt, phtml = [], [], [], []  # pdf_sim
    for u, v, d in G.edges(data=True):
        if d.get("etype") not in ("sender_sim", "pdf_sim"):
            continue
        x0, y0 = pos[u]; x1, y1 = pos[v]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if d["etype"] == "sender_sim":
            n1 = G.nodes[u]["label"]; n2 = G.nodes[v]["label"]
            sx.append(mx); sy.append(my)
            stxt.append(f"{d['sim']:.2f}")
            shtml.append(f"<b>{n1} ↔ {n2}</b><br>유사도: {d['sim']:.2f}")
        else:
            f1 = G.nodes[u]["full"]; f2 = G.nodes[v]["full"]
            px.append(mx); py.append(my)
            ptxt.append(f"{d['sim']:.2f}")
            phtml.append(f"<b>{f1}</b><br>↕ {f2}<br>유사도: {d['sim']:.2f}")
    if sx:
        traces.append(go.Scatter(
            x=sx, y=sy, mode="markers+text",
            marker=dict(size=22, color="rgba(232,115,90,0.18)", line=dict(color="#E8735A", width=1.2)),
            text=stxt, textposition="middle center",
            textfont=dict(size=10, color="#C0392B", family="Arial Black"),
            hoverinfo="text", hovertext=shtml, showlegend=False,
        ))
    if px:
        traces.append(go.Scatter(
            x=px, y=py, mode="markers+text",
            marker=dict(size=22, color="rgba(125,184,216,0.18)", line=dict(color="#7DB8D8", width=1.0)),
            text=ptxt, textposition="middle center",
            textfont=dict(size=9, color="#2471A3", family="Arial Black"),
            hoverinfo="text", hovertext=phtml, showlegend=False,
        ))

    # 노드: 발신자 (클러스터별 색)
    for cid in range(n_clusters):
        color = _CLUSTER_COLORS[cid % len(_CLUSTER_COLORS)]
        nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("ntype") == "sender" and d.get("cluster") == cid]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n, _ in nodes],
            y=[pos[n][1] for n, _ in nodes],
            mode="markers+text",
            marker=dict(symbol="circle", size=32, color=color,
                        line=dict(color="white", width=2.5)),
            text=[d["label"] for _, d in nodes],
            textposition="top center",
            textfont=dict(size=11, color="#111111"),
            hoverinfo="text",
            hovertext=[f"<b>{d['label']}</b><br>{d['full']}<br>첨부 PDF: {d['count']}개"
                       for _, d in nodes],
            name=f"발신자 그룹 {cid + 1}",
        ))

    # 노드: PDF (발신자보다 연하게, 사각형)
    for cid in range(n_clusters):
        color = _CLUSTER_COLORS[cid % len(_CLUSTER_COLORS)]
        nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("ntype") == "pdf" and d.get("cluster") == cid]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n, _ in nodes],
            y=[pos[n][1] for n, _ in nodes],
            mode="markers+text",
            marker=dict(symbol="square", size=20, color=_hex_to_rgba(color, 0.55),
                        line=dict(color=color, width=1.5)),
            text=[d["label"] for _, d in nodes],
            textposition="bottom center",
            textfont=dict(size=9, color="#555555"),
            hoverinfo="text",
            hovertext=[
                f"<b>📄 {d['full']}</b><br>발신: {d['sender']}<br>"
                f"날짜: {d['date']}<br>핵심어: {d['keywords']}"
                for _, d in nodes
            ],
            name=f"PDF 그룹 {cid + 1}",
            showlegend=False,
        ))

    return go.Figure(
        data=traces,
        layout=go.Layout(
            title=dict(text="🕸️ 업무 관계 네트워크  ●발신자  ■PDF", font=dict(size=15)),
            showlegend=True,
            hovermode="closest",
            dragmode="pan",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#F8F9FA",
            paper_bgcolor="white",
            height=640,
            margin=dict(l=10, r=10, t=55, b=10),
            legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)",
                        bordercolor="#DDDDDD", borderwidth=1),
        ),
    )
