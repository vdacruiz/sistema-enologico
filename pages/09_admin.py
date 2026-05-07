import streamlit as st
import pandas as pd
import json
from lib import auth, queries

st.title("Administracion de Usuarios")

auth.require_permission("admin", "ver")

MODULES = {
    "dashboard": "Centro de Control",
    "ordenes_trabajo": "Ordenes de Trabajo",
    "ejecutar_ot": "Ejecutar OT",
    "recepcion_insumos": "Recepcion Insumos",
    "recepcion_vino": "Recepcion Vino",
    "stock_insumos": "Stock Insumos",
    "stock_cubas": "Stock Cubas",
    "laboratorio": "Laboratorio",
    "configuracion": "Configuracion",
    "admin": "Administracion",
}

ACTIONS = ["ver", "crear", "editar", "eliminar", "ejecutar"]

tab_users, tab_roles = st.tabs(["Usuarios", "Roles y Permisos"])

# =============================================================
# TAB: Usuarios
# =============================================================
with tab_users:
    st.subheader("Usuarios del Sistema")

    try:
        users = auth.get_all_users()
        roles = auth.get_active_roles()
        workers = queries.get_workers()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    worker_options = {None: "-- Sin vincular --"}
    worker_options.update({w["id"]: w["full_name"] for w in workers})

    if users:
        rows = []
        for u in users:
            role = u.get("app_roles", {})
            worker_name = "-"
            if u.get("worker_id"):
                w = next((w for w in workers if w["id"] == u["worker_id"]), None)
                worker_name = w["full_name"] if w else "-"
            rows.append({
                "ID": u["id"],
                "Usuario": u["username"],
                "Nombre": u["full_name"],
                "Rol": role.get("name", "-") if role else "-",
                "Operario": worker_name,
                "Activo": "Si" if u.get("is_active") else "No",
                "Ultimo Login": str(u.get("last_login") or "-")[:16],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # --- Crear usuario ---
    st.markdown("---")
    st.subheader("Crear Usuario")

    role_options = {r["id"]: r["name"] for r in roles}

    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Usuario", key="new_username", placeholder="ej: jperez")
        new_password = st.text_input("Clave", key="new_password", type="password")
    with col2:
        new_fullname = st.text_input("Nombre completo", key="new_fullname", placeholder="ej: Juan Perez")
        new_role = st.selectbox("Rol", options=list(role_options.keys()),
                                format_func=lambda x: role_options[x], key="new_role")

    new_worker = st.selectbox(
        "Vincular a operario (solo para rol Operario)",
        options=list(worker_options.keys()),
        format_func=lambda x: worker_options[x],
        key="new_worker"
    )

    if st.button("Crear Usuario", type="primary"):
        if not new_username or not new_password or not new_fullname:
            st.error("Todos los campos son obligatorios")
        elif len(new_password) < 4:
            st.error("La clave debe tener al menos 4 caracteres")
        else:
            try:
                result = auth.create_user(new_username, new_password, new_fullname, new_role)
                if new_worker and result:
                    auth.update_user(result[0]["id"], {"worker_id": new_worker})
                st.success(f"Usuario '{new_username}' creado exitosamente")
                st.rerun()
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    st.error("Ese nombre de usuario ya existe")
                else:
                    st.error(f"Error: {e}")

    # --- Editar usuario ---
    if users:
        st.markdown("---")
        st.subheader("Editar Usuario")

        user_options = {u["id"]: f"{u['username']} - {u['full_name']}" for u in users}
        edit_user_id = st.selectbox("Seleccione usuario:", options=list(user_options.keys()),
                                     format_func=lambda x: user_options[x], key="edit_user",
                                     index=None, placeholder="Seleccione...")

        if edit_user_id:
            user_data = next(u for u in users if u["id"] == edit_user_id)
            current_user = auth.get_current_user()

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                edit_fullname = st.text_input("Nombre", value=user_data["full_name"], key="edit_fn")
                edit_password = st.text_input("Nueva clave (dejar vacio para no cambiar)",
                                              key="edit_pw", type="password")
            with col_e2:
                current_role_idx = next((i for i, r in enumerate(roles) if r["id"] == user_data["role_id"]), 0)
                edit_role = st.selectbox("Rol", options=[r["id"] for r in roles],
                                         format_func=lambda x: next(r["name"] for r in roles if r["id"] == x),
                                         index=current_role_idx, key="edit_role")
                edit_active = st.checkbox("Activo", value=user_data.get("is_active", True), key="edit_active")

            current_worker = user_data.get("worker_id")
            worker_keys = list(worker_options.keys())
            current_worker_idx = worker_keys.index(current_worker) if current_worker in worker_keys else 0
            edit_worker = st.selectbox(
                "Vincular a operario",
                options=worker_keys,
                format_func=lambda x: worker_options[x],
                index=current_worker_idx,
                key="edit_worker"
            )

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("Guardar Cambios", key="save_user", use_container_width=True):
                    update_data = {
                        "full_name": edit_fullname,
                        "role_id": edit_role,
                        "is_active": edit_active,
                        "worker_id": edit_worker,
                    }
                    if edit_password:
                        update_data["password"] = edit_password
                    try:
                        auth.update_user(edit_user_id, update_data)
                        st.success("Usuario actualizado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col_del:
                if current_user and edit_user_id == current_user["id"]:
                    st.button("No puede eliminarse a si mismo", disabled=True, use_container_width=True)
                else:
                    if st.button("Eliminar Usuario", key="del_user", use_container_width=True):
                        st.session_state[f"confirm_del_user_{edit_user_id}"] = True

                    if st.session_state.get(f"confirm_del_user_{edit_user_id}"):
                        st.warning(f"Confirma eliminar a '{user_data['username']}'?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Si, eliminar", key="yes_del_user"):
                                try:
                                    auth.delete_user(edit_user_id)
                                    st.success("Usuario eliminado")
                                    del st.session_state[f"confirm_del_user_{edit_user_id}"]
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with col_no:
                            if st.button("Cancelar", key="no_del_user"):
                                del st.session_state[f"confirm_del_user_{edit_user_id}"]
                                st.rerun()


# =============================================================
# TAB: Roles y Permisos
# =============================================================
with tab_roles:
    st.subheader("Roles del Sistema")

    try:
        all_roles = auth.get_all_roles()
    except Exception as e:
        st.error(f"Error: {e}")
        all_roles = []

    if all_roles:
        for role in all_roles:
            with st.expander(f"**{role['name']}** - {role.get('description', '')}"):
                perms = role.get("permissions", {})

                st.markdown("**Permisos actuales:**")
                perm_rows = []
                for mod_key, mod_name in MODULES.items():
                    mod_perms = perms.get(mod_key, {})
                    actions = [a for a in ACTIONS if mod_perms.get(a, False)]
                    perm_rows.append({
                        "Modulo": mod_name,
                        "Permisos": ", ".join(actions) if actions else "Sin acceso",
                    })
                st.dataframe(pd.DataFrame(perm_rows), use_container_width=True, hide_index=True)

                if auth.has_permission("admin", "editar"):
                    st.markdown("**Editar permisos:**")
                    new_perms = {}
                    for mod_key, mod_name in MODULES.items():
                        mod_perms = perms.get(mod_key, {})
                        available_actions = ACTIONS
                        if mod_key == "ejecutar_ot":
                            available_actions = ["ver", "ejecutar"]
                        elif mod_key in ["stock_insumos", "stock_cubas"]:
                            available_actions = ["ver"]

                        selected = st.multiselect(
                            mod_name,
                            options=available_actions,
                            default=[a for a in available_actions if mod_perms.get(a, False)],
                            key=f"perm_{role['id']}_{mod_key}"
                        )
                        new_perms[mod_key] = {a: (a in selected) for a in available_actions}

                    col_r1, col_r2 = st.columns([3, 1])
                    with col_r1:
                        new_desc = st.text_input("Descripcion", value=role.get("description", ""),
                                                  key=f"desc_{role['id']}")
                    with col_r2:
                        role_active = st.checkbox("Activo", value=role.get("is_active", True),
                                                   key=f"active_{role['id']}")

                    if st.button("Guardar Permisos", key=f"save_role_{role['id']}", type="primary"):
                        try:
                            auth.update_role(role["id"], {
                                "permissions": new_perms,
                                "description": new_desc,
                                "is_active": role_active,
                            })
                            st.success(f"Rol '{role['name']}' actualizado")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # --- Crear rol ---
    st.markdown("---")
    st.subheader("Crear Nuevo Rol")

    new_role_name = st.text_input("Nombre del rol", key="new_role_name", placeholder="ej: Supervisor")
    new_role_desc = st.text_input("Descripcion", key="new_role_desc", placeholder="Descripcion del rol...")

    if new_role_name:
        st.markdown("**Permisos:**")
        create_perms = {}
        for mod_key, mod_name in MODULES.items():
            available_actions = ACTIONS
            if mod_key == "ejecutar_ot":
                available_actions = ["ver", "ejecutar"]
            elif mod_key in ["stock_insumos", "stock_cubas"]:
                available_actions = ["ver"]

            selected = st.multiselect(
                mod_name, options=available_actions, default=[],
                key=f"new_perm_{mod_key}"
            )
            create_perms[mod_key] = {a: (a in selected) for a in available_actions}

        if st.button("Crear Rol", type="primary", key="create_role"):
            try:
                auth.create_role(new_role_name, new_role_desc, create_perms)
                st.success(f"Rol '{new_role_name}' creado exitosamente")
                st.rerun()
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    st.error("Ya existe un rol con ese nombre")
                else:
                    st.error(f"Error: {e}")
