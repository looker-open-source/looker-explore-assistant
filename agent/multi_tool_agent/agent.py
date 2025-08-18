from google.adk.agents import Agent
import requests
import os
from typing import Optional

MCP_SERVER_URL = "https://mcp-server-730192175971.us-central1.run.app/"

def _call_mcp(tool_name: str, arguments: dict) -> dict:
    """Internal helper to call the MCP server with the given tool_name and arguments."""
    url = MCP_SERVER_URL
    payload = {"tool_name": tool_name, "arguments": arguments}
    headers = {"Content-Type": "application/json"}
    try:
        import google.auth.transport.requests as greq
        import google.auth
        creds, _ = google.auth.default()
        auth_req = greq.Request()
        creds.refresh(auth_req)
        id_token = creds.id_token
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"
    except Exception:
        pass
    response = requests.post(url, json=payload, headers=headers)
    try:
        return response.json()
    except Exception:
        return {"error": f"Non-JSON response: {response.text}"}

# Explicit wrappers for each MCP tool (matching server tool names)
def generate_explore_params(prompt: str, restricted_explore_keys: list, conversation_context: Optional[dict] = None) -> dict:
    """Generate Looker explore parameters from a prompt and restricted explores."""
    args = {"prompt": prompt, "restricted_explore_keys": restricted_explore_keys}
    if conversation_context is not None:
        args["conversation_context"] = conversation_context
    return _call_mcp("generate_explore_params", args)

def semantic_field_search(search_terms: list, explore_ids: Optional[list] = None, limit_per_term: int = 5) -> dict:
    """Find indexed fields containing specific values/codes."""
    args = {"search_terms": search_terms, "limit_per_term": limit_per_term}
    if explore_ids is not None:
        args["explore_ids"] = explore_ids
    return _call_mcp("semantic_field_search", args)

def field_value_lookup(search_string: str, field_location: Optional[str] = None, limit: int = 10) -> dict:
    """Find specific dimension values in indexed fields."""
    args = {"search_string": search_string, "limit": limit}
    if field_location is not None:
        args["field_location"] = field_location
    return _call_mcp("field_value_lookup", args)

def extract_searchable_terms(query_text: str) -> dict:
    """Extract searchable terms from natural language."""
    args = {"query_text": query_text}
    return _call_mcp("extract_searchable_terms", args)

def run_looker_query(query_body: dict, result_format: str = "json") -> dict:
    """Run a Looker query and return results."""
    args = {"query_body": query_body, "result_format": result_format}
    return _call_mcp("run_looker_query", args)

def get_explore_fields(model_name: str, explore_name: str) -> dict:
    """Get field metadata for a Looker explore."""
    args = {"model_name": model_name, "explore_name": explore_name}
    return _call_mcp("get_explore_fields", args)

def add_bronze_query(explore_id: str, input: str, output: str, link: str, user_email: str, query_run_count: int = 1) -> dict:
    """Add a bronze query for Olympic training."""
    args = {"explore_id": explore_id, "input": input, "output": output, "link": link, "user_email": user_email, "query_run_count": query_run_count}
    return _call_mcp("add_bronze_query", args)

def add_silver_query(explore_id: str, input: str, output: str, link: str, user_id: str, feedback_type: str, conversation_history: Optional[str] = None) -> dict:
    """Add a silver query for Olympic training."""
    args = {"explore_id": explore_id, "input": input, "output": output, "link": link, "user_id": user_id, "feedback_type": feedback_type}
    if conversation_history is not None:
        args["conversation_history"] = conversation_history
    return _call_mcp("add_silver_query", args)

def promote_to_gold(query_id: str, promoted_by: str) -> dict:
    """Promote a query to gold rank."""
    args = {"query_id": query_id, "promoted_by": promoted_by}
    return _call_mcp("promote_to_gold", args)

def get_gold_queries(explore_id: Optional[str] = None, limit: int = 50) -> dict:
    """Get golden queries for training."""
    args = {"limit": limit}
    if explore_id is not None:
        args["explore_id"] = explore_id
    return _call_mcp("get_gold_queries", args)

# Register all wrappers as tools for the agent
root_agent = Agent(
    name="looker_mcp_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions using the Looker MCP server (vector search, explore selection, parameter generation, etc.)",
    instruction="I can answer your questions about Looker data using the MCP server. Available tools: generate_explore_params, semantic_field_search, field_value_lookup, extract_searchable_terms, run_looker_query, get_explore_fields, add_bronze_query, add_silver_query, promote_to_gold, get_gold_queries.",
    tools=[
        generate_explore_params,
        semantic_field_search,
        field_value_lookup,
        extract_searchable_terms,
        run_looker_query,
        get_explore_fields,
        add_bronze_query,
        add_silver_query,
        promote_to_gold,
        get_gold_queries
    ]
)