from openpyxl import Workbook
from openpyxl.styles.fonts import Font

from configuration import ModuleSettingsLight
from const import DATA_FILES_ADDON_DIR, DATA_FILES_DIR


def create_documentation(router, filename):
    """Take settings information and create full domumentation."""
    doc = Workbook()

    for idx in range(len(router.modules)):
        mod = router.modules[idx]
        ws = doc.create_sheet(mod._name, idx)
        # ws.add_image("./web/configurator_files/logo.png", "F1")
        document_module(ws, mod)
    del doc["Sheet"]
    if router.api_srv.is_addon:
        data_file_path = DATA_FILES_ADDON_DIR
    else:
        data_file_path = DATA_FILES_DIR
    doc.save(data_file_path + filename)


def document_module(ws, mod):
    """Export module information to excel sheet."""

    input_type = {1: "Taster", 2: "Schalter", 3: "Analog"}
    output_type = {1: "", 2: "Dimmbar"}
    cover_type = {-1: "Rollladen", 1: "Rollladen", -2: "Jalousie", 2: "Jalousie"}
    settings = mod.settings
    header_font = Font(b=True, sz=14.0)
    subheader_font = Font(b=True, sz=12.0)

    row = 1
    ws.cell(row, 1).value = mod._name
    ws.cell(row, 1).font = header_font
    row += 2
    ws.cell(row, 1).value = "Typ:"
    ws.cell(row, 2).value = mod._type
    row += 1
    ws.cell(row, 1).value = "Adresse:"
    ws.cell(row, 2).value = mod._id
    ws.cell(row, 3).value = "Seriennnr.:"
    ws.cell(row, 4).value = mod._serial
    row += 1
    ws.cell(row, 1).value = "Kanal:"
    ws.cell(row, 2).value = mod._channel
    ws.cell(row, 3).value = "Firmware:"
    ws.cell(row, 4).value = mod.get_sw_version()
    row += 1
    ws.cell(row, 1).value = "Bereich:"

    if settings is None:
        settings = ModuleSettingsLight(mod)
    row += 2
    if len(settings.inputs):
        ws.cell(row, 1).value = "Eingänge"
        ws.cell(row, 1).font = subheader_font
        row += 1
        for inpt in settings.inputs:
            ws.cell(row, 1).value = inpt.nmbr
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
            row += 1
        row += 1
    if len(settings.outputs):
        ws.cell(row, 1).value = "Ausgänge"
        ws.cell(row, 1).font = subheader_font
        row += 1
        for outpt in settings.outputs:
            if outpt.type > 0:
                ws.cell(row, 1).value = outpt.nmbr
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
                row += 1
        row += 1
    if len(settings.covers):
        ws.cell(row, 1).value = "Rollladen"
        ws.cell(row, 1).font = subheader_font
        row += 1
        for cov in settings.covers:
            if cov.type != 0:
                ws.cell(row, 1).value = cov.nmbr
                ws.cell(row, 2).value = cov.name
                ws.cell(row, 3).value = cover_type[cov.type]
                if cov.type > 0:
                    ws.cell(row, 4).value = "Ausgang A: auf, B: zu"
                else:
                    ws.cell(row, 4).value = "Ausgang A: zu, B: auf"
                row += 1

    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 20
