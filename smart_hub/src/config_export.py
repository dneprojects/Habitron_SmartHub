from openpyxl import Workbook
from openpyxl.styles.fonts import Font
from openpyxl.styles.alignment import Alignment

from configuration import ModuleSettingsLight
from const import DATA_FILES_ADDON_DIR, DATA_FILES_DIR


header_font = Font(b=True, sz=14.0, color="c0372d")
subheader_font = Font(b=True, sz=12.0)
subheader_font_red = Font(b=True, sz=12.0, color="c0372d")
left_aligned = Alignment(horizontal="left")


def create_documentation(router, filename):
    """Take settings information and create full domumentation."""
    doc = Workbook()
    document_overview(doc, router.modules)

    for idx in range(len(router.modules)):
        mod = router.modules[idx]
        # ws.add_image("./web/configurator_files/logo.png", "F1")
        document_module(doc, mod, idx)
    del doc["Sheet"]
    if router.api_srv.is_addon:
        data_file_path = DATA_FILES_ADDON_DIR
    else:
        data_file_path = DATA_FILES_DIR
    doc.save(data_file_path + filename)


def document_overview(doc, mods):
    """Create system overview in excel sheet."""

    ws = doc.create_sheet("System", 0)
    row = 1
    ws.cell(row, 1).value = "Systemübersicht"
    ws.cell(row, 1).font = header_font
    row += 2
    ws.cell(row, 1).value = "Nr."
    ws.cell(row, 2).value = "Name"
    ws.cell(row, 3).value = "Typ"
    ws.cell(row, 4).value = "Bereich"
    ws.cell(row, 5).value = "Adr."
    ws.cell(row, 6).value = "Kanal"
    ws.cell(row, 1).font = subheader_font
    ws.cell(row, 2).font = subheader_font
    ws.cell(row, 3).font = subheader_font
    ws.cell(row, 4).font = subheader_font
    ws.cell(row, 5).font = subheader_font
    ws.cell(row, 6).font = subheader_font
    row += 1
    mod_cnt = 1
    for mod in mods:
        ws.cell(row, 1).value = f"{mod_cnt}"
        ws.cell(row, 1).alignment = left_aligned
        ws.cell(row, 2).value = mod._name
        ws.cell(row, 3).value = mod._type
        ws.cell(row, 4).value = mod.get_area_name()
        ws.cell(row, 5).value = f"{mod._id}"
        ws.cell(row, 6).value = f"{mod._channel}"
        mod_cnt += 1
        row += 1

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 28
    ws.set_printer_settings(ws.PAPERSIZE_A4, ws.ORIENTATION_LANDSCAPE)


def document_module(doc, mod, idx):
    """Export module information to excel sheet."""

    ws = doc.create_sheet(mod._name, idx + 1)
    input_type = {1: "Taster", 2: "Schalter", 3: "Analog"}
    output_type = {1: "", 2: "Dimmbar"}
    cover_type = {-1: "Rollladen", 1: "Rollladen", -2: "Jalousie", 2: "Jalousie"}
    settings = mod.settings

    row = 1
    ws.cell(row, 1).value = f"Modul '{mod._name}'"
    ws.cell(row, 1).font = header_font
    row += 2
    ws.cell(row, 1).value = "Typ:"
    ws.cell(row, 2).value = mod._type
    row += 1
    ws.cell(row, 1).value = "Adresse:"
    ws.cell(row, 2).value = mod._id
    ws.cell(row, 2).alignment = left_aligned
    ws.cell(row, 3).value = "Seriennnr.:"
    ws.cell(row, 4).value = mod._serial
    row += 1
    ws.cell(row, 1).value = "Kanal:"
    ws.cell(row, 2).value = mod._channel
    ws.cell(row, 2).alignment = left_aligned
    ws.cell(row, 3).value = "Firmware:"
    ws.cell(row, 4).value = mod.get_sw_version()
    row += 1
    ws.cell(row, 1).value = "Bereich:"
    ws.cell(row, 2).value = mod.get_area_name()

    if settings is None:
        settings = ModuleSettingsLight(mod)
    row += 2
    if len(settings.inputs):
        ws.cell(row, 1).value = "Eingänge"
        ws.cell(row, 1).font = subheader_font_red
        row += 1
        ws = write_col_headers(ws, row)
        row += 1
        for inpt in settings.inputs:
            ws.cell(row, 1).value = inpt.nmbr
            ws.cell(row, 1).alignment = left_aligned
            ws.cell(row, 2).value = inpt.name
            if mod._typ in [b"\x0a\x1e", b"\x0b\x1e", b"\x32\x01"]:
                ws.cell(row, 3).value = "24V"
            elif (
                mod._typ in [b"\x01\x01", b"\x01\x02", b"\x01\x03", b"\x0b\x1f"]
                and inpt.type == 3
            ):
                ws.cell(row, 3).value = "0..10V"
            elif mod._typ in [b"\x0b\x01"]:
                ws.cell(row, 3).value = "230V"
            elif inpt.nmbr in range(5, 11):
                ws.cell(row, 3).value = "24V"
            else:
                ws.cell(row, 3).value = "230V"
            ws.cell(row, 4).value = input_type[inpt.type]
            ws.cell(row, 5).value = get_area_name(inpt, mod)
            row += 1
        row += 1
    if len(settings.outputs):
        ws.cell(row, 1).value = "Ausgänge"
        ws.cell(row, 1).font = subheader_font_red
        row += 1
        ws = write_col_headers(ws, row)
        row += 1
        for outpt in settings.outputs:
            if outpt.type > 0:
                ws.cell(row, 1).value = outpt.nmbr
                ws.cell(row, 1).alignment = left_aligned
                ws.cell(row, 2).value = outpt.name
                if mod._typ in [b"\x0a\x01", b"\x0a\x1e", b"\x0a\x32", b"\x0a\x33"]:
                    ws.cell(row, 3).value = "Relais"
                elif mod._typ in [b"\x32\x01"]:
                    ws.cell(row, 3).value = "24V"
                elif outpt.nmbr == 15:
                    ws.cell(row, 3).value = "Relais"
                elif outpt.nmbr in [13, 14]:
                    ws.cell(row, 3).value = "24V"
                else:
                    ws.cell(row, 3).value = "230V"
                ws.cell(row, 4).value = output_type[outpt.type]
                ws.cell(row, 5).value = get_area_name(outpt, mod)
                row += 1
        row += 1
    if len(settings.covers):
        ws.cell(row, 1).value = "Rollladen"
        ws.cell(row, 1).font = subheader_font_red
        row += 1
        ws = write_col_headers(ws, row)
        row += 1
        for cov in settings.covers:
            if cov.type != 0:
                ws.cell(row, 1).value = cov.nmbr
                ws.cell(row, 1).alignment = left_aligned
                ws.cell(row, 2).value = cov.name
                ws.cell(row, 3).value = cover_type[cov.type]
                if cov.type > 0:
                    ws.cell(row, 4).value = "Ausgang A: auf, B: zu"
                else:
                    ws.cell(row, 4).value = "Ausgang A: zu, B: auf"
                ws.cell(row, 5).value = get_area_name(cov, mod)
                row += 1

    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 20


def write_col_headers(ws, row: int):
    """Set column headers."""

    ws.cell(row, 1).value = "Nr."
    ws.cell(row, 2).value = "Name"
    ws.cell(row, 3).value = "Typ"
    ws.cell(row, 4).value = "Konfiguration"
    ws.cell(row, 5).value = "Bereich"
    ws.cell(row, 1).font = subheader_font
    ws.cell(row, 2).font = subheader_font
    ws.cell(row, 3).font = subheader_font
    ws.cell(row, 4).font = subheader_font
    ws.cell(row, 5).font = subheader_font
    return ws


def get_area_name(entity, mod) -> str:
    """Return name of area."""

    if entity.area:
        return mod.api_srv.routers[mod.rt_id - 1].get_area_name(entity.area)
    else:
        return mod.get_area_name()
