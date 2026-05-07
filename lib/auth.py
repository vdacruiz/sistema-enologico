import streamlit as st
from lib.database import get_supabase_client


def login(username: str, password: str):
    result = (get_supabase_client().table("app_users")
              .select("*, app_roles(id, name, permissions)")
              .eq("username", username)
              .eq("password", password)
              .eq("is_active", True)
              .execute().data)
    if result:
        user = result[0]
        role = user.get("app_roles", {})
        if not role or not role.get("id"):
            return None
        get_supabase_client().table("app_users").update(
            {"last_login": "now()"}
        ).eq("id", user["id"]).execute()
        return {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role_id": role["id"],
            "role_name": role["name"],
            "permissions": role.get("permissions", {}),
            "worker_id": user.get("worker_id"),
        }
    return None


def get_current_user():
    return st.session_state.get("user")


def has_permission(module: str, action: str = "ver") -> bool:
    user = get_current_user()
    if not user:
        return False
    perms = user.get("permissions", {})
    module_perms = perms.get(module, {})
    return module_perms.get(action, False)


def require_permission(module: str, action: str = "ver"):
    if not has_permission(module, action):
        st.warning("No tiene permisos para acceder a esta seccion")
        st.stop()


def is_admin() -> bool:
    return has_permission("admin", "ver")


def logout():
    for key in ["user", "authenticated"]:
        if key in st.session_state:
            del st.session_state[key]


# --- Gestion de usuarios y roles ---

def get_all_roles():
    return (get_supabase_client().table("app_roles")
            .select("*").order("id").execute().data)


def get_active_roles():
    return (get_supabase_client().table("app_roles")
            .select("*").eq("is_active", True).order("name").execute().data)


def create_role(name: str, description: str, permissions: dict):
    return (get_supabase_client().table("app_roles")
            .insert({"name": name, "description": description, "permissions": permissions})
            .execute().data)


def update_role(role_id: int, data: dict):
    return (get_supabase_client().table("app_roles")
            .update(data).eq("id", role_id).execute().data)


def get_all_users():
    return (get_supabase_client().table("app_users")
            .select("*, app_roles(name)")
            .order("full_name").execute().data)


def create_user(username: str, password: str, full_name: str, role_id: int):
    return (get_supabase_client().table("app_users")
            .insert({"username": username, "password": password,
                      "full_name": full_name, "role_id": role_id})
            .execute().data)


def update_user(user_id: int, data: dict):
    return (get_supabase_client().table("app_users")
            .update(data).eq("id", user_id).execute().data)


def delete_user(user_id: int):
    return (get_supabase_client().table("app_users")
            .delete().eq("id", user_id).execute().data)
