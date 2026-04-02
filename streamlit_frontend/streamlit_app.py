"""
ZTA-AI Streamlit Frontend

Secure chat interface for Zero Trust Architecture AI system.
Features:
- Mock Google OAuth authentication
- Real-time chat with WebSocket streaming
- Persona-based access control visualization
- Query history
- Multi-tenant support
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
import jwt
import websocket
import threading
from queue import Queue

# Configuration
API_BASE_URL = st.secrets.get("api_base_url", "http://api:8000")
# For local development outside Docker, use: http://localhost:8000

# Page config
st.set_page_config(
    page_title="ZTA-AI Command Console",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #0ea5e9;
        margin-bottom: 0.5rem;
    }
    .persona-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        margin-right: 0.5rem;
    }
    .student { background-color: #dbeafe; color: #1e40af; }
    .faculty { background-color: #dcfce7; color: #166534; }
    .it_head { background-color: #fee2e2; color: #991b1b; }
    .executive { background-color: #fef3c7; color: #92400e; }
    .admin_staff { background-color: #e9d5ff; color: #6b21a8; }
    
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #f0f9ff;
        border-left: 4px solid #0ea5e9;
    }
    .assistant-message {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'jwt_token' not in st.session_state:
    st.session_state.jwt_token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'decoded_token' not in st.session_state:
    st.session_state.decoded_token = None

# Helper functions
def decode_jwt_token(token):
    """Decode JWT token to display claims (no verification needed for display)"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        st.error(f"Error decoding token: {e}")
        return None

def authenticate(email):
    """Authenticate user with mock Google OAuth"""
    try:
        google_token = f"mock:{email}"
        response = requests.post(
            f"{API_BASE_URL}/auth/google",
            json={"google_token": google_token},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.jwt_token = data['jwt']
            st.session_state.user_info = data['user']
            st.session_state.decoded_token = decode_jwt_token(data['jwt'])
            st.session_state.chat_history = []
            return True
        else:
            st.error(f"Authentication failed: {response.json().get('error', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return False

def logout():
    """Logout and clear session"""
    if st.session_state.jwt_token:
        try:
            requests.post(
                f"{API_BASE_URL}/auth/logout",
                headers={"Authorization": f"Bearer {st.session_state.jwt_token}"},
                timeout=5
            )
        except:
            pass
    
    st.session_state.jwt_token = None
    st.session_state.user_info = None
    st.session_state.decoded_token = None
    st.session_state.chat_history = []

def send_query_rest(query_text):
    """Send query via REST API (fallback if WebSocket not available)"""
    try:
        # For simplicity, we'll use WebSocket streaming via REST simulation
        # In a real implementation, you'd establish a persistent WebSocket connection
        
        # Simulate streaming by sending request and getting response
        st.session_state.chat_history.append({
            "role": "user",
            "content": query_text,
            "timestamp": datetime.now()
        })
        
        # Call backend chat endpoint (this is a placeholder - actual implementation would use WebSocket)
        # For now, we'll make a simple query to test connectivity
        response = requests.post(
            f"{API_BASE_URL}/chat/query",
            headers={"Authorization": f"Bearer {st.session_state.jwt_token}"},
            json={"query": query_text},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": data.get("response_text", "No response"),
                "timestamp": datetime.now(),
                "source": data.get("source", "unknown"),
                "latency_ms": data.get("latency_ms", 0)
            })
            return True
        else:
            st.error(f"Query failed: {response.json().get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Query error: {e}")
        return False

def get_chat_history():
    """Fetch chat history from backend"""
    if not st.session_state.jwt_token:
        return []
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/chat/history",
            headers={"Authorization": f"Bearer {st.session_state.jwt_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except:
        return []

def get_suggestions():
    """Get query suggestions based on persona"""
    if not st.session_state.jwt_token:
        return []
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/chat/suggestions",
            headers={"Authorization": f"Bearer {st.session_state.jwt_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except:
        return []

# Main App
def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="main-header">🔐 ZTA-AI Command Console</div>', unsafe_allow_html=True)
    
    # Authentication Section
    if not st.session_state.jwt_token:
        st.markdown("### 🔑 Login with Mock OAuth")
        st.info("Select a test user to login. This uses mock authentication for development.")
        
        # Test users
        test_users = {
            "👨‍🎓 Student (CSE)": "student@campusa.edu",
            "👨‍🏫 Faculty (CSE)": "faculty@campusa.edu",
            "👨‍💼 IT Head": "it.head@campusa.edu",
            "👔 IPEDS Executive": "executive@ipeds.local",
            "📋 Admissions Staff": "admissions@ipeds.local",
            "🔧 IPEDS IT Head": "ithead@ipeds.local"
        }
        
        selected_user = st.selectbox("Select Test User:", list(test_users.keys()))
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚀 Login", type="primary"):
                with st.spinner("Authenticating..."):
                    email = test_users[selected_user]
                    if authenticate(email):
                        st.success(f"✅ Logged in as {email}")
                        st.rerun()
        
        # Backend status
        st.markdown("---")
        st.markdown("### 🏥 Backend Status")
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Backend API is healthy")
                st.json(response.json())
            else:
                st.error("❌ Backend API returned an error")
        except Exception as e:
            st.error(f"❌ Cannot reach backend API: {e}")
            st.info(f"Make sure the backend is running at {API_BASE_URL}")
        
        return
    
    # Sidebar - User Info
    with st.sidebar:
        st.markdown("### 👤 User Profile")
        
        user = st.session_state.user_info
        decoded = st.session_state.decoded_token
        
        if user:
            persona_class = user['persona']
            st.markdown(f'<span class="persona-badge {persona_class}">{user["persona"].upper()}</span>', 
                       unsafe_allow_html=True)
            st.markdown(f"**Name:** {user['name']}")
            st.markdown(f"**Email:** {user['email']}")
            st.markdown(f"**Department:** {user.get('department', 'N/A')}")
            
            if decoded:
                st.markdown("---")
                st.markdown("### 🔐 Access Rights")
                
                allowed_domains = decoded.get('allowed_domains', [])
                if allowed_domains:
                    st.markdown("**Allowed Domains:**")
                    for domain in allowed_domains:
                        st.markdown(f"- ✅ {domain}")
                
                denied_domains = decoded.get('denied_domains', [])
                if denied_domains:
                    with st.expander("View Denied Domains"):
                        for domain in denied_domains:
                            st.markdown(f"- ❌ {domain}")
                
                masked_fields = decoded.get('masked_fields', [])
                if masked_fields and masked_fields != ['*']:
                    with st.expander("View Masked Fields"):
                        for field in masked_fields:
                            st.markdown(f"- 🔒 {field}")
                elif masked_fields == ['*']:
                    st.markdown("**Masking:** 🔒 All fields masked")
                
                chat_enabled = decoded.get('chat_enabled', True)
                if not chat_enabled:
                    st.warning("⚠️ Chat is disabled for your persona")
        
        st.markdown("---")
        if st.button("🚪 Logout", type="secondary"):
            logout()
            st.rerun()
        
        # Token expiry
        if decoded:
            exp = decoded.get('exp', 0)
            exp_time = datetime.fromtimestamp(exp)
            remaining = exp_time - datetime.now()
            if remaining.total_seconds() > 0:
                minutes = int(remaining.total_seconds() / 60)
                st.caption(f"⏱️ Token expires in {minutes} minutes")
            else:
                st.error("⚠️ Token expired! Please logout and login again.")
    
    # Main Chat Interface
    st.markdown("### 💬 Chat Interface")
    
    # Check if chat is enabled
    if st.session_state.decoded_token and not st.session_state.decoded_token.get('chat_enabled', True):
        st.warning("⚠️ Chat interface is disabled for your persona. Please use the admin dashboard.")
        return
    
    # Query suggestions
    suggestions = get_suggestions()
    if suggestions:
        st.markdown("**💡 Suggested Queries:**")
        cols = st.columns(min(len(suggestions), 3))
        for idx, suggestion in enumerate(suggestions[:6]):
            with cols[idx % 3]:
                if st.button(suggestion['text'], key=f"suggestion_{idx}"):
                    st.session_state.current_query = suggestion['text']
    
    # Chat history display
    st.markdown("---")
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.chat_history:
            st.info("👋 Welcome! Ask me anything about your data. Try queries like:\n\n"
                   "- How many students are enrolled?\n"
                   "- Show me course information\n"
                   "- What's my fee status?")
        else:
            for msg in st.session_state.chat_history:
                role = msg['role']
                content = msg['content']
                timestamp = msg.get('timestamp', datetime.now())
                
                if role == 'user':
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>👤 You</strong> <span style="color: #64748b; font-size: 0.875rem;">
                        {timestamp.strftime('%H:%M:%S')}</span><br/>
                        {content}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    source = msg.get('source', 'assistant')
                    latency = msg.get('latency_ms', 0)
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>🤖 Assistant</strong> <span style="color: #64748b; font-size: 0.875rem;">
                        {timestamp.strftime('%H:%M:%S')} • {source} • {latency}ms</span><br/>
                        {content}
                    </div>
                    """, unsafe_allow_html=True)
    
    # Query input
    st.markdown("---")
    query_text = st.text_input(
        "Enter your query:",
        value=st.session_state.get('current_query', ''),
        placeholder="Type your question here...",
        key="query_input"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        send_clicked = st.button("📤 Send", type="primary")
    
    if send_clicked and query_text:
        with st.spinner("Processing query..."):
            # Note: This is a simplified version using REST
            # In production, you'd use WebSocket for real-time streaming
            send_query_rest(query_text)
            st.session_state.current_query = ''
            st.rerun()

if __name__ == "__main__":
    main()
