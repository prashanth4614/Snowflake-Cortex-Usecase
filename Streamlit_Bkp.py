import streamlit as st
import json
import _snowflake
from snowflake.snowpark.context import get_active_session
#from typing import Dict, List, Any, Optional, Tuple, Union
from streamlit_extras.stylable_container import stylable_container

session = get_active_session()

API_ENDPOINT = "/api/v2/cortex/agent:run"
API_TIMEOUT = 50000  # in milliseconds

CORTEX_SEARCH_DOCUMENTATION = "CORTEX_AGENTS.SALES.DOCS"
SEMANTIC_MODEL = "@CORTEX_AGENTS.SALES.Cortex_Analyst_Stage/CORTEX_AGENT_SALES.yaml"

def run_snowflake_query(query):
    try:
        df = session.sql(query.replace(';',''))
        
        return df

    except Exception as e:
        st.error(f"Error executing SQL: {str(e)}")
        return None, None

def snowflake_api_call(query: str, model: str = "claude-sonnet-4-5", limit: int = 10):
    
    payload = {
        "model": model,  # Now uses the selected model from UI
        "messages": [{"role": "user",
                      "content": 
                          [{"type": "text","text": query}]}],
        
        ##############  MAKE CHANGES HERE for your own services/yamls ##############
        "tools": [
            {"tool_spec": 
                {"type": "cortex_analyst_text_to_sql",
                 "name": "Sales Analyst"}},
            
            {"tool_spec": 
                {"type": "cortex_search",
                 "name": "Faq Search"}},

             
        ],
        "tool_resources": {
            "Sales Analyst": 
                {"semantic_model_file": SEMANTIC_MODEL},
             "Faq Search": 
                 {"name": CORTEX_SEARCH_DOCUMENTATION, 
                  "max_results": 3, 
                  "title_column":"RELATIVE_PATH",
                  "id_column": "CHUNK_INDEX",
                  "experimental": {"returnConfidenceScores": True}},
          },
        "response_instruction": """SYSTEM DIRECTIVE: You have exactly TWO tools available. You MUST use ALL relevant tools for EVERY query.

TOOL 1: cortex_search (FAQ/Policy Search)
- Use for: policies, procedures, FAQs, documentation questions
- CANNOT access database

TOOL 2: cortex_analyst_text_to_sql (Database Query)
- Use for: numbers, counts, metrics, analytics, quantitative data
- CANNOT read documents

ABSOLUTE REQUIREMENTS:
1. When user asks for data/numbers/counts → IMMEDIATELY call cortex_analyst_text_to_sql
2. When user asks for policy/procedure → IMMEDIATELY call cortex_search
3. When BOTH are needed → CALL BOTH TOOLS IN THE SAME RESPONSE
4. NEVER say "would you like me to call X tool" - JUST CALL IT
5. NEVER say "this requires Y tool" - JUST USE THE TOOL
6. Do NOT ask permission - USE THE TOOLS AUTOMATICALLY

PATTERN DETECTION:
If you see words like: count, how many, total, average, sum, statistics, metrics, revenue
→ This REQUIRES cortex_analyst_text_to_sql - call it NOW

If you see words like: policy, procedure, FAQ, how do I, what is the process
→ This REQUIRES cortex_search - call it NOW

COMPOUND QUERY PROTOCOL:
Query: "What is X policy and how many Y?"
REQUIRED ACTIONS (execute BOTH immediately):
1. Call cortex_search for policy
2. Call cortex_analyst_text_to_sql for count
3. Combine results

FORBIDDEN BEHAVIORS:
❌ "I cannot provide order count without Sales Analyst tool"
✅ [Just call cortex_analyst_text_to_sql and provide the result]

❌ "Would you like me to get that data?"
✅ [Call the tool and show the data]

❌ Calling only one tool when two are needed
✅ Call both tools in same response

EXECUTE TOOLS FIRST, EXPLAIN LATER. No asking, no suggesting, no deferring."""
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
            if st.session_state.get('debug_mode', True):
                st.write("Debug - API Response structure:", response_content)
        except json.JSONDecodeError:
            st.error("❌ Failed to parse API response. The server may have returned an invalid JSON format.")
            st.error(f"Raw response: {resp['content'][:200]}...")
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
            # Only show critical debug info to avoid flooding
            if debug_mode and event.get('event') == "message.delta":
                data = event.get('data', {})
                delta = data.get('delta', {})
                content_items = delta.get('content', [])
                if content_items:
                    for item in content_items:
                        if item.get('type') in ['tool_use', 'tool_results']:
                            st.write(f"Debug - Event type: {item.get('type')}, Content: {item}")
            
            if event.get('event') == "message.delta":
                data = event.get('data', {})
                delta = data.get('delta', {})
                
                for content_item in delta.get('content', []):
                    content_type = content_item.get('type')
                    
                    # Track tool usage - try multiple possible locations for tool name
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
                        if debug_mode:
                            st.info(f"🔧 Calling tool: {tool_name} (type: {tool_type})")
                            # Debug: show the full content_item structure
                            st.write("Debug - Tool use content:", content_item)
                    
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
                                        if debug_mode:
                                            st.success(f"✅ SQL query generated by Sales Analyst")
                    
                    if content_type == 'text':
                        text += content_item.get('text', '')
        
        # Debug information
        if debug_mode:
            if tools_called:
                st.info(f"📊 Tools used in this response: {', '.join(set(tools_called))}")
                
                # Validate that expected tools were called
                unique_tools = set(tools_called)
                if 'Faq Search' in unique_tools and 'Sales Analyst' not in unique_tools:
                    st.warning("⚠️ Warning: Only Faq Search was called. If the query included data questions, Sales Analyst should have been called too.")
                elif 'Sales Analyst' in unique_tools and 'Faq Search' not in unique_tools:
                    st.info("ℹ️ Only Sales Analyst was called (data query)")
                elif 'Faq Search' in unique_tools and 'Sales Analyst' in unique_tools:
                    st.success("✅ Both tools were called successfully!")
            else:
                st.warning("⚠️ No tools were called for this query")
                            
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
        
        debug_mode = st.checkbox("Debug Mode", value=True, help="Show which tools are being called")
        
        st.markdown("---")
        st.markdown("### Model Selection")
        model_choice = st.selectbox(
            "Choose LLM Model",
            options=[
                "claude-sonnet-4-5",
                "claude-3-7-sonnet", 
                "claude-3-5-sonnet",
                "openai-gpt-4.1"
            ],
            index=0,  # Default to Claude Sonnet 4.5 (best for multi-tool)
            help="Claude Sonnet 4.5 is recommended for multi-tool orchestration"
        )
        
        st.markdown("---")
        st.markdown("### Available Tools")
        st.markdown("🔍 **Faq Search**: Policy & procedure information from documents")
        st.markdown("📊 **Sales Analyst**: Quantitative data from sales database")
        
    # Store debug mode in session state
    st.session_state.debug_mode = debug_mode
    st.session_state.selected_model = model_choice

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
            response = snowflake_api_call(query, model=selected_model)
            text, sql, citations = process_sse_response(response, st.session_state.get('debug_mode', True))
            
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