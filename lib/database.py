import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def test_connection() -> bool:
    try:
        client = get_supabase_client()
        client.table("supplies").select("id").limit(1).execute()
        return True
    except Exception:
        return False
