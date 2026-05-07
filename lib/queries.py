import pandas as pd
from lib.database import get_supabase_client


# ============================================================
# INSUMOS
# ============================================================

def get_supplies(active_only=True):
    q = get_supabase_client().table("supplies").select("*").order("name")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def get_supply_by_id(supply_id: int):
    return get_supabase_client().table("supplies").select("*").eq("id", supply_id).single().execute().data


# ============================================================
# LOTES
# ============================================================

def get_lots_by_supply(supply_id: int):
    return (get_supabase_client().table("supply_lots")
            .select("*")
            .eq("supply_id", supply_id)
            .eq("is_active", True)
            .order("expiry_date")
            .execute().data)


def create_lot(supply_id: int, lot_number: str, expiry_date=None, initial_stock=0):
    data = {
        "supply_id": supply_id,
        "lot_number": lot_number,
        "initial_stock": initial_stock,
    }
    if expiry_date:
        data["expiry_date"] = str(expiry_date)
    return get_supabase_client().table("supply_lots").insert(data).execute().data


# ============================================================
# STOCK (vistas)
# ============================================================

def get_stock_by_lot():
    return get_supabase_client().table("v_supply_stock_by_lot").select("*").execute().data


def get_stock_total():
    return get_supabase_client().table("v_supply_stock_total").select("*").execute().data


def get_low_stock_alerts():
    return get_supabase_client().table("v_low_stock_alerts").select("*").execute().data


def get_expiry_alerts():
    return get_supabase_client().table("v_expiry_alerts").select("*").execute().data


# ============================================================
# ORDENES DE TRABAJO
# ============================================================

def create_work_order(data: dict):
    return get_supabase_client().table("work_orders").insert(data).execute().data


def create_work_order_lines(lines: list):
    if lines:
        return get_supabase_client().table("work_order_lines").insert(lines).execute().data
    return []


def get_work_orders(limit=50):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_work_order_lines(work_order_id: int):
    return (get_supabase_client().table("work_order_lines")
            .select("*, supplies(name, code, unit)")
            .eq("work_order_id", work_order_id)
            .execute().data)


def get_next_ot_number():
    result = (get_supabase_client().table("work_orders")
              .select("ot_number")
              .order("ot_number", desc=True)
              .limit(1)
              .execute().data)
    if result:
        return result[0]["ot_number"] + 1
    return 1


def get_work_orders_with_status(from_date: str):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name)")
            .gte("date", from_date)
            .order("date", desc=True)
            .execute().data)


def get_work_orders_by_worker(worker_id: int):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name)")
            .eq("worker_id", worker_id)
            .order("date", desc=True)
            .limit(50)
            .execute().data)


def update_work_order_status(work_order_id: int, status: str, observations: str = None):
    data = {"status": status}
    if status == "En Proceso":
        data["started_at"] = "now()"
    elif status == "Completada":
        data["completed_at"] = "now()"
    if observations:
        data["observations"] = observations
    return (get_supabase_client().table("work_orders")
            .update(data).eq("id", work_order_id).execute().data)


def update_work_order_line(line_id: int, data: dict):
    return (get_supabase_client().table("work_order_lines")
            .update(data).eq("id", line_id).execute().data)


def delete_work_order(work_order_id: int):
    get_supabase_client().table("work_order_lines").delete().eq("work_order_id", work_order_id).execute()
    return get_supabase_client().table("work_orders").delete().eq("id", work_order_id).execute().data


def search_work_orders(search_term: str = None, from_date: str = None, to_date: str = None, status: str = None):
    q = (get_supabase_client().table("work_orders")
         .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name)")
         .order("date", desc=True)
         .limit(100))
    if from_date:
        q = q.gte("date", from_date)
    if to_date:
        q = q.lte("date", to_date)
    if status and status != "Todos":
        q = q.eq("status", status)
    results = q.execute().data
    if search_term:
        search_lower = search_term.lower()
        results = [r for r in results if
                   search_lower in str(r.get("ot_number", "")).lower() or
                   search_lower in str((r.get("grape_varieties") or {}).get("code", "")).lower() or
                   search_lower in str((r.get("workers") or {}).get("full_name", "")).lower() or
                   search_lower in str((r.get("winemaking_processes") or {}).get("name", "")).lower()]
    return results


# ============================================================
# ORDENES DE COMPRA
# ============================================================

def create_purchase_order(data: dict):
    return get_supabase_client().table("purchase_orders").insert(data).execute().data


def create_purchase_order_lines(lines: list):
    if lines:
        return get_supabase_client().table("purchase_order_lines").insert(lines).execute().data
    return []


def get_purchase_orders(limit=50):
    return (get_supabase_client().table("purchase_orders")
            .select("*, suppliers(name)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


# ============================================================
# DATOS DE REFERENCIA
# ============================================================

def get_grape_varieties():
    return (get_supabase_client().table("grape_varieties")
            .select("*").eq("is_active", True).order("code").execute().data)


def get_product_lines():
    return (get_supabase_client().table("product_lines")
            .select("*").eq("is_active", True).order("sort_order").execute().data)


def get_workers():
    return (get_supabase_client().table("workers")
            .select("*").eq("is_active", True).order("full_name").execute().data)


def get_suppliers():
    return (get_supabase_client().table("suppliers")
            .select("*").eq("is_active", True).order("name").execute().data)


def get_processes():
    return (get_supabase_client().table("winemaking_processes")
            .select("*").eq("is_active", True).order("name").execute().data)


def get_tanks():
    return (get_supabase_client().table("tanks")
            .select("*").eq("is_active", True).order("code").execute().data)


def get_tank_contents():
    return (get_supabase_client().table("tank_contents")
            .select("*, tanks(code, name, capacity_liters), wines(code), grape_varieties(code, name)")
            .execute().data)


# ============================================================
# RECEPCION DE VINO
# ============================================================

def create_wine_reception(data: dict):
    return get_supabase_client().table("wine_receptions").insert(data).execute().data


def get_wine_receptions(limit=50):
    return (get_supabase_client().table("wine_receptions")
            .select("*, grape_varieties(code, name), product_lines(name)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_wine_reception_by_id(reception_id: int):
    return (get_supabase_client().table("wine_receptions")
            .select("*, grape_varieties(code, name), product_lines(name)")
            .eq("id", reception_id)
            .single()
            .execute().data)


def update_wine_reception(reception_id: int, data: dict):
    return (get_supabase_client().table("wine_receptions")
            .update(data).eq("id", reception_id).execute().data)


# ============================================================
# LABORATORIO
# ============================================================

def get_lab_parameters(wine_type: str = None):
    q = (get_supabase_client().table("lab_parameters")
         .select("*").eq("is_active", True).order("sort_order"))
    if wine_type:
        q = q.eq("wine_type", wine_type)
    return q.execute().data


def create_lab_analysis(data: dict):
    return get_supabase_client().table("lab_analyses").insert(data).execute().data


def create_lab_analysis_results(results: list):
    if results:
        return get_supabase_client().table("lab_analysis_results").insert(results).execute().data
    return []


def get_lab_analyses(tank_id: int = None, wine_id: int = None, limit=50):
    q = (get_supabase_client().table("lab_analyses")
         .select("*, tanks(code, name), wines(code), grape_varieties(code, name)")
         .order("date", desc=True)
         .limit(limit))
    if tank_id:
        q = q.eq("tank_id", tank_id)
    if wine_id:
        q = q.eq("wine_id", wine_id)
    return q.execute().data


def get_lab_analysis_results(analysis_id: int):
    return (get_supabase_client().table("lab_analysis_results")
            .select("*, lab_parameters(code, name, unit, min_normal, max_normal, alert_value, critical_value, alert_direction)")
            .eq("analysis_id", analysis_id)
            .execute().data)


def get_lab_history_for_tank(tank_id: int, parameter_code: str = None):
    analyses = (get_supabase_client().table("lab_analyses")
                .select("id, date")
                .eq("tank_id", tank_id)
                .order("date")
                .execute().data)
    if not analyses:
        return []
    analysis_ids = [a["id"] for a in analyses]
    results = []
    for aid in analysis_ids:
        r = (get_supabase_client().table("lab_analysis_results")
             .select("*, lab_parameters(code, name, unit, min_normal, max_normal, alert_value, critical_value)")
             .eq("analysis_id", aid)
             .execute().data)
        date_val = next(a["date"] for a in analyses if a["id"] == aid)
        for item in r:
            item["date"] = date_val
        results.extend(r)
    return results


def get_wines():
    return (get_supabase_client().table("wines")
            .select("*").eq("is_active", True).order("code").execute().data)


# ============================================================
# COMPRAS DE VINO
# ============================================================

def create_wine_purchase(data: dict):
    return get_supabase_client().table("wine_purchases").insert(data).execute().data


def get_wine_purchases(limit=50):
    return (get_supabase_client().table("wine_purchases")
            .select("*, suppliers(name), grape_varieties(code, name), product_lines(name)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_wine_purchase_by_id(purchase_id: int):
    return (get_supabase_client().table("wine_purchases")
            .select("*, suppliers(name), grape_varieties(code, name), product_lines(name)")
            .eq("id", purchase_id)
            .single()
            .execute().data)


def update_wine_purchase(purchase_id: int, data: dict):
    return (get_supabase_client().table("wine_purchases")
            .update(data).eq("id", purchase_id).execute().data)


def create_wine_delivery(data: dict):
    return get_supabase_client().table("wine_purchase_deliveries").insert(data).execute().data


def get_wine_deliveries(purchase_id: int):
    return (get_supabase_client().table("wine_purchase_deliveries")
            .select("*, tanks(code, name)")
            .eq("wine_purchase_id", purchase_id)
            .order("date")
            .execute().data)


def get_wine_purchases_by_status(status: str):
    q = (get_supabase_client().table("wine_purchases")
         .select("*, suppliers(name), grape_varieties(code, name)")
         .order("date", desc=True))
    if status and status != "Todos":
        q = q.eq("status", status)
    return q.execute().data
