import logging
import asyncio
from const import (
    RT_CMDS,
    API_RESPONSE,
    RT_RESP,
    RT_STAT_CODES,
    SYS_MODES,
    IfDescriptor,
)
from hdlr_class import HdlrBase
from messages import RtMessage, RtResponse
from collections.abc import Awaitable, Callable


class RtHdlr(HdlrBase):
    """Handling of incoming router messages."""

    def __init__(self, rtr, api_srv) -> None:
        """Creates handler object with msg infos and serial interface"""
        self.rtr = rtr
        self.api_srv = api_srv
        self.ser_if = self.api_srv._rt_serial
        self.rt_id = rtr._id
        self.logger = logging.getLogger(__name__)
        self.rt_msg = RtMessage(self, 0, "   ")  # initialize empty object
        self.protocol = ""
        self.upd_stat_dict: dict = {}

    async def rt_reboot(self):
        """Initiates a router reboot"""
        self.logger.info(f"Router {self.rt_id} will be rebooted, please wait...")
        await self.handle_router_cmd(self.rt_id, RT_CMDS.RT_REBOOT)
        await self.waitfor_rt_booted()

    async def waitfor_rt_booted(self):
        """Wait until router finished booting."""
        router_running = False
        while not (router_running):
            ret_msg = await self.get_rt_status()
            router_running = (len(ret_msg) > 40) and (
                ret_msg[-3] == RT_STAT_CODES.SYS_RUNNING
            )
            if not router_running:
                self.logger.info("Waiting for router booting...")
                await asyncio.sleep(2)
        if ret_msg[-2] == RT_STAT_CODES.SYS_PROBLEMS:
            self.logger.warning("Router running, boot finished with problems")
            await self.get_module_boot_status()
        else:
            self.logger.info("Router running")

    async def get_module_boot_status(self):
        """Return boot status text."""
        self.rtr.mod_boot_status = await self.rtr.get_boot_stat()
        self.rtr.mod_boot_errors: dict[int, str] = {}  # type: ignore
        for err in range(self.rtr.mod_boot_status[0]):
            mod = self.rtr.mod_boot_status[2 * err + 1]
            err_mask = self.rtr.mod_boot_status[2 * err + 2]
            mod_boot_errs = ""
            if err_mask & 0x80:
                mod_boot_errs += " error 128 "
            if err_mask & 0x40:
                mod_boot_errs += " error 64 "
            if err_mask & 0x20:
                mod_boot_errs += " error 32 "
            if err_mask & 0x10:
                mod_boot_errs += " error 16 "
            if err_mask & 0x08:
                mod_boot_errs += " error 8 "
            if err_mask & 0x04:
                mod_boot_errs += " Unknown module type "
            if err_mask & 0x02:
                mod_boot_errs += " Mirror problems "
            if err_mask & 0x01:
                mod_boot_errs += " Forward problems"
            mod_boot_errs = mod_boot_errs.replace("  ", ", ")
            if len(mod_boot_errs) > 0:
                self.rtr.mod_boot_errors[mod] = mod_boot_errs
        self.rtr.mod_boot_errors = dict(sorted(self.rtr.mod_boot_errors.items()))
        for mod_err in list(self.rtr.mod_boot_errors.keys()):
            self.logger.warning(
                f"   Boot error with module {mod_err}: {self.rtr.mod_boot_errors[mod_err]}"
            )

    async def set_mode(self, group: int, new_mode):
        """Changes system or group mode to new_mode"""
        if group == 0:
            # System mode
            rt_cmd = RT_CMDS.SET_GLOB_MODE
            rt_cmd = rt_cmd.replace("<md>", chr(new_mode))
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            return self.rt_msg._resp_buffer[-2:-1]
        if group == 255:
            # All groups but 0
            grps_modes = ""
            rt_cmd = RT_CMDS.SET_GRPS_MODE
            for nm in new_mode:
                grps_modes += chr(nm)
            rt_cmd = rt_cmd.replace("<mds>", grps_modes)
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            return self.rt_msg._resp_buffer[6:-1]
        else:
            rt_cmd = RT_CMDS.SET_GRP_MODE.replace("<grp>", chr(group))
            rt_cmd = rt_cmd.replace("<md>", chr(new_mode))
            await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
            return self.rt_msg._resp_buffer[-2:-1]

    async def get_mode(self, group):
        """Changes system or group mode to new_mode"""
        if group == 0:
            # System mode
            rt_cmd = RT_CMDS.GET_GLOB_MODE
        elif group == 255:
            # All groups but 0
            rt_cmd = RT_CMDS.GET_GRPS_MODE
        else:
            rt_cmd = RT_CMDS.GET_GRP_MODE.replace("<grp>", chr(group))
        await self.handle_router_cmd_resp(self.rt_id, rt_cmd)

        if (len(self.rt_msg._resp_msg) > 1) and (group != 255):
            self.logger.warning(
                f"Response to get mode {group} command too long: {self.rt_msg._resp_buffer}"
            )
            if (b_len := len(self.ser_if[0]._buffer)) > 0:
                await self.ser_if[0].read(b_len)  # empty buffer
            other_responses = True
            while other_responses:
                await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
                other_responses = not (self.rt_msg._resp_buffer[3] == ord(rt_cmd[-2]))
                self.logger.info(f"Other response: {self.rt_msg._resp_buffer[:5]}")
        elif group == 0:
            self.rtr.mode0 = self.rt_msg._resp_msg[0]
        return self.rt_msg._resp_msg

    async def get_rt_channels(self) -> bytes:
        """Get router channels."""
        await asyncio.sleep(0.2)
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_CHANS)
        if self.rt_msg._resp_code == 133:
            # switch to Srv mode made without response, may be still in buffer
            await self.handle_router_resp(self.rt_id)
        self.rtr.channels = self.rt_msg._resp_msg
        ptr = 1
        for ch_i in range(4):
            self.rtr.channel_list[ch_i + 1] = []
            for mod_i in range(self.rtr.channels[ptr]):
                self.rtr.channel_list[ch_i + 1].append(
                    int(self.rtr.channels[ptr + 1 + mod_i])
                )
            ptr += self.rtr.channels[ptr] + 2
        return self.rtr.channels

    async def get_rt_timeout(self) -> bytes:
        """Get router timeout."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_TIMEOUT)
        self.rtr.timeout = self.rt_msg._resp_msg[-1:]
        return self.rtr.timeout

    async def get_rt_group_no(self) -> bytes:
        """Get router group no."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPNO)
        grps = self.rt_msg._resp_msg
        self.rtr.groups = chr(len(grps)).encode("iso8859-1") + grps
        return self.rtr.groups

    async def get_rt_group_deps(self) -> bytes:
        """Get router mode dependencies."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPMODE_DEP)
        grps = self.rt_msg._resp_msg
        self.rtr.mode_dependencies = chr(len(grps)).encode("iso8859-1") + grps
        return self.rtr.mode_dependencies

    async def get_rt_name(self) -> bytes:
        """Get router name."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_NAME)
        name = self.rt_msg._resp_msg
        self.rtr.name = chr(len(name)).encode("iso8859-1") + name
        self.rtr._name = name.decode("iso8859-1").strip()
        return self.rtr.name

    async def get_mode_names(self) -> bytes:
        """Get user mode names 1 and 2."""
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.GET_RT_MODENAM.replace("<umd>", "\x01")
        )
        umode_name_1 = self.rt_msg._resp_msg[1:]
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.GET_RT_MODENAM.replace("<umd>", "\x02")
        )
        umode_name_2 = self.rt_msg._resp_msg[1:]
        nm_len = chr(len(umode_name_1)).encode("iso8859-1")
        self.rtr.user_modes = nm_len + umode_name_1 + nm_len + umode_name_2
        return self.rtr.user_modes

    async def get_rt_serial(self) -> bytes:
        """Get full router serial number."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_SERNO)
        serial = self.rt_msg._resp_msg
        self.rtr.serial = chr(len(serial)).encode("iso8859-1") + serial
        return self.rtr.serial

    async def get_rt_day_night_changes(self) -> bytes:
        """Get full router settings for day night changes."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_DAYNIGHT)
        self.rtr.day_night = b"\x46" + self.rt_msg._resp_msg
        return self.rtr.day_night

    async def get_rt_sw_version(self) -> bytes:
        """Get router software version."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_SW_VERSION)
        self.rtr.version = self.rt_msg._resp_msg
        self.rtr._version = self.rtr.version[1:].strip().decode("iso8859-1")
        return self.rtr.version

    async def get_date(self) -> bytes:
        """Get date settings."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_DATE)
        self.rtr.date = self.rt_msg._resp_buffer[5:9]
        return self.rtr.date

    async def get_grp_mode_status(self) -> bytes:
        """Get router group mode status."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_GRPMOD_STAT)
        return self.rt_msg._resp_msg

    async def get_rt_full_status(self) -> bytes:
        """Get full router status."""
        # Create continuous status byte array and indices
        await self.rt_msg.api_hdlr.api_srv.set_server_mode()
        # await asyncio.sleep(0.3)
        # await self.handle_router_cmd_resp(
        #     1, RT_CMDS.SET_GLOB_MODE.replace("<md>", chr(75))
        # )
        await asyncio.sleep(0.3)
        stat_idx = [0]
        rt_stat = chr(self.rt_id).encode("iso8859-1")
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_channels()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_timeout()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_group_no()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_group_deps()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_name()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_mode_names()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_serial()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_day_night_changes()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_rt_sw_version()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_date()
        stat_idx.append(len(rt_stat))

        rt_stat += await self.get_grp_mode_status()
        stat_idx.append(len(rt_stat))
        self.rtr.grp_mode_status = rt_stat[stat_idx[-2] : stat_idx[-1]]
        self.rtr.status_idx = stat_idx

        return rt_stat

    async def query_rt_status(self) -> str:
        """Get router system status. Used in Operate mode"""
        await self.handle_router_cmd(self.rt_id, RT_CMDS.GET_RT_STATUS)
        return "OK"

    async def get_rt_status(self) -> bytes:
        """Get router system status."""
        if self.api_srv._init_mode and (len(self.rtr.chan_status) > 40):
            self.logger.debug("Returning stored channel status")
            return self.rtr.chan_status
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_STATUS)
        if len(self.rt_msg._resp_msg) < 40:
            # Something went wrong, return buffer as is
            self.logger.warning(
                f"Router channel status with wrong length {len(self.rt_msg._resp_msg)}, return stored value"
            )
            return self.rtr.chan_status
        if self.rt_msg._resp_buffer[5] == 0:
            # mode 0 not zero, should be 'K', config while reading status
            self.logger.warning(
                "Router channel status with mode 0 = 0, return stored value"
            )
            return self.rtr.chan_status
        self.logger.debug("Return valid router status")
        return self.rt_msg._resp_buffer[4:-1]

    async def get_rt_modules(self) -> bytes:
        """Get all modules connected to router."""
        await self.rt_msg.api_hdlr.api_srv.set_server_mode()
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_RT_MODULES)
        return self.rt_msg._resp_msg

    async def get_mod_errors(self) -> bytes:
        """Get all module communication errors with last error."""
        await self.rt_msg.api_hdlr.api_srv.set_server_mode()
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_MD_LASTERR)
        ret_bytes = self.rt_msg._resp_msg
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_MD_ERRORS)
        ret_bytes += self.rt_msg._resp_msg
        return ret_bytes

    async def send_rt_channels(self, rt_channels) -> bytes:
        """Send router channels."""
        cmd_str = RT_CMDS.SEND_RT_CHANS + rt_channels.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_timeout(self, rt_timeout) -> bytes:
        """Send router timeout."""
        if isinstance(rt_timeout, bytes):
            tout = rt_timeout.decode("iso8859-1")
        else:
            tout = chr(rt_timeout)
        cmd_str = RT_CMDS.SEND_RT_TIMEOUT.replace("<tout>", tout)
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_group_no(self, rt_groups) -> bytes:
        """Send router group no."""
        cmd_str = RT_CMDS.SEND_RT_GRPNO + rt_groups.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_mod_group(self, mod, grp) -> bytes:
        """Send module group membership."""
        cmd_str = RT_CMDS.SET_MOD_GROUP.replace("<mod>", chr(mod)).replace(
            "<grp>", chr(grp)
        )
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_group_deps(self, rt_groupdep) -> bytes:
        """Send router mode dependencies."""
        cmd_str = RT_CMDS.SEND_RT_GRPMODE_DEP + rt_groupdep.decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_name(self, rt_name) -> bytes:
        """Send router name."""
        if isinstance(rt_name, bytes):
            rt_name = rt_name.decode("iso8859-1")
        rt_name = rt_name + (" " * (32 - len(rt_name)))
        await self.rtr.set_config_mode(True)
        for part in range(4):
            cmd_str = (
                RT_CMDS.SEND_RT_NAME
                + chr(part * 8)
                + rt_name[part * 8 : (part + 1) * 8]
                + "\xff"
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            await asyncio.sleep(0.2)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_mode_names(self, umd_name1, umd_name2) -> bytes:
        """Send user mode names."""
        if isinstance(umd_name1, bytes):
            umd_name1 = umd_name1.decode("iso8859-1")
        if isinstance(umd_name2, bytes):
            umd_name2 = umd_name2.decode("iso8859-1")
        umd_name1 = umd_name1 + (" " * (10 - len(umd_name1)))
        umd_name2 = umd_name2 + (" " * (10 - len(umd_name2)))
        cmd_str = RT_CMDS.SEND_RT_MODENAM.replace("<umd>", "\x01") + umd_name1 + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        cmd_str = RT_CMDS.SEND_RT_MODENAM.replace("<umd>", "\x02") + umd_name2 + "\xff"
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        return self.rt_msg._resp_msg

    async def send_rt_day_night_changes(self, day_night) -> bytes:
        """Send day night settings."""
        if len(day_night) == 70:
            day_night = b"\x46" + day_night
        cmd_str = RT_CMDS.SEND_RT_DAYNIGHT + day_night[1:].decode("iso8859-1") + "\xff"
        await self.rtr.set_config_mode(True)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_msg
        await self.rtr.set_config_mode(False)
        return resp

    async def send_rt_full_status(self) -> None:
        """Send full router status from uploaded smr."""
        self.logger.debug("Starting SMR data transfer into router")

        await self.send_rt_channels(self.rtr.channels)
        await self.send_rt_timeout(self.rtr.timeout)
        await self.send_rt_group_no(self.rtr.groups[1:])
        await self.send_rt_group_deps(self.rtr.mode_dependencies[1:])
        await self.send_rt_name(self.rtr.name)
        umd_name1 = self.rtr.user_modes[1:11]
        umd_name2 = self.rtr.user_modes[12:22]
        await self.send_mode_names(umd_name1, umd_name2)
        await self.send_rt_day_night_changes(self.rtr.day_night)
        self.logger.debug("SMR data transferred into router")
        # await self.rt_reboot()

    def set_rt_full_status(self) -> None:
        """Set full router status locally from uploaded smr."""
        self.logger.debug("Setting SMR data to local router data")
        smr_ptr = 1
        self.rtr.smr = self.rtr.smr_upload
        rt_channels = b""
        self.rtr.mod_addrs = []
        for ch in range(4):
            self.rtr.channel_list[ch + 1] = []
            ch_count = self.rtr.smr_upload[smr_ptr]
            rt_channels += (
                int.to_bytes(ch + 1)
                + int.to_bytes(ch_count)
                + self.rtr.smr_upload[smr_ptr + 1 : smr_ptr + 1 + ch_count]
            )
            for md_i in range(ch_count):
                self.rtr.mod_addrs.append(self.rtr.smr_upload[smr_ptr + 1 + md_i])
                self.rtr.channel_list[ch + 1].append(
                    self.rtr.smr_upload[smr_ptr + 1 + md_i]
                )
            smr_ptr += 1 + ch_count
        self.rtr.mod_addrs.sort()
        self.rtr.channels = rt_channels
        self.rtr.timeout = self.rtr.smr_upload[smr_ptr : smr_ptr + 1]
        smr_ptr += 1
        self.rtr.groups, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.rtr.mode_dependencies, smr_ptr = self.get_smr_item(
            self.rtr.smr_upload, smr_ptr
        )
        self.rtr.name, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.rtr._name = self.rtr.name.decode("iso8859-1").strip()
        umd_name1, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        umd_name2, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.rtr.user_modes = umd_name1 + umd_name2
        self.rtr.serial, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.rtr.day_night, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)
        self.rtr.version, smr_ptr = self.get_smr_item(self.rtr.smr_upload, smr_ptr)

    def get_smr_item(self, smr_bytes: bytes, smr_ptr: int) -> tuple[bytes, int]:
        """Get one item from smr bytes."""
        item_len = smr_bytes[smr_ptr]
        item = smr_bytes[smr_ptr : smr_ptr + item_len + 1]
        smr_ptr += item_len + 1
        return item, smr_ptr

    async def get_rtr_descriptions(self) -> bytes:
        """Get the router descriptions."""

        desc = []
        desc_cnt = 0
        desc_len = -1  # initial value to enable repeated reading of desc 0
        desc_to_read = True
        while desc_to_read:
            rt_command = (
                RT_CMDS.GET_RTR_DESC.replace("<rtr>", chr(self.rt_id))
                .replace("<cntl>", chr(desc_cnt & 0xFF))
                .replace("<cnth>", chr(desc_cnt >> 8))
            )
            # Send command to router and get description
            await self.handle_router_cmd_resp(self.rt_id, rt_command)
            resp = self.rt_msg._resp_msg
            resp_cnt = int.from_bytes(self.rt_msg._resp_buffer[5:7], "little")

            if desc_cnt == 0 and resp_cnt == 0:
                # first description with length, response OK
                desc_len = int.from_bytes(self.rt_msg._resp_buffer[7:9], "little")

            if desc_len == 0:
                self.logger.info("   Router descriptions empty")
                desc_to_read = False
            elif resp_cnt != desc_cnt:
                self.logger.warning(
                    f"   Router description {desc_cnt}: received {resp_cnt}, read again, discarded"
                )
            else:
                resp = self.rt_msg._resp_buffer[-35:-1]
                desc.append(
                    IfDescriptor(resp[2:].strip().decode("iso8859-1"), resp[1], resp[0])
                )
                desc_cnt += 1

                if desc_cnt >= desc_len:
                    self.logger.info(
                        f"   {desc_len} router descriptions read successfully"
                    )
                    self.rtr.descriptions = desc
                    desc_to_read = False
        self.rtr.descriptions = desc
        return

    async def send_rtr_descriptions(self) -> bool:
        """Store descriptions into router."""

        max_reps = 5
        rep_cnt = 0
        resp_cnt = 0xFFF0  # unknow flag for cnt 0
        desc = self.rtr.descriptions

        desc_len = len(desc)
        no_bytes = 35 * desc_len + 4
        desc_cnt = 0
        while desc_cnt < desc_len and rep_cnt < max_reps:
            desc_pckg = (
                chr(desc_cnt & 0xFF)
                + chr(desc_cnt >> 8)
                + chr(0xFF)
                + chr(desc[desc_cnt].type)
                + chr(desc[desc_cnt].nmbr)
                + (desc[desc_cnt].name + " " * (32 - len(desc[desc_cnt].name)))
                + chr(0xFF)
            )
            if desc_cnt == 0:
                desc_pckg = (
                    chr(0)
                    + chr(0)
                    + chr(desc_len & 0xFF)
                    + chr(desc_len >> 8)
                    + chr(no_bytes & 0xFF)
                    + chr(no_bytes >> 8)
                    + desc_pckg[2:]
                )
            l_p = len(desc_pckg)
            cmd = (
                RT_CMDS.SEND_RTR_DESC.replace("<rtr>", chr(self.rt_id)).replace(
                    "<len>", chr(l_p + 5)
                )
                + desc_pckg
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
            resp_cnt = int.from_bytes(self.rt_msg._resp_buffer[5:7], "little")
            if resp_cnt == desc_cnt:
                desc_cnt += 1
                rep_cnt = 0
            elif resp_cnt == 0xFFFF:
                self.logger.warning(
                    f"Description upload (router) returned error flag, repeat: Count {desc_cnt}"
                )
                rep_cnt += 1
            elif resp_cnt == 0xFFFA:
                self.logger.debug("Description upload (router) returned final flag")
                desc_cnt += 1
            else:
                self.logger.error(
                    f"Description upload (router) unexpected flag: {resp_cnt}, abort"
                )
                break
        if resp_cnt == 0xFFFA:
            self.logger.info(
                f"Description upload terminated successfully, transferred {no_bytes} bytes of {desc_len} definitions to router"
            )
            return True
        self.logger.info(
            f"Description upload (router) terminated: Count {desc_cnt} Flag {resp_cnt}"
        )
        return False

    async def restart_system(self) -> None:
        """Restart router after firmware update."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
        self.logger.info(f"Router {self.rt_id} system restarted")

    async def del_mod_addr(self, mod_addr):
        """Remove module from router."""
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.DEL_MD_ADDR.replace("<mod>", chr(mod_addr))
        )
        self.logger.debug(f"Module address {mod_addr} removed from router")
        return self.rt_msg._resp_msg

    async def upload_router_firmware(
        self, rt_type, progress_fun: Callable[[int, int, int], Awaitable[None]]
    ) -> str:
        """Upload router firmware to router, returns True for success."""

        fw_buf = self.rtr.fw_upload
        self._last_progress = 0
        new_fw = fw_buf[-27:-5]
        fw_len = len(fw_buf)
        if fw_len == 0:
            self.logger.error("Failed to upload / flash router")
            return "ERROR"

        pkg_len = 13
        no_pkgs = int(fw_len / pkg_len)
        rest_len = fw_len - no_pkgs * pkg_len
        if rest_len > 0:
            no_pkgs += 1
        self.logger.info(
            f"Updating router {self.rt_id}: length {fw_len} bytes, {no_pkgs} packages"
        )
        cmd_str = RT_CMDS.SET_ISP_MODE.replace("<lenl>", chr(fw_len & 0xFF)).replace(
            "<lenh>", chr(fw_len >> 8)
        )

        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
        if (
            (resp[0] == 0x42)
            and (resp[1] == 0x4C)
            and (resp[2] == 0)
            and (resp[3] == 0)
        ):
            self.logger.warning("Router set into update mode")
        else:
            self.logger.error("Failed to enter router ISP mode")
            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
            self.logger.info("Router restarted")
            return "ERROR"

        await asyncio.sleep(1)
        await self.handle_router_cmd_resp(self.rt_id, cmd_str)
        resp = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
        if (
            (resp[0] == 0x42)
            and (resp[1] == 0x4C)
            and (resp[2] == 0)
            and (resp[3] == 0)
        ):
            self.logger.warning("Router starting to update")
        else:
            self.logger.error("Failed to enter router ISP mode")
            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
            self.logger.info("Router restarted")
            return "ERROR"
        cmd_org = RT_CMDS.UPDATE_RT_PKG
        for pi in range(no_pkgs):
            pkg_low_target = (pi + 1) & 0xFF
            # pkg_high_target = (pi + 1) >> 8
            if pi < (no_pkgs - 1):
                cmd_str = (
                    cmd_org.replace("<len>", chr(pkg_len + 8))
                    .replace("<pno>", chr(pkg_low_target))
                    .replace(
                        "<buf>",
                        fw_buf[pi * pkg_len : (pi + 1) * pkg_len].decode("iso8859-1"),
                    )
                )
            else:
                # last package with < pkg_len
                cmd_str = (
                    cmd_org.replace("<len>", chr(rest_len + 8))
                    .replace("<pno>", chr(pkg_low_target))
                    .replace("<buf>", fw_buf[pi * pkg_len :].decode("iso8859-1"))
                )
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            resp_code = self.rt_msg._resp_code
            resp_msg = self.rt_msg._resp_buffer[-self.rt_msg._resp_buffer[2] + 4 : -1]
            if (resp_code == 201) and (len(resp_msg) > 3):
                if (resp_msg[0] == 0x42) and (resp_msg[1] == 0x4C):
                    await progress_fun(resp_msg[2], resp_msg[3], no_pkgs)
                else:
                    self.logger.error(
                        f"Failed to flash router, returned message 201: {resp_msg}"
                    )
                    await self.handle_router_cmd_resp(
                        self.rt_id, RT_CMDS.SYSTEM_RESTART
                    )
                    self.logger.info("Router restarted")
                    return "ERROR"
            else:
                self.logger.error("Failed to flash router, returned empty message 201")
                await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
                self.logger.info("Router restarted")
                return "ERROR"
            await asyncio.sleep(0.01)
        self.logger.info("Successfully uploaded and flashed router firmware")
        self.rtr.version = b"\x16" + new_fw
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.SYSTEM_RESTART)
        self.logger.info("Router restarted")
        return "OK"

    async def send_rtr_fw_update_protocol(
        self, pkg_low: int, pkg_high: int, max_count: int
    ) -> None:
        """Send firmware upload counter to ip client."""
        stat_msg = (
            API_RESPONSE.rtfw_flash_stat.replace("<rtr>", chr(self.rt_id))
            .replace("<pkgs>", chr(max_count + 1))
            .replace("<pkgl>", chr(pkg_low))
            .replace("<pkgh>", chr(pkg_high))
        )
        await self.api_srv.hdlr.send_api_response(
            stat_msg,
            RT_STAT_CODES.PKG_OK,
        )

    async def log_rtr_fw_update_protocol(
        self, pkg_low: int, pkg_high: int, max_count: int
    ) -> None:
        """Log firmware upload counter."""
        cur_pkg = pkg_high * 256 + pkg_low
        progress = int(100 * cur_pkg / max_count)
        if progress > self._last_progress:
            self.logger.info(
                f"Router update progress: {cur_pkg} of {max_count +1} : {progress} %"
            )
            self._last_progress = progress

    async def stat_rtr_fw_update_protocol(
        self, pkg_low: int, pkg_high: int, max_count: int
    ) -> None:
        """Prepare firmware upload counter status."""
        cur_pkg = pkg_high * 256 + pkg_low
        self.upd_stat_dict["cur_mod"] = 0
        self.upd_stat_dict["mod_0"]["progress"] = round(100 * cur_pkg / max_count)

    async def upload_module_firmware(
        self, mod_type: bytes, progress_fun: Callable[[int, int, int], Awaitable[None]]
    ) -> bool:
        """Upload firmware to router, returns True for success."""

        fw_buf = self.rtr.fw_upload
        fw_len = len(fw_buf)
        cmd_org = RT_CMDS.UPDATE_MOD_PKG
        pkg_len = 246
        if fw_len > 0:
            no_pkgs = int(fw_len / pkg_len)
            rest_len = fw_len - no_pkgs * pkg_len
            if rest_len > 0:
                no_pkgs += 1
            for pi in range(no_pkgs):
                if pi < no_pkgs - 1:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(pkg_len + 8))
                        .replace("<pno>", chr(pi + 1))
                        .replace("<pcnt>", chr(no_pkgs))
                        .replace("<blen>", chr(pkg_len))
                        .replace(
                            "<buf>",
                            fw_buf[pi * pkg_len : (pi + 1) * pkg_len].decode(
                                "iso8859-1"
                            ),
                        )
                    )
                else:
                    cmd_str = (
                        cmd_org.replace("<len>", chr(rest_len + 8))
                        .replace("<pno>", chr(pi + 1))
                        .replace("<pcnt>", chr(no_pkgs))
                        .replace("<blen>", chr(rest_len))
                        .replace("<buf>", fw_buf[pi * pkg_len :].decode("iso8859-1"))
                    )
                await self.handle_router_cmd_resp(self.rt_id, cmd_str)
                if self.rt_msg._resp_buffer[5] == RT_STAT_CODES.PKG_OK:
                    await progress_fun(pi + 1, no_pkgs, RT_STAT_CODES.PKG_OK)
                else:
                    await progress_fun(pi + 1, no_pkgs, RT_STAT_CODES.PKG_ERR)
                    break  # abort upload
            if (self.rt_msg._resp_buffer[4] == pi + 1) and (
                self.rt_msg._resp_buffer[5] == RT_STAT_CODES.PKG_OK
            ):
                self.logger.debug(
                    f"Successfully uploaded firmware type {mod_type[0]:02d}_{mod_type[1]:02d}"
                )
                return True
        self.logger.error(
            f"Failed to upload firmware type {mod_type[0]:02d}_{mod_type[1]:02d}"
        )
        return False

    async def send_mod_fw_upload_protocol(
        self, pckg: int, no_pkgs: int, code: int
    ) -> None:
        """Send firmware upload status protocol to ip client."""
        stat_msg = (
            API_RESPONSE.bin_upload_stat.replace("<rtr>", chr(self.rt_id))
            .replace("<pkg>", chr(pckg))
            .replace("<pkgs>", chr(no_pkgs + 1))
        )
        await self.api_srv.hdlr.send_api_response(stat_msg, code)

    async def stat_mod_fw_upload_protocol(
        self, pckg: int, no_pkgs: int, code: int
    ) -> None:
        """Prepare firmware upload status protocol."""
        if code == RT_STAT_CODES.PKG_OK:
            self.upd_stat_dict["cur_mod"] = -1
            self.upd_stat_dict["upload"] = round(pckg * 100 / no_pkgs)
        else:
            self.logger.error(f"Firmware upload package {pckg} of {no_pkgs} : failed")

    async def log_mod_fw_upload_protocol(
        self, pckg: int, no_pkgs: int, code: int
    ) -> None:
        """Log firmware upload status protocol."""
        if code == RT_STAT_CODES.PKG_OK:
            self.logger.info(
                f"Firmware upload package {pckg} of {no_pkgs} : {round(pckg * 100 / no_pkgs)}%"
            )
        else:
            self.logger.error(f"Firmware upload package {pckg} of {no_pkgs} : failed")

    async def flash_module_firmware(
        self,
        mod_list,
        progress_fun: Callable[[int, str], Awaitable[None]],
    ) -> str:
        """Update module with uploaded firmware."""

        for mod in mod_list:
            cmd_str = RT_CMDS.FLASH_MOD_FW.replace("<mod>", chr(mod))
            await self.handle_router_cmd_resp(self.rt_id, cmd_str)
            while await self.in_program_mode():
                await asyncio.sleep(1)
                await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.MOD_FLASH_STAT)
                await progress_fun(mod, self.rt_msg._resp_msg.decode("iso8859-1"))

            await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.MOD_FLASH_STAT)
            await progress_fun(mod, self.rt_msg._resp_msg.decode("iso8859-1"))
            self.logger.info(f"Update of module {mod} finished")
        return "OK"

    async def send_mod_fw_update_protocol(self, mod: int, protocol: str) -> None:
        """Send update status protocol to ip client."""
        plen_l = len(protocol) & 0xFF
        plen_h = len(protocol) >> 8
        stat_msg = (
            API_RESPONSE.modfw_flash_stat.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(mod))
            .replace("<lenl>", chr(plen_l))
            .replace("<lenh>", chr(plen_h))
            .replace("<protocol>", protocol)
        )
        await self.api_srv.hdlr.send_api_response(stat_msg, 1)

    async def stat_mod_fw_update_protocol(self, mod: int, protocol: str) -> None:
        """Prepare update status protocol."""
        cmod = ord(protocol[0])
        if not cmod:
            # Ignore first responses, update not started
            self.protocol = protocol
            return
        if protocol == self.protocol:
            # Ignore unchanged status responses
            return
        self.protocol = protocol
        perc = ord(protocol[1])
        self.upd_stat_dict["cur_mod"] = mod
        self.upd_stat_dict["mod_" + str(mod)]["progress"] = perc
        for mod_rdy_i in range(ord(protocol[2])):
            md = ord(protocol[3 + 3 * mod_rdy_i])
            if ord(protocol[5 + 3 * mod_rdy_i]) == 85:
                md_stat = "OK"
            elif ord(protocol[5 + 3 * mod_rdy_i]) == 70:
                md_stat = "failed"
            else:
                md_stat = "skipped"
            no_errs = ord(protocol[4 + 3 * mod_rdy_i])
            self.upd_stat_dict["mod_" + str(md)]["errors"] = no_errs
            self.upd_stat_dict["mod_" + str(md)]["success"] = md_stat

    async def log_mod_fw_update_protocol(self, mod: int, protocol: str) -> None:
        """Log update status protocol."""
        cmod = ord(protocol[0])
        if not cmod:
            # Ignore first responses, update not started
            self.protocol = protocol
            return
        if protocol == self.protocol:
            # Ignore unchanged status responses
            return
        self.protocol = protocol
        perc = ord(protocol[1])
        log_info = f"Update status for modules: Cur. mod: {cmod}: {perc}%"

        for mod_rdy_i in range(ord(protocol[2])):
            if ord(protocol[5 + 3 * mod_rdy_i]) == 85:
                md_stat = "OK"
            elif ord(protocol[5 + 3 * mod_rdy_i]) == 70:
                md_stat = "failed"
            else:
                md_stat = "skipped"
            log_info += f"  Mod {ord(protocol[3 + 3 * mod_rdy_i])}: {md_stat}"
        self.logger.info(log_info)

    async def forward_message(self, src_rt: int, fwd_cmd: bytes) -> bytes:
        """Forward message from other router."""
        # insert src_rt into command
        fwd_str = fwd_cmd.decode("iso8859-1")
        fwd_str = (
            "\x2a<rtr>\xff"
            + fwd_str[:4]
            + chr(self.rt_id)
            + fwd_str[5:7]
            + chr(src_rt)
            + fwd_str[8:]
        )
        await self.handle_router_cmd_resp(self.rt_id, fwd_str)
        return self.rt_msg._resp_msg

    def parse_event(self, rt_resp: bytes):
        """Handle router responses in API mode to seperate events"""
        resp_msg = RtResponse(self, rt_resp)
        if not (resp_msg._crc_ok):
            self.logger.warning(
                f"Invalid Operate mode router message crc, message: {resp_msg.resp_data}"
            )
            return
        if resp_msg.resp_cmd == RT_RESP.MIRR_STAT:
            mod_id = resp_msg.resp_data[0]
            if mod_id in self.rtr.mod_addrs:
                return self.rtr.get_module(mod_id).update_status(resp_msg.resp_data)
            return

    async def in_program_mode(self) -> bool:
        """Return True while in program mode."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.GET_GLOB_MODE)
        return self.rt_msg._resp_msg[0] == SYS_MODES.Update

    async def set_module_address(self, mode: int, ch_or_mod: int, new_mod: int):
        """Set module address in router adress table."""
        await self.rt_msg.api_hdlr.api_srv.set_server_mode()
        if mode == 0:
            rt_cmd = RT_CMDS.NEXT_MD_ADDR.replace("<ch>", chr(ch_or_mod))
        elif mode == 1:
            rt_cmd = RT_CMDS.SET_MD_ADDR.replace("<ch>", chr(ch_or_mod))
        elif mode == 2:
            rt_cmd = RT_CMDS.CHG_MD_ADDR.replace("<mod>", chr(ch_or_mod))
        rt_cmd = rt_cmd.replace("<mdnew>", chr(new_mod))
        await self.handle_router_cmd_resp(self.rt_id, rt_cmd)
        return self.rt_msg._resp_msg
