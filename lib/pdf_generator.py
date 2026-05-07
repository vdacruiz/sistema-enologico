import io
from fpdf import FPDF


class OTPdf(FPDF):
    def __init__(self, logo_path=None):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.logo_path = logo_path

    def header_block(self, ot_number, ot_date):
        # --- Logo ---
        if self.logo_path:
            try:
                self.image(self.logo_path, x=12, y=10, w=35)
            except Exception:
                pass

        # --- Titulo central ---
        self.set_xy(50, 10)
        self.set_font("Helvetica", "B", 12)
        self.cell(100, 7, "SISTEMA DE GESTION INTEGRADO", align="C")
        self.set_xy(50, 18)
        self.set_font("Helvetica", "B", 13)
        self.cell(100, 8, "ORDEN DE TRABAJO", align="C")

        # --- Recuadro derecho ---
        self.set_font("Helvetica", "", 7)
        rx = 155
        ry = 10
        rw = 50
        rh = 5
        self.set_xy(rx, ry)
        self.cell(rw, rh, "R03 POE - 014", border=1, align="C")
        self.set_xy(rx, ry + rh)
        self.cell(rw, rh, "Version 3 del 8/10/2018", border=1, align="C")
        self.set_xy(rx, ry + rh * 2)
        self.cell(rw, rh, "Pagina 1 de 1", border=1, align="C")
        self.set_xy(rx, ry + rh * 3)
        self.cell(rw, rh, "Responsable", border=1, align="C")
        self.set_xy(rx, ry + rh * 4)
        self.cell(rw, rh, "Enologo Jefe", border=1, align="C")

        # --- Linea separadora ---
        self.set_draw_color(0, 0, 0)
        self.line(12, 37, 205, 37)

        # --- Fecha y Numero ---
        self.set_xy(12, 40)
        self.set_font("Helvetica", "B", 10)
        self.cell(50, 6, f"Fecha: {ot_date}", align="L")

        self.set_xy(150, 38)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 128, 0)
        self.cell(55, 8, f"N  {str(ot_number).zfill(6)}", align="R")
        self.set_text_color(0, 0, 0)

    def build(self, ot_data, lines, worker_name, creator_name):
        self.add_page()
        self.set_auto_page_break(auto=True, margin=25)

        ot_number = ot_data.get("ot_number", "?")
        ot_date = ot_data.get("date", "-")
        self.header_block(ot_number, ot_date)

        # --- Tabla ---
        self.set_xy(12, 50)

        col_widths = [22, 18, 28, 20, 65, 20, 22]
        headers = ["CUBA\nINICIAL", "CEPA", "CLASIFICACION", "CODIGO", "OBSERVACIONES", "CUBA\nFINAL", "LITROS\nFINALES"]

        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(240, 240, 240)
        y_start = self.get_y()
        for i, (w, h) in enumerate(zip(col_widths, headers)):
            x = 12 + sum(col_widths[:i])
            self.set_xy(x, y_start)
            self.multi_cell(w, 5, headers[i], border=1, align="C", fill=True)

        self.set_y(y_start + 10)

        # Datos de cabecera OT (primera fila)
        cepa = ot_data.get("grape_varieties", {})
        cepa_code = cepa.get("code", "-") if cepa else "-"
        process = ot_data.get("winemaking_processes", {})
        process_name = process.get("name", "-") if process else "-"
        source_tank = ot_data.get("source_tank_code") or str(ot_data.get("source_tank_id", "-") or "-")
        dest_tank = ot_data.get("dest_tank_code") or str(ot_data.get("dest_tank_id", "-") or "-")
        liters = ot_data.get("liters", "-") or "-"
        wine = ot_data.get("wines") or {}
        wine_code = wine.get("code", "") if isinstance(wine, dict) else ""

        self.set_font("Helvetica", "", 8)
        row_h = 7
        y = self.get_y()
        row_data = [
            str(source_tank),
            cepa_code,
            process_name,
            wine_code,
            ot_data.get("observations", "") or "",
            str(dest_tank),
            str(liters),
        ]
        for i, (w, val) in enumerate(zip(col_widths, row_data)):
            x = 12 + sum(col_widths[:i])
            self.set_xy(x, y)
            self.cell(w, row_h, str(val)[:30], border=1, align="C")
        self.set_y(y + row_h)

        # Lineas de insumos
        if lines:
            for line in lines:
                supply = line.get("supplies", {})
                supply_name = supply.get("name", "?") if supply else "?"
                supply_code = supply.get("code", "") if supply else ""
                qty = line.get("quantity", 0)
                planned = line.get("planned_quantity", qty)

                y = self.get_y()
                row_vals = [
                    "",
                    "",
                    "",
                    supply_code[:8],
                    f"{supply_name} - Cant: {planned}",
                    "",
                    "",
                ]
                for i, (w, val) in enumerate(zip(col_widths, row_vals)):
                    x = 12 + sum(col_widths[:i])
                    self.set_xy(x, y)
                    self.cell(w, row_h, str(val)[:40], border=1, align="C" if i != 4 else "L")
                self.set_y(y + row_h)

        # Filas vacias para completar
        empty_rows = max(10 - len(lines or []) - 1, 3)
        for _ in range(empty_rows):
            y = self.get_y()
            for i, w in enumerate(col_widths):
                x = 12 + sum(col_widths[:i])
                self.set_xy(x, y)
                self.cell(w, row_h, "", border=1)
            self.set_y(y + row_h)

        # --- Pie: Firmas ---
        self.ln(10)
        self.set_font("Helvetica", "B", 9)

        y = self.get_y()
        self.set_xy(12, y)
        self.cell(0, 6, f"Nombre del operario responsable de la orden: {worker_name}", align="L")
        self.ln(4)
        self.line(12, self.get_y() + 2, 205, self.get_y() + 2)

        self.ln(10)
        self.cell(0, 6, f"Nombre de la persona que emite la orden: {creator_name}", align="L")
        self.ln(4)
        self.line(12, self.get_y() + 2, 205, self.get_y() + 2)

        return self.output()


class OCPdf(FPDF):
    def __init__(self, logo_path=None):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.logo_path = logo_path

    def build(self, oc_data, lines, supplier_data=None):
        self.add_page()
        self.set_auto_page_break(auto=True, margin=25)

        # --- Cabecera empresa ---
        if self.logo_path:
            try:
                self.image(self.logo_path, x=155, y=10, w=40)
            except Exception:
                pass

        self.set_xy(12, 12)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 6, "Bodegas y Vinedos de Aguirre S.A.", align="L")
        self.set_xy(12, 18)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Vina Sol de Chile", align="L")

        # --- Datos proveedor ---
        self.set_y(30)
        self.set_font("Helvetica", "B", 10)
        supplier = oc_data.get("suppliers", {}) or supplier_data or {}
        supp_name = supplier.get("name", "-")
        supp_rut = supplier.get("rut", "-") or "-"
        supp_contact = supplier.get("contact_name", "-") or "-"
        supp_phone = supplier.get("phone", "-") or "-"
        supp_email = supplier.get("email", "-") or "-"

        fields = [
            ("Senores:", supp_name),
            ("Rut:", supp_rut),
            ("Atencion:", supp_contact),
            ("Telefono:", supp_phone),
            ("Correo Elect:", supp_email),
            ("Fecha:", oc_data.get("date", "-")),
        ]
        for label, val in fields:
            self.set_x(12)
            self.set_font("Helvetica", "B", 10)
            self.cell(30, 6, label, align="L")
            self.set_font("Helvetica", "", 10)
            self.cell(0, 6, str(val), align="L")
            self.ln(6)

        # --- Titulo ---
        self.ln(5)
        self.set_font("Helvetica", "B", 13)
        oc_num = oc_data.get("oc_number") or str(oc_data.get("id", "?"))
        self.cell(0, 8, f"ORDEN DE COMPRA N. {oc_num}", align="C")
        self.ln(3)

        # --- Linea ---
        self.line(12, self.get_y() + 2, 205, self.get_y() + 2)
        self.ln(6)

        # --- Info proyecto ---
        if oc_data.get("purchase_type") == "Vino":
            cepa = oc_data.get("grape_varieties", {})
            cepa_txt = cepa.get("code", "") if cepa else ""
            if cepa_txt:
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(0, 0, 200)
                self.cell(0, 5, f"CEPA: {cepa_txt} - {oc_data.get('wine_type', '')}", align="C")
                self.ln(5)
                self.set_text_color(0, 0, 0)

        # --- Tabla ---
        col_widths = [25, 90, 35, 40]
        headers = ["CANTIDAD", "DESCRIPCION", "VALOR NETO", "TOTAL"]

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(240, 240, 240)
        y = self.get_y()
        for i, (w, h) in enumerate(zip(col_widths, headers)):
            x = 12 + sum(col_widths[:i])
            self.set_xy(x, y)
            self.cell(w, 8, h, border=1, align="C", fill=True)
        self.set_y(y + 8)

        # Filas
        self.set_font("Helvetica", "", 9)
        row_h = 7
        subtotal = 0

        if oc_data.get("purchase_type") == "Insumos" and lines:
            for line in lines:
                supply = line.get("supplies", {})
                supply_name = supply.get("name", "?") if supply else "?"
                qty = line.get("quantity", 0)
                y = self.get_y()
                vals = [str(qty), supply_name, "", ""]
                for i, (w, val) in enumerate(zip(col_widths, vals)):
                    x = 12 + sum(col_widths[:i])
                    self.set_xy(x, y)
                    self.cell(w, row_h, str(val)[:50], border=1,
                              align="C" if i in (0, 2, 3) else "L")
                self.set_y(y + row_h)

        elif oc_data.get("purchase_type") == "Vino":
            liters = oc_data.get("expected_liters", 0) or 0
            ppl = float(oc_data.get("price_per_liter", 0) or 0)
            total_line = float(oc_data.get("total_price", 0) or 0)
            if total_line == 0 and ppl > 0:
                total_line = liters * ppl
            subtotal = total_line

            cepa = oc_data.get("grape_varieties", {})
            desc = f"Vino {oc_data.get('wine_type', '')} - {cepa.get('code', '') if cepa else ''}"

            y = self.get_y()
            vals = [str(liters), desc, f"$ {ppl:,.0f}" if ppl else "", f"$ {total_line:,.0f}" if total_line else ""]
            for i, (w, val) in enumerate(zip(col_widths, vals)):
                x = 12 + sum(col_widths[:i])
                self.set_xy(x, y)
                self.cell(w, row_h, val, border=1, align="C" if i in (0, 2, 3) else "L")
            self.set_y(y + row_h)

        elif oc_data.get("purchase_type") == "Uva":
            kilos = oc_data.get("expected_kilos", 0) or 0
            ppk = float(oc_data.get("price_per_kilo", 0) or 0)
            total_line = float(oc_data.get("total_price", 0) or 0)
            if total_line == 0 and ppk > 0:
                total_line = float(kilos) * ppk
            subtotal = total_line

            cepa = oc_data.get("grape_varieties", {})
            desc = f"Uva {cepa.get('code', '') if cepa else ''}"

            y = self.get_y()
            vals = [f"{kilos:,.0f} kg", desc, f"$ {ppk:,.0f}" if ppk else "", f"$ {total_line:,.0f}" if total_line else ""]
            for i, (w, val) in enumerate(zip(col_widths, vals)):
                x = 12 + sum(col_widths[:i])
                self.set_xy(x, y)
                self.cell(w, row_h, val, border=1, align="C" if i in (0, 2, 3) else "L")
            self.set_y(y + row_h)

        # Filas vacias
        for _ in range(max(8 - len(lines or []), 3)):
            y = self.get_y()
            for i, w in enumerate(col_widths):
                x = 12 + sum(col_widths[:i])
                self.set_xy(x, y)
                self.cell(w, row_h, "", border=1)
            self.set_y(y + row_h)

        # --- Totales ---
        total_price = float(oc_data.get("total_price", 0) or subtotal or 0)
        iva = total_price * 0.19
        total_con_iva = total_price + iva
        currency = oc_data.get("currency", "CLP")

        self.set_font("Helvetica", "B", 9)
        for label, val in [("NETO", total_price), ("IVA 19%", iva), ("TOTAL", total_con_iva)]:
            y = self.get_y()
            x_c = 12 + sum(col_widths[:2])
            self.set_xy(x_c, y)
            self.cell(col_widths[2], row_h, label, border=1, align="L")
            self.set_xy(x_c + col_widths[2], y)
            self.cell(col_widths[3], row_h, f"$ {val:,.0f}" if val else "", border=1, align="C")
            self.set_y(y + row_h)

        # --- Condiciones ---
        self.ln(8)
        self.set_font("Helvetica", "B", 9)
        conditions = [
            ("CONDICIONES DE PAGO:", "CREDITO"),
            ("ENTREGA:", ""),
            ("DESPACHO:", "ENTREGA EN PLANTA"),
        ]
        for label, val in conditions:
            self.set_x(12)
            self.cell(45, 5, label, align="L")
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, val, align="L")
            self.set_font("Helvetica", "B", 9)
            self.ln(5)

        # --- Facturacion ---
        self.ln(5)
        self.set_font("Helvetica", "B", 10)
        self.set_x(12)
        self.cell(30, 5, "FACTURAR A:", align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Bodegas y Vinedos de Aguirre S.A.", align="L")
        self.ln(5)
        self.set_x(42)
        self.cell(0, 5, "96.997.500-9", align="L")
        self.ln(5)
        self.set_x(42)
        self.cell(0, 5, "Avda. Kennedy N. 5454, Of. 601, Vitacura, Santiago", align="L")
        self.ln(5)
        self.set_x(42)
        self.cell(0, 5, "Giro: Produccion y Comercializacion de Vinos", align="L")

        # --- Firmas ---
        self.ln(15)
        y = self.get_y()

        self.line(12, y, 90, y)
        self.line(115, y, 195, y)
        self.set_xy(12, y + 2)
        self.set_font("Helvetica", "B", 8)
        self.cell(78, 5, "Realizada por", align="C")
        self.set_xy(115, y + 2)
        self.cell(80, 5, "V.B. Jefe de Area", align="C")

        y2 = y + 20
        self.line(12, y2, 90, y2)
        self.line(115, y2, 195, y2)
        self.set_xy(12, y2 + 2)
        self.cell(78, 5, "V.B. Gerente Area", align="C")
        self.set_xy(115, y2 + 2)
        self.cell(80, 5, "V.B. Gerente Adm. y Finanzas", align="C")

        return self.output()


def generate_ot_pdf(ot_data, lines, worker_name, creator_name, logo_path=None):
    pdf = OTPdf(logo_path=logo_path)
    return pdf.build(ot_data, lines, worker_name, creator_name)


def generate_oc_pdf(oc_data, lines=None, supplier_data=None, logo_path=None):
    pdf = OCPdf(logo_path=logo_path)
    return pdf.build(oc_data, lines or [], supplier_data)
