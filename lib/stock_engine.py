from lib.database import get_supabase_client


def get_available_stock(supply_id: int, lot_id: int = None) -> float:
    client = get_supabase_client()
    if lot_id:
        result = (client.table("v_supply_stock_by_lot")
                  .select("current_stock")
                  .eq("lot_id", lot_id)
                  .execute().data)
    else:
        result = (client.table("v_supply_stock_total")
                  .select("total_stock")
                  .eq("supply_id", supply_id)
                  .execute().data)
    if result:
        return float(result[0].get("current_stock") or result[0].get("total_stock") or 0)
    return 0.0


def check_availability(supply_id: int, lot_id: int, quantity: float) -> tuple[bool, str]:
    available = get_available_stock(supply_id, lot_id)
    if quantity <= 0:
        return False, "La cantidad debe ser mayor a 0"
    if quantity > available:
        return False, f"Stock insuficiente. Disponible: {available:.2f}"
    return True, "OK"


def get_lots_with_stock(supply_id: int) -> list:
    result = (get_supabase_client().table("v_supply_stock_by_lot")
              .select("*")
              .eq("supply_id", supply_id)
              .gt("current_stock", 0)
              .order("expiry_date")
              .execute().data)
    return result
