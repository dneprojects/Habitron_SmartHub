from math import copysign
from aiohttp import web
from datetime import datetime
from urllib.parse import parse_qs
from automtn_trigger import Weekdays
from configuration import RouterSettings
from config_commons import (
    activate_side_menu,
    adjust_automations_button,
    adjust_ekeylog_button,
    adjust_settings_button,
    adjust_side_menu,
    fill_page_template,
    indent,
    get_module_image,
    disable_button,
    hide_button,
    client_not_authorized,
    show_not_authorized,
    inspect_header,
)
from config_testing import show_module_testpage
from const import (
    LGC_TYPES,
    WEB_FILES_DIR,
    AUTOMATIONS_TEMPLATE_FILE,
    SETTINGS_TEMPLATE_FILE,
    CONF_PORT,
    SYS_MODES,
    FingerNames,
    MirrIdx,
    IfDescriptor,
    LgcDescriptor,
    DAY_NIGHT_MODES,
    DAY_NIGHT_MODES_HELP,
    RT_ERROR_CODE,
    MOD_CHANGED,
)
from configuration import set_cover_name, set_cover_output_name
from multidict import MultiDict

routes = web.RouteTableDef()


class ConfigSettingsServer:
    """Web server for settings configuration tasks."""

    def __init__(self, parent, api_srv):
        self.api_srv = api_srv
        self._ip = api_srv.sm_hub._host_ip
        self._port = CONF_PORT
        self.parent = parent
        self.app = web.Application()
        self.app.add_routes(routes)
        self.app["parent"] = self.parent

    @routes.get("/module-{mod_addr}")
    async def get_module(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        mod_addr = int(request.match_info["mod_addr"])
        return show_module_overview(request.app["parent"], mod_addr)

    @routes.get("/settings")
    async def get_settings(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        if args[0] == "ModSettings":
            mod_addr = int(args[1])
            return show_settings(request.app["parent"], mod_addr)
        elif args[0] == "RtrSettings":
            return show_settings(request.app["parent"], 0)

    @routes.get("/step")
    async def get_step(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        return await show_next_prev(request.app["parent"], args[1])

    @routes.post("/settings")
    async def post_settings(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        resp = await request.text()
        form_data = parse_qs(resp)
        settings = request.app["parent"]["settings"]
        if "sim_pin1" in form_data.keys() and "sim_pin2" in form_data.keys():
            if form_data["sim_pin1"] == form_data["sim_pin2"]:
                settings.sim_pin = form_data["sim_pin1"][0]
                settings.sim_pin_changed = True
            else:
                # both fields filled, but don't match
                return show_settings(request.app["parent"], settings.id)
        elif "sim_pin1" in form_data.keys() or "sim_pin2" in form_data.keys():
            # only one field filled
            return show_settings(request.app["parent"], settings.id)
        for form_key in list(form_data.keys())[:-1]:
            if form_key == "area_member":
                settings.__setattr__(form_key, int(form_data[form_key][0]))
            elif form_key == "mov_led":
                if form_data[form_key][0] == "on":
                    settings.mov_led = 74  # "J"
                else:
                    settings.mov_led = 78  # "N"
            elif form_key == "mov_level":
                # special: if mov_led unchecked, no form_key is sent
                if "mov_led" not in list(form_data.keys()):
                    settings.mov_led = 78  # "N"
                settings.__setattr__(form_key, form_data[form_key][0])
            elif form_key == "sens_type":
                settings.is_outdoor = form_data[form_key][0] == "on"
            else:
                settings.__setattr__(form_key, form_data[form_key][0])

        if settings.typ == b"\x32\x28" and "sens_type" not in list(
            form_data.keys()
        ):  # Smart Sensor
            # if unchecekd no form_key is sent
            settings.is_outdoor = False
        args = form_data["ModSettings"][0]
        return await show_next_prev(request.app["parent"], args)

    @routes.post("/step")
    async def post_step(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        resp = await request.text()
        form_data = parse_qs(resp)
        args = parse_response_form(request.app["parent"], form_data)
        return await show_next_prev(request.app["parent"], args)

    @routes.get("/teach")
    async def get_teach(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        return await show_next_prev(request.app["parent"], args)

    @routes.get("/show_logs")
    async def show_logs(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        return await show_ekey_logs(request.app["parent"], args[1])

    @routes.get("/ekey_log_table")
    async def ekey_logs(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        args = request.query_string.split("=")
        if args[0] == "":
            module = request.app["parent"]["module"]
            await module.hdlr.ekey_log_delete()
            return show_module_overview(request.app["parent"], module._id)
        cmd = args[1].split("-")[0]
        mod_addr = int(args[1].split("-")[1])
        if cmd == "save":
            return log_download(request.app["parent"])
        else:
            return show_module_overview(request.app["parent"], mod_addr)

    @routes.get("/pair")
    async def ekey_pair(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        module = request.app["parent"]["module"]
        await module.hdlr.set_ekey_pairing()
        return await show_module_testpage(request.app["parent"], module._id, True)


async def show_router_overview(main_app, popup_msg="") -> web.Response:
    """Prepare overview page of module."""
    api_srv = main_app["api_srv"]
    rtr = api_srv.routers[0]

    side_menu = activate_side_menu(
        main_app["side_menu"], ">Router<", api_srv.is_offline or api_srv._pc_mode
    )
    type_desc = "Smart Router - Kommunikationsschnittstelle zwischen den Modulen"
    if rtr.channels == b"":  #  and not main_app["is_install"]:
        page = fill_page_template(
            "Router", type_desc, "", "--", side_menu, "router.jpg", ""
        )
        page = adjust_settings_button(page, "", f"{0}")
        return web.Response(text=page, content_type="text/html")
    props = "<h3>Eigenschaften</h3>\n"
    props += "<table>\n"
    props += f'<tr><td style="width:90px;">Hardware:</td><td>{rtr.serial.decode("iso8859-1")[1:]}</td></tr>\n'
    props += (
        f"<tr><td>Firmware:</td><td>{rtr.version.decode('iso8859-1')[1:]}</td></tr>\n"
    )
    if api_srv.is_offline or api_srv._pc_mode:
        rtr.chan_status = f"{chr(len(rtr.modules))}\x20".encode("iso8859-1")
    mode0 = rtr.chan_status[1]
    config_mode = mode0 == SYS_MODES.Config
    day_mode = mode0 & 0x3
    alarm_mode = mode0 & 0x4
    mode0 = mode0 & 0xF8
    mode_str = ""
    if config_mode:
        mode_str = "Konfig"
    elif mode0 == 0:
        mode_str = "Undefined (0)"
    elif mode0 == 112:
        mode_str = "Urlaub"
    elif mode0 == 96:
        mode_str = rtr.user_modes[12:].decode("iso8859-1").strip()
    elif mode0 == 80:
        mode_str = rtr.user_modes[1:11].decode("iso8859-1").strip()
    elif mode0 == 48:
        mode_str = "Schlafen"
    elif mode0 == 32:
        mode_str = "Anwesend"
    elif mode0 == 16:
        mode_str = "Abwesend"
    if day_mode == 1:
        mode_str += ", Tag"
    elif day_mode == 2:
        mode_str += ", Nacht"
    if alarm_mode == 4:
        mode_str += ", Alarm"
    if mode_str[0] == ",":
        mode_str = mode_str[2:]
    props += "</table>\n"
    props += "<h3>Status</h3>\n"
    props += "<table>\n"
    props += '<tr><td style="width:90px;">Mode:</td><td>' + mode_str + "</td></tr>\n"
    if api_srv._opr_mode:
        props += "<tr><td>Betriebsart:</td><td>Operate</td></tr>\n"
    else:
        props += "<tr><td>Betriebsart:</td><td>Client/Server</td></tr>\n"
    if api_srv.mirror_mode_enabled and api_srv._opr_mode:
        props += "<tr><td>Spiegel:</td><td>aktiv</td></tr>\n"
    else:
        props += "<tr><td>Spiegel:</td><td>inaktiv</td></tr>\n"
    if api_srv.event_mode_enabled and api_srv._opr_mode:
        props += "<tr><td>Events:</td><td>aktiv</td></tr>\n"
    else:
        props += "<tr><td>Events:</td><td>inaktiv</td></tr>\n"
    props += f"<tr><td>Modulanzahl:</td><td>{rtr.chan_status[0]}</td></tr>\n"
    if rtr.comm_errors[0]:
        last_err_str = f'Modul {rtr.comm_errors[0]}: <a title="{RT_ERROR_CODE[rtr.comm_errors[1]]}">F{rtr.comm_errors[1]}</a>'
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
    props += f"<tr><td>Fehler:</td><td>{mod_err_str}</td></tr>\n"
    props += f"<tr><td>Letzter Fehler:</td><td>{last_err_str}</td></tr>\n"

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
    page = adjust_settings_button(page, "rtr", f"{0}")
    if len(popup_msg):
        page = page.replace(
            '<h3 id="resp_popup_txt">response_message</h3>',
            f'<h3 id="resp_popup_txt">{popup_msg}</h3>',
        ).replace('id="resp-popup-disabled"', 'id="resp-popup"')
    return web.Response(text=page, content_type="text/html")


def show_module_overview(main_app, mod_addr, popup_msg="") -> web.Response:
    """Prepare overview page of module."""
    api_srv = main_app["api_srv"]
    module = api_srv.routers[0].get_module(mod_addr)
    side_menu = activate_side_menu(
        main_app["side_menu"], ">Module<", api_srv.is_offline or api_srv._pc_mode
    )
    side_menu = activate_side_menu(
        side_menu, f"module-{module._id}", api_srv.is_offline or api_srv._pc_mode
    )
    mod_image, type_desc = get_module_image(module._typ)
    main_app["module"] = module
    if module.settings is None:
        module.get_module_settings()
    mod_description = get_module_properties(module)
    def_filename = f"module_{mod_addr}.hmd"
    page = fill_page_template(
        f"Modul '{module._name}'",
        type_desc,
        "",
        mod_description,
        side_menu,
        mod_image,
        def_filename,
    )
    page = adjust_settings_button(page, "mod", f"{mod_addr}")
    if module.has_automations():
        page = adjust_automations_button(page)
    elif module._typ == b"\x1e\x01":
        page = adjust_ekeylog_button(page)
    if len(popup_msg):
        page = page.replace(
            '<h3 id="resp_popup_txt">response_message</h3>',
            f'<h3 id="resp_popup_txt">{popup_msg}</h3>',
        ).replace('id="resp-popup-disabled"', 'id="resp-popup"')
    return web.Response(text=page, content_type="text/html")


async def show_next_prev(main_app, args):
    """Do the step logic and prepare next page."""

    settings = main_app["settings"]
    if isinstance(args, list):
        time = int(args[1].split("&")[0])
        args1 = args[2].split("-")
        button = args1[0]
        mod_addr = int(args1[1])
        step = 2
        user_id = settings.users_sel + 1
        finger_id = int(args1[2])
        await settings.teach_new_finger(main_app, user_id, finger_id, time)
        return show_setting_step(main_app, mod_addr, step)
    else:
        args1 = args.split("-")
        button = args1[0]
        mod_addr = int(args1[1])
        step = int(args1[2])
    if button == "cancel":
        if mod_addr > 0:
            return show_module_overview(main_app, mod_addr, "Änderungen verworfen")
        else:
            return await show_router_overview(main_app, "Änderungen verworfen")

    if button == "save":
        if mod_addr > 0:
            module = settings.module
            router = module.get_rtr()
            await main_app["api_srv"].block_network_if(module.rt_id, True)
            try:
                await module.set_settings(settings)
                main_app["side_menu"] = adjust_side_menu(
                    router.modules, main_app["is_offline"], main_app["is_install"]
                )
                if settings.group != int(settings.group_member):
                    # group membership changed, update in router
                    await router.set_module_group(mod_addr, int(settings.group_member))
                    settings.group = int(settings.group_member)
                if module.changed & MOD_CHANGED.NEW:
                    success_msg = "Neues Modul, Änderungen temporär übernommen,<br>Daten in Konfigurationsdatei speichern<br>oder Modul durch Übertragen hinzufügen."
                else:
                    success_msg = "Änderungen übernommen"
            except Exception as err_msg:
                success_msg = f"Error while saving module settings: {err_msg}"
                main_app.logger.error(success_msg)

            await main_app["api_srv"].block_network_if(module.rt_id, False)
            return show_module_overview(main_app, mod_addr, success_msg)
        else:
            # Save settings in router
            router = main_app["api_srv"].routers[0]
            await main_app["api_srv"].block_network_if(router._id, True)
            try:
                await router.set_settings(settings)
                await router.set_descriptions(settings)
                main_app["side_menu"] = adjust_side_menu(
                    main_app["api_srv"].routers[0].modules,
                    main_app["is_offline"],
                    main_app["is_install"],
                )
                success_msg = "Änderungen übernommen"
            except Exception as err_msg:
                success_msg = f"Error while saving router settings: {err_msg}"
                main_app.logger.error(success_msg)
            await main_app["api_srv"].block_network_if(router._id, False)
            return await show_router_overview(main_app, success_msg)
    props = settings.properties
    main_app["props"] = props
    io_keys = settings.prop_keys
    main_app["io_keys"] = io_keys
    no_props = props["no_keys"]
    if button == "next":
        if step < no_props:
            step += 1
    elif button == "back":
        if step > 0:
            step -= 1
    return show_setting_step(main_app, mod_addr, step)


def show_settings(main_app, mod_addr) -> web.Response:
    """Prepare settings page of module."""
    if mod_addr > 0:
        settings = (
            main_app["api_srv"].routers[0].get_module(mod_addr).get_module_settings()
        )
        title_str = f"Modul '{settings.name}'"
    else:
        settings = main_app["api_srv"].routers[0].get_router_settings()
        title_str = f"Router '{settings.name}'"
    main_app["settings"] = settings
    main_app["key"] = ""
    page = fill_settings_template(
        main_app, title_str, "Grundeinstellungen", 0, settings, ""
    )
    return web.Response(text=page, content_type="text/html")


def show_setting_step(main_app, mod_addr, step) -> web.Response:
    """Prepare overview page of module."""
    mod_settings = main_app["settings"]
    if mod_addr > 0:
        title_str = f"Modul '{mod_settings.name}'"
    else:
        title_str = f"Router '{mod_settings.name}'"
    if step > 0:
        key, header, prompt = get_property_kind(main_app, step)
        main_app["prompt"] = prompt
        main_app["key"] = key
        page = fill_settings_template(
            main_app, title_str, header, step, mod_settings, key
        )
    else:
        page = fill_settings_template(
            main_app, title_str, "Grundeinstellungen", 0, mod_settings, ""
        )
    return web.Response(text=page, content_type="text/html")


def fill_settings_template(main_app, title, subtitle, step, settings, key: str) -> str:
    """Return settings page."""
    if settings.typ == b"\x00\x00":
        mod_addr = 0
    else:
        mod_addr = settings.id
    with open(
        WEB_FILES_DIR + SETTINGS_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    if key == "fingers":
        mod_image, mod_type = get_module_image(b"\x1f")
    else:
        mod_image, mod_type = get_module_image(settings.typ)
    page = (
        page.replace("ContentTitle", title)
        .replace("ContentSubtitle", subtitle)
        .replace("controller.jpg", mod_image)
        .replace("ModAddress", f"{mod_addr}-{step}")
    )
    if key == "fingers":
        finger_dict_str = "const fngrNames = {\n"
        for f_i in range(10):
            finger_dict_str += f'  {f_i+1}: "{FingerNames[f_i + 1]}",\n'
        finger_dict_str += "}\n"
        page = page.replace("const fngrNames = {}", finger_dict_str)
        if main_app["api_srv"].is_offline:
            page = disable_button("Start", page)
    if step == 0:
        page = disable_button("zurück", page)
        # page = page.replace('form="settings_table"', "")
        settings_form = prepare_basic_settings(main_app, mod_addr, mod_type)
        if settings.properties["no_keys"] == 0:
            page = disable_button("weiter", page)
    else:
        if step == main_app["props"]["no_keys"]:
            page = disable_button("weiter", page)
        settings_form = prepare_table(main_app, mod_addr, step, key)
    if key == "logic":
        page = page.replace(
            "reserved_numbers = []",
            f"reserved_numbers = {settings.get_counter_numbers()}",
        )
    if key == "counters":
        page = page.replace(
            "reserved_numbers = []",
            f"reserved_numbers = {settings.get_logic_numbers()}",
        )
    page = page.replace("<p>ContentText</p>", settings_form)
    return page


def get_module_properties(mod) -> str:
    """Return module properties, like firmware."""
    props = "<h3>Eigenschaften</h3>\n"
    props += "<table>\n"
    props += f'<tr><td style="width:80px;">Adresse:</td><td>{mod._id}</td></tr>\n'
    props += f"<tr><td>Kanalpaar:</td><td>{mod._channel*2 - 1} + {mod._channel*2}</td></tr>\n"
    props += f"<tr><td>Bereich:</td><td>{mod.get_area_name()}</td></tr>\n"
    props += f"<tr><td>Gruppe:</td><td>{mod.get_group_name()}</td></tr>\n"
    props += f"<tr><td>Hardware:</td><td>{mod._serial}</td></tr>\n"
    props += f"<tr><td>Firmware:</td><td>{mod.get_sw_version()}</td></tr>\n"
    props += "</table>\n"
    return props


def prepare_basic_settings(main_app, mod_addr, mod_type):
    """Prepare settings page for basic settings, e.g. name."""
    settings = main_app["settings"]
    tbl = (
        indent(4)
        + '<form id="settings_table" action="settings/settings" method="post">\n'
    )
    tbl += "\n" + indent(5) + "<table>\n"
    id_name = "mname"
    if mod_addr > 0:
        prompt = "Modulname"
    else:
        prompt = "Routername"
    tbl += (
        indent(7)
        + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="name" '
        + f'type="text" maxlength="32" id="{id_name}" value="{settings.name}"/></td></tr>\n'
    )
    if mod_addr > 0:
        # Module
        id_name = "area_member"
        prompt = "Zuordnung zu Bereich"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td>'
            + f'<td><select name="{id_name}" id="{id_name}">\n'
        )
        rtr = main_app["api_srv"].routers[0]
        rt_settings = RouterSettings(rtr)
        areas = rt_settings.areas
        for area in areas:
            if area.nmbr == settings.area_member:
                tbl += (
                    indent(8)
                    + f'<option value="{area.nmbr}" selected>{area.name}</option>\n'
                )
            else:
                tbl += indent(8) + f'<option value="{area.nmbr}">{area.name}</option>\n'
        tbl += indent(7) + "/select></td></tr>\n"
        id_name = "group_member"
        prompt = "Gruppenzugehörigkeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td>'
            + f'<td><select name="{id_name}" id="{id_name}">\n'
        )
        grps = rt_settings.groups
        for grp in grps:
            if grp.nmbr == settings.group:
                tbl += (
                    indent(8)
                    + f'<option value="{grp.nmbr}" selected>{grp.name}</option>\n'
                )
            else:
                tbl += indent(8) + f'<option value="{grp.nmbr}">{grp.name}</option>\n'
        tbl += indent(7) + "/select></td></tr>\n"
    else:
        # Router
        id_name = "user1_name"
        prompt = "Benutzer Modus 1"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="text" maxlength="10" id="{id_name}" value="{settings.user1_name}"/>\n'
        )
        id_name = "user2_name"
        prompt = "Benutzer Modus 2"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="text" maxlength="10" id="{id_name}" value="{settings.user2_name}"/>\n'
        )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller XL-2 (LE2)",
        "Smart Controller Mini",
    ]:
        id_name = "displ_contr"
        prompt = "Display-Kontrast"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="number" min="0" max="50" id="{id_name}" value="{settings.displ_contr}"/></td></tr>\n'
        )
        id_name = "displ_time"
        prompt = "Display-Leuchtzeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="number" min="1" max="255" id="{id_name}" value="{settings.displ_time}"/></td></tr>\n'
        )
    if settings.type in ["Smart Sensor"]:
        id_name = "sens_type"
        prompt = "Verwendung als Außensensor"
        if settings.is_outdoor:
            sens_type_str = "checked"
        else:
            sens_type_str = ""
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="checkbox" id="{id_name}" {sens_type_str}/></td></tr>\n'
        )
    if settings.type in [
        "Smart Detect 180",
        "Smart Detect 360",
        "Smart Detect 180-2",
    ]:
        id_name = "mov_led"
        prompt = "LED-Anzeige"
        if settings.mov_led == 74:
            mov_led_str = "checked"
        else:
            mov_led_str = ""
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="checkbox" id="{id_name}" {mov_led_str}/></td></tr>\n'
        )
        id_name = "mov_level"
        prompt = "Bewegungsschwelle"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="number" min="1" max="250" id="{id_name}" value="{settings.mov_level}"/></td></tr>\n'
        )
    if mod_addr > 0:
        if len(settings.inputs) > 0:
            id_name = "t_short"
            prompt = "Tastendruck kurz [ms]"
            tbl += (
                indent(7)
                + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
                + f'type="number" min="10" max="250" id="{id_name}" value="{settings.t_short}"/></td></tr>\n'
            )
            id_name = "t_long"
            prompt = "Tastendruck lang [ms]"
            tbl += (
                indent(7)
                + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
                + f'type="number" min="100" max="2500" id="{id_name}" value="{settings.t_long}"/></td></tr>\n'
            )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller XL-2 (LE2)",
        "Smart Dimm",
        "Smart Dimm-1",
        "Smart Dimm-2",
    ]:
        id_name = "t_dimm"
        prompt = "Dimmgeschwindigkeit"
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="{id_name}" '
            + f'type="number" min="1" max="10" id="{id_name}" value="{settings.t_dimm}"/></td></tr>\n'
        )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller XL-2 (LE2)",
        "Smart Controller Mini",
        "Smart Sensor",
    ]:
        id_name = "temp_ctl"
        prompt = "Temperatur-Regelverhalten"
        cl1_checked = ""
        cl2_checked = ""
        cl3_checked = ""
        cl4_checked = ""
        if len(settings.status) == 0:
            cl4_checked = "checked"
        else:
            match settings.temp_ctl:
                case 1:
                    cl1_checked = "checked"
                case 2:
                    cl2_checked = "checked"
                case 3:
                    cl3_checked = "checked"
                case 4:
                    cl4_checked = "checked"
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_cl1">Heizen</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_cl1" value="1" {cl1_checked}></div>'
            + f'<div><label for="{id_name}_cl2">Kühlen</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_cl2" value="2" {cl2_checked}></div>'
            + f'<div><label for="{id_name}_cl3">Heizen / Kühlen</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_cl3" value="3" {cl3_checked}></div>'
            + f'<div><label for="{id_name}_cl4">Aus</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_cl4" value="4" {cl4_checked}></div></td></tr>\n'
        )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller XL-2 (LE2)",
        "Smart Controller Mini",
    ]:
        id_name = "temp_1_2"
        prompt = "Temperatursensor"
        if len(settings.status) == 0:
            s1_checked = "checked"
            s2_checked = ""
        else:
            if settings.temp_1_2 == 1:
                s1_checked = "checked"
                s2_checked = ""
            else:
                s1_checked = ""
                s2_checked = "checked"
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_s1">Sensor 1</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_s1" value="1" {s1_checked}></div>'
            + f'<div><label for="{id_name}_s2">Sensor 2</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_s2" value="2" {s2_checked}></div></td></tr>\n'
        )
    if settings.type in [
        "Smart Controller XL-1",
        "Smart Controller XL-2",
        "Smart Controller XL-2 (LE2)",
    ]:
        id_name = "supply_prio"
        prompt = "Versorgungspriorität"
        if len(settings.status) == 0:
            v230_checked = "checked"
            v24_checked = ""
        else:
            if settings.status[MirrIdx.SUPPLY_PRIO] == 66:
                v230_checked = ""
                v24_checked = "checked"
            else:
                v230_checked = "checked"
                v24_checked = ""
        tbl += (
            indent(7)
            + f'<td style="vertical-align: top;">{prompt}</td>'
            + f'<td><div><label for="{id_name}_230">230V</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_230" value="230" {v230_checked}></div>'
            + f'<div><label for="{id_name}_24">24V</label><input type="radio" '
            + f'name="{id_name}" id="{id_name}_24" value="24" {v24_checked}></div></td></tr>\n'
        )
    if settings.type in ["Smart GSM"]:
        tbl += (
            indent(7)
            + '<td style="vertical-align: top;">SIM Pin (nur bei Änderung eingeben)</td>'
            + '<td><div><input type="password" '
            + 'name="sim_pin1" id="sim_pin1" minlength="4" maxlength="4">'
            + "</div></td></tr>\n"
            + indent(7)
            + '<td style="vertical-align: top;">SIM Pin (wiederholen)</td>'
            + '<td><div><input type="password" '
            + 'name="sim_pin2" id="sim_pin2" minlength="4" maxlength="4">'
            + "</div></td></tr>\n"
        )
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def prepare_table(main_app, mod_addr, step, key) -> str:
    """Prepare settings table with form of edit fields."""

    if key in ["inputs", "outputs"]:  # prepare area popup menu
        module = main_app["settings"].module
        rtr = main_app["api_srv"].routers[module.rt_id - 1]
        areas = rtr.settings.areas
        area_name_mod = rtr.get_area_name(main_app["settings"].area_member)
        area_menu = '<td><select name="area_sel" id="area-select" title="Zuordnung zu Bereich (Raum)" style="width:50px;">'
        for area in areas:
            area_menu += f'<option value="{area.nmbr}">{area.name}</option>'
        area_menu += "</td>"

    key_prompt = main_app["prompt"]
    if hasattr(main_app["settings"], "covers"):
        covers = getattr(main_app["settings"], "covers")

    tbl_data = getattr(main_app["settings"], key)
    tbl = (
        indent(4) + '<form id="settings_table" action="settings/step" method="post">\n'
    )
    tbl += "\n" + indent(5) + '<table id="set_tbl">\n'

    tbl_entries = dict()
    for ci in range(len(tbl_data)):
        if key == "fingers":
            user_id = main_app["settings"].users[main_app["settings"].users_sel].nmbr
            if tbl_data[ci].type == user_id:
                f_nmbr = tbl_data[ci].nmbr
                tbl_entries.update({f_nmbr: ci})
        elif key in ["day_sched", "night_sched"]:
            light_modules: list[tuple[int, str]] = []
            modules = main_app["api_srv"].routers[0].modules
            for mod in modules:
                if mod._typ[0] == 0x14:
                    # smart nature
                    light_modules.append((mod._id, mod._name))
            for mod in modules:
                if mod._typ[0] == 1 or mod._typ == b"\x32\x01" or mod._typ[0] == 0x50:
                    # smart controllers and smart detect
                    light_modules.append((mod._id, mod._name))
            if ci:
                tbl_entries.update({ci: ci - 1})
            else:
                tbl_entries.update({0: 6})  # sunday 1st day
        elif key in ["messages", "gsm_messages", "gsm_numbers"]:
            # only entries in language 1 (german) supported
            if tbl_data[ci].type == 1:
                tbl_entries.update({tbl_data[ci].nmbr: ci})
        else:
            tbl_entries.update({tbl_data[ci].nmbr: ci})
    tbl_entries = sorted(tbl_entries.items())
    if key in ["leds"]:
        # For SC skip night light, for small SC skip ambient light
        tbl_entries = tbl_entries[1:]
    ci = 0
    wd = 50  # code for weekdays, starting with Sunday
    for entry in tbl_entries:
        ci = entry[1]
        id_name = key[:-1] + str(ci)
        if key not in ["day_sched", "night_sched"]:
            prompt = key_prompt + f"&nbsp;{tbl_data[ci].nmbr}"
        if key in [
            "leds",
            "buttons",
            "dir_cmds",
            "messages",
        ]:
            maxl = 18
        else:
            maxl = 32
        if key == "covers":
            if covers[ci].type == 0:
                tbl += (
                    indent(7)
                    + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},0]" '
                    + f'type="text" id="{id_name}" maxlength="{maxl}" value=" --" disabled></td>'
                )
            else:
                tbl += (
                    indent(7)
                    + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},0]" '
                    + f'type="text" id="{id_name}" maxlength="{maxl}" value="{tbl_data[ci].name[:maxl].strip()}"></td>'
                )
        elif key in ["day_sched", "night_sched"]:
            tbl += (
                indent(7)
                + "<tr>"
                + indent(8)
                + f'<td><label for="{id_name}">{Weekdays[wd]}</label></td>'
                + indent(8)
                + f'<td><select title="Auswahl des Umschaltmodus" name="data[{ci},2]" class="daytime" id="{id_name}">\n'
            )
            wd += 1
            for md in range(-1, 4):
                if tbl_data[ci]["mode"] == md:
                    tbl += (
                        indent(9)
                        + f'<option value="{md}" title="{DAY_NIGHT_MODES_HELP[md]}" selected>{DAY_NIGHT_MODES[md]}</option>\n'
                    )
                else:
                    tbl += (
                        indent(9)
                        + f'<option value="{md}" title="{DAY_NIGHT_MODES_HELP[md]}">{DAY_NIGHT_MODES[md]}</option>\n'
                    )
            tbl += (
                indent(8)
                + "</td>\n"
                + indent(8)
                + f'<td><input name="data[{ci},0]" '
                + f'type="time" title="Uhrzeit" class="daytime" id="{id_name}" maxlength="{maxl}" value="{tbl_data[ci]["hour"]:02}:{tbl_data[ci]["minute"]:02}"></td>'
                + indent(8)
                + f'<td><input title="Helligkeitswert" name="data[{ci},1]" type="number" min="0" max="2550" step="10" class="daytime" id="{id_name}" value="{tbl_data[ci]["light"] * 10}">&nbsp;lx</td>'
            )
            if entry[0]:
                tbl += indent(8) + "<td></td>\n"
            else:
                tbl += (
                    indent(8)
                    + f'<td><select title="Auswahl des Helligkeitssensors" name="data[{ci},3]" class="daytime" id="{id_name}">\n'
                )
                if tbl_data[ci]["module"] == 0:
                    # use smart nature (first in list, if available)
                    tbl_data[ci]["module"] = light_modules[0][0]
                for mod in light_modules:
                    if tbl_data[ci]["module"] == mod[0]:
                        tbl += (
                            indent(9)
                            + f'<option value="{mod[0]}" title="Helligkeitssensor von Modul {mod[0]} verwenden" selected>{mod[0]} - {mod[1]}</option>\n'
                        )
                    else:
                        tbl += (
                            indent(9)
                            + f'<option value="{mod[0]}" title="Helligkeitssensor von Modul {mod[0]} verwenden">{mod[0]} - {mod[1]}</option>\n'
                        )
                tbl += indent(8) + "</td>\n"
        else:
            tbl += (
                indent(7)
                + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="data[{ci},0]" '
                + f'type="text" id="{id_name}" class="desc_input1" maxlength="{maxl}" title="Beschriftung (max. {maxl} Zeichen)"value="{tbl_data[ci].name[:maxl].strip()}"></td>'
            )
        if key in ["leds", "buttons", "dir_cmds", "messages"]:
            tbl += (
                f'<td><input name="data[{ci},1]" type="text" id="{id_name}" class="desc_input2" maxlength="14" '
                + f'title="2. Zeile (max. 14 Zeichen)" value="{tbl_data[ci].name[18:].strip()}"></td>'
            )
        elif key == "inputs":
            if tbl_data[ci].area == 0:
                area_name_e = area_name_mod
            else:
                area_name_e = rtr.get_area_name(tbl_data[ci].area)
            tbl += area_menu.replace(f">{area_name_e}<", f" selected>{area_name_e}<")
            title_sw = "Eingang für Schalteranschluss konfigurieren"
            title_btn = "Eingang für Tasteranschluss konfigurieren"
            title_anl = "Eingang für analogen Messwert (0..10 V) konfigurieren"
            if tbl_data[ci].type == 1:
                btn_checked = "checked"
                sw_checked = ""
                anlg_checked = ""
            elif tbl_data[ci].type == 2:
                btn_checked = ""
                sw_checked = "checked"
                anlg_checked = ""
            elif tbl_data[ci].type == 3:
                btn_checked = ""
                sw_checked = ""
                anlg_checked = "checked"

            mod = main_app["api_srv"].routers[0].get_module(mod_addr)
            if (
                mod._typ == b"\x01\x03"
                and ci
                >= mod.io_properties["inputs_230V"]
                + mod.io_properties["inputs_24V"]
                - mod.io_properties["inputs_analog"]
            ):
                tbl += "<td></td><td></td>"
                tbl += (
                    f'<td><label title="{title_anl}" for="{id_name}_btn">analog</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_anlg" title="{title_anl}" value="anlg" checked></td>'
                )
            else:
                tbl += (
                    f'<td><label title="{title_sw}" for="{id_name}_sw">Schalter</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_sw" title="{title_sw}" value="sw" {sw_checked}></td>'
                )
                tbl += (
                    f'<td><label title="{title_btn}" for="{id_name}_btn">Taster</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_btn" title="{title_btn}" value="btn" {btn_checked}></td>'
                )
            if (
                mod._typ == b"\x0b\x1f"
                and ci
                >= mod.io_properties["inputs_230V"]
                + mod.io_properties["inputs_24V"]
                - mod.io_properties["inputs_analog"]
            ):
                tbl += (
                    f'<td><label for="{id_name}_btn">analog</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_anlg" value="anlg" {anlg_checked}></td>'
                )
        elif key == "outputs":
            if tbl_data[ci].area == 0:
                area_name_e = area_name_mod
            else:
                area_name_e = rtr.get_area_name(tbl_data[ci].area)
            tbl += area_menu.replace(f">{area_name_e}<", f" selected>{area_name_e}<")
            title_out = "Ausgänge einzeln verwenden"
            title_cov = "Ausgangspaar für Rollladen gebündelt"
            if (ci < 2 * len(covers)) and ((ci % 2) == 0):
                if tbl_data[ci].type == -10:
                    out_chkd = ""
                    cvr_chkd = "checked"
                else:
                    out_chkd = "checked"
                    cvr_chkd = ""
                tbl += (
                    f'<td><label title="{title_out}" for="{id_name}_out">Ausgang</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_out" title="{title_out}" value="out" {out_chkd}></td>'
                )
                tbl += (
                    f'<td><label title="{title_cov}" for="{id_name}_cvr">Rollladen</label><input type="radio" '
                    + f'name="data[{ci},1]" id="{id_name}_cvr" title="{title_cov}" value="cvr" {cvr_chkd}></td>'
                )
        elif key == "covers":
            if covers[ci].type != 0:
                cov_t = main_app["settings"].cover_times
                bld_t = main_app["settings"].blade_times
                title_txt = "Auswahl: Ausgang A auf, B ab / Abwahl: B auf, A ab "
                if tbl_data[ci].type > 0:
                    ipol_chkd = "checked"
                else:
                    ipol_chkd = ""
                tbl += (
                    f'<td></td><td><input name="data[{ci},1]" type="number" id="{id_name}_tc" min="0" step="1" max="255" '
                    + f'title="Verfahrzeit in s" value={cov_t[ci]} style="width: 40px;"></td>'
                )
                tbl += (
                    f'<td></td><td><input name="data[{ci},2]" type="number" id="{id_name}_tb" min="0" step="0.5" max="25.5" '
                    + f'title="Jalousiezeit in s (0 falls Rollladen)" value={bld_t[ci]} style="width: 40px;"></td>'
                )
                tbl += (
                    f'<td><input type="checkbox" title="{title_txt}" name="data[{ci},3]" value="pol_nrm" id="{id_name}_pinv" '
                    + f'{ipol_chkd}><label title="{title_txt}" for="{id_name}_pinv">Polarität, Ausg. A: auf</label></td>'
                )
        elif key == "groups":
            if tbl_data[ci].nmbr != 0:
                id_name = "group_dep"
                dep_names = [
                    "unabhängig",
                    "Tag/Nacht",
                    "Alarm",
                    "Tag/Nacht, Alarm",
                ]
                dep_titles = [
                    "Tag/Nacht- und Alarm-Zustand sind unabhängig von Gruppe 0",
                    "Tag/Nacht-Zustand ist wie in Gruppe 0, Alarm-Zustand ist unabhängig",
                    "Alarm-Zustand ist wie in Gruppe 0, Tag/Nacht-Zustand ist unabhängig",
                    "Tag/Nacht- und Alarm-Zustand sind wie in Gruppe 0",
                ]
                tbl += (
                    indent(7)
                    + f'<td><select title="Auswahl der Abhängigkeit des Tag/Nacht- und Alarm-Zustands von Gruppe 0" name="data[{ci},1]" id="{id_name}">\n'
                )
                for dep in range(4):
                    if main_app["settings"].mode_dependencies == b"":
                        tbl += (
                            indent(8)
                            + f'<option title="{dep_titles[dep]}" value="{dep}">{dep_names[dep]}</option>\n'
                        )
                    elif (
                        dep
                        == main_app["settings"].mode_dependencies[tbl_data[ci].nmbr - 1]
                    ):
                        tbl += (
                            indent(8)
                            + f'<option title="{dep_titles[dep]}" value="{dep}" selected>{dep_names[dep]}</option>\n'
                        )
                    else:
                        tbl += (
                            indent(8)
                            + f'<option title="{dep_titles[dep]}" value="{dep}">{dep_names[dep]}</option>\n'
                        )
                tbl += indent(7) + "/select></td>\n"
            else:
                tbl += "<td>&nbsp;&nbsp;Modi von Gruppe 0</td>"
        elif key == "users":
            # add check buttons to enable user
            id_name = "users_enable"
            title_txt = "Benutzerzugang freigeben bzw. sperren"
            if main_app["settings"].users[ci].type > 0:
                en_chkd = "checked"
            else:
                en_chkd = ""
            tbl += (
                f'<td><div style="position: absolute;"><label title="{title_txt}" for="{id_name}-{ci}">aktiv</label><input type="checkbox" '
                + f'name="{id_name}" id="{id_name}-{ci}" title="{title_txt}" value="{main_app["settings"].users[ci].nmbr}" {en_chkd}></div>'
            )
            # add radio buttons to select user
            id_name = "users_sel"
            title_txt = "Fingerabdrücke auf der nächsten Seite bearbeiten"
            if ci == main_app["settings"].users_sel:
                sel_chkd = "checked"
            else:
                sel_chkd = ""
            tbl += (
                f'<div style="margin-left: 60px;"><label title="{title_txt}" for="{id_name}-{ci}">Fingerabdrücke</label><input type="radio" '
                + f'name="{id_name}" id="{id_name}-{ci}" title="{title_txt}" value="{ci}" {sel_chkd}></div></td>'
            )
        if key in [
            "glob_flags",
            "flags",
            "areas",
            "groups",
            "vis_cmds",
            "coll_cmds",
            "dir_cmds",
            "messages",
            "counters",
            "logic",
            "users",
            "fingers",
            "gsm_numbers",
            "gsm_messages",
        ]:
            # Add additional checkbox element
            title_txt = "Auswahl um Eintrag zu entfernen"
            if key == "groups" and tbl_data[ci].nmbr == 0:
                pass  # group 0 not removable
            else:
                tbl += f'<td><input type="checkbox" class="sel_element" name="sel_{ci}" title="{title_txt}" value="{ci}"></td>'
        tbl += "</tr>\n"
    if key in [
        "glob_flags",
        "flags",
        "areas",
        "groups",
        "dir_cmds",
        "vis_cmds",
        "messages",
        "coll_cmds",
        "counters",
        "logic",
        "users",
        "fingers",
        "gsm_numbers",
        "gsm_messages",
    ]:
        # Add additional lines to append or delete element
        prompt = key_prompt
        id_name = key[:-1] + str(ci + 1)
        elem_nmbrs = []
        for elem in tbl_data:
            elem_nmbrs.append(elem.nmbr)
        elem_nmbrs = sorted(elem_nmbrs)
        if len(elem_nmbrs) > 0:
            min_new = 1
            for n_idx in range(len(elem_nmbrs)):
                if (elem_nmbrs[n_idx]) == min_new:
                    min_new = elem_nmbrs[n_idx] + 1
                else:
                    break
        else:
            min_new = 1
        if key in ["glob_flags", "flags"]:
            max_new = 16
        elif key in ["dir_cmds"]:
            max_new = 25
        elif key in ["messages"]:
            max_new = 150
        elif key in ["vis_cmds"]:
            max_new = 65280
        elif key in ["groups"]:
            max_new = 80
        elif key in ["areas", "coll_cmds", "users", "gsm_messages"]:
            max_new = 255
        elif key in ["counters", "logic", "fingers"]:
            max_new = 10
        elif key in ["gsm_numbers"]:
            max_new = 50
        tbl += indent(7) + "<tr><td>&nbsp;</td></tr>\n"
        tbl += (
            indent(7)
            + "<tr><td>&nbsp;</td><td></td><td>"
            + '<button name="ModSettings" class="new_button" id="config_button" type="submit" '
            + f'form="settings_table" value="del-{mod_addr}-{step}">entfernen</button></td></tr>\n'
        )
        tbl += (
            indent(7)
            + f'<tr><td><label for="{id_name}">{prompt}</label></td><td><input name="new_entry" '
            + f'type="number" class="desc_input1"  min="{min_new}" max="{max_new}" placeholder="Neue Nummer eintragen" id="{id_name}"/></td>\n'
        )
        if key == "counters":
            tbl += (
                indent(7)
                + '<td><button name="ModSettings" class="new_cntr_button" id="config_button" '
                + f'type="button" value="new-{mod_addr}-{step}">anlegen</button>\n'
            )
        elif key == "logic":
            tbl += (
                indent(7)
                + '<td><button name="ModSettings" class="new_lgc_button" id="config_button" '
                + f'type="button" value="new-{mod_addr}-{step}">anlegen</button>\n'
            )
        else:
            tbl += (
                indent(7)
                + '<td><button name="ModSettings" class="new_button" id="config_button" type="submit" '
                + f'form="settings_table" value="new-{mod_addr}-{step}">anlegen</button>\n'
            )
        if key in ["fingers"]:
            tbl = tbl.replace(
                '<button name="ModSettings" class="new_button" id="config_button" type="submit" form="settings_table" value="new',
                '<button name="TeachNewFinger" class="new_button" id="config_button" type="button" form="settings_table" value="new',
            )
        tbl += indent(7) + "</tr>\n"
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def parse_response_form(main_app, form_data):
    """Parse configuration input form and store results in settings."""
    key = main_app["key"]
    settings = main_app["settings"]
    if form_data["ModSettings"][0].startswith("del-"):  # remove element
        idxs = [
            int(form_data[ky][0], base=10)
            for ky in form_data.keys()
            if ky.startswith("sel_")
        ]
        idxs.sort(reverse=True)
        for idx in idxs:
            del settings.__getattribute__(key)[idx]
            if key == "users":
                del settings.all_fingers[idx + 1]
        main_app["settings"] = settings
        return form_data["ModSettings"][0]
    for elem in settings.__getattribute__(key):
        if "name" in dir(elem):
            elem.name = ""  # clear names to get empty entries

    for form_key in list(form_data.keys())[:-1]:
        if form_key[:4] in ["area", "sel_"]:
            pass  # checked, but no delete command; area_sel handled later
        elif form_key == "new_entry":
            # add element
            if form_data["ModSettings"][0].startswith("next") or form_data[
                "ModSettings"
            ][0].startswith("back"):
                continue  # skip "new_entry" if step buttons pressed
            entry_found = False
            for elem in settings.__getattribute__(key):
                if elem.nmbr == int(form_data[form_key][0]):
                    entry_found = True
                    break
            if not entry_found:
                if key == "fingers":
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            FingerNames[int(form_data[form_key][0])],
                            int(form_data[form_key][0]),
                            settings.users[settings.users_sel].nmbr,
                        )
                    )
                elif key in ["counters"]:
                    max_cnt = int(form_data["ModSettings"][0].split("-")[-1])
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            f"Counter{max_cnt}_{int(form_data[form_key][0])}",
                            int(form_data[form_key][0]),
                            max_cnt,
                        )
                    )
                elif key in ["logic"]:
                    no_inpts = int(form_data["ModSettings"][0].split("-")[-1])
                    lgc_type = int(form_data["ModSettings"][0].split("-")[-2])
                    settings.__getattribute__(key).append(
                        LgcDescriptor(
                            f"{LGC_TYPES[lgc_type]}{no_inpts}_{int(form_data[form_key][0])}",
                            int(form_data[form_key][0]),
                            lgc_type,
                            no_inpts,
                        )
                    )
                elif key in ["messages", "gsm_messages", "gsm_numbers"]:
                    # only entries in language 1 (german) supported
                    language_code: int = 1
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            f"{key}_{int(form_data[form_key][0])}",
                            int(form_data[form_key][0]),
                            language_code,
                        )
                    )
                else:
                    if key == "users":
                        settings.all_fingers[int(form_data[form_key][0])] = []
                        if "users_sel" not in dir(settings):
                            settings.users_sel = 0
                    settings.__getattribute__(key).append(
                        IfDescriptor(
                            f"{key}_{int(form_data[form_key][0])}",
                            int(form_data[form_key][0]),
                            0,
                        )
                    )
        elif form_key == "users_sel":
            settings.users_sel = int(form_data[form_key][0])
        elif form_key == "users_enable":
            for usr in settings.users:
                if f"{usr.nmbr}" in form_data[form_key]:
                    usr.type = abs(usr.type)
                else:
                    usr.type = abs(usr.type) * (-1)
        else:
            indices = form_key.replace("data[", "").replace("]", "").split(",")
            indices[0] = int(indices[0])
            indices[1] = int(indices[1])
            if len(indices) == 1:
                settings.__getattribute__(key)[int(indices[0])].name = form_data[
                    form_key
                ][0]
            elif indices[1] == 0 and key not in ["day_sched", "night_sched"]:
                settings.__getattribute__(key)[int(indices[0])].name = form_data[
                    form_key
                ][0]
            if len(indices) > 1:
                match main_app["key"]:
                    case "inputs":
                        if form_data[form_key][0] == "btn":
                            settings.inputs[indices[0]].type = 1
                        elif form_data[form_key][0] == "sw":
                            settings.inputs[indices[0]].type = 2
                        elif form_data[form_key][0] == "anlg":
                            settings.inputs[indices[0]].type = 3
                        settings.inputs[indices[0]].area = int(
                            form_data["area_sel"][indices[0]]
                        )
                    case "outputs":
                        o_idx = indices[0]
                        c_idx = settings.out_2_cvr(o_idx)
                        if form_data[form_key][0] == "cvr":
                            settings.outputs[o_idx].type = -10
                            settings.outputs[o_idx + 1].type = -10
                            outp_name = settings.outputs[o_idx].name
                            cvr_name = set_cover_name(outp_name)
                            if settings.covers[c_idx].type == 0:
                                # needs new setting (polarity, blades)
                                settings.covers[c_idx].type = 1
                                settings.covers[c_idx].name = cvr_name
                            elif len(settings.covers[c_idx].name) == 0:
                                settings.covers[c_idx].name = cvr_name
                            if settings.covers[c_idx].type > 0:
                                settings.outputs[o_idx].name = set_cover_output_name(
                                    outp_name, cvr_name, "up"
                                )
                                settings.outputs[
                                    o_idx + 1
                                ].name = set_cover_output_name(
                                    outp_name, cvr_name, "dwn"
                                )
                            else:
                                settings.outputs[o_idx].name = set_cover_output_name(
                                    outp_name, cvr_name, "dwn"
                                )
                                settings.outputs[
                                    o_idx + 1
                                ].name = set_cover_output_name(
                                    outp_name, cvr_name, "up"
                                )
                        elif form_data[form_key][0] == "out":
                            settings.outputs[o_idx].type = 1
                            settings.outputs[o_idx + 1].type = 1
                            settings.covers[c_idx].type = 0
                            settings.covers[c_idx].name = ""
                        settings.outputs[indices[0]].area = int(
                            form_data["area_sel"][indices[0]]
                        )
                    case "covers":
                        c_idx = indices[0]
                        o_idx = settings.cvr_2_out(c_idx)
                        if indices[1] == 0:
                            # names
                            cover_name = form_data[form_key][0]
                            pol_key = f"data[{c_idx},3]"
                            if pol_key in form_data.keys():
                                pol = form_data[pol_key][0]
                            else:
                                pol = "pol_inv"
                            settings.covers[c_idx].name = cover_name
                            outp_name = settings.outputs[o_idx].name
                            if pol == "pol_nrm":
                                settings.outputs[o_idx].name = set_cover_output_name(
                                    outp_name, cover_name, "up"
                                )
                                settings.outputs[
                                    o_idx + 1
                                ].name = set_cover_output_name(
                                    outp_name, cover_name, "dwn"
                                )
                            else:
                                settings.outputs[o_idx].name = set_cover_output_name(
                                    outp_name, cover_name, "dwn"
                                )
                                settings.outputs[
                                    o_idx + 1
                                ].name = set_cover_output_name(
                                    outp_name, cover_name, "up"
                                )
                                # unchecked 'normal polarity' => no entry in form, so set pol here
                                settings.covers[c_idx].type = abs(
                                    settings.covers[c_idx].type
                                ) * (-1)
                        elif indices[1] == 1:
                            settings.cover_times[c_idx] = int(form_data[form_key][0])
                        elif indices[1] == 2:
                            settings.blade_times[c_idx] = float(form_data[form_key][0])
                            if float(form_data[form_key][0]) > 0:
                                settings.covers[c_idx].type = int(
                                    copysign(2, settings.covers[c_idx].type)  # type: ignore
                                )
                        elif indices[1] == 3:
                            # checked 'normal polarity' => entry in form, so set pol here
                            if form_data[form_key][0] == "pol_nrm":
                                settings.covers[c_idx].type = abs(
                                    settings.covers[c_idx].type
                                )
                            else:
                                settings.covers[c_idx].type = abs(
                                    settings.covers[c_idx].type
                                ) * (-1)
                    case "leds" | "buttons" | "dir_cmds" | "messages":
                        if indices[1] == 0:
                            # use only first part for parsing and look for second
                            if f"data[{indices[0]},1]" in form_data.keys():
                                name = form_data[form_key][0]
                                name += " " * (18 - len(name))
                                name += form_data[f"data[{indices[0]},1]"][0]
                                name += " " * (32 - len(name))
                            else:
                                name = form_data[form_key][0]
                                name += " " * (32 - len(name))
                            settings.__getattribute__(key)[indices[0]].name = name
                    case "groups":
                        if (indices[0] > 0) and (indices[1] == 1):
                            if indices[0] == 1:
                                # Empty dependencies
                                settings.mode_dependencies = b"P" + b"\0" * 80
                            grp_nmbr = settings.__getattribute__(key)[
                                int(indices[0])
                            ].nmbr
                            settings.mode_dependencies = (
                                settings.mode_dependencies[:grp_nmbr]
                                + int.to_bytes(int(form_data[form_key][0]))
                                + settings.mode_dependencies[grp_nmbr + 1 :]
                            )
                    case "gsm_numbers" | "gsm_messages":
                        settings.__getattribute__(key)[indices[0]].name = form_data[
                            form_key
                        ][0]
                    case "day_sched" | "night_sched":
                        if indices[1] == 3:
                            for day in settings.__getattribute__(key):
                                day["module"] = int(form_data[form_key][0])
                        elif indices[1] == 2:
                            settings.__getattribute__(key)[indices[0]]["mode"] = int(
                                form_data[form_key][0]
                            )
                        elif indices[1] == 1:
                            settings.__getattribute__(key)[indices[0]]["light"] = int(
                                int(form_data[form_key][0]) / 10
                            )
                        else:
                            time = form_data[form_key][0].split(":")
                            settings.__getattribute__(key)[indices[0]]["hour"] = int(
                                time[0]
                            )
                            settings.__getattribute__(key)[indices[0]]["minute"] = int(
                                time[1]
                            )

    if key == "fingers":
        settings.all_fingers[settings.users[settings.users_sel].nmbr] = settings.fingers
        if "TeachNewFinger" in list(form_data.keys()):
            form_data["ModSettings"] = form_data["TeachNewFinger"]
    if key in ["day_sched", "night_sched"]:
        settings.set_day_night()
    main_app["settings"] = settings
    return form_data["ModSettings"][0]


def get_property_kind(main_app, step) -> tuple[str, str, str]:
    """Return header of property kind."""
    if step == 0:
        return "", "Grundeinstellungen", ""
    cnt = 0
    props = main_app["props"]
    io_keys = main_app["io_keys"]
    settings = main_app["settings"]
    for key in io_keys:
        if props[key] > 0:
            cnt += 1
        if cnt == step:
            break
    match key:
        case "buttons":
            header = "Einstellungen Tasterbeschriftung"
            prompt = "Taste"
        case "leds":
            header = "Einstellungen LED-Beschriftung"
            prompt = "LED"
        case "inputs":
            header = "Einstellungen Eingänge"
            prompt = "Eingang"
        case "outputs":
            header = "Einstellungen Ausgänge"
            prompt = "Ausgang"
        case "covers":
            header = "Einstellungen Rollladen"
            prompt = "Rollladen"
        case "counters":
            header = "Einstellungen Zähler"
            prompt = "Zähler"
        case "logic":
            header = "Einstellungen Logikfunktionen"
            prompt = "Logik"
        case "users":
            header = "Benutzerverwaltung"
            prompt = "Benutzer"
            if len(settings.users) == 0:
                # disable fingers
                props["no_keys"] = 1
            else:
                # enable fingers
                props["no_keys"] = 2
        case "fingers":
            user_id = settings.users[settings.users_sel].name
            header = f"Fingerabdrücke von '{user_id}'"
            prompt = "Finger"
            if settings.users[settings.users_sel].nmbr in settings.all_fingers.keys():
                settings.fingers = settings.all_fingers[
                    settings.users[settings.users_sel].nmbr
                ]
            else:
                settings.fingers = []
            main_app["settings"] = settings
        case "flags":
            header = "Einstellungen Lokale Merker"
            prompt = "Merker"
        case "dir_cmds":
            header = "Einstellungen Direktbefehle"
            prompt = "Direktbefehl"
        case "vis_cmds":
            header = "Einstellungen Visualisierungsbefehle"
            prompt = "Visualisierungsbefehl"
        case "glob_flags":
            header = "Einstellungen Globale Merker"
            prompt = "Merker"
        case "coll_cmds":
            header = "Einstellungen Sammelbefehle"
            prompt = "Sammelbefehl"
        case "day_sched":
            header = "Einstellungen Tagumschaltung"
            prompt = "Tag"
        case "messages":
            header = "Einstellungen Meldungen"
            prompt = "Meldung"
        case "gsm_messages":
            header = "Einstellungen SMS-Meldungen"
            prompt = "Meldung"
        case "gsm_numbers":
            header = "Einstellungen Mobilfunkrufnummern"
            prompt = "Nummer"
        case "night_sched":
            header = "Einstellungen Nachtumschaltung"
            prompt = "Nacht"
        case "areas":
            header = "Einstellungen Bereiche (Räume, etc.)"
            prompt = "Bereich"
        case "groups":
            header = "Einstellungen Gruppen"
            prompt = "Gruppe"
    return key, header, prompt


async def show_ekey_logs(main_app, mod_addr) -> web.Response:
    """Upload and show ekey logging protocol."""

    module = main_app["module"]
    with open(
        WEB_FILES_DIR + AUTOMATIONS_TEMPLATE_FILE, mode="r", encoding="utf-8"
    ) as tplf_id:
        page = tplf_id.read()
    mod_image, mod_type = get_module_image(module._typ)
    page = (
        page.replace("ContentTitle", f"Modul '{module._name}'")
        .replace("ContentSubtitle", "Protokoll der Ereignisse")
        .replace("ContentSubtext", "")
        .replace("controller.jpg", mod_image)
        .replace('form="automations_table"', 'form="log_table"')
        .replace(
            'value="cancel-ModAddress">Abbruch<', 'value="cancel-ModAddress">Beenden<'
        )
        .replace(">Neu<", ">Protokoll sichern<")
        .replace("ModAddress", f"{mod_addr}")
        .replace('value="new"', f'value="save-{mod_addr}"')
        .replace('class="config_button"', 'class="protoc_button"')
        .replace(">Löschen<", ">Protokoll löschen<")
        .replace(
            "Löschen der ausgewählten Automatisierung",
            "Löschen des Zugangsprotokolls im Smart Key",
        )
    )
    page = hide_button("zurück", page)
    page = hide_button("weiter", page)
    page = hide_button("Speichern", page)
    page = hide_button("Ändern", page)
    settings_form = await prepare_log_list(main_app)
    # page = disable_chg_del_button(main_app, step, page)
    page = page.replace("<p>ContentText</p>", settings_form)
    return web.Response(text=page, content_type="text/html")


async def prepare_log_list(main_app):
    ekey_protocol: list[dict[str, str]] = []
    module = main_app["module"]
    settings = module.get_module_settings()
    await main_app["api_srv"].set_server_mode()
    await main_app["api_srv"].block_network_if(module.rt_id, True)
    try:
        log_list = await module.hdlr.ekey_log_read()
        ll_len = int.from_bytes(log_list[1:3], "little") >> 3  # 8 bytes per entry
        main_app.logger.info(f"Ekey log list read successfully: {ll_len} lines")
        for line_idx in range(ll_len):
            entry: dict[str, str] = {}
            log_line = log_list[line_idx * 8 + 3 : line_idx * 8 + 3 + 8]
            main_app.logger.debug(f"Log line {line_idx + 1}: {log_line}")
            if len(log_line) == 8:
                user = settings.get_interf_name(
                    settings.users, log_line[2], "Unbekannt"
                )
                finger = log_line[3]
                if finger in range(128, 139):
                    finger -= 128
                    user = "Nicht freigeben: " + user

                time_stamp = int.from_bytes(log_line[4:], "little")
                entry["no"] = f"{line_idx + 1}"
                if time_stamp:
                    dt = convert_to_daytime(log_line)
                    entry["date"] = dt.strftime("%d. %m. %Y")
                    entry["time"] = dt.strftime("%H:%M:%S")
                else:
                    entry["date"] = "-"
                    entry["time"] = "-"
                entry["user"] = user
                if finger in FingerNames:
                    entry["finger"] = FingerNames[finger]
                else:
                    entry["finger"] = f"unknown {finger}"
                ekey_protocol.append(entry)
        main_app["ekey_log"] = ekey_protocol
    except Exception as err_msg:
        main_app.logger.error(f"Error loading ekey log: {err_msg}")
    await main_app["api_srv"].block_network_if(module.rt_id, False)
    return prepare_log_table(ekey_protocol)


def convert_to_daytime(log_line) -> datetime:
    """Convert special timestamp format."""
    if log_line[6] & 0x01 == 1:
        sd = 65536 + (log_line[5] * 256) + log_line[4]
    else:
        sd = log_line[5] * 256 + log_line[4]
    hr = int(sd / 3600)
    me = int((sd - (hr * 3600)) / 60)
    sd = int(sd - (hr * 3600) - (me * 60))

    dy = int((log_line[6] & 62) / 2)
    mh = int((log_line[7] * 256 + log_line[6] & 960) / 64)
    yr = int((log_line[7] * 256 + log_line[6] & 64512) / 1024) + 2000

    return datetime(yr, mh, dy, hr, me, sd)


def prepare_log_table(log_list) -> str:
    """Return html table."""

    tbl = indent(4) + '<form id="log_table" action="settings/ekey_log_table">\n'
    tbl += indent(5) + '<table id="atm-table">\n'
    tbl += indent(6) + "<thead>\n"
    tbl += (
        indent(6)
        + '<tr id="atm-th"><th data-sort-method="number">Nr.</th><th data-sort-method="none"><b>Datum</b></th><th data-sort-method="none"><b>Uhrzeit</b></th><th><b>Benutzer</b></th><th>Finger</th></tr>\n'
    )
    tbl += indent(6) + "</thead>\n"
    tbl += indent(6) + "<tbody>\n"
    for entry in log_list:
        tbl += indent(6) + '<tr id="atm-tr">\n'
        tbl += indent(7) + f'<td>{entry["no"]}</td>\n'
        tbl += indent(7) + f'<td>{entry["date"]}</td>\n'
        tbl += indent(7) + f'<td>{entry["time"]}</td>\n'
        tbl += indent(7) + f'<td>{entry["user"]}</td>\n'
        tbl += indent(7) + f'<td>{entry["finger"]}</td>\n'
        tbl += indent(6) + "</tr>\n"
    tbl += indent(6) + "</tbody>\n"
    tbl += indent(5) + "</table>\n"
    tbl += indent(4) + "</form>\n"
    return tbl


def log_download(main_app):
    """Download ekey logging protocol."""
    date = datetime.now().strftime("%Y-%m-%d")
    file_name = f"ekey_protocol_{date}.csv"
    str_data = ""
    ekey_protocol = main_app["ekey_log"]
    for entry in ekey_protocol:
        str_data += f'{entry["no"]},{entry["date"]},{entry["time"]},{entry["user"]},{entry["finger"]}\n'
    return web.Response(
        headers=MultiDict(
            {"Content-Disposition": f"Attachment; filename = {file_name}"}
        ),
        body=str_data,
    )
