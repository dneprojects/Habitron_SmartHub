from aiohttp import web
from asyncio import sleep
from config_commons import (
    get_module_image,
    get_html,
    client_not_authorized,
    show_not_authorized,
    fill_page_template,
    inspect_header,
    adjust_settings_button,
    indent,
    hide_button,
)
from config_settings import activate_side_menu
from const import (
    CONF_PORT,
    MirrIdx,
    HA_EVENTS,
    RT_ERROR_CODE,
    RT_CMDS,
    MStatIdx,
    WEB_FILES_DIR,
    SETTINGS_TEMPLATE_FILE,
)
import json
import datetime

routes = web.RouteTableDef()


class ConfigTestingServer:
    """Web server for testing tasks."""

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
        inspect_header(request)
        main_app = request.app["parent"]
        if client_not_authorized(request):
            return show_not_authorized(main_app)
        return show_diag_page(main_app)

    @routes.get("/router")
    async def test_router(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        return await show_router_testpage(main_app)

    @routes.get("/comm")
    async def test_communication(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        return await show_comm_testpage(main_app)

    @routes.get("/comm_reset")
    async def reset_comm_errors(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        rtr = main_app["api_srv"].routers[0]
        mod_addrs = []
        for key in list(request.query.keys()):
            if key.startswith("modsel"):
                mod_addrs.append(int(key.split("_")[1]))
        return await show_comm_testpage(main_app, mod_addrs)

    @routes.get("/modules")
    async def test_modules(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        return show_modules_overview(main_app)

    @routes.get("/start-{mod_addr}")
    async def start_test(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        mod_addr = int(request.match_info["mod_addr"])
        main_app["mod_addr"] = mod_addr
        await api_srv.set_testing_mode(True)
        return await show_module_testpage(main_app, mod_addr, True)

    @routes.get("/events")
    async def get_events(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        main_app = request.app["parent"]
        mod_addr = main_app["mod_addr"]
        events_dict: dict[str, list[list[int]]] = {}
        # get events
        events_buf = main_app["api_srv"].evnt_srv.get_events_buffer()
        if main_app["module"]._typ in [b"\x14\x01", b"\x32\x28"]:
            # nature / sensor module, get temperature every 10 s
            ct = datetime.datetime.now()
            if ct.second % 10 == 0 and ct.microsecond < 500000:
                curr_temp = main_app["module"].comp_status[MStatIdx.TEMP_ROOM - 1]
                events_dict["Temperature"] = [[curr_temp, 0]]
        for evnt in events_buf:
            if evnt[0] == mod_addr:
                dict_str = HA_EVENTS.EVENT_DICT[evnt[1]].replace(" ", "_")
                if dict_str == "Motion" and main_app["module"]._typ[0] not in [80]:
                    # skip motion events for test output if not detect module
                    pass
                elif dict_str in events_dict.keys():
                    events_dict[dict_str].append([evnt[2], evnt[3]])
                else:
                    events_dict[dict_str] = [[evnt[2], evnt[3]]]
        return web.Response(
            text=json.dumps(events_dict), content_type="text/plain", charset="utf-8"
        )

    @routes.get("/stop")
    async def stop_test(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        await api_srv.set_testing_mode(False)
        return show_modules_overview(main_app)

    @routes.get("/set_output")
    async def set_output(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        out_args = args[1].split("-")
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        mod_addr = main_app["mod_addr"]
        rtr = api_srv.routers[0]
        mod = rtr.get_module(mod_addr)
        await mod.hdlr.set_output(int(out_args[0]), int(out_args[1]))
        return await show_module_testpage(main_app, mod_addr, False)

    @routes.get("/sys_settings")
    async def sys_settings(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        return await show_router_syspage(main_app, "")

    @routes.post("/master_timeout")
    async def set_sys_settings(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        data = await request.post()
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        t_out = int(int(data["rtr_timeout"]) / 10)
        rtr.settings.timeout = t_out * 10
        rtr.timeout = chr(t_out).encode("iso8859-1")
        await rtr.hdlr.send_rt_timeout(t_out)
        return await show_router_syspage(main_app, "")

    @routes.post("/cov_autostop")
    async def set_cov_autostop(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        data = await request.post()
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        c_cnt = int(data["cov_autostop_cnt"])
        rtr.settings.cov_autostop_cnt = c_cnt
        rtr.set_descriptions(rtr.settings)
        return await show_router_syspage(main_app, "")

    @routes.post("/rt_reboot")
    async def rt_reboot(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        await api_srv.block_network_if(rtr._id, True)
        await api_srv.set_server_mode(rtr._id)
        await api_srv.set_initial_server_mode(rtr._id)
        main_app.logger.info(f"Router {rtr._id} will be rebooted, please wait...")
        await rtr.hdlr.handle_router_cmd(rtr._id, RT_CMDS.RT_REBOOT)
        main_app.logger.info(f"Router {rtr._id} will be initialized, please wait...")
        rtr.__init__(api_srv, rtr._id)
        main_app.logger.info("Reloading system status, please wait...")
        try:
            await rtr.get_full_system_status()
        except Exception as err_msg:
            main_app.logger.error(f"Error initializing system: {err_msg}")
        api_srv._init_mode = False
        await api_srv.block_network_if(rtr._id, False)
        await api_srv.set_operate_mode(rtr._id)
        return await show_router_syspage(main_app, "")

    @routes.post("/chan_reset")
    async def chan_reset(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        data = await request.post()
        chan_mask = 1 << (int(data["reset_ch"]) - 1)
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        await rtr.reset_chan_power(chan_mask)
        return await show_router_syspage(main_app, "")

    @routes.post("/new_chan_id")
    async def new_chan_id(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        data = await request.post()
        id = int(data["new_mod_id"])
        chan = int(data["new_mod_ch"])
        main_app = request.app["parent"]
        api_srv = main_app["api_srv"]
        rtr = api_srv.routers[0]
        await rtr.hdlr.set_module_address(0, chan, id)
        return await show_router_syspage(main_app, "")


def show_diag_page(app, popup_msg="") -> web.Response:
    """Prepare modules page."""
    side_menu = activate_side_menu(
        app["side_menu"], ">Diagnose<", app["is_offline"] or app["api_srv"]._pc_mode
    )
    page = get_html("setup.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>HubTitle", "<h1>Habitron-Installation untersuchen")
    page = page.replace("Overview", "Diagnosebereich")
    page = page.replace(
        "ContentText",
        "<h3>Router</h3>"
        + "1. Status des Routers wird aktuell ausgelesen:<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;Kommunikationsfehler werden angezeigt.<br>"
        + "2. Systemeinstellungen des Routers (Timeout) können verändert werden.<br>"
        + "3. Die Versorgungspannung einzelner Router-Kanäle kann für 3s ausgeschaltet werden:<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;Alle an diesem Kanal angeschlossenen Module<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;(außer Raumcontroller mit 230V-Anschluss) werden neu gestartet.<br>"
        + "4. Der Routers kann rückgesetzt und neu gestartet werden:<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;Alle Modulinformationen werden neu eingelesen.<br>"
        + "<h3>Kommunikation</h3>"
        + "1. Status des Routerkommunikation mit allen Modulen wird aktuell ausgelesen:<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;Kommunikationsfehler werden für jedes Modul angezeigt.<br>"
        + "2. Für ausgewählte Module lassen sich die Zähler der Kommunikationsfehler rücksetzen."
        + "<h3>Module testen</h3>"
        + "1. Bereits angelegte und in der Habitron-Anlage eingespeicherte Module<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;können ausgewählt werden.<br>"
        + "2. Auf der folgenden Seite kann das gewählte Modul getestet werden, indem<br>"
        + "&nbsp;&nbsp;&nbsp;&nbsp;Eingangszustände angezeigt und Ausgänge geschaltet werden.<br>",
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
        page = page.replace(
            'action="setup/table_transfer"', 'action="setup/table_close"'
        )
    else:
        page = page.replace(
            'value="cancel" style="visibility: hidden;"',
            'value="cancel" style="width: 140px;"',
        )
        page = page.replace("Abbruch", "Neustart")

    return web.Response(text=page, content_type="text/html", charset="utf-8")


def show_modules_overview(app) -> web.Response:
    """Prepare modules page."""
    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    side_menu = activate_side_menu(
        app["side_menu"], ">Diagnose<", app["is_offline"] or app["api_srv"]._pc_mode
    )
    side_menu = activate_side_menu(
        side_menu, ">Module testen<", app["is_offline"] or app["api_srv"]._pc_mode
    )
    page = get_html("modules.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>Module", "<h1>Module testen")
    images = ""
    for mod in rtr.modules:
        m_type = mod._typ
        pic_file, title = get_module_image(m_type)
        images += f'<div class="figd_grid" name="test_mod_img" id=test-{mod._id}><a href="test/start-{mod._id}"><div class="fig_grid"><img src="configurator_files/{pic_file}" alt="{mod._name}"><p class="mod_subtext">{mod._name}</p></div></a></div>\n'
    page = page.replace("<!-- ImageGrid -->", images)
    page = page.replace("const mod_addrs = [];", f"const mod_addrs = {rtr.mod_addrs};")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


async def show_router_testpage(main_app, popup_msg="") -> web.Response:
    """Prepare overview page of module."""
    api_srv = main_app["api_srv"]
    rtr = api_srv.routers[0]
    await api_srv.block_network_if(rtr._id, True)
    await rtr.get_status()
    await rtr.get_module_boot_status()
    await api_srv.block_network_if(rtr._id, False)
    chan_stat = rtr.chan_status
    error_stat = rtr.comm_errors
    side_menu = main_app["side_menu"]
    side_menu = activate_side_menu(
        side_menu, ">Diagnose<", api_srv.is_offline or api_srv._pc_mode
    )
    side_menu = activate_side_menu(
        side_menu, ">Router testen<", api_srv.is_offline or api_srv._pc_mode
    )
    type_desc = "Smart Router - Kommunikationsschnittstelle zwischen den Modulen"
    if rtr.channels == b"":  #  and not main_app["is_install"]:
        page = fill_page_template(
            "Router", type_desc, "", "--", side_menu, "router.jpg", ""
        )
        page = adjust_settings_button(page, "", f"{0}")
        return web.Response(text=page, content_type="text/html")
    props = "<h3>Status</h3>\n"
    props += "<table>\n"
    if error_stat[0]:
        last_err_str = f'Modul {error_stat[0]}: <a title="{RT_ERROR_CODE[error_stat[1]]}">F{error_stat[1]}</a>'
    else:
        last_err_str = "-"
    mod_err_str = ""
    for err_cnt in range(rtr.comm_errors[2]):
        err_code = rtr.comm_errors[4 + 2 * err_cnt]
        mod_err_str += f'Modul {rtr.comm_errors[3 + 2*err_cnt]}: <a title="{RT_ERROR_CODE[err_code]}">F{err_code}</a>; '
    if mod_err_str == "":
        mod_err_str = "-"
    else:
        mod_err_str = mod_err_str[:-2]
    if chan_stat[40] == 78:
        mod_fdback_str = "Korrekt"
    else:
        mod_fdback_str = "Mit Fehlern"
    if chan_stat[36] == 78:
        sys_probl_str = "OK"
    else:
        sys_probl_str = "Fehler"
    if chan_stat[39] == 78:
        booting_str = "Beendet"
    else:
        booting_str = "Noch aktiv"

    v_5 = (chan_stat[18] + chan_stat[19] * 256) / 10
    v_24 = (chan_stat[16] + chan_stat[17] * 256) / 10
    i_1 = chan_stat[20] + chan_stat[21] * 256
    i_2 = chan_stat[22] + chan_stat[23] * 256
    i_3 = chan_stat[24] + chan_stat[25] * 256
    i_4 = chan_stat[26] + chan_stat[27] * 256
    i_5 = chan_stat[28] + chan_stat[29] * 256
    i_6 = chan_stat[30] + chan_stat[31] * 256
    i_7 = chan_stat[32] + chan_stat[33] * 256
    i_8 = chan_stat[34] + chan_stat[35] * 256

    mod_boot_status_txt = ""
    for mod_err in list(rtr.mod_boot_errors.keys()):
        mod_boot_status_txt += f"Module {mod_err}: {rtr.mod_boot_errors[mod_err]} \n"
    mod_boot_status_txt = mod_boot_status_txt[:-1]
    props += f"<tr><td>Bootvorgang:</td><td>{booting_str}</td></tr>\n"
    props += f"<tr><td>Systemzustand:</td><td>{sys_probl_str}</td></tr>\n"
    props += f"<tr><td>Modulanzahl:</td><td>{chan_stat[0]}</td></tr>\n"
    if mod_boot_status_txt == "":
        props += f"<tr><td>Modulrückmeldungen:</td><td>{mod_fdback_str}</td></tr>\n"
    else:
        props += f'<tr><td>Modulrückmeldungen:</td><td><a title="{mod_boot_status_txt}">{mod_fdback_str}</a></td></tr>\n'
    props += f"<tr><td>Modulfehler:</td><td>{mod_err_str}</td></tr>\n"
    props += f"<tr><td>Letzter Modulfehler:</td><td>{last_err_str}</td></tr>\n"
    props += f"<tr><td>Fehler Speicherbank 1-2:</td><td>{chan_stat[2]+chan_stat[3]*256} | {chan_stat[4]+chan_stat[5]*256}</td></tr>\n"
    props += f"<tr><td>Timeouts Kanäle 1-4:</td><td>{chan_stat[7]} | {chan_stat[8]} | {chan_stat[9]} | {chan_stat[10]}</td></tr>\n"
    props += f"<tr><td>Fehler Masterring:</td><td>{chan_stat[11]}</td></tr>\n"
    props += f"<tr><td>Einschaltvorgänge:</td><td>{chan_stat[14]+chan_stat[15]*256}</td></tr>\n"
    props += f"<tr><td>Spannungen 5 V | 24 V:</td><td>{v_5} V | {v_24} V</td></tr>\n"
    props += f"<tr><td>Kanalströme 1-4:</td><td>{i_1} mA | {i_2} mA | {i_3} mA | {i_4} mA</td></tr>\n"
    props += f"<tr><td>Kanalströme 5-8:</td><td>{i_5} mA | {i_6} mA | {i_7} mA | {i_8} mA</td></tr>\n"

    props += "</table>\n"
    def_filename = "my_router.hrt"
    page = fill_page_template(
        f"Router '{rtr._name}'",
        type_desc,
        "",
        props,
        side_menu,
        "router.jpg",
        def_filename,
    )
    page = adjust_settings_button(page, "rtr_tst", f"{0}")
    if len(popup_msg):
        page = page.replace(
            '<h3 id="resp_popup_txt">response_message</h3>',
            f'<h3 id="resp_popup_txt">{popup_msg}</h3>',
        ).replace('id="resp-popup-disabled"', 'id="resp-popup"')
    return web.Response(text=page, content_type="text/html")


async def show_module_testpage(main_app, mod_addr, update: bool) -> web.Response:
    """Prepare overview page of module."""
    api_srv = main_app["api_srv"]
    module = api_srv.routers[0].get_module(mod_addr)
    mod_image, type_desc = get_module_image(module._typ)
    main_app["module"] = module
    mod_description = ""
    def_filename = f"module_{mod_addr}.hmd"
    page = fill_page_template(
        f"Modul '{module._name}'",
        "Modul Testseite",
        "Ein- und Ausgangsänderungen, sowie Events kontrollieren und Ausgänge schalten",
        mod_description,
        "",
        mod_image,
        def_filename,
    )
    page = page.replace("<!-- SetupContentStart >", "<!-- SetupContentStart -->")
    # reconfigure existing buttons
    page = page.replace(
        ">Modul entfernen<", 'style="visibility: hidden;">Modul entfernen<'
    )
    page = page.replace(">Modul testen<", 'style="visibility: hidden;">Modul testen<')
    page = page.replace(">Einstellungen<", 'style="visibility: hidden;">Einstellungen<')
    page = page.replace(
        ">Konfigurationsdatei<",
        'form="test_form" value="ModAddress">Modultest beenden<',
    )
    page = page.replace("left: 68%;", "")
    page = page.replace('action="test/start"', 'action="test/stop"')
    page = page.replace("ModAddress", f"{mod_addr}")
    page = page.replace(
        '<form action="automations/list" id="atm_form">',
        '<form action="test/stop" id="test_form">',
    )
    page = page.replace('id="files_button"', 'id="finish_button"')
    page = page.replace("left: 560px;", "left: 200px;")
    page = page.replace("config.js", "update_testing.js")
    if module._typ == b"\x1e\x01":
        page = page.replace(
            '<h3 id="msg_popup_txt">Upload</h3>',
            '<h3 id="msg_popup_txt">Kopplung</h3>',
        )
    tbl_str = await build_status_table(main_app, mod_addr, update)
    page = page.replace("<p></p>", tbl_str)
    return web.Response(text=page, content_type="text/html")


async def show_comm_testpage(main_app, mod_addrs: list[int] = []) -> web.Response:
    """Prepare overview page of module comm status."""
    api_srv = main_app["api_srv"]
    rtr = api_srv.routers[0]
    await api_srv.block_network_if(rtr._id, True)
    await rtr.get_module_comm_status(mod_addrs)
    await api_srv.block_network_if(rtr._id, False)

    mod_image, type_desc = get_module_image(rtr.settings.typ)
    side_menu = activate_side_menu(
        main_app["side_menu"],
        ">Diagnose<",
        main_app["is_offline"] or main_app["api_srv"]._pc_mode,
    )
    side_menu = activate_side_menu(
        side_menu,
        ">Kommunikation<",
        main_app["is_offline"] or main_app["api_srv"]._pc_mode,
    )
    page = get_html("setup.html").replace("<!-- SideMenu -->", side_menu)
    page = page.replace("<h1>HubTitle", "<h1>Kommunikation testen")
    page = page.replace("Overview", "Modulübersicht")
    page = page.replace(
        "ContentText",
        "Kommunikationsstatus aller Module, Fehlerzähler rücksetzen<br>Für eine Beschreibung der Abkürzungen den Mauszeiger über den Text führen.<br><br>",
    )
    page = page.replace("<!-- SetupContentStart >", "<!-- SetupContentStart -->")
    # reconfigure existing buttons
    page = page.replace(
        ">Modul entfernen<", 'style="visibility: hidden;">Modul entfernen<'
    )
    page = page.replace(">Übertragen<", ' style="visibility: hidden;">Übertragen<')
    page = page.replace(">Abbruch<", ' style="visibility: hidden;">Abbruch<')
    page = page.replace(">Übernehmen<", ' style="visibility: hidden;">Übernehmen<')
    page = page.replace(
        'id="files_button" type="button" style="',
        'id="files_button" type="button" style="visibility: hidden; ',
    )
    page = page.replace("left: 68%;", "")
    page = page.replace('action="test/start"', 'action="test/stop"')
    page = page.replace(
        '<form action="automations/list" id="atm_form">',
        '<form action="test/stop" id="test_form">',
    )
    page = page.replace("left: 560px;", "left: 200px;")
    tbl_str = build_comm_table(rtr)
    page = page.replace(
        "<!-- MainContentEnd -->", tbl_str + "<br><!-- MainContentEnd -->"
    )
    return web.Response(text=page, content_type="text/html")


async def show_router_syspage(main_app, popup_msg="") -> web.Response:
    """Prepare page for router system settings."""
    api_srv = main_app["api_srv"]
    rtr = api_srv.routers[0]
    main_app["settings"] = rtr.settings
    settings = main_app["settings"]

    with open(
        WEB_FILES_DIR + SETTINGS_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    mod_image, subtitle = get_module_image(settings.typ)
    page = (
        page.replace("ContentTitle", f"Router '{rtr._name}'")
        .replace("ContentSubtitle", "Systemeinstellungen")
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", "0-0")
        .replace("Einstellungen speichern", "Router bootet")
    )

    page = hide_button("zurück", page)
    page = hide_button("weiter", page)
    page = hide_button("Speichern", page)
    page = page.replace(">Abbruch<", ">Beenden<")
    page = page.replace('action="settings/step"', 'action="test/router"')
    page = page.replace(
        "reserved_numbers = [];", f"reserved_numbers = {rtr.mod_addrs};"
    )
    tbl = indent(5) + "<table><tbody>\n"
    id_name = "rt_reboot"
    prompt = "Router neu starten"
    tbl += indent(6) + '<form action="test/rt_reboot" method="post">\n'
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td></td><td></td>'
        + f'<td><input name="btn_{id_name}" type="submit" id="btn_{id_name}" value="Neustart"/></td></tr>\n'
    )
    tbl += indent(6) + "</form>"
    id_name = "chan_reset"
    prompt = "Spannungsreset auf Routerkanal"
    tbl += indent(6) + '<form action="test/chan_reset" method="post">\n'
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td></td>'
        + '<td><input name="reset_ch" type="number" min="1" max="8" id="reset_ch" value="1" title="Routerkanal"/></td>\n'
        + f'<td><input name="btn_{id_name}" type="submit" id="btn_{id_name}" value="Rücksetzen"/></td></tr>\n'
    )
    tbl += indent(6) + "</form>"
    id_name = "new_mod_id"
    prompt = "Neue Moduladresse auf Kanalpaar anbieten"
    tbl += indent(6) + '<form action="test/new_chan_id" method="post">\n'
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td>'
        + f'<td><input name="{id_name}" type="number" min="1" max="64" id="{id_name}" value="1" title="neue Moduladresse"/></td>\n'
        + '<td><select name="new_mod_ch" id="new_mod_ch" title="Routerkanalpaar"><option value="1">1 + 2</option><option value="2">3 + 4</option><option value="3">5 + 6</option><option value="4">7 + 8</option></select></td>\n'
        + f'<td><input name="btn_{id_name}" type="submit" id="btn_{id_name}" value="Anbieten"/></td></tr>\n'
    )
    tbl += indent(6) + "</form>"
    id_name = "rtr_timeout"
    prompt = "Master-Timeout [ms]"
    tbl += indent(6) + '<form action="test/master_timeout" method="post">\n'
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td></td>'
        + f'<td><input name="{id_name}" type="number" min="0" step="10" max="2550" id="{id_name}" value="{settings.timeout}"/></td>\n'
        + f'<td><input name="btn_{id_name}" type="submit" id="btn_{id_name}" value="Speichern"/></td></tr>\n'
    )
    tbl += indent(6) + "</form>"
    id_name = "cov_autostop_cnt"
    prompt = "Rollladen Autostop-Zähler (0 = inaktiv)"
    tbl += indent(6) + '<form action="test/cov_autostop" method="post">\n'
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td></td>'
        + f'<td><input name="{id_name}" type="number" min="0" max="10" id="{id_name}" value="{settings.cov_autostop_cnt}"/></td>\n'
        + f'<td><input name="btn_{id_name}" type="submit" id="btn_{id_name}" value="Speichern"/></td></tr>\n'
    )
    tbl += indent(6) + "</form>"
    tbl += indent(5) + "</tbody></table>\n"
    page = page.replace("<p>ContentText</p>", tbl)
    return web.Response(text=page, content_type="text/html")


def build_comm_table(rtr):
    """Show table with module communication statistics."""

    comm_stat = rtr.mod_comm_status
    chan_pairs = ["1 + 2", "3 + 4", "5 + 6", "7 + 8"]

    tr_line = '        <tr id="inst-tr">\n'
    tre_line = "        </tr>\n"
    td_line = "            <td></td>\n"
    thead_lines = (
        '<form action="test/comm_reset" id="table-form">\n'
        '<table id="mod-table">\n'
        + "    <thead>\n"
        + '        <tr id="inst-th">\n'
        + "            <th>Name</th>\n"
        + "            <th>Adr.</th>\n"
        + "            <th>Kanäle</th>\n"
        + '            <th title="Wartende Bytes im Ringsspeicher">Buf.</th>\n'
        + '            <th title="Anzahl Timeouts">Tout.</th>\n'
        + '            <th title="Anzahl defekter Strings">Def.</th>\n'
        + '            <th title="Anzahl interner Abspeicherfehler">Speich.</th>\n'
        + '            <th title="Momentante Antwortzeit [ms]">Antw.</th>\n'
        + '            <th title="Maximale Antwortzeit [ms]">Max.</th>\n'
        + '            <th data-sort-method="none" title="Auswählen, um Fehlerzähler zurückzusetzen"></th>\n'
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tend_lines = (
        "  </tbody>\n</table>\n"
        + '<button name="RemoveModules" id="tbl-button" title="Rücksetzen aller Fehlerereignisse für ausgewählte Module" type="submit" disabled>Fehler rücksetzen</button>'
        + "</form>\n"
    )

    table_str = thead_lines
    for mod_addr in list(comm_stat.keys()):
        name = comm_stat[mod_addr][0]
        chan_pair = chan_pairs[comm_stat[mod_addr][1] - 1]
        waiting_bytes = comm_stat[mod_addr][2]
        no_timeouts = comm_stat[mod_addr][3]
        no_str_errs = comm_stat[mod_addr][4]
        no_storage_errs = comm_stat[mod_addr][5]
        curr_resp_time = comm_stat[mod_addr][6]
        max_resp_time = comm_stat[mod_addr][7]
        table_str += tr_line
        table_str += td_line.replace("><", f">{name}<")
        table_str += td_line.replace("><", f">{mod_addr}<")
        table_str += td_line.replace("><", f">{chan_pair}<")
        table_str += td_line.replace("><", f">{waiting_bytes}<")
        table_str += td_line.replace("><", f">{no_timeouts}<")
        table_str += td_line.replace("><", f">{no_str_errs}<")
        table_str += td_line.replace("><", f">{no_storage_errs}<")
        table_str += td_line.replace("><", f">{round(curr_resp_time / 4, 1)}<")
        table_str += td_line.replace("><", f">{round(max_resp_time / 4, 1)}<")
        table_str += td_line.replace(
            "><",
            f'><input type="checkbox" class="mod_sels" name="modsel_{mod_addr}" id="mod-{mod_addr}"><',
        )
        table_str += tre_line
    table_str += tend_lines
    return table_str


async def build_status_table(app, mod_addr: int, update: bool) -> str:
    """Get module status and build table."""

    table_str = ""
    tr_line = '        <tr id="inst-tr">\n'
    tre_line = "        </tr>\n"
    td_line = "            <td></td>\n"
    thead_lines = (
        '<form action="test/execute" id="table-form">\n'
        '<table id="<tbl_id>">\n'
        + "    <thead>\n"
        + '        <tr id="inst-th">\n'
        + '            <th style="width: 10%;">Nr.</th>\n'
        + '            <th style="width: 65%;">Name</th>\n'
        + '            <th style="width: 15%;">Typ</th>\n'
        + '            <th style="width: 10%;">Aktiv</th>\n'
        + "        </tr>\n"
        + "    </thead>\n"
        + "    <tbody>\n"
    )
    tbl_end_line = "  </tbody>\n</table>\n"
    form_end_line = "</form>\n"

    api_srv = app["api_srv"]
    rtr = api_srv.routers[0]
    mod = rtr.get_module(mod_addr)
    if update:
        await api_srv.set_server_mode()
        await mod.hdlr.get_module_status(mod_addr)
        # hot fix for comm errors
        await sleep(0.1)
        await api_srv.set_operate_mode()
    settings = mod.get_module_settings()
    if settings.properties["inputs"] > 0:
        table_str += "<h3>Eingänge</h3>"
        inp_state = int.from_bytes(
            mod.status[MirrIdx.INP_1_8 : MirrIdx.INP_1_8 + 3], "little"
        )
        table_str += thead_lines.replace("<tbl_id>", "mod-inputs-table")
        for inp in settings.buttons:
            inp_nmbr = inp.nmbr
            table_str += tr_line
            table_str += td_line.replace("><", f">{inp_nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{inp.name}<",
            )
            table_str += td_line.replace("><", ">Modul<")
            if inp_state & 1 << (inp_nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            table_str += td_line.replace(
                "><",
                ">Taste<",
            )
            table_str += tre_line
        for inp in settings.inputs:
            inp_nmbr = inp.nmbr + len(settings.buttons)
            table_str += tr_line
            table_str += td_line.replace("><", f">{inp_nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{inp.name}<",
            )
            if inp.nmbr <= settings.properties["inputs_230V"]:
                table_str += td_line.replace("><", ">230V<")
            elif inp.type == 3:
                table_str += td_line.replace("><", ">0..10V<")
            else:
                table_str += td_line.replace("><", ">24V<")
            if inp_state & 1 << (inp_nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            if inp.type == 2:
                table_str += td_line.replace(
                    "><",
                    f' title="Zeigt den Schalterzustand an"><input type="checkbox" class="inp_chk" name="inp-{inp_nmbr}" {sel_chkd}><',
                )
            elif inp.type == 3:
                table_str += td_line.replace(
                    "><",
                    ">analog<",
                )
            else:
                table_str += td_line.replace(
                    "><",
                    ">Taste<",
                )
            table_str += tre_line
        table_str += tbl_end_line
    if settings.properties["outputs"] > 0:
        table_str += "<h3>Ausgänge</h3>"
        out_state = int.from_bytes(
            mod.status[MirrIdx.OUT_1_8 : MirrIdx.OUT_1_8 + 3], "little"
        )
        table_str += thead_lines.replace("<tbl_id>", "mod-outputs-table")
        for outp in settings.outputs:
            table_str += tr_line
            table_str += td_line.replace("><", f">{outp.nmbr}<")
            table_str += td_line.replace(
                "><",
                f">{outp.name}<",
            )
            if outp.nmbr <= settings.properties["outputs_230V"]:
                table_str += td_line.replace("><", ">230V<")
            elif (
                outp.nmbr
                <= settings.properties["outputs_230V"]
                + settings.properties["outputs_dimm"]
            ):
                table_str += td_line.replace("><", ">Dimmer<")
            elif (
                outp.nmbr
                <= settings.properties["outputs_230V"]
                + settings.properties["outputs_dimm"]
                + settings.properties["outputs_24V"]
            ):
                table_str += td_line.replace("><", ">24V<")
            else:
                table_str += td_line.replace("><", ">Relais<")
            if out_state & 1 << (outp.nmbr - 1):
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            table_str += td_line.replace(
                "><",
                f' title="Auswahl um Ausgang einzuschalten"><input type="checkbox" class="out_chk" name="out-{outp.nmbr}" {sel_chkd}><',
            )
            table_str += tre_line
        table_str += tbl_end_line
    table_str += "<h3>Events</h3>"
    table_str += (
        thead_lines.replace("<tbl_id>", "mod-events-table")
        .replace("Nr.", "Zeit")
        .replace("Typ", "Wert")
        .replace("Aktiv", "")
    )
    for line in range(8):
        table_str += tr_line
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += td_line.replace("><", ">&nbsp;<")
        table_str += tre_line
    table_str += tbl_end_line
    table_str += form_end_line

    if mod._typ == b"\x1e\x01":
        # Ekey-Modul
        table_str += "<h3>SmartKey koppeln</h3>"
        table_str += '  <form id="pair_ekey" action="settings/pair">'
        table_str += (
            thead_lines.replace("<tbl_id>", "mod-outputs-table")
            .replace('            <th style="width: 10%;">Nr.</th>\n', "")
            .replace('            <th style="width: 15%;">Typ</th>\n', "")
            .replace(">Name<", ' style="width: 132px;">Kopplung starten<')
        ).replace(
            '<th style="width: 10%;">Aktiv<',
            '<th style="width: 100px;"><button form="pair_ekey" title="Betätigen, um Kopplung zwischen FanSer und Ekey zu starten (nur einmalig nötig)" class="ekey_pair" name="ekey_pair">Koppeln<',
        )
        table_str += tbl_end_line
        table_str += "  </form>"

    return table_str
