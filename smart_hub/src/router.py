import asyncio
from datetime import datetime
from glob import glob
from messages import calc_crc
from os.path import isfile
from config_commons import is_outdated
from const import (
    MOD_CHANGED,
    RT_STAT_CODES,
    DATA_FILES_DIR,
    DATA_FILES_ADDON_DIR,
    FW_FILES_DIR,
    MODULE_CODES,
    RT_CMDS,
    MirrIdx,
    IfDescriptor,
)
from router_hdlr import RtHdlr
from module import HbtnModule
from module_hdlr import ModHdlr
from configuration import RouterSettings


class HbtnRouter:
    """Router object, holds status."""

    def __init__(self, api_srv, id: int) -> None:
        self._ready = False
        self._id = id
        self._name = "Router"
        self._in_config_mode: bool = False
        self.recent_mode: int = 0x20
        self.api_srv = api_srv
        self.logger = api_srv.logger
        self.status = b""
        self.status_upload = b""
        self.chan_status = b""
        self.status_idx = []
        self.mod_addrs = []
        self.modules = []
        self.err_modules = []
        self.removed_modules = []
        self.hdlr = RtHdlr(self, self.api_srv)
        self.descriptions_file: str = ""
        self.descriptions: list[IfDescriptor] = []
        self.smr: bytes = b""
        self.smr_crc: int = 0
        self.smr_upload: bytes = b""
        self.fw_upload: bytes = b""
        self.name: bytes = b""
        self.channels: bytes = b""
        self.channel_list: dict[int, list[int]] = {}
        self.comm_errors = b"\x00\x00\x00"
        self.timeout: bytes = b"\x14"
        self.groups: bytes = b"\x50" + b"\0" * 80
        self.mode_dependencies: bytes = b"\0" * 80
        self.mode0 = 0
        self.cov_autostop_cnt = 1
        self.user_modes: bytes = b""
        self.serial: bytes = (chr(16) + "0010010824000010").encode("iso8859-1")
        self.day_night: bytes = (
            chr(70)
            + "\x08\x00\0\1\0\x08\x00\0\1\0\x08\x00\0\1\0\x08\x00\0\1\0\x08\x00\0\1\0\x08\x00\0\1\0\x00\x00\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0\x17\x1e\0\1\0"
        ).encode("iso8859-1")
        self.version: bytes = (chr(22) + "VM V3.5310 12/2023    ").encode("iso8859-1")
        self.date: bytes = b""
        self.settings: RouterSettings
        self.properties, self.prop_keys = self.get_properties()
        self.update_available = False
        self.update_version = ""

    def mirror_running(self) -> bool:
        """Return mirror status based on chan_status."""
        if len(self.chan_status) > 40:
            return self.chan_status[-1] == RT_STAT_CODES.MIRROR_ACTIVE
        return False

    def get_version(self) -> str:
        """Return firmware version"""
        return self.version[1:].decode("iso8859-1").strip()

    def check_firmware(self) -> None:
        """Check local update files and set flag."""
        if self.api_srv.is_offline or self.api_srv._pc_mode:
            self.update_available = False
            self.update_fw_file = ""
            self.update_version = ""
            return
        fw_files = FW_FILES_DIR + "*.rbin"
        file_found = False
        # uploaded_fw_file = (
        #     DATA_FILES_DIR + f"Firmware_{self._typ[0]:02d}_{self._typ[1]:02d}.bin"
        # )
        curr_fw = self.get_version()
        for fw_file in glob(fw_files):
            file_found = True
            with open(fw_file, "rb") as fid:
                fw_bytes = fid.read()
            new_fw = fw_bytes[-27:-5].decode().strip()
        if file_found and is_outdated(curr_fw, new_fw):
            self.update_available = True
            self.update_fw_file = fw_file
            self.update_version = new_fw
            self.logger.info(f"     Found new router firmware file: version {new_fw}")
        else:
            self.update_available = False
            self.update_fw_file = ""
            self.update_version = curr_fw

    async def update_firmware(self) -> None:
        """Use internal firmware file for update service."""
        with open(self.update_fw_file, "rb") as fid:
            fw_bytes = fid.read()
        self.fw_upload = fw_bytes
        new_fw = fw_bytes[-27:-5]

        await self.api_srv.block_network_if(self._id, True)
        await self.hdlr.upload_router_firmware(
            None, self.hdlr.log_rtr_fw_update_protocol
        )
        self.version: bytes = b"\x16" + new_fw
        await self.api_srv.block_network_if(self._id, False)

    async def get_full_status(self):
        """Load full router status."""
        await self.set_config_mode(True)
        self.status = await self.hdlr.get_rt_full_status()
        self.chan_status = await self.hdlr.get_rt_status()
        self.comm_errors = await self.hdlr.get_mod_errors()
        self.build_smr()
        self.check_firmware()
        self.logger.debug("Router status initialized")
        modules = await self.hdlr.get_rt_modules()
        return modules

    async def get_full_system_status(self):
        """Startup procedure: wait for router #1, get router info, start modules."""
        from module_hdlr import ModHdlr

        await self.hdlr.waitfor_rt_booted()
        modules = await self.get_full_status()
        await self.get_descriptions()
        self.get_router_settings()
        self.logger.info("   Router initialized")

        self.logger.info("Setting up modules...")
        for m_idx in range(modules[0]):
            self.mod_addrs.append(modules[m_idx + 1])
        self.mod_addrs.sort()
        mods_to_remove = []
        for mod_addr in self.mod_addrs:
            try:
                self.modules.append(
                    HbtnModule(
                        mod_addr,
                        self.get_channel(mod_addr),
                        self._id,
                        ModHdlr(mod_addr, self.api_srv),
                        self.api_srv,
                    )
                )
                self.logger.debug(f"   Module {mod_addr} instantiated")
                init_msg = await self.modules[-1].initialize()
                if init_msg == "":
                    self.logger.info(f"   Module {mod_addr} initialized")
                else:
                    self.logger.info(f"   Module {mod_addr} initialized: {init_msg}")
            except Exception as err_msg:
                self.logger.error(f"   Failed to setup module {mod_addr}: {err_msg}")
                self.err_modules.append(self.modules[-1])
                self.modules.remove(self.modules[-1])
                mods_to_remove.append(mod_addr)
                self.logger.warning(f"   Module {mod_addr} removed")
        await self.get_module_comm_status()
        for mod_addr in mods_to_remove:
            self.mod_addrs.remove(mod_addr)
        self.api_srv.sm_hub.start_datetime = datetime.now().strftime("%d.%m.%Y, %H:%M")

    async def get_status(self) -> bytes:
        """Return router channel status and mod errors."""
        await self.api_srv.set_server_mode(self._id)
        self.chan_status = await self.hdlr.get_rt_status()
        self.comm_errors = await self.hdlr.get_mod_errors()
        return self.chan_status

    async def get_module_boot_status(self):
        """Get module boot status properties."""
        await self.hdlr.get_module_boot_status()

    def get_module(self, mod_id: int) -> HbtnModule | None:
        """Return module object."""
        if mod_id not in self.mod_addrs:
            return None
        md_idx = self.mod_addrs.index(mod_id)
        if md_idx >= len(self.modules):
            return None
        return self.modules[md_idx]

    def get_modules(self) -> str:
        """Return id, type, and name of all modules."""
        mod_str = ""
        for mod in self.modules:
            mod_str += chr(mod._id) + mod._typ.decode("iso8859-1")
            mod_str += chr(len(mod._name)) + mod._name
        return mod_str

    def get_module_list(self) -> list:
        """Return id, type, and name of all modules in a list."""

        class Mdle:
            """Class for module defs."""

            def __init__(self, id: int, typ: bytes, name: str, fw: str):
                self.id: int = id
                self.typ: bytes = typ
                self.name: str = name
                self.fw: str = fw

        mod_list = []
        for mod in self.modules:
            mod_list.append(Mdle(mod._id, mod._typ, mod._name, mod.get_sw_version()))
        return mod_list

    def get_channel(self, mod_addr: int) -> int:
        """Return router channel of module."""
        for ch_i in range(4):
            if mod_addr in self.channel_list[ch_i + 1]:
                return ch_i + 1
        return 0

    def get_group_name(self, grp_no: int) -> str:
        """Return name of group."""
        for grp in self.settings.groups:
            if grp.nmbr == grp_no:
                return grp.name
        return f"{grp_no}"

    def get_area_name(self, area_idx: int) -> str:
        """Return area name from index."""
        for area in self.settings.areas:
            if area_idx == area.nmbr:
                return area.name
        return "unbekannt"

    def build_smr(self) -> None:
        """Build SMR file content from status."""
        st_idx = self.status_idx  # noqa: F841
        chan_buf = self.channels
        self.logger.debug(f"self.channels: {chan_buf}")
        chan_list = b""
        ch_idx = 1
        for ch_i in range(4):
            cnt = chan_buf[ch_idx]
            chan_list += chan_buf[ch_idx : ch_idx + cnt + 1]
            ch_idx += cnt + 2

        self.smr = (
            chr(self._id).encode("iso8859-1")
            + chan_list
            + self.timeout
            + self.groups
            + self.mode_dependencies
            + self.name
            + self.user_modes
            + self.serial
            + self.day_night
            + self.version
        )
        self.calc_SMR_crc(self.smr)

    def calc_SMR_crc(self, smr_buf: bytes) -> None:
        """Calculate and store crc of SMR data."""
        self.smr_crc = calc_crc(smr_buf)

    async def set_config_mode(self, set_not_reset: bool) -> None:
        """Switches to config mode and back."""
        if self.api_srv._init_mode:
            return
        if set_not_reset:
            if not self.api_srv._opr_mode:
                # already in Srv mode, config mode is set in router
                return
            if self.api_srv._opr_mode:
                self.logger.error("Not in Srv mode when switching to config mode!")
                await self.api_srv.set_server_mode(self._id)
        return

    async def reset_config_mode(self) -> None:
        """Switches back from config mode (special function for testing mode)."""
        if self.mode0 != 75 and self.mode0 != 0:
            new_mode = self.mode0
        else:
            new_mode = 32
        await self.hdlr.set_mode(0, new_mode)
        return

    async def get_boot_stat(self) -> bytes:
        """Ask for boot errors."""
        rt_command = RT_CMDS.GET_RT_BOOTSTAT
        await self.hdlr.handle_router_cmd_resp(self._id, rt_command)
        return self.hdlr.rt_msg._resp_msg

    async def flush_buffer(self) -> None:
        """Empty router buffer."""
        await self.hdlr.handle_router_cmd(self._id, RT_CMDS.CLEAR_RT_SENDBUF)

    async def set_module_group(self, mod: int, grp: int) -> None:
        """Store new module group setting into router."""
        self.groups = self.groups[:mod] + int.to_bytes(grp) + self.groups[mod + 1 :]
        # await self.set_config_mode(True)
        await self.hdlr.send_rt_mod_group(mod, grp)
        # await self.set_config_mode(False)

    def pack_descriptions(self) -> str:
        """Pack descriptions to string with lines."""
        out_buf = ""
        desc_buf = self.set_descriptions_to_file().encode("iso8859-1")
        desc_no = int.from_bytes(desc_buf[0:2], "little")
        for ptr in range(4):
            out_buf += f"{desc_buf[ptr]};"
        out_buf += "\n"
        ptr = 4
        for desc_i in range(desc_no):
            l_len = desc_buf[ptr + 8] + 9
            line = desc_buf[ptr : ptr + l_len]
            for li in range(l_len):
                out_buf += f"{line[li]};"
            out_buf += "\n"
            ptr += l_len
        return out_buf

    def save_descriptions_file(self) -> None:
        """Save descriptions to file."""
        file_name = f"Rtr_{self._id}_descriptions.smb"
        if self.api_srv.is_addon:
            file_path = DATA_FILES_ADDON_DIR
        else:
            file_path = DATA_FILES_DIR
        # if not isfile(file_path + file_name):
        #     file_path = DATA_FILES_DIR
        #     self.logger.debug(f"Add-on config path not found, using {file_path}")
        try:
            fid = open(file_path + file_name, "w")
            desc_buf = self.pack_descriptions()
            fid.write(desc_buf)
            fid.close()
            self.logger.info(f"Descriptions saved to {file_path + file_name}")
        except Exception as err_msg:
            self.logger.error(
                f"Error saving description to file {file_path + file_name}: {err_msg}"
            )
            fid.close()

    def unpack_descriptions(self, lines: list[str]) -> str:
        """Merge ;-seperated values to string."""
        res = ""
        for line in lines:
            for val in line.split(";"):
                if len(val) > 0:
                    res += chr(int(val))
        return res

    def get_glob_descriptions(self, descriptions) -> None:
        """Get descriptions of commands, etc."""

        self.descriptions = []
        resp = descriptions.encode("iso8859-1")

        no_lines = int.from_bytes(resp[:2], "little")
        resp = resp[4:]
        for _ in range(no_lines):
            if resp == b"":
                break
            line_len = int(resp[8]) + 9
            line = resp[:line_len]
            content_code = int.from_bytes(line[1:3], "little")
            entry_no = int(line[3])
            entry_name = line[9:line_len].decode("iso8859-1").strip()
            if content_code == 767:  # FF 02: global flg (Merker)
                self.descriptions.append(IfDescriptor(entry_name, entry_no, 3))
            elif content_code == 1023:  # FF 03: collective commands (Sammelbefehle)
                self.descriptions.append(IfDescriptor(entry_name, entry_no, 4))
            elif content_code == 2047:  # FF 07: group names
                self.descriptions.append(IfDescriptor(entry_name, entry_no, 2))
            elif content_code == 2303:  # FF 08: alarm commands
                pass
            elif content_code == 2815:  # FF 0A: areas
                self.descriptions.append(IfDescriptor(entry_name, entry_no, 1))
            elif content_code == 3071:  # FF 0B: cover autostop count
                self.cov_autostop_cnt = entry_no
            resp = resp[line_len:]

    def set_descriptions_to_file(self, descriptions: str = "") -> str:
        """Add new descriptions into description string."""
        desc_types = [10, 7, 2, 3]
        if descriptions == "":
            # init description header
            descriptions = "\x00\x00\x00\x00"
        resp = descriptions.encode("iso8859-1")
        desc = resp[:4].decode("iso8859-1")
        no_lines = int.from_bytes(resp[:2], "little")
        line_no = 0
        resp = resp[4:]
        # Remove all global flags, coll commands, areas, cov_autostop, and group names
        # Leave rest unchanged
        for _ in range(no_lines):
            if resp == b"":
                break
            line_len = int(resp[8]) + 9
            line = resp[:line_len]
            content_code = int.from_bytes(line[1:3], "little")
            if content_code not in [767, 1023, 2047, 2815, 3071]:
                desc += line.decode("iso8859-1")
                line_no += 1
            resp = resp[line_len:]
        for descn in self.descriptions:
            desc += f"\x01\xff{chr(desc_types[descn.type - 1])}{chr(descn.nmbr)}\x00\x00\x00\x00{chr(len(descn.name))}{descn.name}"
            line_no += 1
        desc += f"\x01\xff\x0b{chr(self.cov_autostop_cnt)}\x00\x00\x00\x00\x00"
        line_no += 1
        descriptions = chr(line_no & 0xFF) + chr(line_no >> 8) + desc[2:]
        return descriptions

    async def get_descriptions(self) -> None:
        """Load descriptions from router or file."""
        self.descriptions_file = ""
        if float(self.version.decode("iso8859-1").strip().split()[1][1:]) >= 3.6:
            # Router is capable to store descriptions
            await self.hdlr.get_rtr_descriptions()
            if len(self.descriptions) < 2:  # == 0:
                # Legacy mode: look for description file
                self.load_descriptions_file()
                if len(self.descriptions) > 0:
                    # Remove from file and store in router
                    await self.cleanup_descriptions()
        else:
            self.load_descriptions_file()

    def load_descriptions_file(self) -> None:
        """Load descriptions from file."""
        self.descriptions_file = ""
        file_name = f"Rtr_{self._id}_descriptions.smb"
        if self.api_srv.is_addon:
            file_path = DATA_FILES_ADDON_DIR
        else:
            file_path = DATA_FILES_DIR
        if not isfile(file_path + file_name):
            file_path = DATA_FILES_DIR
            self.logger.debug(f"   Add-on config path not found, using {file_path}")
        if isfile(file_path + file_name):
            try:
                fid = open(file_path + file_name, "r")
                line = fid.readline().split(";")
                for ci in range(len(line) - 1):
                    self.descriptions_file += chr(int(line[ci]))
                desc_no = int(line[0]) + 256 * int(line[1])
                for li in range(desc_no):
                    line = fid.readline().split(";")
                    for ci in range(len(line) - 1):
                        self.descriptions_file += chr(int(line[ci]))
                fid.close()
                self.logger.info(f"   Descriptions loaded from {file_path + file_name}")
                self.get_glob_descriptions(self.descriptions_file)
            except Exception as err_msg:
                self.logger.error(
                    f"   Error loading description from file {file_path + file_name}: {err_msg}"
                )
                fid.close()
        else:
            self.logger.warning(
                f"   Descriptions file {file_path + file_name} not found"
            )

    def save_firmware(self, bin_data) -> None:
        "Save firmware binary to file and fw_data buffer."
        file_path = DATA_FILES_DIR
        file_name = f"Firmware_{bin_data[0]:02d}_{bin_data[1]:02d}.bin"
        fid = open(file_path + file_name, "wb")
        fid.write(bin_data)
        fid.close()
        self.fw_upload = bin_data
        self.logger.debug(f"Firmware file {file_path + file_name} saved")

    def load_firmware(self, mod_type) -> bool:
        "Load firmware binary from file to fw_data buffer."
        if isinstance(mod_type, str):
            mod_type = mod_type.encode("iso8859-1")
        file_path = DATA_FILES_DIR
        file_name = f"Firmware_{mod_type[0]:02d}_{mod_type[1]:02d}.bin"
        if isfile(file_path + file_name):
            fid = open(file_path + file_name, "rb")
            self.fw_upload = fid.read()
            fid.close()
            self.logger.debug(f"Firmware file {file_path + file_name} loaded")
            return True
        self.fw_upload = b""
        self.logger.error(
            f"Failed to load firmware file 'Firmware_{mod_type[0]:02d}_{mod_type[1]:02d}.bin'"
        )
        return False

    def get_router_settings(self) -> RouterSettings:
        """Collect all settings and prepare for config server."""
        self.settings = RouterSettings(self)
        return self.settings

    async def set_settings(self, settings: RouterSettings) -> None:
        """Store settings into router."""
        self.settings = settings
        self.day_night = self.settings.day_night
        if self.api_srv.is_offline:
            self._name = settings.name
            self.name = (chr(len(self._name)) + self._name).encode("iso8859-1")
            self.user_modes = (
                b"\n"
                + (settings.user1_name + " " * (10 - len(settings.user1_name))).encode(
                    "iso8859-1"
                )
                + b"\n"
                + (settings.user2_name + " " * (10 - len(settings.user2_name))).encode(
                    "iso8859-1"
                )
            )
            self.mode_dependencies = settings.mode_dependencies
            self.build_smr()
            settings.smr = self.smr
        else:
            await self.api_srv.block_network_if(self._id, True)
            await self.hdlr.send_rt_name(settings.name)
            await self.hdlr.send_mode_names(settings.user1_name, settings.user2_name)
            await self.hdlr.send_rt_day_night_changes(self.day_night)
            await self.hdlr.send_rt_group_deps(settings.mode_dependencies[1:])
            await self.get_full_status()
            await self.api_srv.block_network_if(self._id, False)

    async def get_module_comm_status(self, mod_addrs: list[int] = []):
        """Ask communication status for all modules."""
        self.mod_comm_status = {}
        for mod in self.modules + self.err_modules:
            if mod._id in mod_addrs:
                rt_command = RT_CMDS.RST_MD_COMMSTAT.replace("<mod>", chr(mod._id))
            else:
                rt_command = RT_CMDS.GET_MD_COMMSTAT.replace("<mod>", chr(mod._id))
            await self.hdlr.handle_router_cmd_resp(self._id, rt_command)
            resp = self.hdlr.rt_msg._resp_buffer[-7:]  # different length in both cases
            name = mod._name
            chan_no = mod._channel
            waiting_bytes = resp[0]
            no_timeouts = resp[1]
            no_mod_errs = resp[2]
            no_buf_overflow = resp[3]
            curr_resp_time = resp[4]
            if len(resp) < 6:
                max_resp_time = resp[4]
            else:
                max_resp_time = resp[5]
            self.mod_comm_status[mod._id] = (
                name,
                chan_no,
                waiting_bytes,
                no_timeouts,
                no_mod_errs,
                no_buf_overflow,
                curr_resp_time,
                max_resp_time,
            )

    async def switch_chan_power(self, mode: str, chan_mask: int):
        """Switch router channel power on or off."""
        if chan_mask == 0:
            rt_command = RT_CMDS.GET_RT_CHAN_STAT
        elif mode == "on":
            rt_command = RT_CMDS.SET_RT_CHAN.replace("<msk>", chr(chan_mask))
        elif mode == "off":
            rt_command = RT_CMDS.RES_RT_CHAN.replace("<msk>", chr(chan_mask))
        await self.hdlr.handle_router_cmd_resp(self._id, rt_command)
        resp = self.hdlr.rt_msg._resp_msg
        if len(resp) == 0:
            resp = "OK"
        return resp

    async def reset_chan_power(self, chan_mask: int):
        """Pulse router channel power for 1s."""
        if chan_mask > 0:
            await self.api_srv.block_network_if(self._id, True)
            await self.switch_chan_power("off", chan_mask)
            await asyncio.sleep(3)
            await self.switch_chan_power("on", chan_mask)
            await self.api_srv.block_network_if(self._id, False)

    async def set_descriptions(self, settings: RouterSettings) -> None:
        """Store names into router descriptions."""
        # groups, group names, mode dependencies
        self.descriptions, self.cov_autostop_cnt = settings.set_rtr_descriptions()
        await self.store_descriptions()

    async def store_descriptions(self):
        """Store router descriptions to router or file."""
        if float(self.version.decode("iso8859-1").strip().split()[1][1:]) >= 3.6:
            await self.hdlr.send_rtr_descriptions()
        else:
            self.descriptions_file = self.set_descriptions_to_file()
            self.save_descriptions_file()

    def get_properties(self) -> tuple[dict[str, int], list[str]]:
        """Return number of flags, commands, etc."""

        props: dict = {}
        props["day_sched"] = 7
        props["night_sched"] = 7
        props["areas"] = 255
        props["groups"] = 16
        props["glob_flags"] = 16
        props["coll_cmds"] = 16

        keys = [
            "areas",
            "groups",
            "day_sched",
            "night_sched",
            "glob_flags",
            "coll_cmds",
        ]
        no_keys = 0
        for key in keys:
            if props[key] > 0:
                no_keys += 1
        props["no_keys"] = no_keys

        return props, keys

    async def cleanup_descriptions(self) -> None:
        """If descriptions in desc file, store them into router and remove them from file."""
        if await self.hdlr.send_rtr_descriptions():
            # tmp_desc = self.descriptions
            # self.descriptions = []  # clear all descriptions
            # self.descriptions_file = self.set_descriptions_to_file()
            # self.save_descriptions_file()
            # self.logger.info(
            #     "Router descriptions stored in router and removed from file"
            # )
            # self.descriptions = tmp_desc
            self.logger.info("Router descriptions stored in router")

    def new_module(
        self,
        rtr_chan: int,
        mod_addr: int,
        mod_typ: bytes,
        mod_name: str,
        mod_serial: str,
    ):
        """Instantiate new module and add to router lists."""

        new_module = HbtnModule(
            mod_addr,
            rtr_chan,
            self._id,
            ModHdlr(mod_addr, self.api_srv),
            self.api_srv,
        )
        new_module._name = mod_name
        new_module._typ = mod_typ
        new_module._type = MODULE_CODES[mod_typ.decode("iso8859-1")]
        new_module._serial = mod_serial
        new_module.io_properties, new_module.io_prop_keys = (
            new_module.get_io_properties()
        )
        new_module.status = (
            chr(mod_addr)
            + mod_typ.decode("iso8859-1")
            + "\x00" * (MirrIdx.MOD_SERIAL - 3)
            + mod_serial
            + "\x00" * (MirrIdx.END - MirrIdx.MOD_SERIAL - 16)
        ).encode("iso8859-1")
        new_module.changed = MOD_CHANGED.NEW
        self.modules.append(new_module)
        self.mod_addrs.append(mod_addr)
        channels_str = ""
        for ch_i in range(4):
            # add entry to channel list
            if (ch_i + 1) not in self.channel_list.keys():
                self.channel_list[ch_i + 1] = []
            if ch_i + 1 == rtr_chan:
                self.channel_list[ch_i + 1].append(mod_addr)
            # prepare channels byte string
            channels_str += f"{chr(ch_i + 1)}{chr(len(self.channel_list[ch_i + 1]))}"
            for m_a in self.channel_list[ch_i + 1]:
                channels_str += f"{chr(m_a)}"
        self.channels = channels_str.encode("iso8859-1")
        # set entry initially to group 0
        self.groups = (
            self.groups[:mod_addr] + int.to_bytes(0) + self.groups[mod_addr + 1 :]
        )

    def remove_module(self, mod):
        """Remove module from router lists."""

        md_chan = mod._channel  # type: ignore
        if mod in self.modules:
            self.modules.remove(mod)
        if mod._id in self.mod_addrs:
            self.mod_addrs.remove(mod._id)
        # remove entry from channel list
        self.channel_list[md_chan].remove(mod._id)
        channels_str = ""
        for ch_i in range(4):
            # prepare channels byte string
            channels_str += f"{chr(ch_i + 1)}{chr(len(self.channel_list[ch_i + 1]))}"
            for m_a in self.channel_list[ch_i + 1]:
                channels_str += f"{chr(m_a)}"
        self.channels = channels_str.encode("iso8859-1")
        # set entry back to group 0
        self.groups = (
            self.groups[: mod._id] + int.to_bytes(0) + self.groups[mod._id + 1 :]
        )

    def get_module_by_serial(self, serial: str):
        """Return module by its serial number."""
        for mod in self.modules:
            if mod._serial == serial:
                return mod
        return None

    def apply_id_chan_changes(self, changes_dict):
        """Adjust all entries for modules address and channel changes."""

        # clear structures
        ch_ptr = 1
        for ch_i in range(1, 5):
            self.channel_list[ch_i] = []
            for ch_mbr in range(self.channels[ch_ptr]):
                self.channel_list[ch_i].append(self.channels[ch_ptr + ch_mbr + 1])
            ch_ptr += self.channels[ch_ptr] + 2
        channels_str = ""
        old_groups = self.groups
        self.groups = b"\x50" + b"\0" * 80

        # get new settings
        rm_list = []
        for m_i in range(len(self.modules)):
            mod = self.modules[m_i]
            mod_group = old_groups[mod._id - 1]
            if "modid_" + mod._serial in changes_dict.keys():
                old_id = mod._id
                new_id = int(changes_dict["modid_" + mod._serial])
                new_chan = int(changes_dict["modchan_" + mod._serial])
                if new_id != mod._id:
                    self.mod_addrs[m_i] = new_id
                    mod.old_id = mod._id
                    mod._id = new_id
                    mod.status = chr(new_id).encode("iso8859-1") + mod.status[1:]
                    mod.changed |= MOD_CHANGED.ID
                if new_chan != mod._channel:
                    mod._channel = new_chan
                    mod.changed |= MOD_CHANGED.CHAN
                if mod.changed:
                    # adapt channel list
                    for chan, mod_ids in self.channel_list.items():
                        if old_id in mod_ids:
                            self.channel_list[chan].remove(old_id)
                    self.channel_list[new_chan].append(new_id)
                    # build new group list
                    self.groups = (
                        self.groups[:new_id]
                        + int.to_bytes(mod_group)  # type: ignore
                        + self.groups[new_id + 1 :]
                    )
            else:
                # module not in list, remember to be removed
                rm_list.append(mod._serial)
        for m_ser in rm_list:
            # remove in second loop to not change order in fist loop
            mod = self.get_module_by_serial(m_ser)
            self.removed_modules.append(mod)
            self.remove_module(mod)
        for mod in self.err_modules:
            if f"modid_unknown{mod._id}" not in changes_dict.keys():
                # remove router module entry from list
                self.removed_modules.append(mod)
                self.remove_module(mod)
        for mod in self.removed_modules:
            if mod in self.err_modules:
                self.err_modules.remove(mod)
        # prepare channels byte string from channel list
        for ch_i in range(1, 5):
            channels_str += f"{chr(ch_i)}{chr(len(self.channel_list[ch_i]))}"
            for m_a in self.channel_list[ch_i]:
                channels_str += f"{chr(m_a)}"
        self.channels = channels_str.encode("iso8859-1")
        self.build_smr()
        self.settings.smr = self.smr
