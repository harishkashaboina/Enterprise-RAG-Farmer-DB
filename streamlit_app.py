import streamlit as st
import pandas as pd
import json
from dotenv import load_dotenv
load_dotenv()

from app.graph import GRAPH

st.set_page_config(
    page_title="Farmers Market RAG — Text to SQL",
    page_icon="🌽",
    layout="wide"
)

st.title("🌽 Farmers Market — Enterprise RAG (Text → SQL)")
st.caption("Powered by LangGraph · LangChain · Pinecone · Redis · MCP · LangSmith")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    # role = st.selectbox("User Role", ["viewer", "analyst", "admin"], index=1)
    show_pipeline = st.checkbox("Show Pipeline Steps", value=True)
    show_sql = st.checkbox("Show Generated SQL", value=True)
    st.divider()
    st.subheader("💡 Sample Queries")
    samples = [
        "Show me all product categories",
        "What is the total revenue per vendor?",
        "Which market dates had rain in 2022?",
        "Top 5 products by quantity sold",
        "List all vendors with booth assignments",
        "Average vendor sales per market season",
        "Show vendor inventory with prices",
        "How many customers per zip area?",
    ]
    for s in samples:
        if st.button(s, width='stretch'):
            st.session_state["query_input"] = s

# ── Main ───────────────────────────────────────────────────────────────────────



# user_input = st.text_area(
#     "Enter your natural language query",
#     value=st.session_state.get("query_input", ""),
#     height=100,
#     key="query_input"
# )
user_input = st.text_area("Query", key="query_input", height=150)


if st.button("🔍 Run Query", type="primary", width='stretch'):
    if not user_input.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("Processing pipeline..."):
            config = {"configurable": {"thread_id": "streamlit"}}
            state = {
                "user_query": user_input,
                # "role": role,
                "sanitized": {}, "guardrails": {}, "cache_hit": False,
                "rewritten": {}, "contexts": [], "reranked": [],
                "optimized_context": "", "generated": {}, "validated_sql": {},
                "db_result": {}, "final_response": {}, "error": None,
            }
            result = GRAPH.invoke(state, config)

        # ── error banner ──
        if result.get("error"):
            st.error(f"❌ Pipeline blocked: {result['error']}")
            if result.get("guardrails", {}).get("needs_human_approval"):
                st.warning("⚠️ This query requires human approval due to sensitive data access.")
        else:
            final = result.get("final_response", {})

            # cache hit badge
            if result.get("cache_hit"):
                st.success("⚡ Cache HIT — returned from Redis semantic cache")

            # results table
            if final.get("rows"):
                st.subheader(f"📊 Results ({final['row_count']} rows)")
                df = pd.DataFrame(final["rows"])
                st.dataframe(df, width='stretch')
                st.download_button("⬇️ Download CSV", df.to_csv(index=False), "results.csv", "text/csv")
            else:
                st.info("No rows returned.")

            # explanation
            if final.get("explanation"):
                st.info(f"💬 {final['explanation']}")

            # provenance
            st.caption(f"🔎 Provenance: {final.get('provenance', 'N/A')}")
            if final.get("redactions_applied", 0) > 0:
                st.caption(f"🔒 {final['redactions_applied']} PII field(s) redacted")

        # ── pipeline steps ──
        if show_pipeline:
            with st.expander("🔬 Pipeline Steps", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Sanitizer")
                    st.json(result.get("sanitized", {}))
                    st.subheader("Guardrails")
                    st.json(result.get("guardrails", {}))
                    st.subheader("Query Rewrite")
                    st.json(result.get("rewritten", {}))
                with col2:
                    st.subheader("Top Contexts (reranked)")
                    for i, ctx in enumerate(result.get("reranked", [])[:3]):
                        st.markdown(f"**[{i+1}] Score: {ctx.get('combined_score',0):.3f}** | {ctx.get('view_name','')}")
                        st.caption(ctx.get("text", "")[:200])

        if show_sql and not result.get("cache_hit"):
            with st.expander("🗄️ Generated SQL", expanded=False):
                gen = result.get("generated", {})
                if gen.get("sql"):
                    st.code(gen["sql"], language="sql")
                    st.json(gen.get("params", {}))
                    st.metric("Confidence", f"{gen.get('confidence', 0):.0%}")