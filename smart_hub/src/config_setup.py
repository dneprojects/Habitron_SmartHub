from aiohttp import web
from config_commons import (
    get_module_image,
    show_modules,
    get_html,
    client_not_authorized,
    show_not_authorized,
    activate_side_menu,
)
from const import (
    CONF_PORT,
    MODULE_TYPES,
)

routes = web.RouteTableDef()


class ConfigSetupServer:
    """Web server for setup tasks."""

    def __init__(self, parent, api_srv):
        self.api_srv = api_srv
        self._ip = api_srv.sm_hub._host_ip
        self._port = CONF_PORT
        self.parent = parent
        self.app = web.Application()
        self.app.add_routes(routes)
        self.app["parent"] = self.parent

    @routes.get("/")
    async def setup_page(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_setup_page(main_app)

    @routes.get("/add")
    async def type_list(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_module_types(main_app)

    @routes.get("/add_type-{mod_cat}-{mod_subtype}")
    async def add_type(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        if len(rtr.modules) == 0:
            rtr._name = "NewRouter"
            rtr.get_router_settings()
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        mod_type = int(request.match_info["mod_cat"])
        mod_subtype = int(request.match_info["mod_subtype"])
        mod_typ = (chr(mod_type) + chr(mod_subtype)).encode("iso8859-1")
        # popup für Kanal und Adresse
        rtr_chan = int(request.query["chan_number"])
        mod_addr = int(request.query["mod_addr"])
        mod_serial = request.query["mod_serial"]
        mod_name = f"NewModule_{len(rtr.modules) + 1}"
        rtr.new_module(rtr_chan, mod_addr, mod_typ, mod_name, mod_serial)
        return show_module_types(main_app)

    @routes.get("/remove")
    async def mod_remove(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        mod_addr = int(request.query["RemoveModule"])
        rtr.rem_module(mod_addr)
        return show_modules(main_app)

    @routes.get("/table_close")
    async def tbl_close(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        return show_setup_page(main_app, "Änderungen verworfen")

    @routes.get("/adapt")
    async def mod_adapt(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_module_table(main_app)

    @routes.get("/apply")
    async def tbl_apply(request: web.Request) -> web.Response:  # type: ignore
        main_app = request.app["parent"]
        rtr = main_app["api_srv"].routers[0]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        rtr.apply_id_chan_changes(request.query)
        return show_setup_page(
            main_app,
            "Änderungen übernommen,<br>müssen aber noch übertragen oder<br>als Systemkonfiguration gesichert werden",
        )


def show_setup_page(app, popup_msg="") -> web.Response:
    """Prepare modules page."""
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    page = get_html("setup.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>HubTitle", "<h1>Habitron-Geräte einrichten")
    page = page.replace("Overview", "Installationsbereich")
    if not app["api_srv"].is_offline:
        page = page.replace(
            "ContentText",
            "<h3>Module anlegen</h3>"
            + "Hier werden die Module erstmalig angelegt:<br>"
            + "1. Modultyp auswählen<br>"
            + "2. Die Seriennummer, Modul-Adresse und das Kanalpaar des Routers eingeben,<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;an dem das Modul angeschlossen werden soll.<br>"
            + "3. Router und Module können in den Bereichen 'Router' und 'Module'<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;umbenannt und weiter konfiguriert werden.<br>"
            + "4. Erst mit dem Button 'Übertragen' auf dieser Seite erhalten die intern angelegten<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Module im System ihre Adressen und werden im Router registriert.<br>"
            + "<h3>Module verwalten</h3>"
            + "1. Bereits angelegte Module können bezüglich der Adresse und der<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Kanalzuordnung angepasst werden.<br>"
            + "2. Module können ausgewählt und aus der Konfiguration entfernt werden.<br>"
            + "3. Mit dem Button 'Übernehmen' wird die neue Adress- und Kanalzuordnung<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;intern im Configurator abgelegt, aber noch nicht übertragen.<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Die Änderungen können mit 'Abbruch' auch verworfen werden.<br>"
            + "4. Mit dem Button 'Übertragen' auf dieser Seite wird die Konfiguration in die <br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Habitron-Anlage übertragen und dort umgesetzt.<br>"
            + "5. Über 'Systemkonfiguration' kann die Konfiguration auch als Download gespeichert<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;werden, um später in die Anlage übertragen zu werden."
            + "<h3>Module testen</h3>"
            + "1. Bereits angelegte und in der Habitron-Anlage eingespeicherte Module<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;können ausgewählt werden.<br>"
            + "2. Auf der folgenden Seite kann das gewählte Modul getestet werden, indem<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Eingangszustände angezeigt und Ausgänge geschaltet werden.<br>",
        )
    else:
        page = page.replace(
            "ContentText",
            "<h3>Module anlegen</h3>"
            + "Hier werden die Module erstmalig angelegt:<br>"
            + "1. Modultyp auswählen<br>"
            + "2. Die Seriennummer, Modul-Adresse und das Kanalpaar des Routers eingeben,<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;an dem das Modul angeschlossen werden soll.<br>"
            + "3. Router und Module können in den Bereichen 'Router' und 'Module'<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;umbenannt und weiter konfiguriert werden.<br>"
            + "<h3>Module verwalten</h3>"
            + "1. Bereits angelegte Module können bezüglich der Adresse und der<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Kanalzuordnung angepasst werden.<br>"
            + "2. Module können ausgewählt und aus der Konfiguration entfernt werden.<br>"
            + "3. Mit dem Button 'Übernehmen' wird die neue Adress- und Kanalzuordnung<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;intern im Configurator abgelegt.<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;Die Änderungen können mit 'Abbruch' auch verworfen werden.<br>"
            + "4. Über 'Systemkonfiguration' kann die Konfiguration auch als Download gespeichert<br>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;werden, um später in die Anlage übertragen zu werden.",
        )
    page = page.replace(">Abbruch<", ' style="visibility: hidden;">Abbruch<')
    page = page.replace(">Übernehmen<", ' style="visibility: hidden;">Übernehmen<')
    if len(popup_msg):
        page = page.replace(
            '<h3 id="resp_popup_txt">response_message</h3>',
            f'<h3 id="resp_popup_txt">{popup_msg}</h3>',
        ).replace('id="resp-popup-disabled"', 'id="resp-popup"')
    if app["api_srv"].is_offline:
        page = page.replace(">Übertragen<", ' style="visibility: hidden;">Übertragen<')
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_module_types(app) -> web.Response:
    """Prepare modules page."""
    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    side_menu = activate_side_menu(side_menu, ">Module anlegen<", app["is_offline"])
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>Module", "<h1>Module anlegen")
    page = page.replace("Übersicht", "Mögliche Modultypen")
    page = page.replace(
        "Wählen Sie ein Modul aus",
        "Zum Neuanlegen eines Moduls wählen Sie den Modultyp aus",
    )
    images = ""
    for m_item in MODULE_TYPES.items():
        m_type = m_item[0]
        type_str = str(ord(m_type[0])) + "-" + str(ord(m_type[1]))
        pic_file, title = get_module_image(m_type.encode())
        images += f'<div class="figd_grid" name="add_type_img" id=add-type-{type_str}><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{MODULE_TYPES[m_type]}"><p class="mod_subtext">{MODULE_TYPES[m_type]}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("const mod_addrs = [];", f"const mod_addrs = {rtr.mod_addrs};")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_module_table(app) -> web.Response:
    """Build html table string from table line list."""
    side_menu = activate_side_menu(app["side_menu"], ">Einrichten<", app["is_offline"])
    side_menu = activate_side_menu(side_menu, ">Module verwalten<", app["is_offline"])
    page = get_html("setup.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>HubTitle", "<h1>Module verwalten")
    page = page.replace("Overview", "Modulübersicht")
    page = page.replace(
        "<p>ContentText</p>",
        "<p>Moduladressen und Kanalzugehörigkeit anpassen, sowie Module entfernen</p><br>\n<p>ContentText</p>",
    )

    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]

    tr_line = '        <tr id="inst-tr">\n'
    tre_line = "        </tr>\n"
    td_line = "            <td></td>\n"
    thead_lines = (
        '<form action="setup/apply" id="table-form">\n'
        '<table id="mod-table">\n'
        + "    <thead>\n"
        + '        <tr id="inst-th">\n'
        + "            <th>Name</th>\n"
        + "            <th data-sort-method='number' data-sort-input-attr='value'>Adr.</th>\n"
        + "            <th>Typ</th>\n"
        + "            <th data-sort-method='number' data-sort-input-attr='value'>Kanal</th>\n"
        + "            <th></th>\n"
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tend_lines = (
        "  </tbody>\n</table>\n"
        + '<button name="RemoveModules" id="tbl-button" type="button" disabled>Module entfernen</button>'
        + "</form>\n"
    )

    table_str = thead_lines
    for mod in rtr.modules:
        table_str += tr_line
        table_str += td_line.replace("><", f">{mod._name}<")
        table_str += td_line.replace(
            "><",
            f'><input type="number" value="{mod._id}" class="mod_ids" name="modid_{mod._serial}" id="modno-{mod._serial}" min="1" max="64"><',
        )
        table_str += td_line.replace("><", f">{mod._type}<")
        table_str += td_line.replace(
            "><",
            f'><input type="number" value="{mod._channel}" class="mod_chans" name="modchan_{mod._serial}" id="modch-{mod._serial}" min="1" max="4"><',
        )
        table_str += td_line.replace(
            "><",
            f'><input type="checkbox" class="mod_sels" name="modsel_{mod._id}" id="mod-{mod._id}"><',
        )
        table_str += tre_line
    table_str += tend_lines
    page = page.replace("ContentText", table_str)
    page = page.replace(
        '<script type="text/javascript" src="configurator_files/files.js"></script>', ""
    )
    page = page.replace(">Übertragen<", ' style="visibility: hidden;">Übertragen<')
    page = page.replace(
        '">Systemkonfiguration<', ' visibility: hidden;">Systemkonfiguration<'
    )
    return web.Response(text=page, content_type="text/html", charset="utf-8")
