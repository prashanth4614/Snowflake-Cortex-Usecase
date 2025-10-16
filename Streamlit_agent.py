import streamlit as st
import json
import _snowflake
from snowflake.snowpark.context import get_active_session
from streamlit_extras.stylable_container import stylable_container
from typing import Optional, Tuple, Dict, List, Any
import os

session = get_active_session()

# Pre-configured Cortex Agent endpoint
AGENT_NAME = "CORTEX_SALES_AGENT"
AGENT_DATABASE = "SNOWFLAKE_INTELLIGENCE"
AGENT_SCHEMA = "AGENTS"
API_ENDPOINT = f"/api/v2/databases/{AGENT_DATABASE.lower()}/schemas/{AGENT_SCHEMA.lower()}/agents/{AGENT_NAME}:run"
THREAD_ENDPOINT = "/api/v2/cortex/threads"
AGENT_CONFIG_FILE = "CORTEX_AGENT_SALES.json"
API_TIMEOUT = 50000  # in milliseconds

def check_agent_exists() -> bool:
    """Check if the Cortex Agent exists in Snowflake."""
    try:
        # Use REST API to check agent existence
        agent_endpoint = f"/api/v2/databases/{AGENT_DATABASE.lower()}/schemas/{AGENT_SCHEMA.lower()}/agents/{AGENT_NAME}"
        
        resp = _snowflake.send_snow_api_request(
            "GET",
            agent_endpoint,
            {},
            {},
            {},
            None,
            API_TIMEOUT,
        )
        
        return resp["status"] == 200
    except Exception as e:
        return False

def load_agent_config() -> Optional[Dict]:
    """Load agent configuration from JSON file."""
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, AGENT_CONFIG_FILE)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('data', {}).get('agent_spec', {})
    except FileNotFoundError:
        st.error(f"❌ Configuration file '{AGENT_CONFIG_FILE}' not found.")
        return None
    except json.JSONDecodeError:
        st.error(f"❌ Invalid JSON in configuration file '{AGENT_CONFIG_FILE}'.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading configuration: {str(e)}")
        return None

def create_agent() -> bool:
    """Create the Cortex Agent if it doesn't exist."""
    try:
        st.info("🔧 Agent not found. Creating agent...")
        
        # Load agent configuration (returns the agent_spec object)
        agent_spec = load_agent_config()
        if not agent_spec:
            st.error("❌ Failed to load agent configuration.")
            return False
        
        # Prepare the creation endpoint
        create_endpoint = f"/api/v2/databases/{AGENT_DATABASE.lower()}/schemas/{AGENT_SCHEMA.lower()}/agents"
        
        # Prepare payload - agent_spec needs to be a JSON string for the API
        # The structure should be: {"name": "...", "agent_spec": "<json_string>"}
        payload = {
            "name": AGENT_NAME,
            "agent_spec": json.dumps(agent_spec)  # Convert the spec object to JSON string
        }
        
        # Debug: Show what we're sending
        if st.session_state.get('debug_mode', False):
            st.info(f"Creating agent at: {create_endpoint}")
            with st.expander("📤 Creation Payload", expanded=False):
                st.json(payload)
        
        # Create the agent via REST API
        resp = _snowflake.send_snow_api_request(
            "POST",
            create_endpoint,
            {},
            {},
            payload,
            None,
            API_TIMEOUT,
        )
        
        if resp["status"] == 200 or resp["status"] == 201:
            st.success(f"✅ Agent '{AGENT_NAME}' created successfully!")
            return True
        else:
            st.error(f"❌ Failed to create agent. Status: {resp['status']}")
            if resp.get('content'):
                try:
                    error_data = json.loads(resp['content'])
                    st.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    st.error(f"Response: {resp['content']}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error creating agent: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return False

def ensure_agent_exists() -> bool:
    """Ensure the agent exists, create it if it doesn't."""
    if not check_agent_exists():
        return create_agent()
    return True

def create_thread():
    """Create a new thread for maintaining conversation context."""
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",
            THREAD_ENDPOINT,
            {},
            {},
            {"origin_application": "streamlit_sales_assistant"},
            None,
            API_TIMEOUT,
        )
        
        if resp["status"] == 200:
            thread_data = json.loads(resp["content"])
            return thread_data.get('thread_id')
        return None
    except Exception as e:
        st.warning(f"Could not create thread: {str(e)}")
        return None

def run_snowflake_query(query):
    try:
        df = session.sql(query.replace(';',''))
        
        return df

    except Exception as e:
        st.error(f"Error executing SQL: {str(e)}")
        return None, None

def snowflake_api_call(query: str, model: str = "claude-sonnet-4-5", thread_id: Optional[int] = None, parent_message_id: Optional[int] = None):
    """
    Call pre-configured Cortex Agent with optional thread support.
    
    Args:
        query: User query text
        model: LLM model to use for orchestration
        thread_id: Optional thread ID for maintaining conversation context
        parent_message_id: Optional parent message ID for threading
    
    The agent has tools pre-configured in Snowflake, so we don't need to pass
    tools, tool_resources, or tool_choice parameters.
    """
    
    # Build payload with thread support
    payload = {
        "model": model,
        "messages": [{"role": "user",
                      "content": [{"type": "text", "text": query}]}]
    }
    
    # Add thread parameters if provided
    if thread_id is not None and parent_message_id is not None:
        payload["thread_id"] = thread_id
        payload["parent_message_id"] = parent_message_id
     
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",
            API_ENDPOINT,
            {},
            {'stream': True},
            payload,
            None,
            API_TIMEOUT,
        )
        
        if resp["status"] != 200:
            st.error(f"❌ HTTP Error: {resp['status']} - {resp.get('reason', 'Unknown reason')}")
            if st.session_state.get('debug_mode', False):
                st.error(f"Response details: {resp}")
            return None
        
        try:
            response_content = json.loads(resp["content"])
            
            # Debug: Show the actual response structure
            if st.session_state.get('debug_mode', False):
                with st.expander("📋 Raw API Response", expanded=False):
                    st.json(response_content)
                    
        except json.JSONDecodeError:
            st.error("❌ Failed to parse API response.")
            return None

        return response_content
            
    except Exception as e:
        st.error(f"Error making request: {str(e)}")
        return None

def process_sse_response(response, debug_mode=False):
    """
    Process SSE response from pre-configured Cortex Agent.
    
    Extracts text, SQL, citations, and tracks metadata from the agent response.
    Returns tuple of (text, sql, citations, metadata)
    """
    text = ""
    sql = ""
    citations = []
    tools_called = []
    metadata = {}
    
    if not response:
        return text, sql, citations, metadata
    if isinstance(response, str):
        return text, sql, citations, metadata
    
    event_count = 0
    
    try:
        for event in response:
            event_count += 1
            
            if debug_mode:
                with st.expander(f"🔍 Event #{event_count}: {event.get('event', 'unknown')}", expanded=False):
                    st.json(event)
            
            # Extract metadata for threading
            if event.get('event') == "metadata":
                metadata = event.get('data', {})
                if debug_mode:
                    st.info(f"📨 Metadata: message_id={metadata.get('message_id')}, role={metadata.get('role')}")
            
            # Pre-configured agents use "response" event
            if event.get('event') == "response":
                data = event.get('data', {})
                content_items = data.get('content', [])
                
                for content_item in content_items:
                    content_type = content_item.get('type')
                    
                    # Track tool usage
                    if content_type == "tool_use":
                        tool_use_data = content_item.get('tool_use', {})
                        tool_type = tool_use_data.get('type', '')
                        tool_name = tool_use_data.get('name', tool_type)
                        
                        tools_called.append(tool_name)
                        
                        if debug_mode:
                            st.info(f"🔧 Tool called: {tool_name}")
                    
                    # Extract text from response
                    if content_type == "text":
                        text += content_item.get('text', '')
                        
                        # Process annotations for citations
                        annotations = content_item.get('annotations', [])
                        for annotation in annotations:
                            if annotation.get('type') == 'cortex_search_citation':
                                citations.append({
                                    'source_id': annotation.get('index', 0),
                                    'doc_title': annotation.get('doc_title', ''),
                                    'doc_chunk': annotation.get('doc_id', '')
                                })
                    
                    # Process tool results for SQL and search results
                    if content_type == "tool_result":
                        tool_result = content_item.get('tool_result', {})
                        tool_content = tool_result.get('content', [])
                        
                        for result in tool_content:
                            if result.get('type') == 'json':
                                json_data = result.get('json', {})
                                
                                # Extract SQL if present
                                result_sql = json_data.get('sql', '')
                                if result_sql:
                                    sql = result_sql
                                
                                # Extract search results for citations
                                search_results = json_data.get('search_results', [])
                                for search_result in search_results:
                                    citations.append({
                                        'source_id': search_result.get('source_id', 0),
                                        'doc_title': search_result.get('doc_title', ''),
                                        'doc_chunk': search_result.get('doc_id', '')
                                    })
        
        # Show tool usage summary in debug mode
        if debug_mode:
            st.info(f"📊 Processed {event_count} events")
            if tools_called:
                unique_tools = set(tools_called)
                if len(unique_tools) > 1:
                    st.success(f"✅ Multiple tools used: {', '.join(unique_tools)}")
                else:
                    st.info(f"📊 Tool used: {', '.join(unique_tools)}")
                            
    except json.JSONDecodeError as e:
        st.error(f"Error processing events: {str(e)}")
                
    except Exception as e:
        st.error(f"Error processing events: {str(e)}")
        
    return text, sql, citations, metadata

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
    
    # Ensure agent exists before proceeding
    if 'agent_checked' not in st.session_state:
        with st.spinner("Checking agent status..."):
            if not ensure_agent_exists():
                st.error("❌ Failed to initialize agent. Please check your configuration and try again.")
                st.stop()
            st.session_state.agent_checked = True
    
    # Display current model at the top
    current_model = st.session_state.get('selected_model', 'claude-sonnet-4-5')
    st.caption(f"🤖 Using model: **{current_model}**")

    # Sidebar for new chat and debug mode
    with st.sidebar:
        st.markdown("### Controls")
        if st.button("New Conversation", key="new_chat"):
            st.session_state.messages = []
            st.session_state.thread_id = None
            st.session_state.parent_message_id = 0
            st.rerun()
        
        debug_mode = st.checkbox("Debug Mode", value=False, help="Show which tools are being called and detailed logs")
        
        use_threads = st.checkbox(
            "Use Conversation Context", 
            value=True, 
            help="Maintain conversation history on server using threads (recommended)"
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
            help="Claude Sonnet 4.5 is recommended for best performance"
        )
        
        st.markdown("---")
        st.markdown("### Available Tools")
        st.markdown("🔍 **Cortex-Sales-Search**: Policy & documentation search")
        st.markdown("📊 **Cortex Sales Analyst**: Database queries & analytics")
        
        st.markdown("---")
        st.markdown("### About")
        st.caption("Using pre-configured Cortex Agent with automatic multi-tool orchestration")
        if use_threads:
            thread_status = "✅ Active" if st.session_state.get('thread_id') else "⏳ Starting"
            st.caption(f"Thread: {thread_status}")
        
    # Store settings in session state
    st.session_state.debug_mode = debug_mode
    st.session_state.selected_model = model_choice
    st.session_state.use_threads = use_threads

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None
    if 'parent_message_id' not in st.session_state:
        st.session_state.parent_message_id = 0

    # Create thread if enabled and not exists
    if use_threads and st.session_state.thread_id is None:
        with st.spinner("Initializing conversation thread..."):
            thread_id = create_thread()
            if thread_id:
                st.session_state.thread_id = thread_id
                if debug_mode:
                    st.success(f"✅ Thread created: {thread_id}")

    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'].replace("•", "\n\n"))

    if query := st.chat_input("Ask me anything about sales, orders, or policies..."):
        # Add user message to chat
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Get response from API
        with st.spinner("Processing your request..."):
            selected_model = st.session_state.get('selected_model', 'claude-sonnet-4-5')
            debug_mode = st.session_state.get('debug_mode', False)
            
            # Use threads if enabled
            thread_id = st.session_state.thread_id if use_threads else None
            parent_msg_id = st.session_state.parent_message_id if use_threads else None
            
            response = snowflake_api_call(
                query, 
                model=selected_model,
                thread_id=thread_id,
                parent_message_id=parent_msg_id
            )
            
            text, sql, citations, metadata = process_sse_response(response, debug_mode)
            
            # Update parent_message_id for next turn
            if use_threads and metadata.get('message_id'):
                st.session_state.parent_message_id = metadata['message_id']
            
            if debug_mode:
                st.write(f"Debug - Text length: {len(text)}, SQL: {bool(sql)}, Citations: {len(citations)}")
            
            # Add assistant response to chat
            if text:
                text = text.replace("【†", "[")
                text = text.replace("†】", "]")
                st.session_state.messages.append({"role": "assistant", "content": text})
                
                with st.chat_message("assistant"):
                    st.markdown(text.replace("•", "\n\n"))
                    if citations:
                        display_citations(citations)
            else:
                st.warning("⚠️ No response text generated.")
    
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