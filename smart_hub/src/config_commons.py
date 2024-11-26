from aiohttp import web
from const import (
    WEB_FILES_DIR,
    SIDE_MENU_FILE,
    CONFIG_TEMPLATE_FILE,
    ALLOWED_INGRESS_IPS,
    CONF_HOMEPAGE,
    DOCUMENTATIONPAGE,
    HUB_HOMEPAGE,
    HOMEPAGE,
    MESSAGE_PAGE,
    INSTALLER_GROUP,
    SMHUB_INFO,
    LOGGING_LEVELS,
)


def inspect_header(req: web.Request):
    """Get login information from header."""
    if "api_srv" in req.app.keys():
        main_app = req.app
    else:
        main_app = req.app["parent"]
    api_srv = main_app["api_srv"]
    if api_srv.is_addon:
        api_srv.user_login = req.headers["X-Remote-User-Name"]
        api_srv.hass_ip = req.headers["Host"].split(":")[0]
        if (
            api_srv.user_login.lower() in INSTALLER_GROUP
            and main_app["is_install"] is False
        ):
            main_app["is_install"] = True
        elif (
            api_srv.user_login.lower() not in INSTALLER_GROUP
            and main_app["is_install"] is True
        ):
            main_app["is_install"] = False
            init_side_menu(main_app)
    elif api_srv._pc_mode:
        api_srv.user_login = ""
        main_app["is_install"] = True
    elif api_srv.is_offline:
        api_srv.user_login = ""
        main_app["is_install"] = False
    else:  # Development
        api_srv.user_login = ""
        main_app["is_install"] = True
    init_side_menu(main_app)


def get_html(html_file) -> str:
    """Return loaded html page."""
    with open(WEB_FILES_DIR + html_file, mode="r", encoding="utf-8") as pg_id:
        return pg_id.read()


def html_response(html_file) -> web.Response:
    """Return loaded html page as web response."""
    with open(WEB_FILES_DIR + html_file, mode="r", encoding="utf-8") as pg_id:
        text = pg_id.read()
    return web.Response(text=text, content_type="text/html", charset="utf-8")


def show_message_page(msg_header: str, msg_text: str) -> web.Response:
    """Return page with message text."""
    page = get_html(MESSAGE_PAGE)
    page = page.replace("msg_header", msg_header)
    page = page.replace("msg_text", msg_text)
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_homepage(app) -> web.Response:
    """Show configurator home page."""
    api_srv = app["api_srv"]
    page = get_html(HOMEPAGE)
    side_menu = activate_side_menu(
        app["side_menu"], "", api_srv.is_offline or api_srv._pc_mode
    )
    page = page.replace("<!-- SideMenu -->", side_menu)
    if api_srv.is_offline or api_srv._pc_mode:
        page = page.replace(">Hub<", ">Home<")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_documentation_page(app) -> web.Response:
    """Show configurator home page."""
    api_srv = app["api_srv"]
    page = get_html(DOCUMENTATIONPAGE)
    api_srv = app["api_srv"]
    side_menu = activate_side_menu(
        app["side_menu"], ">Dokumentation<", app["is_offline"] or api_srv._pc_mode
    )
    page = page.replace("<!-- SideMenu -->", side_menu)
    if app["is_install"]:
        page = page.replace('style="visibility: hidden;"', "")
    if api_srv.is_offline or api_srv._pc_mode:
        page = page.replace(">Hub<", ">Home<")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_exitpage(app) -> web.Response:
    """Show configurator exit page."""
    api_srv = app["api_srv"]
    page = get_html(HOMEPAGE)
    side_menu = activate_side_menu(
        app["side_menu"], "", api_srv.is_offline or api_srv._pc_mode
    )
    if api_srv._in_shutdown:
        page = page.replace(
            "Passen Sie hier die Grundeinstellungen des Systems an.",
            "Das Fenster kann geschlossen werden.",
        )
    else:
        page = page.replace(
            "Passen Sie hier die Grundeinstellungen des Systems an.", "Beendet."
        )
        api_srv._in_shutdown = True
    page = page.replace("<!-- SideMenu -->", side_menu)
    if api_srv.is_offline or api_srv._pc_mode:
        page = page.replace(">Hub<", ">Home<")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_hub_overview(app) -> web.Response:
    """Show hub overview page."""

    api_srv = app["api_srv"]
    smhub = api_srv.sm_hub
    smhub_info = smhub.get_info()
    hub_name = smhub._host
    side_menu = activate_side_menu(
        app["side_menu"], ">Hub<", api_srv.is_offline or api_srv._pc_mode
    )
    if api_srv.is_offline or api_srv._pc_mode:
        side_menu = side_menu.replace(">Hub<", ">Home<")
        pic_file, subtitle = get_module_image(b"\xc9\x00")
        html_str = get_html(CONF_HOMEPAGE).replace(
            "Version: x.y.z", f"Version: {SMHUB_INFO.SW_VERSION}"
        )
        if not api_srv.is_offline and api_srv._pc_mode:
            html_str = adjust_update_button(html_str)
    elif api_srv.is_addon:
        pic_file, subtitle = get_module_image(b"\xca\x00")
        html_str = get_html(HUB_HOMEPAGE).replace(
            "HubTitle", f"Smart Center '{hub_name}'"
        )
        smhub_info = smhub_info.replace("type: Smart Hub", "type:  Smart Hub Add-on")
    else:
        pic_file, subtitle = get_module_image(b"\xc9\x00")
        html_str = get_html(HUB_HOMEPAGE).replace("HubTitle", f"Smart Hub '{hub_name}'")

    info_obj = api_srv.sm_hub.get_info_obj()
    props = "<h3>Eigenschaften</h3>\n"
    props += "<table>\n"
    props += f'<tr><td style="width:90px;">Typ:</td><td>{info_obj["software"]["type"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">Version:</td><td>{info_obj["software"]["version"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">Logging:</td><td>Ausgabe: {LOGGING_LEVELS[info_obj["software"]["loglevel"]["console"]]}, Datei: {LOGGING_LEVELS[info_obj["software"]["loglevel"]["file"]]}</td></tr>\n'
    props += '<tr><td style="width:90px;">&nbsp;</td><td>&nbsp;</td></tr>\n'
    props += f'<tr><td style="width:90px;">Hardware:</td><td>{info_obj["hardware"]["platform"]["type"]} #{info_obj["hardware"]["platform"]["serial"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">CPU:</td><td>{info_obj["hardware"]["cpu"]["type"]}, Takt {info_obj["hardware"]["cpu"]["frequency max"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">Auslastung:</td><td>{info_obj["hardware"]["cpu"]["load"]}, akt. Takt {info_obj["hardware"]["cpu"]["frequency current"]}, Temperatur {info_obj["hardware"]["cpu"]["temperature"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">Arbeitsspeicher:</td><td>{info_obj["hardware"]["memory"]["total"]}, genutzt {info_obj["hardware"]["memory"]["percent"]}</td></tr>\n'
    props += f'<tr><td style="width:90px;">Dateispeicher:&nbsp;</td><td>{info_obj["hardware"]["disk"]["total"]}, genutzt {info_obj["hardware"]["disk"]["percent"]}</td></tr>\n'
    props += '<tr><td style="width:90px;">&nbsp;</td><td>&nbsp;</td></tr>\n'
    props += f'<tr><td style="width:90px;">Netzwerk:</td><td>{info_obj["hardware"]["network"]["ip"]}, Host {info_obj["hardware"]["network"]["host"]}</td></tr>\n'
    if (
        info_obj["hardware"]["network"]["mac"]
        == info_obj["hardware"]["network"]["lan mac"]
    ):
        props += f'<tr><td style="width:90px;">Verbindung:</td><td>LAN, MAC Adresse {info_obj["hardware"]["network"]["mac"]}</td></tr>\n'
    else:
        props += f'<tr><td style="width:90px;">Verbindung:</td><td>WLAN, MAC Adresse {info_obj["hardware"]["network"]["mac"]}</td></tr>\n'
    props += "</table>\n"
    props = props.replace(".0MHz", " MHz")
    html_str = html_str.replace("Overview", subtitle)
    html_str = html_str.replace("smart-Ip.jpg", pic_file)
    html_str = html_str.replace("ContentText", props)
    rtr = api_srv.routers[0]
    rtr.check_firmware()
    if rtr.update_fw_file == "":
        html_str = html_str.replace('"rtr">Lokal<', '"rtr" disabled="true">aktuell<')
    opt_str = ""
    mod_updates: list[bytes] = []
    for mod in rtr.modules:
        mod.check_firmware()
        if mod.update_available and mod._typ not in mod_updates:
            opt_str += f'\n<option value="{mod._id}">{mod._type}</option>'
            mod_updates.append(mod._typ)
    if len(mod_updates) > 0:
        html_str = html_str.replace(
            ">-- Modultyp --</option>", ">-- Modultyp --</option>" + opt_str
        )
    else:
        html_str = html_str.replace(
            'name="mod_type_select">', 'name="mod_type_select" disabled="true">'
        )
        html_str = html_str.replace(
            'title="Modultyp für Updates auswählen"',
            'title="Firmware aller Module aktuell"',
        )
        html_str = html_str.replace(
            ">-- Modultyp --<",
            ">alle aktuell<",
        )
    html_str = html_str.replace("<!-- SideMenu -->", side_menu)
    return web.Response(text=html_str, content_type="text/html", charset="utf-8")


def show_modules(app) -> web.Response:
    """Prepare modules page."""
    modules = app["api_srv"].routers[0].modules
    side_menu = adjust_side_menu(modules, app["is_offline"], app["is_install"])
    app["side_menu"] = side_menu
    side_menu = activate_side_menu(
        side_menu, ">Module<", app["is_offline"] or app["api_srv"]._pc_mode
    )
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    images = ""
    for module in modules:
        pic_file, title = get_module_image(module._typ)
        images += f'<div class="figd_grid"><a href="module-{module._id}"><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{module._name}"><p class="mod_subtext">{module._name}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_update_router(rtr, new_fw: str) -> web.Response:
    """Prepare modules page with update candidates."""
    page = get_html("modules.html")
    page = page.replace(
        "</html>",
        '</html>\n<script type="text/javascript" src="configurator_files/update_status.js"></script>',
    )
    images = '<form id="mod-update-grid" action="update_modules" method="post">'
    pic_file, title = get_module_image(b"\x00\x00")
    images += '<div class="figd_grid">\n'
    images += f'<img src="configurator_files/{pic_file}" alt="{rtr.name}">&nbsp;&nbsp;&nbsp;{rtr._name}&nbsp;&nbsp;&nbsp;\n'
    images += (
        f'<p class="fw_subtext" id="stat_0">{rtr.version[1:].decode("iso8859-1")}</p>\n'
    )
    images += "</div>\n"
    images += "</div>\n"
    images += "<br><br>"
    images += '<button name="UpdButton" id="upd_cancel_button" type="submit" value="cancel">Abbruch</button>'
    images += '<button name="UpdButton" id="flash_button" type="submit" value="flash">Flashen</button>'
    images += "</form>"
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("<h1>Module</h1>", "<h1>Firmware Update</h1>")
    page = page.replace("Übersicht", f"Version {new_fw} für Smart Router")
    page = page.replace("Wählen Sie ein Modul aus", "")
    page = page.replace('action="update_modules"', 'action="update_router"')
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def is_outdated(cur_fw: str, new_fw: str) -> bool:
    """Compare two firmware strings and return update status."""
    cur_fw_fields = cur_fw.strip().split()
    new_fw_fields = new_fw.strip().split()
    cur_date = cur_fw_fields[-1]
    new_date = new_fw_fields[-1]
    cur_year = cur_date.split("/")[1][:4]
    cur_month = cur_date.split("/")[0][-2:]
    new_year = new_date.split("/")[1][:4]
    new_month = new_date.split("/")[0][-2:]
    if int(new_year) > int(cur_year):
        return True
    if (int(new_year) == int(cur_year)) and (int(new_month) > int(cur_month)):
        return True
    if (
        (int(new_year) == int(cur_year))
        and (int(new_month) == int(cur_month))
        and (len(new_date.split("/")[1]) > 4)
    ):
        return True
    # if (new_date == cur_date) and ():
    #     return True
    return False


def show_update_modules(mod_list, new_fw: str, mod_type: str) -> web.Response:
    """Prepare modules page with update candidates."""
    page = get_html("modules.html")
    page = page.replace(
        "</html>",
        '</html>\n<script type="text/javascript" src="configurator_files/update_status.js"></script>',
    )
    page = page.replace("Übersicht", f"Version {new_fw} für {mod_type}")
    images = '<form id="mod-update-grid" action="update_modules" method="post">'
    for module in mod_list:
        pic_file, title = get_module_image(module.typ)
        images += '<div class="figd_grid">\n'
        if is_outdated(module.fw, new_fw):
            images += f'<input type="checkbox" class="mod_chk" id="chk_{module.id}" name="chk_{module.id}" value="{module.id}" checked>\n'
        else:
            images += f'<input type="checkbox" class="mod_chk" id="chk_{module.id}" name="chk_{module.id}" value="{module.id}">\n'
        images += f'<label for="chk_{module.id}">\n'
        images += f'<img src="configurator_files/{pic_file}" alt="{module.name}"><br>{module.name}\n'
        images += f'<p class="fw_subtext" id="stat_{module.id}">{module.fw}</p>\n'
        images += "</label>\n"
        images += "</div>\n"
    images += "</div>\n"
    images += "<br><br>\n"
    images += '<button name="UpdButton" id="upd_cancel_button" type="submit" value="cancel">Abbruch</button>\n'
    images += '<button name="UpdButton" id="flash_button" type="submit" value="flash">Flashen</button>\n'
    images += "</form>\n"
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("<h1>Module</h1>", "<h1>Firmware Update</h1>")
    if len(mod_list) == 0:
        page = page.replace(
            "Wählen Sie ein Modul aus", "Kein kompatibles Modul vorhanden"
        )
        page = page.replace(">Flashen</button>", " disabled>Flashen</button>")
    else:
        page = page.replace(
            "Wählen Sie ein Modul aus", "Wählen Sie Module für das Update aus"
        )
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def fill_page_template(
    title: str,
    subtitle: str,
    help_text: str,
    content: str,
    menu: str,
    image: str,
    download_file: str,
) -> str:
    """Prepare config web page with content, image, and menu."""
    with open(
        WEB_FILES_DIR + CONFIG_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    if download_file == "":
        ext = ""
    else:
        ext = download_file.split(".")[1]
    if len(help_text):
        page = page.replace(
            "<p>ContentText</p>", f"<p>{help_text}</p>\n<p>ContentText</p>"
        )
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("ContentText", content)
        .replace("<!-- SideMenu -->", menu)
        .replace("controller.jpg", image)
        .replace("my_module.hmd", download_file)
        .replace('accept=".hmd"', f'accept=".{ext}"')
    )
    return page


def init_side_menu(app):
    """Setup side menu."""
    side_menu = adjust_side_menu(
        app["api_srv"].routers[0].modules, app["is_offline"], app["is_install"]
    )
    app["side_menu"] = side_menu


def adjust_side_menu(modules, is_offline: bool, is_install: bool) -> str:
    """Load side_menu and adjust module entries."""
    mod_lines = []
    with open(WEB_FILES_DIR + SIDE_MENU_FILE, mode="r", encoding="utf-8") as smf_id:
        if is_install:
            side_menu = (
                smf_id.read()
                .replace("submenu modules last", "submenu modules")
                .splitlines(keepends=True)
            )
            side_menu.append('<ul class="level_1">')
            side_menu.append(
                '<li class="submenu modules last"><a href="setup/" title="Einrichten" class="submenu modules last">Einrichten</a>'
            )
            side_menu.append(
                '\n  <ul class="level_2">\n'
                + '    <li class="setup sub"><a href="setup/add" title="Module anlegen" class="setup sub">Module anlegen</a></li>\n'
            )
            side_menu.append(
                '    <li class="setup sub"><a href="setup/adapt" title="Module verwalten" class="setup sub">Module verwalten</a></li>\n'
            )
            side_menu.append("</ul></li>\n")
            if not is_offline:
                side_menu.append('<ul class="level_1">')
                side_menu.append(
                    '<li class="submenu modules last"><a href="test/" title="Diagnose und spezielle Einstellungen" class="submenu modules last">Diagnose</a>'
                )
                side_menu.append(
                    '\n  <ul class="level_2">\n'
                    '    <li class="setup sub"><a href="test/router" title="Router testen" class="setup sub">Router testen</a></li>\n'
                )
                side_menu.append(
                    '    <li class="setup sub"><a href="test/comm" title="Kommunikation testen" class="setup sub">Kommunikation</a></li>\n'
                )
                side_menu.append(
                    '    <li class="setup sub"><a href="test/modules" title="Module testen" class="setup sub">Module testen</a></li>\n'
                )
            side_menu.append("</ul></li></ul>\n")
        else:
            side_menu = smf_id.read().splitlines(keepends=True)
    for sub_line in side_menu:
        if sub_line.find("modules sub") > 0:
            sub_idx = side_menu.index(sub_line)
            break
    first_lines = side_menu[:sub_idx]
    last_lines = side_menu[sub_idx + 1 :]
    for module in modules:
        mod_lines.append(
            sub_line.replace("module-1", f"module-{module._id}").replace(
                "ModuleName", module._name
            )
        )
    page = "".join(first_lines) + "".join(mod_lines) + "".join(last_lines)
    if is_offline:
        page = page.replace(
            'class="submenu modules">Hub</a>',
            'class="submenu modules">Home</a>',
        )
    return page


def activate_side_menu(menu: str, entry: str, is_offline: bool) -> str:
    """Mark menu entry as active."""
    side_menu = menu.splitlines(keepends=True)
    sub_idx = None
    for sub_line in side_menu:
        if sub_line.find(entry) > 0:
            sub_idx = side_menu.index(sub_line)
            break
    if sub_idx is not None:
        # side_menu[sub_idx] = re.sub(
        #     r"title=\"[a-z,A-z,0-9,\-,\"]+ ", "", side_menu[sub_idx]
        # )
        side_menu[sub_idx] = side_menu[sub_idx].replace('class="', 'class="active ')
    side_menu_str = "".join(side_menu)
    if is_offline:
        side_menu_str = side_menu_str.replace(
            'class="submenu modules">Hub</a>',
            'class="submenu modules">Home</a>',
        )
    return side_menu_str


def get_module_image(type_code: bytes) -> tuple[str, str]:
    """Return module image based on type code bytes."""
    match type_code[0]:
        case 0:
            mod_image = "router.jpg"
            type_desc = (
                "Smart Router - Kommunikationsschnittstelle zwischen den Modulen"
            )
        case 1:
            mod_image = "controller.jpg"
            type_desc = "Smart Controller - Raumzentrale mit Sensorik und Aktorik"
        case 10:
            match type_code[1]:
                case 1 | 50 | 51:
                    mod_image = "smart-out-8-R.jpg"
                    type_desc = "Smart-Out 8/R - 8fach Binärausgang (potentialfrei)"
                case 2:
                    mod_image = "smart-out-8-T.jpg"
                    type_desc = "Smart-Out 8/T - 8fach Binärausgang (potentialgebunden)"
                case 20 | 21 | 22:
                    mod_image = "dimm.jpg"
                    type_desc = "Smart Dimm - 4fach Dimmer"
                case 30:
                    mod_image = "smart-io.jpg"
                    type_desc = "Smart IO - 2fach 24 V-Binäreingang, 2fach Binärausgang (potentialfrei)"
        case 11:
            match type_code[1]:
                case 1:
                    mod_image = "smart-In-8-230V.jpg"
                    type_desc = "Smart-Input 8/230V - 8fach 230 V-Binäreingang"
                case 30 | 31:
                    mod_image = "smart-In-8-24V.jpg"
                    type_desc = "Smart-Input 8/230V - 8fach 24 V-Binäreingang"
        case 20:
            mod_image = "smart-nature.jpg"
            type_desc = "Smart Nature - Externe Wetterstation"
        case 30:
            match type_code[1]:
                case 1:
                    mod_image = "mod_smartkey.jpg"
                    type_desc = "Smart Key - Zugangskontroller über Fingerprint"
                case 3:
                    mod_image = "smart-gsm.jpg"
                    type_desc = "Smart GSM - Kommunikationsmodul über GSM"
        case 31:
            mod_image = "finger_numbers.jpg"
            type_desc = "Smart Key - Zugangskontroller über Fingerprint"
        case 50:
            match type_code[1]:
                case 1:
                    mod_image = "scc.jpg"
                    type_desc = "Smart Controller compakt - Controller mit Sensorik und 24 V Anschlüssen"
                case 40:
                    mod_image = "smart-sensor.jpg"
                    type_desc = "Smart Sensor - Externer Temperatursensor"
        case 80:
            match type_code[1]:
                case 100 | 102:
                    mod_image = "smart-detect-1802.jpg"
                    type_desc = "Smart Detect 180 - Bewegungsmelder"
                case 101:
                    mod_image = "smart-detect-360.jpg"
                    type_desc = "Smart Detect 360 - Bewegungsmelder für Deckeneinbau"
        case 200:
            mod_image = "smart-ip.jpg"
            type_desc = "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        case 201:
            mod_image = "smart-center.jpg"
            type_desc = "Smart Hub - Systemzentrale und Schnittstelle zum Netzwerk"
        case 202:
            mod_image = "smart-center.jpg"
            type_desc = "Smart Center - Habitron Home Assistant Zentrale"
    return mod_image, type_desc


def indent(level):
    """Return sequence of tabs according to level."""
    return "\t" * level


def adjust_settings_button(page, type, addr: str) -> str:
    """Specify button."""
    if type.lower() == "gtw":
        page = page.replace("ModSettings", "GtwSettings")
    elif type.lower() == "rtr":
        page = page.replace("ModSettings", "RtrSettings")
    elif type.lower() == "rtr_tst":
        page = page.replace("ConfigFile", "RtrTesting")
        page = page.replace('action="settings/settings"', "action=test/sys_settings")
        page = page.replace('id="files_button"', 'id="chan_reset_button" type="button"')
        page = page.replace(">Einstellungen", ">System-Einstellungen")
        page = page.replace(
            '">Konfigurationsdatei<',
            ' visibility: hidden;">Konfigurationsdatei<',
        )
    elif type == "":
        page = page.replace(">Einstellungen", " disabled >Einstellungen")
        page = page.replace(">Konfigurationsdatei", " disabled >Konfigurationsdatei")
    else:
        page = page.replace("ModAddress", addr)
    return page


def adjust_update_button(page: str) -> str:
    """Enable update button on home page"""
    page = page.replace("<!--<button", "<button").replace("</button>-->", "</button>")
    return page


def adjust_automations_button(page: str) -> str:
    """Enable edit automations button."""
    page = page.replace("<!--<button", "<button").replace("</button>-->", "</button>")
    return page


def adjust_ekeylog_button(page: str) -> str:
    """Enable edit automations button."""
    page = (
        page.replace(
            '<!--<button name="EditAutomtns" id="automtns_button"',
            '<button name="ShowLogs" id="showlogs_button"',
        )
        .replace("Automatisierungen</button>-->", "Protokoll</button>")
        .replace('action="automations/list"', 'action="settings/show_logs"')
        .replace('"msg_popup_txt">Upload<', '"msg_popup_txt">Lade Protokoll<')
    )
    return page


def disable_button(key: str, page) -> str:
    return page.replace(f">{key}<", f" disabled>{key}<")


def hide_button(key: str, page) -> str:
    return page.replace(f">{key}<", f' style="visibility: hidden;">{key}<')


def client_not_authorized(request) -> bool:
    """If addon, check allowed ingress internal IP address, return True if not authorized."""
    app = request.app
    if "parent" in app._state.keys():
        app = app["parent"]
    if not app["api_srv"].is_addon:
        # No checks if not addon
        return False
    return request.remote not in ALLOWED_INGRESS_IPS


def show_not_authorized(request) -> web.Response:
    """Return web page with 'not authorized' message'."""
    return show_message_page(
        "Zugriff nicht erlaubt.", "Anmeldung über Home Assistant nötig."
    )


def format_smc(buf: bytes) -> str:
    """Parse line structure and add ';' and linefeeds."""
    if len(buf) < 5:
        return ""
    no_lines = int.from_bytes(buf[:2], "little")
    str_data = ""
    for byt in buf[:4]:
        str_data += f"{byt};"
    str_data += "\n"
    ptr = 4  # behind header with no of lines/chars
    for l_idx in range(no_lines):
        l_len = buf[ptr + 5] + 5
        for byt in buf[ptr : ptr + l_len]:
            str_data += f"{byt};"  # dezimal values, seperated with ';'
        str_data += "\n"
        ptr += l_len
    return str_data


def format_smg(buf: bytes) -> str:
    """Parse structure and add ';' and final linefeed."""
    str_data = ""
    for byt in buf:
        str_data += f"{byt};"
    str_data += "\n"
    return str_data


def format_hmd(status, list: bytes) -> str:
    """Generate single module data file."""
    smg_str = format_smg(status)
    smc_str = format_smc(list)
    return smg_str + smc_str
