from typing_extensions import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from app.sanitizer import sanitize_input
from app.input_guardrail import check_guardrails
from app.cache import get_cached_result, set_cached_result
from app.retriever import retrieve_context
from app.context_manager import validate_optimize_contexts
from app.sql_generator import generate_sql
from app.sql_validator import validate_sql
from app.db_executor import execute_sql
from app.output_guardrails import apply_output_guardrails
from app.query_rewriter import rewrite_query

# ── State ─────────────────────────────────────────────────────────────────────
class RAGState(TypedDict):
    # input
    user_query: str
    role: str
    # pipeline stages
    sanitized: Dict[str, Any]
    guardrails: Dict[str, Any]
    cache_hit: bool
    rewritten: Dict[str, Any]
    contexts: List[Dict[str, Any]]
    # reranked: List[Dict[str, Any]]
    optimized_context: str
    generated: Dict[str, Any]
    validated_sql: Dict[str, Any]
    db_result: Dict[str, Any]
    final_response: Dict[str, Any]
    rewrite_attempts: int
    error: Optional[str]


# ── Nodes ─────────────────────────────────────────────────────────────────────
@traceable(name="sanitize_node")
def sanitize_node(state: RAGState) -> RAGState:
    result = sanitize_input(state["user_query"])
    state["sanitized"] = result
    if not result["ok"]:
        state["error"] = result.get("error", "Sanitization failed")
    return state


@traceable(name="guardrail_node")
def guardrail_node(state: RAGState) -> RAGState:

    if not state["sanitized"].get("ok", False):
        state["error"] = "Input not sanitized"
        return state
    else:
        result = check_guardrails(state["sanitized"].get("text", ""))
        state["guardrails"] = result
        if not result["ok"]:
            state["error"] = result.get("error", "Guardrail check failed")
        return state

@traceable(name="cache_check_node")
def cache_check_node(state: RAGState) -> RAGState:
    if state.get("error"):
        return state
    cached = get_cached_result(state["sanitized"]["query_hash"])
    if cached:
        state["cache_hit"] = True
        state["final_response"] = cached
    else:
        state["cache_hit"] = False
    #print(state)
    return state

@traceable(name="context_retrieval_node")
def context_retrieval_node(state: RAGState) -> RAGState:

    if state.get("error") or state.get("cache_hit"):
        return state
    query = state["sanitized"]["text"]
    contexts = retrieve_context(query, top_k=25)
    state["contexts"] = contexts
    #print('context', state)
    return state

@traceable(name="context_optimize_node")
def context_optimize_node(state: RAGState) -> RAGState:
    if state.get("error") or state.get("cache_hit"):
        return state
    validated = validate_optimize_contexts(state["contexts"], state["sanitized"]["text"])
    state["optimized_context"] = validated
    #print('optimized_context', state)
    return state

@traceable(name="generate_sql_node")
def generate_sql_node(state: RAGState) -> RAGState:
    if state.get("error") or state.get("cache_hit"):
        return state
    query = state["sanitized"]["text"]
    state["generated"] = generate_sql(query, state["optimized_context"])
    #print('sql_generator', state["generated"])
    return state

@traceable(name="validate_sql_node")
def validate_sql_node(state: RAGState) -> RAGState:
    if state.get("error") or state.get("cache_hit"):
        return state
    result = validate_sql(state["generated"]["sql"], state["generated"].get("params"))
    state["validated_sql"] = result
    if not result["ok"]:
        state["error"] = " | ".join(result["issues"])
    #print('validate_sql', state["validated_sql"])
    return state


@traceable(name="execute_sql_node")
def execute_sql_node(state: RAGState) -> RAGState:
    if state.get("error") or state.get("cache_hit"):
        return state
    sql = state["validated_sql"]["sql"]
    params = state["generated"].get("params", {})
    state["db_result"] = execute_sql(sql, params)
    if state["db_result"].get("error"):
        state["error"] = state["db_result"]["error"]

    #print('DB Result:', state["db_result"])
    return state


@traceable(name="output_guardrails_node")
def output_guardrails_node(state: RAGState) -> RAGState:
    if state.get("cache_hit"):
        return state
    if state.get("error"):
        state["final_response"] = {"error": state["error"], "rows": [], "row_count": 0}
        return state
    rows = state["db_result"].get("rows", [])
    sql = state["validated_sql"].get("sql", "")
    explanation = state["generated"].get("explanation", "")
    response = apply_output_guardrails(rows, sql, explanation)
    state["final_response"] = response
    # cache result
    set_cached_result(state["sanitized"]["query_hash"], response)
    #print('out_put:', state)
    return state

@traceable(name="rewrite_node")
def rewrite_node(state: RAGState) -> RAGState:
    if state.get("cache_hit"):
        return state

    attempts = state.get("rewrite_attempts", 0)
    if attempts >= 2:
        state["error"] = "Query rewrite failed after 2 attempts. Please revise your query."
        return state

    result = rewrite_query(state["sanitized"]["text"], state["error"], state["optimized_context"])
    state["rewritten"] = result
    state["rewrite_attempts"] = attempts + 1

    rewritten_query = result.get("rewritten_query")
    if rewritten_query:
        state["sanitized"]["text"] = rewritten_query
        state["error"] = None
    else:
        state["error"] = "Query rewrite failed to produce a usable rewritten query."

    return state

# ── Router ────────────────────────────────────────────────────────────────────
def should_stop_cache(state: RAGState) -> str:
    if state.get("cache_hit"):
        return "output_guardrails"
    return "context_retrieval"

def should_stop_db(state: RAGState) -> str:
    if state.get("error"):
        if state.get("rewrite_attempts", 0) >= 2:
            return "output_guardrails"
        return "rewrite"
    return "output_guardrails"

# ── Build graph ───────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    g = StateGraph(RAGState)

    # g.add_node(START, "start")
    g.add_node("sanitize",         sanitize_node)
    g.add_node("input_guardrail", guardrail_node)
    g.add_node("cache_check",     cache_check_node)
    g.add_node("context_retrieval", context_retrieval_node)
    g.add_node("context_optimize", context_optimize_node)
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("execute_sql", execute_sql_node)
    g.add_node("output_guardrails", output_guardrails_node)
    g.add_node("rewrite", rewrite_node) 

    g.set_entry_point("sanitize")
    g.add_edge("sanitize", "input_guardrail")
    g.add_edge("input_guardrail", "cache_check")
    g.add_conditional_edges("cache_check", should_stop_cache, {
        "output_guardrails": "output_guardrails",
        "context_retrieval": "context_retrieval",
    })
    # g.add_edge("cache_check", "context_retrieval")
    g.add_edge("context_retrieval", "context_optimize")
    g.add_edge("context_optimize", "generate_sql")

    g.add_edge("rewrite", "generate_sql")

    g.add_edge("generate_sql", "validate_sql")
    g.add_edge("validate_sql", "execute_sql")
    g.add_conditional_edges("execute_sql", should_stop_db, {
        "rewrite": "rewrite",
        "output_guardrails": "output_guardrails",
    })
    # g.add_edge("execute_sql", "output_guardrails")
    g.add_edge("output_guardrails", END)

    return g.compile(checkpointer=MemorySaver())

GRAPH = build_graph()