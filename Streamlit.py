import streamlit as st
import json
import _snowflake
from snowflake.snowpark.context import get_active_session
#from typing import Dict, List, Any, Optional, Tuple, Union
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

def snowflake_api_call(query: str, limit: int = 10):
    
    payload = {
        "model": "claude-3-5-sonnet",
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
        "response_instruction": """You are an intelligent assistant with access to two independent tools:

1. 'Faq Search' - searches a PDF document for policy/procedure information
2. 'Sales Analyst' - queries a database to get quantitative sales data

CRITICAL RULES:
- These tools have COMPLETELY SEPARATE data sources
- 'Faq Search' ONLY has access to policy documents (refund policy, shipping policy, etc.)
- 'Sales Analyst' ONLY has access to the sales database (orders, revenue, customers, etc.)
- You CANNOT answer database questions using 'Faq Search' results
- You CANNOT answer policy questions using 'Sales Analyst' results

EXECUTION STRATEGY:
When a user asks a compound question with multiple parts:
1. Identify ALL distinct questions in the query
2. For EACH question about policies/procedures → call 'Faq Search'
3. For EACH question about data/analytics/numbers → call 'Sales Analyst' 
4. You MUST call BOTH tools if the query requires both types of information
5. Only after receiving results from ALL necessary tools, synthesize a complete answer

EXAMPLES:
- "What is the refund policy and how many orders were placed?" 
  → MUST call BOTH: 'Faq Search' for policy AND 'Sales Analyst' for order count
- "How many refunds were processed?"
  → MUST call 'Sales Analyst' (this is asking for data, not policy)
- "What is the shipping policy?"
  → MUST call 'Faq Search' (this is asking for policy information)

If you fail to call 'Sales Analyst' for a data question, you are providing incorrect information."""
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
            if event.get('event') == "message.delta":
                data = event.get('data', {})
                delta = data.get('delta', {})
                
                for content_item in delta.get('content', []):
                    content_type = content_item.get('type')
                    
                    # Track tool usage
                    if content_type == "tool_use":
                        tool_name = content_item.get('name', 'Unknown')
                        tools_called.append(tool_name)
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
                                        if debug_mode:
                                            st.success(f"✅ SQL query generated by Sales Analyst")
                    
                    if content_type == 'text':
                        text += content_item.get('text', '')
        
        # Debug information
        if debug_mode:
            if tools_called:
                st.info(f"📊 Tools used in this response: {', '.join(set(tools_called))}")
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

    # Sidebar for new chat and debug mode
    with st.sidebar:
        st.markdown("### Controls")
        if st.button("New Conversation", key="new_chat"):
            st.session_state.messages = []
            st.rerun()
        
        debug_mode = st.checkbox("Debug Mode", value=True, help="Show which tools are being called")
        
        st.markdown("---")
        st.markdown("### Available Tools")
        st.markdown("🔍 **Faq Search**: Policy & procedure information from documents")
        st.markdown("📊 **Sales Analyst**: Quantitative data from sales database")
        
    # Store debug mode in session state
    st.session_state.debug_mode = debug_mode

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
            response = snowflake_api_call(query, 1)
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