import pandas as pd
from datetime import date, datetime, timezone
from lib.database import get_supabase_client


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def get_work_order_by_id(work_order_id: int):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name), wines(code)")
            .eq("id", work_order_id)
            .single()
            .execute().data)


def get_work_orders(limit=50):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name), wines(code)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_work_order_lines(work_order_id: int):
    return (get_supabase_client().table("work_order_lines")
            .select("*, supplies(name, code, unit), supply_lots(lot_number, expiry_date)")
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
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name), wines(code)")
            .gte("date", from_date)
            .order("date", desc=True)
            .execute().data)


def get_work_orders_by_worker(worker_id: int):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name), wines(code), product_lines(name)")
            .eq("worker_id", worker_id)
            .order("date", desc=True)
            .limit(50)
            .execute().data)


def update_work_order_status(work_order_id: int, status: str, observations: str = None):
    data = {"status": status}
    if status == "En Proceso":
        data["started_at"] = _utcnow()
    elif status == "Completada":
        data["completed_at"] = _utcnow()
    if observations:
        data["observations"] = observations
    return (get_supabase_client().table("work_orders")
            .update(data).eq("id", work_order_id).execute().data)


def update_work_order_line(line_id: int, data: dict):
    return (get_supabase_client().table("work_order_lines")
            .update(data).eq("id", line_id).execute().data)


def complete_movement_ot(ot: dict):
    from datetime import date as _date
    client = get_supabase_client()
    src_id = ot.get("source_tank_id")
    dst_id = ot.get("dest_tank_id")
    liters = float(ot.get("liters") or 0)
    wine_id = ot.get("wine_id")
    movement_date = ot.get("date") or str(_date.today())
    if liters <= 0:
        return

    wine_data = {}
    if wine_id:
        wine_rec = client.table("wines").select("grape_variety_id, product_line_id, wine_type").eq("id", wine_id).execute().data
        if wine_rec:
            wine_data = wine_rec[0]

    src_data = {}
    if src_id:
        src_rows = client.table("tank_contents").select("*").eq("tank_id", src_id).execute().data
        if src_rows:
            src_data = src_rows[0]
            src_liters = float(src_data.get("current_liters", 0))
            if liters > src_liters:
                raise ValueError(
                    f"Cuba origen solo tiene {src_liters:.0f} L, se intentan mover {liters:.0f} L")

    if dst_id:
        tank_rec = client.table("tanks").select("capacity_liters").eq("id", dst_id).execute().data
        dst_rows = client.table("tank_contents").select("*").eq("tank_id", dst_id).execute().data
        dst_current = float(dst_rows[0].get("current_liters", 0)) if dst_rows else 0
        capacity = float((tank_rec[0].get("capacity_liters") or 0)) if tank_rec else 0
        if capacity > 0 and (dst_current + liters) > capacity:
            raise ValueError(
                f"Cuba destino capacidad {capacity:.0f} L, tiene {dst_current:.0f} L, "
                f"no caben {liters:.0f} L mas")

    if src_id and src_data:
        new_liters = max(float(src_data.get("current_liters", 0)) - liters, 0)
        update = {"current_liters": new_liters, "updated_at": _utcnow()}
        if new_liters == 0:
            update["status"] = "Vacio"
            update["wine_id"] = None
            update["grape_variety_id"] = None
            update["product_line_id"] = None
            update["wine_type"] = None
            update["wine_state"] = None
            update["apto_envasado"] = False
            update["apto_envasado_at"] = None
            update["apto_envasado_by"] = None
            update["vintage_year"] = None
            update["fml"] = None
            update["last_analysis_date"] = None
            update["alcohol_degree"] = None
            update["ph"] = None
            update["total_acidity"] = None
            update["volatile_acidity"] = None
            update["free_so2"] = None
            update["total_so2"] = None
            update["residual_sugar"] = None
            update["so2_molecular"] = None
            update["ntu"] = None
            update["color"] = None
            update["co2"] = None
            update["test_color_4"] = False
            update["test_color_4_date"] = None
            update["test_tartarica_neg4"] = False
            update["test_tartarica_neg4_date"] = None
            update["fecha_ac"] = None
            update["control_mensual_date"] = None
            update["blend_notes"] = None
            update["last_operation"] = "Vaciada por OT"
        else:
            update["last_operation"] = f"Traspaso salida {liters:.0f} L"
        client.table("tank_contents").update(update).eq("id", src_data["id"]).execute()

    copy_fields = {
        "wine_id": wine_id,
        "grape_variety_id": wine_data.get("grape_variety_id") or src_data.get("grape_variety_id"),
        "product_line_id": wine_data.get("product_line_id") or src_data.get("product_line_id"),
        "wine_type": wine_data.get("wine_type") or src_data.get("wine_type"),
        "wine_state": src_data.get("wine_state"),
        "vintage_year": src_data.get("vintage_year"),
        "fml": src_data.get("fml"),
    }
    lab_fields = [
        "last_analysis_date", "alcohol_degree", "ph", "total_acidity",
        "volatile_acidity", "free_so2", "total_so2", "residual_sugar",
        "so2_molecular", "ntu", "color", "co2",
        "test_color_4", "test_color_4_date", "test_tartarica_neg4",
        "test_tartarica_neg4_date", "fecha_ac", "control_mensual_date", "blend_notes",
    ]
    lab_copy = {}
    for f in lab_fields:
        val = src_data.get(f)
        if val is not None:
            lab_copy[f] = val

    if dst_id:
        dst = client.table("tank_contents").select("*").eq("tank_id", dst_id).execute().data
        if dst:
            dst = dst[0]
            new_liters = float(dst.get("current_liters", 0)) + liters
            update = {
                "current_liters": new_liters,
                "status": "Ocupado",
                "last_operation": f"Traspaso entrada {liters:.0f} L",
                "updated_at": _utcnow(),
            }
            if not dst.get("wine_id"):
                update.update(copy_fields)
                update.update(lab_copy)
            client.table("tank_contents").update(update).eq("id", dst["id"]).execute()
        else:
            insert = {
                "tank_id": dst_id,
                "current_liters": liters,
                "status": "Ocupado",
                "last_operation": f"Traspaso entrada {liters:.0f} L",
            }
            insert.update(copy_fields)
            insert.update(lab_copy)
            client.table("tank_contents").insert(insert).execute()

    client.table("tank_movements").insert({
        "date": movement_date,
        "source_tank_id": src_id,
        "dest_tank_id": dst_id,
        "wine_id": wine_id,
        "liters": liters,
        "operation": "Traspaso",
        "work_order_id": ot["id"],
    }).execute()


def delete_work_order(work_order_id: int):
    get_supabase_client().table("work_order_lines").delete().eq("work_order_id", work_order_id).execute()
    return get_supabase_client().table("work_orders").delete().eq("id", work_order_id).execute().data


def search_work_orders(search_term: str = None, from_date: str = None, to_date: str = None, status: str = None):
    q = (get_supabase_client().table("work_orders")
         .select("*, grape_varieties(code, name), workers(full_name), winemaking_processes(name), wines(code)")
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
                   search_lower in str((r.get("winemaking_processes") or {}).get("name", "")).lower() or
                   search_lower in str((r.get("wines") or {}).get("code", "")).lower()]
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
            .select("*, tanks(code, name, capacity_liters), wines(code), grape_varieties(code, name), product_lines(name)")
            .execute().data)


def get_work_orders_by_tank(tank_id: int, limit=20):
    q1 = (get_supabase_client().table("work_orders")
          .select("id, ot_number, date, status, ot_type, liters, winemaking_processes(name), wines(code)")
          .eq("source_tank_id", tank_id)
          .order("date", desc=True)
          .limit(limit)
          .execute().data)
    q2 = (get_supabase_client().table("work_orders")
          .select("id, ot_number, date, status, ot_type, liters, winemaking_processes(name), wines(code)")
          .eq("dest_tank_id", tank_id)
          .order("date", desc=True)
          .limit(limit)
          .execute().data)
    seen = set()
    combined = []
    for ot in q1 + q2:
        if ot["id"] not in seen:
            seen.add(ot["id"])
            combined.append(ot)
    combined.sort(key=lambda x: x.get("date", ""), reverse=True)
    return combined[:limit]


# ============================================================
# RECEPCION DE VINO
# ============================================================

def create_wine_reception(data: dict):
    return get_supabase_client().table("wine_receptions").insert(data).execute().data


def get_wine_receptions(limit=50):
    return (get_supabase_client().table("wine_receptions")
            .select("*, grape_varieties(code, name), product_lines(name), "
                    "suppliers(name), tanks:dest_tank_id(code, name)")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_wine_reception_by_id(reception_id: int):
    return (get_supabase_client().table("wine_receptions")
            .select("*, grape_varieties(code, name), product_lines(name), "
                    "suppliers(name), tanks:dest_tank_id(code, name)")
            .eq("id", reception_id)
            .single()
            .execute().data)


def get_wine_receptions_pending_invoice(limit=200):
    return (get_supabase_client().table("wine_receptions")
            .select("*, grape_varieties(code, name), product_lines(name), "
                    "suppliers(name), tanks:dest_tank_id(code, name)")
            .eq("reception_type", "Compra Vino")
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def update_wine_reception(reception_id: int, data: dict):
    return (get_supabase_client().table("wine_receptions")
            .update(data).eq("id", reception_id).execute().data)


def get_wine_by_code(code: str):
    result = (get_supabase_client().table("wines")
              .select("*").eq("code", code).execute().data)
    return result[0] if result else None


def find_or_create_wine(code: str, grape_variety_id: int, product_line_id: int = None,
                        wine_type: str = "Tinto", vintage_year: int = None):
    existing = get_wine_by_code(code)
    if existing:
        return existing
    data = {"code": code, "grape_variety_id": grape_variety_id, "wine_type": wine_type}
    if product_line_id:
        data["product_line_id"] = product_line_id
    if vintage_year:
        data["vintage_year"] = vintage_year
    result = get_supabase_client().table("wines").insert(data).execute().data
    return result[0]


def assign_wine_to_tank(tank_id: int, wine_id: int, liters: float,
                        grape_variety_id: int = None, product_line_id: int = None,
                        wine_type: str = None, vintage_year: int = None,
                        alcohol_degree: float = None, so2_total: float = None,
                        ph: float = None):
    client = get_supabase_client()
    existing = client.table("tank_contents").select("id, current_liters, status").eq("tank_id", tank_id).execute().data
    update_data = {
        "wine_id": wine_id,
        "status": "Ocupado",
        "updated_at": _utcnow(),
    }
    if grape_variety_id:
        update_data["grape_variety_id"] = grape_variety_id
    if product_line_id:
        update_data["product_line_id"] = product_line_id
    if wine_type:
        update_data["wine_type"] = wine_type
    if vintage_year:
        update_data["vintage_year"] = vintage_year
    if alcohol_degree and alcohol_degree > 0:
        update_data["alcohol_degree"] = alcohol_degree
    if so2_total and so2_total > 0:
        update_data["total_so2"] = so2_total
    if ph and ph > 0:
        update_data["ph"] = ph

    if existing:
        current = existing[0].get("current_liters") or 0
        update_data["current_liters"] = current + liters
        client.table("tank_contents").update(update_data).eq("tank_id", tank_id).execute()
    else:
        update_data["tank_id"] = tank_id
        update_data["current_liters"] = liters
        client.table("tank_contents").insert(update_data).execute()

    client.table("tank_movements").insert({
        "date": date.today().isoformat(),
        "dest_tank_id": tank_id,
        "wine_id": wine_id,
        "liters": liters,
        "operation": "Recepcion",
    }).execute()


# ============================================================
# LABORATORIO
# ============================================================

def get_lab_parameters(wine_type: str = None):
    q = (get_supabase_client().table("lab_parameters")
         .select("*").eq("is_active", True).order("sort_order"))
    if wine_type:
        q = q.eq("wine_type", wine_type)
    return q.execute().data


def get_next_analysis_number():
    result = (get_supabase_client().table("lab_analyses")
              .select("analysis_number")
              .not_.is_("analysis_number", "null")
              .order("analysis_number", desc=True)
              .limit(1)
              .execute().data)
    if result:
        return result[0]["analysis_number"] + 1
    return 1


def create_lab_analysis(data: dict):
    if "analysis_number" not in data:
        data["analysis_number"] = get_next_analysis_number()
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


def get_lab_history_for_wine(wine_id: int):
    analyses = (get_supabase_client().table("lab_analyses")
                .select("id, date, tank_id, tanks(code)")
                .eq("wine_id", wine_id)
                .order("date")
                .execute().data)
    if not analyses:
        return []
    results = []
    for a in analyses:
        r = (get_supabase_client().table("lab_analysis_results")
             .select("*, lab_parameters(code, name, unit, min_normal, max_normal, alert_value, critical_value)")
             .eq("analysis_id", a["id"])
             .execute().data)
        tank = a.get("tanks") or {}
        for item in r:
            item["date"] = a["date"]
            item["tank_code"] = tank.get("code", "-") if isinstance(tank, dict) else "-"
        results.extend(r)
    return results


def get_wines_in_tanks():
    client = get_supabase_client()
    contents = (client.table("tank_contents")
                .select("tank_id, wine_id, grape_variety_id, wine_type, current_liters, status, "
                        "wine_state, apto_envasado, apto_envasado_at, apto_envasado_by, "
                        "last_analysis_date, alcohol_degree, ph, total_acidity, volatile_acidity, "
                        "free_so2, total_so2, residual_sugar, so2_molecular, ntu, color, co2, "
                        "fml, vintage_year, "
                        "test_color_4, test_color_4_date, test_tartarica_neg4, test_tartarica_neg4_date, "
                        "fecha_ac, control_mensual_date, blend_notes, "
                        "tanks(id, code), wines(id, code), grape_varieties(code, name)")
                .not_.is_("wine_id", "null")
                .order("tank_id")
                .execute().data)
    return contents


def get_latest_analysis_for_wine(wine_id: int):
    result = (get_supabase_client().table("lab_analyses")
              .select("id, date, tank_id, stage, analyst, notes, status, tanks(code)")
              .eq("wine_id", wine_id)
              .order("date", desc=True)
              .limit(1)
              .execute().data)
    return result[0] if result else None


def get_latest_analysis_for_tank(tank_id: int):
    result = (get_supabase_client().table("lab_analyses")
              .select("id, date, tank_id, stage, analyst, notes, status, tanks(code)")
              .eq("tank_id", tank_id)
              .order("date", desc=True)
              .limit(1)
              .execute().data)
    return result[0] if result else None


def get_wines():
    return (get_supabase_client().table("wines")
            .select("*, grape_varieties(id, code, name), product_lines(id, name)")
            .eq("is_active", True).order("code").execute().data)


def create_wine(data: dict):
    return get_supabase_client().table("wines").insert(data).execute().data


def get_wine_by_id(wine_id: int):
    result = (get_supabase_client().table("wines")
              .select("*, grape_varieties(id, code, name), product_lines(id, name)")
              .eq("id", wine_id).execute().data)
    return result[0] if result else None


def get_work_orders_by_wine(wine_id: int, limit=100):
    return (get_supabase_client().table("work_orders")
            .select("*, grape_varieties(code), workers(full_name), winemaking_processes(name), wines(code)")
            .eq("wine_id", wine_id)
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


def get_tank_movements_by_wine(wine_id: int, limit=50):
    return (get_supabase_client().table("tank_movements")
            .select("*, wines(code), work_orders(ot_number)")
            .eq("wine_id", wine_id)
            .order("date", desc=True)
            .limit(limit)
            .execute().data)


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


# ============================================================
# ORDENES DE COMPRA UNIFICADAS
# ============================================================

def get_purchase_orders_unified(purchase_type: str = None, status: str = None, limit=100):
    q = (get_supabase_client().table("purchase_orders")
         .select("*, suppliers(name), grape_varieties(code, name), product_lines(name)")
         .order("date", desc=True)
         .limit(limit))
    if purchase_type and purchase_type != "Todos":
        q = q.eq("purchase_type", purchase_type)
    if status and status != "Todos":
        q = q.eq("status", status)
    return q.execute().data


def get_purchase_order_by_id(po_id: int):
    return (get_supabase_client().table("purchase_orders")
            .select("*, suppliers(name, rut, contact_name, phone, email), grape_varieties(code, name), product_lines(name)")
            .eq("id", po_id)
            .single()
            .execute().data)


def update_purchase_order(po_id: int, data: dict):
    return (get_supabase_client().table("purchase_orders")
            .update(data).eq("id", po_id).execute().data)


def delete_purchase_order(po_id: int):
    get_supabase_client().table("purchase_order_lines").delete().eq("purchase_order_id", po_id).execute()
    return get_supabase_client().table("purchase_orders").delete().eq("id", po_id).execute().data


def get_po_wine_deliveries(po_id: int):
    return (get_supabase_client().table("wine_purchase_deliveries")
            .select("*, tanks(code, name)")
            .eq("purchase_order_id", po_id)
            .order("date")
            .execute().data)


def create_po_wine_delivery(data: dict):
    return get_supabase_client().table("wine_purchase_deliveries").insert(data).execute().data


def get_po_grape_deliveries(po_id: int):
    return (get_supabase_client().table("grape_reception_deliveries")
            .select("*, tanks(code, name)")
            .eq("purchase_order_id", po_id)
            .order("date")
            .execute().data)


def create_po_grape_delivery(data: dict):
    return get_supabase_client().table("grape_reception_deliveries").insert(data).execute().data


def get_po_supply_lines(po_id: int):
    return (get_supabase_client().table("purchase_order_lines")
            .select("*, supplies(name, code, unit)")
            .eq("purchase_order_id", po_id)
            .execute().data)


# ============================================================
# BACKFILL / MANTENIMIENTO
# ============================================================

def backfill_analyses_wine_id():
    client = get_supabase_client()
    analyses = client.table("lab_analyses").select("id, tank_id").is_("wine_id", "null").not_.is_("tank_id", "null").execute().data
    updated = 0
    for a in analyses:
        tc = client.table("tank_contents").select("wine_id").eq("tank_id", a["tank_id"]).execute().data
        if tc and tc[0].get("wine_id"):
            client.table("lab_analyses").update({"wine_id": tc[0]["wine_id"]}).eq("id", a["id"]).execute()
            updated += 1
    return updated


# ============================================================
# LOTES DE EMBOTELLADO
# ============================================================

def create_bottling_lot(data: dict):
    return get_supabase_client().table("bottling_lots").insert(data).execute().data


def get_bottling_lots(limit=50):
    return (get_supabase_client().table("bottling_lots")
            .select("*, wines(code), grape_varieties(code, name), product_lines(name), tanks(code)")
            .order("bottling_date", desc=True)
            .limit(limit)
            .execute().data)


def get_bottling_lot_by_number(lot_number: str):
    result = (get_supabase_client().table("bottling_lots")
              .select("*, wines(code, grape_variety_id, product_line_id, wine_type, notes), "
                      "grape_varieties(code, name), product_lines(name), tanks(code)")
              .eq("lot_number", lot_number)
              .execute().data)
    return result[0] if result else None


def get_bottling_lots_by_wine(wine_id: int):
    return (get_supabase_client().table("bottling_lots")
            .select("*, tanks(code)")
            .eq("wine_id", wine_id)
            .order("bottling_date", desc=True)
            .execute().data)


def search_bottling_lots(search_term: str = None, from_date: str = None, to_date: str = None):
    q = (get_supabase_client().table("bottling_lots")
         .select("*, wines(code), grape_varieties(code, name), product_lines(name), tanks(code)")
         .order("bottling_date", desc=True)
         .limit(100))
    if from_date:
        q = q.gte("bottling_date", from_date)
    if to_date:
        q = q.lte("bottling_date", to_date)
    results = q.execute().data
    if search_term:
        s = search_term.lower()
        results = [r for r in results if
                   s in r.get("lot_number", "").lower() or
                   s in ((r.get("wines") or {}).get("code", "")).lower() or
                   s in ((r.get("grape_varieties") or {}).get("code", "")).lower()]
    return results
