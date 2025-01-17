from aiohttp import web

# import ssl
from urllib.parse import parse_qs
from multidict import MultiDict
import yaml
from config_settings import (
    ConfigSettingsServer,
    show_router_overview,
    show_module_overview,
)
import json
from config_automations import ConfigAutomationsServer
from config_setup import ConfigSetupServer
from config_testing import ConfigTestingServer
from config_commons import (
    adjust_settings_button,
    fill_page_template,
    format_hmd,
    get_html,
    get_module_image,
    init_side_menu,
    show_documentation_page,
    show_homepage,
    show_exitpage,
    show_modules,
    show_update_router,
    show_update_modules,
    show_hub_overview,
    client_not_authorized,
    show_not_authorized,
    inspect_header,
)
from config_export import create_documentation
from licenses import get_package_licenses, show_license_text
from messages import calc_crc
from module import HbtnModule
from module_hdlr import ModHdlr
import asyncio
import logging
import pathlib
from const import (
    LOGGING_DEF_FILE,
    MODULE_CODES,
    LICENSE_PAGE,
    OWN_INGRESS_IP,
    CONF_PORT,
    INGRESS_PORT,
    WEB_FILES_DIR,
    MirrIdx,
    MOD_CHANGED,
)

routes = web.RouteTableDef()
root_path = pathlib.Path(__file__).parent
routes.static("/configurator_files", "./web/configurator_files")


class HubSettings:
    """Object with all module settings and changes."""

    def __init__(self, hub):
        """Fill all properties with module's values."""
        self.name = hub._name
        self.typ = hub._typ


class ConfigServer:
    """Web server for basic configuration tasks."""

    def __init__(self, api_srv):
        self.api_srv = api_srv
        if api_srv.is_addon:
            self._ip = OWN_INGRESS_IP  # api_srv.sm_hub._host_ip
            self._port = INGRESS_PORT
        else:
            self._ip = api_srv.sm_hub._host_ip
            self._port = CONF_PORT
        self.conf_running = False
        self.is_install = False  # Install mode default off

    async def initialize(self):
        """Initialize config server."""

        @web.middleware
        async def ingress_middleware(request: web.Request, handler) -> web.Response:
            response = await handler(request)
            if (
                request.app["api_srv"].is_addon
                and request.headers["Accept"].find("text/html") >= 0
                and "body" in response.__dir__()
                and response.status == 200
            ):
                ingress_path = request.headers["X-Ingress-Path"]
                request.app.logger.debug(f"Request path: {request.path_qs}")
                request.app.logger.debug(
                    f"Response status: {response.status} , Body type: {type(response.body)}"
                )
                if isinstance(response.body, bytes):
                    response.body = (
                        response.body.decode("utf_8")
                        .replace(
                            '<base href="/">',
                            f'<base href="{ingress_path}/">',
                        )
                        .encode("utf_8")
                    )
            return response

        @web.middleware
        async def release_network_block(request: web.Request, handler) -> web.Response:
            """Release network block after next action if previous action enabled it."""
            api_srv = request.app["api_srv"]
            rt_no = api_srv.routers[0]._id
            if api_srv.release_block_next:
                api_srv.block_network_if(rt_no, False)
                api_srv.release_block_next = False
            response = await handler(request)
            return response

        self.app = web.Application(
            middlewares=[ingress_middleware, release_network_block]
        )
        self.app.logger = logging.getLogger(__name__)
        self.settings_srv = ConfigSettingsServer(self.app, self.api_srv)
        self.app.add_subapp("/settings", self.settings_srv.app)
        self.automations_srv = ConfigAutomationsServer(self.app, self.api_srv)
        self.app.add_subapp("/automations", self.automations_srv.app)
        self.setup_srv = ConfigSetupServer(self.app, self.api_srv)
        self.app.add_subapp("/setup", self.setup_srv.app)
        self.testing_srv = ConfigTestingServer(self.app, self.api_srv)
        self.app.add_subapp("/test", self.testing_srv.app)
        self.app.add_routes(routes)
        # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # ssl_context.load_cert_chain("domain_srv.crt", "domain_srv.key")
        self.runner = web.AppRunner(self.app)  # , ssl_context=ssl_context)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self._ip, self._port)
        # self.site = web.TCPSite(
        #     self.runner, self._ip, self._port, ssl_context=ssl_context
        # )

    async def prepare(self):
        """Second initialization after api_srv is initialized."""
        self.app["api_srv"] = self.api_srv
        self.app["is_offline"] = self.api_srv.is_offline
        self.app["is_install"] = False
        init_side_menu(self.app)

    @routes.get("/")
    async def get_root(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        return show_homepage(request.app)

    @routes.get("/licenses")
    async def get_licenses(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        return show_license_table(request.app)

    @routes.get("/exit")
    async def get_exit(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        api_srv = request.app["api_srv"]
        if api_srv._in_shutdown:
            api_srv.sm_hub.tg.create_task(terminate_delayed(api_srv))
        return show_exitpage(request.app)

    @routes.get("/router")
    async def get_router(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return await show_router_overview(request.app)

    @routes.get("/hub")
    async def get_hub(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return show_hub_overview(request.app)

    @routes.get("/modules")
    async def get_modules(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        return show_modules(request.app)

    @routes.get("/module-{mod_addr}")
    async def get_module_addr(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        mod_addr = int(request.match_info["mod_addr"])
        return show_module_overview(request.app, mod_addr)

    @routes.get("/log_file")
    async def download_logs(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)

        with open(f"./{LOGGING_DEF_FILE}", "r") as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
        file_name = config["handlers"]["file"]["filename"]
        request.app.logger.debug(f"Open log file '{file_name}'...")
        with open(file_name) as fid:
            str_data = fid.read()
        return web.Response(
            headers=MultiDict(
                {
                    "Content-Disposition": f"Attachment; filename = {file_name.split('/')[-1]}"
                }
            ),
            body=str_data,
        )

    @routes.get("/sysdoc")
    async def get_documentation(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        file_name = request.query["file"]
        file_name = file_name.split(".")[0] + ".html"
        api_srv = request.app["api_srv"]
        rtr = api_srv.routers[0]
        page = create_documentation(rtr, file_name)
        return web.Response(
            headers=MultiDict(
                {"Content-Disposition": f"Attachment; filename = {file_name}"}
            ),
            body=page,
        )

    @routes.get("/download")
    async def get_download(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        file_name = request.query["file"]
        file_name = file_name.split(".")[0]
        rtr = request.app["api_srv"].routers[0]
        separator = "---\n"
        if "SysDownload" in request.query.keys():
            # System backup
            file_name += ".hcf"
            settings = rtr.get_router_settings()
            file_content = settings.smr
            str_data = ""
            for byt in file_content:
                str_data += f"{byt};"
            str_data += "\n"
            str_data += rtr.pack_descriptions()
            str_data += separator
            for mod in rtr.modules:
                settings = mod.get_module_settings()
                str_data += format_hmd(settings.smg, settings.list)
                str_data += separator
        else:
            # Module download
            addr_str = request.query["ModDownload"]
            if addr_str == "ModAddress":
                mod_addr = 0
            else:
                mod_addr = int(addr_str)
            if mod_addr > 0:
                # module
                settings = rtr.get_module(mod_addr).get_module_settings()
                file_name += ".hmd"
                str_data = format_hmd(settings.smg, settings.list)
            else:
                # router
                file_content = rtr.smr
                file_name += ".hrt"
                str_data = ""
                for byt in file_content:
                    str_data += f"{byt};"
                str_data += "\n"
                str_data += rtr.pack_descriptions()
        return web.Response(
            headers=MultiDict(
                {"Content-Disposition": f"Attachment; filename = {file_name}"}
            ),
            body=str_data,
        )

    @routes.post("/upload")
    async def get_upload(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        data = await request.post()
        config_file = data["file"].file  # type: ignore
        content = config_file.read()
        content_str = content.decode()
        if "SysUpload" in data.keys():
            content_parts = content_str.split("---\n")
            if content_parts[-1] == "":
                content_parts = content_parts[:-1]
            app.logger.info("Router configuration file uploaded")
            await send_to_router(app, content_parts[0])
            for mod_addr in app["api_srv"].routers[0].mod_addrs:
                for cont_part in content_parts[1:]:
                    if mod_addr == int(cont_part.split(";")[0]):
                        break
                await send_to_module(app, cont_part, mod_addr)
                app.logger.info(
                    f"Module configuration file for module {mod_addr} uploaded"
                )
            init_side_menu(app)
            return show_modules(app)
        elif data["ModUpload"] == "ModAddress":
            # router upload
            await send_to_router(app, content_str)
            init_side_menu(app)
            success_msg = "Router configuration file uploaded"
            app.logger.info(success_msg)  # noqa: F541
            return await show_router_overview(app, success_msg)  # type: ignore
        else:
            mod_addr = int(str(data["ModUpload"]))
            if data["ModUpload"] == content_str.split(";")[0]:
                await send_to_module(app, content_str, mod_addr)
                success_msg = (
                    f"Module configuration file for module {mod_addr} uploaded"
                )
                app.logger.info(success_msg)
            else:
                success_msg = f"Module configuration file does not fit to module number {mod_addr}, upload aborted"
                app.logger.warning(success_msg)
            init_side_menu(app)
            return show_module_overview(
                app, mod_addr, success_msg
            )  # web.HTTPNoContent()

    @routes.post("/loc_update")
    async def post_loc_update(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        data = await request.post()
        if "mod_type_select" in data.keys():
            module = rtr.get_module(int(data["mod_type_select"]))
            with open(module.update_fw_file, "rb") as fid:
                rtr.fw_upload = fid.read()
            mod_type = module._typ
            mod_type_str = module._type
            fw_vers = rtr.fw_upload[-27:-5].decode().strip()
            app.logger.info(
                f"Firmware file v. {fw_vers} for '{MODULE_CODES[mod_type.decode()]}' modules uploaded"
            )
            mod_list = rtr.get_module_list()
            upd_list = []
            for mod in mod_list:
                if mod.typ == mod_type:
                    upd_list.append(mod)
            return show_update_modules(upd_list, fw_vers, mod_type_str)
        else:
            with open(rtr.update_fw_file, "rb") as fid:
                rtr.fw_upload = fid.read()
            fw_vers = rtr.fw_upload[-27:-5]
            app.logger.info(f"Firmware file for router {rtr._name} uploaded")
            return show_update_router(rtr, fw_vers)

    @routes.post("/upd_upload")
    async def get_upd_upload(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        data = await request.post()
        fw_filename = data["file"].filename  # type: ignore
        rtr.fw_upload = data["file"].file.read()  # type: ignore
        upd_type = str(data["SysUpload"])
        if upd_type == "rtr":
            fw_vers = rtr.fw_upload[-27:-5].decode()
            app.logger.info(f"Firmware file for router {rtr._name} uploaded")
            return show_update_router(rtr, fw_vers)
        elif upd_type == "mod":
            mod_type = rtr.fw_upload[:2]
            if mod_type == b"\x01\x02" and fw_filename[:8] == "scrmgv46":
                mod_type = b"\x01\x03"
            mod_type_str = MODULE_CODES[mod_type.decode()]
            fw_vers = rtr.fw_upload[-27:-5].decode().strip()
            app.logger.info(
                f"Firmware file v. {fw_vers} for '{MODULE_CODES[mod_type.decode()]}' modules uploaded"
            )
            mod_list = rtr.get_module_list()
            upd_list = []
            for mod in mod_list:
                if mod.typ == mod_type:
                    upd_list.append(mod)
            return show_update_modules(upd_list, fw_vers, mod_type_str)
        else:
            mod_type = rtr.fw_upload[:2]
            mod_type_str = MODULE_CODES[mod_type.decode()]
            fw_vers = rtr.fw_upload[-27:-5].decode().strip()
            mod_addr = int(upd_type)
            module = rtr.get_module(mod_addr)
            if module is None:
                app.logger.error(f"Could not find module {mod_addr}")
                return show_hub_overview(app)
            elif module._typ == mod_type:
                app.logger.info(f"Firmware file for module {module._name} uploaded")
                return show_update_modules([module], fw_vers, mod_type_str)
            else:
                app.logger.error(
                    f"Firmware file for {MODULE_CODES[mod_type.decode()]} uploaded, not compatible with module {module._name}"
                )
                return show_hub_overview(app)

    @routes.post("/update_router")
    async def get_update_router(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        resp = await request.text()
        form_data = parse_qs(resp)
        if form_data["UpdButton"][0] == "cancel":
            return show_hub_overview(app)
        rtr.hdlr.upd_stat_dict = {"modules": [0], "upload": 100}
        rtr.hdlr.upd_stat_dict["mod_0"] = {
            "progress": 0,
            "errors": 0,
            "success": "OK",
        }
        if api_srv.sm_hub.flash_only:
            await rtr.hdlr.upload_router_firmware(
                None, rtr.hdlr.stat_rtr_fw_update_protocol
            )
        else:
            await api_srv.block_network_if(rtr._id, True)
            await rtr.hdlr.upload_router_firmware(
                None, rtr.hdlr.stat_rtr_fw_update_protocol
            )
            await api_srv.block_network_if(rtr._id, False)
        return show_hub_overview(app)

    @routes.post("/update_modules")
    async def get_update_modules(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        if client_not_authorized(request):
            return show_not_authorized(request.app)
        app = request.app
        api_srv = app["api_srv"]
        rtr = api_srv.routers[0]
        resp = await request.text()
        form_data = parse_qs(resp)
        if form_data["UpdButton"][0] == "cancel":
            return show_hub_overview(app)
        if len(form_data.keys()) == 1:
            # nothing selected
            return show_hub_overview(app)

        mod_type = rtr.fw_upload[:2]
        mod_list = []
        for checked in list(form_data.keys())[:-1]:
            mod_list.append(int(form_data[checked][0]))
        rtr.hdlr.upd_stat_dict = {"modules": mod_list, "upload": 0}
        for md in mod_list:
            rtr.hdlr.upd_stat_dict[f"mod_{md}"] = {
                "progress": 0,
                "errors": 0,
                "success": "OK",
            }
        app.logger.info(f"Update of Modules {mod_list}")
        await api_srv.block_network_if(rtr._id, True)
        if await rtr.hdlr.upload_module_firmware(
            mod_type, rtr.hdlr.stat_mod_fw_upload_protocol
        ):
            app.logger.info("Firmware uploaded to router successfully")
            await rtr.hdlr.flash_module_firmware(
                mod_list, rtr.hdlr.stat_mod_fw_update_protocol
            )
            for mod in mod_list:
                await rtr.get_module(mod).initialize()
        else:
            app.logger.info("Firmware upload to router failed, update terminated")
        await api_srv.block_network_if(rtr._id, False)
        return show_hub_overview(app)

    @routes.get("/update_status")
    async def get_update_status(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        app = request.app
        stat = app["api_srv"].routers[0].hdlr.upd_stat_dict
        return web.Response(
            text=json.dumps(stat), content_type="text/plain", charset="utf-8"
        )

    @routes.get(path="/Documentation")
    async def show_doccenter(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        app = request.app
        return show_documentation_page(app)

    @routes.get(path="/Smart Center Introduction")
    async def show_doc(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)

        page = (
            get_html("smartcenterintro_doc.html", "windows-1252")
            .replace("smartcenterintro_doc-Dateien", "smartcenterintro_doc_files")
            .replace('"text/html; charset=windows-1252"', '"text/html; charset=utf-8"')
        )
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get(path="/Smart Configurator Documentation")
    async def show_doc(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)

        page = (
            get_html("configurator_doc.html", "windows-1252")
            .replace("configurator_doc-Dateien", "configurator_doc_files")
            .replace('"text/html; charset=windows-1252"', '"text/html; charset=utf-8"')
        )
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get(path="/Grundbegriffe Home Assistant")
    async def show_hadoc(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        page = (
            get_html("habasics_doc.html", "windows-1252")
            .replace("habasics_doc-Dateien", "habasics_doc_files")
            .replace('"text/html; charset=windows-1252"', '"text/html; charset=utf-8"')
        )
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get(path="/Setup Guide")
    async def show_setup_doc(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)

        page = (
            get_html("setup_doc.html", "windows-1252")
            .replace("setup_doc-Dateien", "setup_doc_files")
            .replace('"text/html; charset=windows-1252"', '"text/html; charset=utf-8"')
        )
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    @routes.get(path="/{key:.*}.txt")
    async def get_license_text(request: web.Request) -> web.Response:  # type: ignore
        inspect_header(request)
        return show_license_text(request)


@routes.get(path="/smartcenterintro_doc_files/{key:.*}")
async def load_doc_pic(request):
    with open(WEB_FILES_DIR + request.path[1:], "rb") as img_file:
        img_content = img_file.read()
    return web.Response(body=img_content)


@routes.get(path="/configurator_doc_files/{key:.*}")
async def load_sconfdoc_pic(request):
    with open(WEB_FILES_DIR + request.path[1:], "rb") as img_file:
        img_content = img_file.read()
    return web.Response(body=img_content)


@routes.get(path="/setup_doc_files/{key:.*}")
async def load_setup_pic(request):
    with open(WEB_FILES_DIR + request.path[1:], "rb") as img_file:
        img_content = img_file.read()
    return web.Response(body=img_content)


@routes.get(path="/favicon.ico")
async def do_nothing(request: web.Request) -> web.Response:
    inspect_header(request)
    return web.HTTPNoContent()


@routes.get(path="/{key:.*}")
async def _(request):
    inspect_header(request)
    app = request.app
    warning_txt = f"Route '{request.path}' not yet implemented"
    app.logger.warning(warning_txt)
    mod_image, type_desc = get_module_image(app["module"]._typ)
    page = fill_page_template(
        f"Modul '{app['module']._name}'",
        type_desc,
        "",
        warning_txt,
        app["side_menu"],
        mod_image,
        "",
    )
    page = adjust_settings_button(page, "", f"{0}")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


@routes.post(path="/{key:.*}")
async def _(request):
    inspect_header(request)
    app = request.app
    warning_txt = f"Route '{request.path}' not yet implemented"
    app.logger.warning(warning_txt)
    mod_image, type_desc = get_module_image(app["settings"]._typ)
    page = fill_page_template(
        f"Modul '{app['settings'].name}'",
        type_desc,
        "",
        warning_txt,
        app["side_menu"],
        mod_image,
        "",
    )
    page = adjust_settings_button(page, "", f"{0}")
    return web.Response(text=page, content_type="text/html", charset="utf-8")


def seperate_upload(upload_str: str) -> tuple[bytes, bytes]:
    """Seperate smg and list from data, remove ';' and lf, correct counts, and convert to bytes"""
    lines = upload_str.split("\n")
    l_l = len(lines)
    for l_i in range(l_l):
        # count backwards to keep line count after deletion
        l_bi = l_l - l_i - 1  # runs from l_l-1 .. 0
        if lines[l_bi].strip() == "":
            del lines[l_bi]
        else:
            lines[l_bi] = lines[l_bi].replace(";\r", ";")
    smg_bytes = b""
    for byt in lines[0].split(";"):
        if len(byt) > 0:
            smg_bytes += int.to_bytes(int(byt))
    no_list_lines = len(lines) - 2
    no_list_chars = 0
    smc_bytes = b""
    for line in lines[1:]:
        for byt in line.split(";"):
            if len(byt) > 0:
                smc_bytes += int.to_bytes(int(byt))
                no_list_chars += 1
    if len(lines) > 1:
        smc_bytes = (
            chr(no_list_lines & 0xFF)
            + chr(no_list_lines >> 8)
            + chr(no_list_chars & 0xFF)
            + chr(no_list_chars >> 8)
        ).encode("iso8859-1") + smc_bytes[4:]
    return smg_bytes, smc_bytes


async def send_to_router(app, content: str):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        lines = content.split("\n")
        buf = b""
        for byt in lines[0].split(";")[:-1]:
            buf += int.to_bytes(int(byt))
        rtr.smr_upload = buf
        rtr.hdlr.set_rt_full_status()
        if not app["api_srv"].is_offline:
            await rtr.hdlr.send_rt_full_status()
        rtr.smr_upload = b""
        desc_lines = lines[1:]
        if len(desc_lines) > 0:
            rtr.get_glob_descriptions(rtr.unpack_descriptions(desc_lines))
            await rtr.store_descriptions()
    except Exception as err_msg:
        app.logger.error(f"Error while uploading router settings: {err_msg}")
    await rtr.api_srv.block_network_if(rtr._id, False)


async def send_to_module(app, content: str, mod_addr: int):
    """Send uploads to module."""
    rtr = app["api_srv"].routers[0]
    module = rtr.get_module(mod_addr)
    if module is None:
        rtr.modules.append(
            HbtnModule(
                mod_addr,
                rtr.get_channel(mod_addr),
                rtr._id,
                ModHdlr(mod_addr, rtr.api_srv),
                rtr.api_srv,
            )
        )
        module = rtr.modules[-1]
        module.changed = MOD_CHANGED.NEW
    if app["api_srv"].is_offline or module.changed & MOD_CHANGED.NEW:
        module.smg_upload, module.list = seperate_upload(content)
        module.calc_SMG_crc(module.smg_upload)
        module.calc_SMC_crc(module.list)
        module._name = module.smg_upload[52 : 52 + 32].decode("iso8859-1").strip()
        module._typ = module.smg_upload[1:3]
        module._type = MODULE_CODES[module._typ.decode("iso8859-1")]
        module.status = b"\0" * MirrIdx.END
        module.build_status(module.smg_upload)
        module.io_properties, module.io_prop_keys = module.get_io_properties()
        return

    module.smg_upload, module.list_upload = seperate_upload(content)
    list_update = calc_crc(module.list_upload) != module.get_smc_crc()
    stat_update = module.different_smg_crcs()
    if list_update or stat_update:
        await rtr.api_srv.block_network_if(rtr._id, True)
    try:
        if list_update:
            await module.hdlr.send_module_list(mod_addr)
            module.list = await module.hdlr.get_module_list(
                mod_addr
            )  # module.list_upload
            module.calc_SMC_crc(module.list)
            app.logger.info("Module list upload from configuration server finished")
        else:
            app.logger.info(
                "Module list upload from configuration server skipped: Same CRC"
            )
        if stat_update:
            await module.hdlr.send_module_smg(module._id)
            await module.hdlr.get_module_status(module._id)
            app.logger.info("Module status upload from configuration server finished")
        else:
            app.logger.info(
                "Module status upload from configuration server skipped: Same CRC"
            )
    except Exception as err_msg:
        app.logger.error(f"Error while uploading module settings: {err_msg}")
    if list_update or stat_update:
        await rtr.api_srv.block_network_if(rtr._id, False)
    module.smg_upload = b""
    module.list_upload = b""


async def terminate_delayed(api_srv):
    """suspend for a time limit in seconds"""
    await asyncio.sleep(2)
    # execute the other coroutine
    await api_srv.shutdown(1, False)


def show_license_table(app):
    """Return html page with license table."""
    page = get_html(LICENSE_PAGE)
    table_str = get_package_licenses()
    if app["is_offline"]:
        page = page.replace("Smart Hub", "Smart Configurator")
    elif app["api_srv"].is_addon:
        page = page.replace("Smart Hub", "Smart Center")
    page = page.replace("<table></table>", table_str)
    return web.Response(text=page, content_type="text/html", charset="utf-8")
