import streamlit as st
import json
import _snowflake
from snowflake.snowpark.context import get_active_session
from typing import Optional
from streamlit_extras.stylable_container import stylable_container

session = get_active_session()

API_ENDPOINT = "/api/v2/cortex/agent:run"
API_TIMEOUT = 50000  # in milliseconds

CORTEX_SEARCH_DOCUMENTATION = "CORTEX_AGENTS.CORTEX_AGENTS_SALES.DOCS"
SEMANTIC_MODEL = "@CORTEX_AGENTS.CORTEX_AGENTS_SALES.Cortex_Analyst_Stage/CORTEX_AGENT_SALES.yaml"

def run_snowflake_query(query):
    try:
        df = session.sql(query.replace(';',''))
        
        return df

    except Exception as e:
        st.error(f"Error executing SQL: {str(e)}")
        return None, None

def analyze_query_intent(query: str, model: str = "claude-sonnet-4-5") -> dict:
    """Use LLM to intelligently analyze query and extract tool-specific sub-queries"""
    query_lower = query.lower()
    
    # Keywords that indicate FAQ/Policy search needs
    search_keywords = ['policy', 'procedure', 'how do i', 'how to', 'what is the process', 
                       'refund', 'return policy', 'shipping', 'warranty', 'faq', 'guidelines',
                       'rules', 'documentation', 'manual', 'instructions']
    
    # Keywords that indicate database query needs
    analyst_keywords = ['how many', 'count', 'total', 'number of', 'sum', 'average',
                        'orders', 'revenue', 'sales', 'metrics', 'statistics', 'data',
                        '2024', '2025', 'last year', 'this year', 'yesterday', 'today',
                        'last month', 'last week', 'quarter', 'ytd', 'amount', 'returned']
    
    needs_search = any(keyword in query_lower for keyword in search_keywords)
    needs_analyst = any(keyword in query_lower for keyword in analyst_keywords)
    
    # Extract relevant parts for each tool
    search_query = query
    analyst_query = query
    
    # If both tools are needed, use LLM to intelligently split the query
    if needs_search and needs_analyst:
        try:
            analysis_prompt = f"""Analyze this user query and split it into two parts:

User Query: "{query}"

Instructions:
1. SEARCH_QUERY: Extract ONLY the parts asking about policies, procedures, guidelines, or documentation (e.g., return policy, refund policy, shipping policy)
2. ANALYST_QUERY: Extract ONLY the parts asking for data, metrics, counts, or quantitative information from the database (e.g., order counts, amounts, revenue)

Rules:
- Each part should be a complete, standalone question
- If a part of the query needs both tools, include it in BOTH queries
- Preserve the original wording and intent
- Return ONLY valid JSON, no additional text

Return EXACTLY this JSON format:
{{
    "search_query": "the policy/documentation question",
    "analyst_query": "the data/metrics question"
}}"""

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": analysis_prompt}]}],
                "response_instruction": "Return only valid JSON with search_query and analyst_query fields. No markdown formatting."
            }
            
            resp = _snowflake.send_snow_api_request(
                "POST",
                API_ENDPOINT,
                {},
                {},  # No streaming for this simple analysis
                payload,
                None,
                API_TIMEOUT,
            )
            
            if resp["status"] == 200:
                response_content = json.loads(resp["content"])
                
                # Extract the text from the response
                llm_text = ""
                if isinstance(response_content, list):
                    for event in response_content:
                        if event.get('event') == "message.delta":
                            data = event.get('data', {})
                            delta = data.get('delta', {})
                            for content_item in delta.get('content', []):
                                if content_item.get('type') == 'text':
                                    llm_text += content_item.get('text', '')
                
                # Parse the JSON response from LLM
                # Remove markdown code blocks if present
                llm_text = llm_text.strip()
                if llm_text.startswith('```'):
                    llm_text = llm_text.split('```')[1]
                    if llm_text.startswith('json'):
                        llm_text = llm_text[4:]
                llm_text = llm_text.strip()
                
                parsed = json.loads(llm_text)
                search_query = parsed.get('search_query', query).strip()
                analyst_query = parsed.get('analyst_query', query).strip()
                
        except Exception as e:
            # If LLM analysis fails, fall back to original query for both
            pass
    
    return {
        'needs_search': needs_search,
        'needs_analyst': needs_analyst,
        'needs_both': needs_search and needs_analyst,
        'query': query,
        'search_query': search_query,
        'analyst_query': analyst_query
    }

def snowflake_api_call(query: str, model: str = "claude-sonnet-4-5", limit: int = 10, tool_filter: Optional[str] = None):
    """
    Make API call to Cortex Agent
    tool_filter: None (both tools), 'search_only', or 'analyst_only'
    """
    
    # Determine which tools to include based on filter
    tools_list = []
    tool_resources = {}
    response_instruction = ""
    
    if tool_filter == 'analyst_only':
        tools_list = [{"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "Sales Analyst"}}]
        tool_resources = {"Sales Analyst": {"semantic_model_file": SEMANTIC_MODEL}}
        response_instruction = """You have access to the Sales Analyst tool which can query the sales database. 
Use it to answer any questions about orders, sales data, revenue, or metrics. 
Extract the data-related parts of the question and query the database."""
    elif tool_filter == 'search_only':
        tools_list = [{"tool_spec": {"type": "cortex_search", "name": "Faq Search"}}]
        tool_resources = {
            "Faq Search": {
                "name": CORTEX_SEARCH_DOCUMENTATION,
                "max_results": 3,
                "title_column": "RELATIVE_PATH",
                "id_column": "CHUNK_INDEX",
                "experimental": {"returnConfidenceScores": True}
            }
        }
        response_instruction = """You have access to the Faq Search tool which searches through documentation and policy documents.
Use it to answer questions about policies, procedures, and guidelines.
Extract the policy-related parts of the question and search the documentation."""
    else:
        # Both tools (default)
        tools_list = [
            {"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "Sales Analyst"}},
            {"tool_spec": {"type": "cortex_search", "name": "Faq Search"}}
        ]
        tool_resources = {
            "Sales Analyst": {"semantic_model_file": SEMANTIC_MODEL},
            "Faq Search": {
                "name": CORTEX_SEARCH_DOCUMENTATION,
                "max_results": 3,
                "title_column": "RELATIVE_PATH",
                "id_column": "CHUNK_INDEX",
                "experimental": {"returnConfidenceScores": True}
            }
        }
        response_instruction = """Answer the user's question using the available tools. Be concise and direct."""
    
    payload = {
        "model": model,
        "messages": [{"role": "user",
                      "content": 
                          [{"type": "text","text": query}]}],
        
        "tools": tools_list,
        "tool_resources": tool_resources,
        "response_instruction": response_instruction
    }   
     
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",  # method
            API_ENDPOINT,  # path
            {},  # headers
            {'stream': True},  # query params
            payload,  # body
            None,  # request_guid
            API_TIMEOUT,  # timeout in milliseconds,
        )
        
        if resp["status"] != 200:
            st.error(f"❌ HTTP Error: {resp['status']} - {resp.get('reason', 'Unknown reason')}")
            st.error(f"Response details: {resp}")
            return None
        
        try:
            response_content = json.loads(resp["content"])
            # Only show raw response in debug mode when explicitly needed
            # (Removed automatic debug output for cleaner UI)
        except json.JSONDecodeError:
            st.error("❌ Failed to parse API response. The server may have returned an invalid JSON format.")
            return None

        return response_content
            
    except Exception as e:
        st.error(f"Error making request: {str(e)}")
        return None

def process_sse_response(response, debug_mode=True):
    """Process SSE response with enhanced multi-tool support"""
    text = ""
    sql = ""
    citations = []
    tools_called = []
    
    if not response:
        return text, sql, citations
    if isinstance(response, str):
        return text, sql, citations
    try:
        for event in response:
            # Removed verbose debug output for cleaner UI
            
            if event.get('event') == "message.delta":
                data = event.get('data', {})
                delta = data.get('delta', {})
                
                for content_item in delta.get('content', []):
                    content_type = content_item.get('type')
                    
                    # Track tool usage
                    if content_type == "tool_use":
                        # Extract tool name from the nested tool_use structure
                        tool_use_data = content_item.get('tool_use', {})
                        tool_type = tool_use_data.get('type', '')
                        
                        # Map the internal tool type to our friendly names
                        tool_name_map = {
                            'cortex_search': 'Faq Search',
                            'cortex_analyst_text_to_sql': 'Sales Analyst'
                        }
                        
                        tool_name = tool_name_map.get(tool_type, tool_type or 'Unknown')
                        tools_called.append(tool_name)
                        
                        # Show only clean tool indicator in debug mode
                        if debug_mode:
                            st.info(f"🔧 Calling tool: {tool_name}")
                    
                    if content_type == "tool_results":
                        tool_results = content_item.get('tool_results', {})
                        if 'content' in tool_results:
                            for result in tool_results['content']:
                                if result.get('type') == 'json':
                                    json_data = result.get('json', {})
                                    
                                    # Accumulate text from tool results
                                    result_text = json_data.get('text', '')
                                    if result_text:
                                        text += result_text
                                    
                                    # Process search results and citations
                                    search_results = json_data.get('searchResults', [])
                                    for search_result in search_results:
                                        citations.append({'source_id': search_result.get('source_id', ''), 
                                                          'doc_title': search_result.get('doc_title', ''),
                                                          'doc_chunk': search_result.get('doc_id')})
                                    
                                    # Accumulate SQL queries (keep the last non-empty one)
                                    result_sql = json_data.get('sql', '')
                                    if result_sql:
                                        sql = result_sql
                    
                    if content_type == 'text':
                        text += content_item.get('text', '')
        
        # Show only summary in debug mode (removed verbose tool tracking)
        if debug_mode and tools_called:
            unique_tools = set(tools_called)
            if 'Faq Search' in unique_tools and 'Sales Analyst' in unique_tools:
                st.success("✅ Both tools used")
            elif len(unique_tools) > 0:
                st.info(f"📊 Used: {', '.join(unique_tools)}")
                            
    except json.JSONDecodeError as e:
        st.error(f"Error processing events: {str(e)}")
                
    except Exception as e:
        st.error(f"Error processing events: {str(e)}")
        
    return text, sql, citations

def display_citations(citations):

    for citation in citations:
        source_id = citation.get("source_id", "")
        doc_title = citation.get("doc_title", "")
        doc_chunk = citation.get("doc_chunk", "")
    
        if (doc_title.lower().endswith("jpeg")):
            query = f"SELECT GET_PRESIGNED_URL('@DOCS', '{doc_title}') as URL"
            result = run_snowflake_query(query)
            result_df = result.to_pandas()
            if not result_df.empty:
                url = result_df.iloc[0, 0]
            else:
                url = "No URL available"
    
            with st.expander(f"[{source_id}]"):
                st.image(url)

        if (doc_title.lower().endswith("pdf")):
            query = f"""
                    SELECT CHUNK from DOCS_CHUNKS_TABLE
                    WHERE RELATIVE_PATH = '{doc_title}' AND
                          CHUNK_INDEX = {doc_chunk}
            """
            result = run_snowflake_query(query)
            result_df = result.to_pandas()
            if not result_df.empty:
                text = result_df.iloc[0, 0]
            else:
                text = "No text available"

            with st.expander(f"[{source_id}]"):
                with stylable_container(
                        f"[{source_id}]",
                        css_styles="""
                        {
                            border: 1px solid #e0e7ff;
                            border-radius: 8px;
                            padding: 14px;
                            margin-bottom: 12px;
                            background-color: #f5f8ff;
                        }
                        """
                    ):
                    st.markdown(text)

def main():
    st.title("Intelligent Sales Assistant")
    
    # Display current model at the top
    current_model = st.session_state.get('selected_model', 'claude-sonnet-4-5')
    st.caption(f"🤖 Using model: **{current_model}**")

    # Sidebar for new chat and debug mode
    with st.sidebar:
        st.markdown("### Controls")
        if st.button("New Conversation", key="new_chat"):
            st.session_state.messages = []
            st.rerun()
        
        debug_mode = st.checkbox("Debug Mode", value=False, help="Show which tools are being called")
        
        st.markdown("---")
        st.markdown("### Orchestration Mode")
        orchestration_mode = st.radio(
            "Choose Mode",
            options=["Client-Side (Reliable)", "LLM-Based (Experimental)"],
            index=0,
            help="Client-Side: App decides which tools to call (100% reliable)\nLLM-Based: Model decides which tools to call (may fail)"
        )
        
        st.markdown("---")
        st.markdown("### Model Selection")
        model_choice = st.selectbox(
            "Choose LLM Model",
            options=[
                "claude-sonnet-4-5",
                "claude-3-7-sonnet", 
                "claude-3-5-sonnet"
            ],
            index=0,
            help="Claude Sonnet 4.5 is recommended"
        )
        
        st.markdown("---")
        st.markdown("### Available Tools")
        st.markdown("🔍 **Faq Search**: Policy & procedure information from documents")
        st.markdown("📊 **Sales Analyst**: Quantitative data from sales database")
        
    # Store settings in session state
    st.session_state.debug_mode = debug_mode
    st.session_state.selected_model = model_choice
    st.session_state.orchestration_mode = orchestration_mode

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'].replace("•", "\n\n"))

    if query := st.chat_input("Would you like to learn?"):
        # Add user message to chat
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Get response from API
        with st.spinner("Processing your request..."):
            selected_model = st.session_state.get('selected_model', 'claude-sonnet-4-5')
            orchestration_mode = st.session_state.get('orchestration_mode', 'Client-Side (Reliable)')
            debug_mode = st.session_state.get('debug_mode', False)  # Fixed: was True, should match checkbox default
            
            if orchestration_mode == "Client-Side (Reliable)":
                # Client-side orchestration: We decide which tools to call
                intent = analyze_query_intent(query, model=selected_model)
                
                # Removed verbose query analysis output
                
                all_text = ""
                all_sql = ""
                all_citations = []
                
                if intent['needs_both']:
                    # Call both tools separately with extracted query parts
                    if debug_mode:
                        st.info("🎯 Fetching policy information and data analytics...")
                        st.info(f"🔍 Search query: '{intent['search_query']}'")
                        st.info(f"📊 Analyst query: '{intent['analyst_query']}'")
                    
                    # Call Faq Search with extracted search-relevant part
                    search_response = snowflake_api_call(intent['search_query'], model=selected_model, tool_filter='search_only')
                    if search_response:
                        search_text, _, search_citations = process_sse_response(search_response, False)
                    else:
                        search_text, search_citations = "", []
                    
                    # Call Sales Analyst with extracted data-relevant part
                    analyst_response = snowflake_api_call(intent['analyst_query'], model=selected_model, tool_filter='analyst_only')
                    if analyst_response:
                        analyst_text, analyst_sql, _ = process_sse_response(analyst_response, False)
                    else:
                        analyst_text, analyst_sql = "", ""
                    
                    if debug_mode and analyst_response:
                        # Show if analyst actually returned something
                        if analyst_text.strip():
                            st.info(f"✅ Analyst returned: {len(analyst_text)} characters")
                        else:
                            st.warning("⚠️ Analyst returned empty response")
                    
                    # Combine results intelligently
                    combined_parts = []
                    if search_text.strip():
                        combined_parts.append(search_text.strip())
                    if analyst_text.strip():
                        combined_parts.append(analyst_text.strip())
                    
                    all_text = "\n\n".join(combined_parts) if combined_parts else "No response generated."
                    all_sql = analyst_sql
                    all_citations = search_citations
                    
                    if debug_mode:
                        st.success("✅ Retrieved information from both sources")
                    
                elif intent['needs_search']:
                    # Only Faq Search needed
                    if debug_mode:
                        st.info("🔍 Searching documentation...")
                    response = snowflake_api_call(query, model=selected_model, tool_filter='search_only')
                    all_text, all_sql, all_citations = process_sse_response(response, False)
                    
                elif intent['needs_analyst']:
                    # Only Sales Analyst needed
                    if debug_mode:
                        st.info("📊 Analyzing sales data...")
                    response = snowflake_api_call(query, model=selected_model, tool_filter='analyst_only')
                    all_text, all_sql, all_citations = process_sse_response(response, False)
                    
                else:
                    # General query - let LLM decide (both tools available)
                    response = snowflake_api_call(query, model=selected_model)
                    all_text, all_sql, all_citations = process_sse_response(response, debug_mode)
                
                text, sql, citations = all_text, all_sql, all_citations
                
            else:
                # LLM-based orchestration: Let the model decide (original behavior)
                if debug_mode:
                    st.info("🤖 Processing with AI model...")
                response = snowflake_api_call(query, model=selected_model)
                text, sql, citations = process_sse_response(response, debug_mode)
            
            # Add assistant response to chat
            if text:
                text = text.replace("【†", "[")
                text = text.replace("†】", "]")
                st.session_state.messages.append({"role": "assistant", "content": text})
                
                with st.chat_message("assistant"):
                    st.markdown(text.replace("•", "\n\n"))
                    if citations:
                        display_citations(citations)
    
            # Display SQL if present
            if sql:
                st.markdown("### Generated SQL")
                st.code(sql, language="sql")
                sales_results = run_snowflake_query(sql)
                if sales_results:
                    st.write("### Sales Metrics Report")
                    st.dataframe(sales_results)

if __name__ == "__main__":
    main()