import logging
import math
from copy import deepcopy as dpcopy
from const import (
    IfDescriptor,
    IoDescriptor,
    LgcDescriptor,
    LGC_TYPES,
    MirrIdx,
    SMGIdx,
    FingerNames,
)
from automation import AutomationsSet


def covertime_2_interptime(cov_time: int) -> tuple[int, int]:
    """Transform cover times to storage format and interp values."""
    if cov_time in range(127, 256):
        interp_val = 10
    elif cov_time in range(51, 127):
        interp_val = 5
    elif cov_time in range(25, 51):
        interp_val = 2
    else:
        interp_val = 1
    interp_time = round(cov_time * 10 / interp_val)
    return interp_time, interp_val


def interptime_2_covertime(interp_time: int, interp_val: int) -> int:
    """Transform cover times from storage format with interp value to float value."""
    cov_time = round(interp_time * interp_val / 10)
    return cov_time


class ModuleSettings:
    """Object with all module settings, including automations."""

    def __init__(self, module):
        """Fill all properties with module's values."""
        self.id: int = module._id
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialzing module settings object")
        self.module = module
        self.name = dpcopy(module._name)
        self.typ = module._typ
        self.type = module._type
        self.list = dpcopy(module.list)
        self.status = dpcopy(module.status)
        self.smg = dpcopy(module.build_smg())
        # self.desc = dpcopy(module.get_rtr().descriptions)
        self.properties: dict = module.io_properties
        self.prop_keys = module.io_prop_keys
        self.cover_times: list[int] = [0, 0, 0, 0, 0]
        self.blade_times: list[int] = [0, 0, 0, 0, 0]
        self.user1_name: str = (
            module.get_rtr().user_modes[1:11].decode("iso8859-1").strip()
        )
        self.user2_name: str = (
            module.get_rtr().user_modes[12:].decode("iso8859-1").strip()
        )
        self.save_desc_file_needed: bool = False
        self.upload_desc_info_needed: bool = False
        self.area_member = 0
        self.group = dpcopy(module.get_group())
        self.get_io_interfaces()
        self.get_logic()
        self.get_names()
        self.get_settings()
        self.get_descriptions()
        self.automtns_def = AutomationsSet(self)
        self.sim_pin: str = ""
        self.sim_pin_changed = False
        self.is_outdoor = (
            self.status[MirrIdx.OUTDOOR_MODE] == 65
        )  # only for sensor module

    def get_io_interfaces(self):
        """Parse config files to extract names, etc."""
        self.leds = [
            IfDescriptor("", i, 1) for i in range(self.properties["leds"])
        ]  # 0 for ambient light (sc mini) / night light led (sc)
        self.buttons = [
            IfDescriptor("", i + 1, 1) for i in range(self.properties["buttons"])
        ]
        self.inputs = [
            IoDescriptor("", i + 1, 1, 0) for i in range(self.properties["inputs"])
        ]
        self.outputs = [
            IoDescriptor("", i + 1, 1, 0) for i in range(self.properties["outputs"])
        ]
        self.covers = [
            IoDescriptor("", i + 1, 0, 0) for i in range(self.properties["covers"])
        ]
        self.dimmers = [
            IfDescriptor("", i + 1, -1) for i in range(self.properties["outputs_dimm"])
        ]
        self.flags: list[IfDescriptor] = []
        self.counters: list[IfDescriptor] = []
        self.logic: list[LgcDescriptor] = []
        self.messages: list[IfDescriptor] = []
        self.dir_cmds: list[IfDescriptor] = []
        self.vis_cmds: list[IfDescriptor] = []
        self.setvalues: list[IfDescriptor] = []
        self.users: list[IfDescriptor] = []
        self.fingers: list[IfDescriptor] = []
        self.glob_flags: list[IfDescriptor] = []
        self.coll_cmds: list[IfDescriptor] = []
        self.gsm_numbers: list[IfDescriptor] = []
        self.gsm_messages: list[IfDescriptor] = []

    def get_logic(self) -> None:
        """Get module counters from status."""
        self.logger.debug("Getting logic settings from module status")
        conf = self.status
        if len(conf) == 0:
            return
        for l_idx in range(10):
            if conf[MirrIdx.LOGIC + 3 * l_idx] == 5:
                # counter found
                self.counters.append(
                    IfDescriptor(
                        f"Counter{conf[MirrIdx.LOGIC + 3 * l_idx + 1]}_{l_idx + 1}",
                        l_idx + 1,
                        conf[MirrIdx.LOGIC + 3 * l_idx + 1],
                    )
                )
            elif conf[MirrIdx.LOGIC + 3 * l_idx] in [1, 2, 3, 4]:
                # logic found
                self.logic.append(
                    LgcDescriptor(
                        f"{LGC_TYPES[conf[MirrIdx.LOGIC + 3 * l_idx]]}{conf[MirrIdx.LOGIC + 3 * l_idx + 1]}_{l_idx + 1}",
                        l_idx + 1,
                        conf[MirrIdx.LOGIC + 3 * l_idx],
                        conf[MirrIdx.LOGIC + 3 * l_idx + 1],
                    )
                )

    def get_settings(self) -> bool:
        """Get module settings from status."""

        self.logger.debug("Getting module settings from module status")
        conf = self.status
        if len(conf) == 0 or sum(conf[3:120]) == 0:
            self.displ_contr = 30
            self.displ_time = 120
            self.t_short = 100
            self.t_long = 1000
            self.t_dimm = 1
            self.supply_prio = 230
            self.temp_ctl = 4
            self.temp_1_2 = 1
            return False
        self.hw_version = (
            conf[MirrIdx.MOD_SERIAL : MirrIdx.MOD_SERIAL + 16]
            .decode("iso8859-1")
            .strip()
        )
        self.sw_version = self.module.get_sw_version()
        self.supply_prio = conf[MirrIdx.SUPPLY_PRIO]
        self.displ_contr = conf[MirrIdx.DISPL_CONTR]
        self.displ_time = conf[MirrIdx.MOD_LIGHT_TIM]
        if self.displ_time == 0:
            if self.type == "Smart Controller Mini":
                self.displ_time = 100
        self.temp_ctl = conf[MirrIdx.CLIM_SETTINGS]
        self.temp_1_2 = conf[MirrIdx.TMP_CTL_MD]
        self.t_short = conf[MirrIdx.T_SHORT] * 10
        self.t_long = conf[MirrIdx.T_LONG] * 10
        self.t_dimm = conf[MirrIdx.T_DIM]
        self.is_outdoor = conf[MirrIdx.OUTDOOR_MODE] == 65
        inp_state = int.from_bytes(
            conf[MirrIdx.SWMOD_1_8 : MirrIdx.SWMOD_1_8 + 3], "little"
        )
        ad_state = conf[MirrIdx.STAT_AD24_ACTIVE]
        for inp in self.inputs:
            nmbr = inp.nmbr - 1 + len(self.buttons)
            if inp_state & (0x01 << (nmbr)) > 0:
                inp.type *= 2  # switch
            if ad_state & (0x01 << (nmbr)) > 0:
                inp.type *= 3  # ad input
            if inp.nmbr > 10:
                inp.type *= 3  # dedicated ad input of sc module

        # pylint: disable-next=consider-using-enumerate
        covr_pol = int.from_bytes(
            conf[MirrIdx.COVER_POL : MirrIdx.COVER_POL + 2], "little"
        )
        for c_idx in range(len(self.covers)):
            o_idx = self.cvr_2_out(c_idx)
            if (
                conf[MirrIdx.COVER_SETTINGS] & (0x01 << c_idx) > 0
            ):  # binary flag for shutters
                self.cover_times[c_idx] = interptime_2_covertime(
                    int(conf[MirrIdx.COVER_T + c_idx]),
                    int(conf[MirrIdx.COVER_INTERP + c_idx]),
                )
                self.blade_times[c_idx] = round(int(conf[MirrIdx.BLAD_T + c_idx]) / 10)
                # polarity defined per output, 2 per cover
                polarity = (covr_pol & (0x01 << (2 * c_idx)) == 0) * 2 - 1
                tilt = 1 + (self.blade_times[c_idx] > 0)
                pol = polarity * tilt  # +-1 for shutters, +-2 for blinds
                cname = set_cover_name(self.outputs[o_idx].name.strip())
                self.covers[c_idx] = IoDescriptor(
                    cname.strip(), c_idx + 1, pol, self.outputs[o_idx].area
                )
                self.outputs[o_idx].type = -10  # disable light output
                self.outputs[o_idx + 1].type = -10
        if self.typ[0] == 80:
            # Motion detectors
            self.mov_led = conf[MirrIdx.MOV_LED]
            self.mov_level = conf[MirrIdx.MOV_LVL]
        return True

    def get_pin(self) -> str:
        """Return GSM SIM Pin from smg."""
        p1_idx = SMGIdx.index(MirrIdx.COVER_T)  # 1a
        p3_idx = p1_idx + 3  # 2b
        p4_idx = p1_idx + 6  # 4a
        p2_idx = p3_idx + 3  # 5b
        p1 = int((self.smg[p1_idx] / 9) - 9)
        p2 = int((((self.smg[p2_idx] / 2) + 88) / 10) - 10)
        p3 = int((self.smg[p3_idx] / 7) - 4)
        p4 = int(self.smg[p4_idx])
        if (p1 >= 10) or (p2 >= 10) or (p3 >= 10) or (p4 >= 10):
            self.logger.error(f"Error decoding pin for module {self.id}.")
            return "ERROR"
        return f"{p1}{p2}{p3}{p4}"

    def set_pin(self) -> None:
        """Store GSM SIM Pin to smg."""
        if not self.sim_pin_changed:
            return

        p1_idx = SMGIdx.index(MirrIdx.COVER_T)  # 1a
        p3_idx = p1_idx + 3  # 2b
        p4_idx = p1_idx + 6  # 4a
        p2_idx = p3_idx + 3  # 5b
        p1 = int(self.sim_pin[1])
        p2 = int(self.sim_pin[2])
        p3 = int(self.sim_pin[3])
        p4 = int(self.sim_pin[4])
        ps1 = (p1 + 9) * 9
        ps2 = ((p2 + 10) * 10 - 88) * 2
        ps3 = (p3 + 4) * 7
        ps4 = p4

        self.smg = replace_bytes(
            self.smg,
            int.to_bytes(ps1),
            p1_idx,
        )
        self.smg = replace_bytes(
            self.smg,
            int.to_bytes(ps2),
            p2_idx,
        )
        self.smg = replace_bytes(
            self.smg,
            int.to_bytes(ps3),
            p3_idx,
        )
        self.smg = replace_bytes(
            self.smg,
            int.to_bytes(ps4),
            p4_idx,
        )

    def set_module_settings(self, status: bytes) -> bytes:
        """Restore settings to module status."""
        status = replace_bytes(
            status,
            (self.name + " " * (32 - len(self.name))).encode("iso8859-1"),
            MirrIdx.MOD_NAME,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.displ_contr)),
            MirrIdx.DISPL_CONTR,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.displ_time)),
            MirrIdx.MOD_LIGHT_TIM,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.temp_ctl)),
            MirrIdx.CLIM_SETTINGS,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.temp_1_2)),
            MirrIdx.TMP_CTL_MD,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(float(self.t_short) / 10)),
            MirrIdx.T_SHORT,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(float(self.t_long) / 10)),
            MirrIdx.T_LONG,
        )
        status = replace_bytes(
            status,
            int.to_bytes(int(self.t_dimm)),
            MirrIdx.T_DIM,
        )
        if self.typ[0] == 80:
            status = replace_bytes(
                status,
                int.to_bytes(int(self.mov_level)),
                MirrIdx.MOV_LVL,
            )
            if self.mov_led == 78:
                byte_mov_led = b"N"
            else:
                byte_mov_led = b"J"
            status = replace_bytes(
                status,
                byte_mov_led,
                MirrIdx.MOV_LED,
            )
        if self.supply_prio == "230":
            byte_supply_prio = b"N"
        else:
            byte_supply_prio = b"B"
        status = replace_bytes(
            status,
            byte_supply_prio,
            MirrIdx.SUPPLY_PRIO,
        )
        inp_state = 0
        ad_state = 0
        no_btns = len(self.buttons)
        for inp in self.inputs:
            if abs(inp.type) == 2:  # switch
                inp_state = inp_state | (0x01 << (inp.nmbr + no_btns - 1))
            if abs(inp.type) == 3:  # analog
                ad_state = ad_state | (0x01 << (inp.nmbr + no_btns - 1))
                ad_state = ad_state & 0xFF
        inp_bytes = (
            chr(inp_state & 0xFF)
            + chr((inp_state >> 8) & 0xFF)
            + chr((inp_state >> 16) & 0xFF)
        ).encode("iso8859-1")
        status = replace_bytes(
            status,
            inp_bytes,
            MirrIdx.SWMOD_1_8,
        )
        status = replace_bytes(status, int.to_bytes(ad_state), MirrIdx.STAT_AD24_ACTIVE)
        outp_state = 0
        covr_pol = 0
        for c_idx in range(len(self.covers)):
            o_idx = self.cvr_2_out(c_idx)
            if self.outputs[o_idx].type == -10:
                outp_state = outp_state | (0x01 << int(c_idx))
            t_interp, interp_val = covertime_2_interptime(self.cover_times[c_idx])
            status = replace_bytes(
                status,
                int.to_bytes(t_interp),
                MirrIdx.COVER_T + c_idx,
            )
            status = replace_bytes(
                status,
                int.to_bytes(interp_val),
                MirrIdx.COVER_INTERP + c_idx,
            )
            status = replace_bytes(
                status,
                int.to_bytes(int(self.blade_times[c_idx] * 10)),
                MirrIdx.BLAD_T + c_idx,
            )
            if self.covers[c_idx].type < 0:
                covr_pol = covr_pol | (0x01 << (2 * c_idx))
            else:
                covr_pol = covr_pol | (0x01 << (2 * c_idx + 1))

        outp_bytes = (chr(outp_state & 0xFF)).encode("iso8859-1")
        status = replace_bytes(
            status,
            outp_bytes,
            MirrIdx.COVER_SETTINGS,
        )
        status = replace_bytes(
            status,
            f"{chr(covr_pol & 0xFF)}{chr(covr_pol >> 8)}".encode("iso8859-1"),
            MirrIdx.COVER_POL,
        )

        # Clear all logic entries mode
        status = replace_bytes(
            status,
            b"\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00",
            MirrIdx.LOGIC,
        )
        for cnt in self.counters:
            status = replace_bytes(
                status,
                b"\x05" + int.to_bytes(cnt.type),  # type 5 counter + max_count
                MirrIdx.LOGIC + 3 * (cnt.nmbr - 1),
            )
        for lgk in self.logic:
            status = replace_bytes(
                status,
                int.to_bytes(lgk.type) + int.to_bytes(lgk.inputs),  # type + no_inputs
                MirrIdx.LOGIC + 3 * (lgk.nmbr - 1),
            )
        if self.typ == b"\x1e\x03":  # Smart GSM
            self.logger.info(f"SIM Pin: {self.sim_pin}")
            self.set_pin()  # to smg
        if self.typ == b"\x32\x28":  # Smart Sensor
            if self.is_outdoor:
                stat_byte = b"A"
            else:
                stat_byte = b"U"
            status = replace_bytes(status, stat_byte, MirrIdx.OUTDOOR_MODE)
        return status

    def get_names(self) -> bool:
        """Get names of entities from list, initialize interfaces."""

        self.logger.debug("Getting module names from list")
        self.all_fingers = {}
        list = self.list
        no_lines = int.from_bytes(list[:2], "little")
        list = list[4 : len(list)]  # Strip 4 header bytes
        if len(list) == 0:
            return False
        for _ in range(no_lines):
            if list == b"":
                break
            line_len = int(list[5]) + 5
            line = list[0:line_len]
            event_code = int(line[2])
            if event_code == 235:  # Beschriftung
                text = line[8:]
                text = text.decode("iso8859-1")
                text = text.strip()
                arg_code = int(line[3])
                if int(line[0]) == 252:
                    # Finger users: user, bitmap of fingers as type
                    user_id = int(line[1])
                    user_enabled = (int(line[4]) & 0x80) > 0
                    f_map = (int(line[4]) & 0x7F) * 256 + int(line[3])
                    if user_enabled:
                        self.users.append(IfDescriptor(text, user_id, f_map))
                    else:
                        self.users.append(IfDescriptor(text, user_id, f_map * (-1)))
                    self.all_fingers[user_id] = []
                    for fi in range(10):
                        if f_map & (1 << fi):
                            self.all_fingers[user_id].append(
                                IfDescriptor(FingerNames[fi + 1], fi + 1, user_id)
                            )
                elif int(line[0]) == 253:
                    # Description of commands
                    self.dir_cmds.append(IfDescriptor(text, arg_code, 0))
                elif int(line[0]) == 254:
                    # Description of messages with lang code
                    if self.type == "Smart GSM":
                        self.gsm_numbers.append(IfDescriptor(text, arg_code, line[4]))
                    else:
                        self.messages.append(IfDescriptor(text, arg_code, line[4]))
                elif int(line[0]) == 255:
                    try:
                        if self.type == "Smart GSM":
                            self.gsm_messages.append(
                                IfDescriptor(text, arg_code, line[4])
                            )
                        elif arg_code in range(10, 18):
                            if self.type == "Smart Controller Mini":
                                if arg_code in range(10, 12):
                                    self.buttons[arg_code - 10] = IfDescriptor(
                                        text, arg_code - 9, 1
                                    )
                            elif self.type[:16] == "Smart Controller":
                                # Description of module buttons
                                self.buttons[arg_code - 10] = IfDescriptor(
                                    text, arg_code - 9, 1
                                )
                            elif self.type == "Smart Sensor":
                                pass
                            else:
                                self.inputs[arg_code - 10].name = text
                                self.inputs[arg_code - 10].nmbr = arg_code - 9
                                if int(line[1]) > 0:
                                    self.inputs[arg_code - 10].area = int(line[1])
                        elif arg_code in range(18, 26):
                            # Description of module LEDs
                            self.leds[arg_code - 17] = IfDescriptor(
                                text, arg_code - 17, 0
                            )
                        elif arg_code in range(40, 52):
                            # Description of Inputs
                            if self.type == "Smart Controller Mini":
                                if arg_code in range(44, 48):
                                    self.inputs[arg_code - 44].name = text
                                    self.inputs[arg_code - 44].nmbr = arg_code - 43
                                    # Set area index, where included, else apply module area later
                                    if int(line[1]) > 0:
                                        self.inputs[arg_code - 44].area = int(line[1])
                            else:  # sc inputs 24V
                                self.inputs[arg_code - 40].name = text
                                self.inputs[arg_code - 40].nmbr = arg_code - 39
                                # Set area index, where included, else apply module area later
                                if int(line[1]) > 0:
                                    self.inputs[arg_code - 40].area = int(line[1])

                        elif arg_code in range(110, 120):
                            # Description of counters
                            for cnt in self.counters:
                                if cnt.nmbr == arg_code - 109:
                                    cnt.name = text
                                    break
                            # Description of logic units
                            for lgc in self.logic:
                                if lgc.nmbr == arg_code - 109:
                                    lgc.name = text
                                    break
                        elif arg_code in range(120, 136):
                            # Description of flags
                            self.flags.append(IfDescriptor(text, arg_code - 119, 0))
                        elif arg_code == 136:
                            # Description of module area
                            self.area_member = line[1]
                        elif arg_code in range(140, 173):
                            # Description of vis commands (max 32)
                            self.vis_cmds.append(
                                IfDescriptor(
                                    text[2:], ord(text[1]) * 256 + ord(text[0]), 0
                                )
                            )
                        elif self.type[0:9] == "Smart Out":
                            # Description of outputs in Out modules
                            self.outputs[arg_code - 60] = IoDescriptor(
                                text, arg_code - 59, 1
                            )
                            # Set area index, where included, else apply module area later
                            if int(line[1]) > 0:
                                self.outputs[arg_code - 60].area = int(line[1])
                        else:
                            # Description of outputs
                            self.outputs[arg_code - 60].name = text
                            if int(line[1]) > 0:
                                self.outputs[arg_code - 60].area = int(line[1])
                    except Exception as err_msg:
                        self.logger.error(
                            f"Parsing of names for module {self.name} failed: {err_msg}: Code {arg_code}, Text {text}"
                        )

            list = list[line_len : len(list)]  # Strip processed line

        if self.type == "Smart Controller Mini":
            self.leds[0].name = "Ambient"
            self.leds[0].nmbr = 0
            return True
        if self.type[:16] == "Smart Controller":
            self.dimmers[0].name = self.outputs[10].name
            self.dimmers[1].name = self.outputs[11].name
            self.outputs[10].type = 2
            self.outputs[11].type = 2
            self.leds[0].name = "Nachtlicht"
            self.leds[0].nmbr = 0
            return True
        if self.type[:10] == "Smart Dimm":
            self.dimmers[0].name = self.outputs[0].name
            self.dimmers[1].name = self.outputs[1].name
            self.dimmers[2].name = self.outputs[2].name
            self.dimmers[3].name = self.outputs[3].name
            self.outputs[0].type = 2
            self.outputs[1].type = 2
            self.outputs[2].type = 2
            self.outputs[3].type = 2
            return True
        if self.type == "Fanekey":
            self.users_sel = 0
            self.module.org_fingers = dpcopy(
                self.all_fingers
            )  # stores the active settings
            if len(self.users) > 0:
                self.fingers = self.all_fingers[self.users[self.users_sel].nmbr]
            return True
        return False

    def get_descriptions(self) -> str | None:
        """Get descriptions of commands, etc."""

        self.save_desc_file_needed = False
        self.upload_desc_info_needed = False

        self.logger.debug("Getting router descriptions")
        # Settings for automations must also include global entities
        rtr_desc = self.module.get_rtr().descriptions
        for desc in rtr_desc:
            if desc.type == 3:  # global flg (Merker)
                self.glob_flags.append(IfDescriptor(desc.name, desc.nmbr, 0))
            elif desc.type == 4:  # collective commands (Sammelbefehle)
                self.coll_cmds.append(IfDescriptor(desc.name, desc.nmbr, 0))

        if (len(self.counters) > 0) and ("counters" not in self.prop_keys):
            self.properties["counters"] = len(self.counters)
            self.properties["no_keys"] += 1
            self.prop_keys.append("counters")
        if (len(self.logic) > 0) and ("logic" not in self.prop_keys):
            self.properties["logic"] = len(self.logic)
            self.properties["no_keys"] += 1
            self.prop_keys.append("logic")
        if (len(self.flags) > 0) and ("flags" not in self.prop_keys):
            self.properties["flags"] = len(self.flags)
            self.properties["no_keys"] += 1
            self.prop_keys.append("flags")
        if (len(self.dir_cmds) > 0) and ("dir_cmds" not in self.prop_keys):
            self.properties["dir_cmds"] = len(self.dir_cmds)
            self.properties["no_keys"] += 1
            self.prop_keys.append("dir_cmds")
        if (len(self.vis_cmds) > 0) and ("vis_cmds" not in self.prop_keys):
            self.properties["vis_cmds"] = len(self.vis_cmds)
            self.properties["no_keys"] += 1
            self.prop_keys.append("vis_cmds")
        if (len(self.users) > 0) and ("users" not in self.prop_keys):
            self.properties["users"] = len(self.users)
            self.properties["no_keys"] += 1
            self.prop_keys.append("users")

    def get_counter_numbers(self) -> list[int]:
        """Return counter numbers."""
        cnt_nos = []
        for cnt in self.counters:
            cnt_nos.append(cnt.nmbr)
        return cnt_nos

    def get_logic_numbers(self) -> list[int]:
        """Return logic unit numbers."""
        lgc_nos = []
        for lgc in self.logic:
            lgc_nos.append(lgc.nmbr)
        return lgc_nos

    def get_modes(self):
        """Return all mode strings as list."""
        modes_list1 = [
            "Immer",
            "Abwesend",
            "Anwesend",
            "Schlafen",
            f"{self.module.rt.user_modes[1:11].decode('iso8859-1').strip()}",
            f"{self.module.rt.user_modes[12:].decode('iso8859-1').strip()}",
            "Urlaub",
            "'Tag'/'Nacht'/'Alarm'",
        ]
        mode_list2 = ["Immer", "Tag", "Nacht", "Alarm"]
        return modes_list1, mode_list2

    def format_smc(self, buf: bytes) -> str:
        """Parse line structure and add ';' and linefeeds."""
        if len(buf) < 5:
            return "00;00;00;00;\n"
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

    async def update_ekey_entries(self):
        """Check for differences in users/fingers and delete if needed."""
        if "org_fingers" not in dir(self.module):
            self.module.org_fingers = {}
        org_fingers = self.module.org_fingers
        new_fingers = self.all_fingers
        usr_nmbrs = []
        for u_i in range(len(self.users)):
            usr_nmbrs.append(self.users[u_i].nmbr)
        for usr_id in org_fingers.keys():
            if usr_id not in new_fingers.keys():
                # user missing, must be deleted
                self.response = await self.module.hdlr.del_ekey_entry(usr_id, 255)
                self.logger.info(f"User {usr_id} deleted from ekey data base")
            else:
                # user found
                new_usr_fngr_ids = []
                for fngr_idx in range(len(new_fingers[usr_id])):
                    # get all defined finger ids of user after editing
                    new_usr_fngr_ids.append(new_fingers[usr_id][fngr_idx].nmbr)
                for fngr_idx in range(len(org_fingers[usr_id])):
                    org_finger = org_fingers[usr_id][fngr_idx].nmbr
                    if org_finger not in new_usr_fngr_ids:
                        # finger id of user before editing not found: delete
                        self.response = await self.module.hdlr.del_ekey_entry(
                            usr_id, org_finger
                        )
                        self.logger.info(
                            f"Finger {org_finger} of user {usr_id} deleted from ekey data base"
                        )
        # all user and/or finger deletions done
        for usr_id in new_fingers.keys():
            f_msk = 0
            for fngr in new_fingers[usr_id]:
                # create finger mask
                f_msk = f_msk | 1 << (fngr.nmbr - 1)
            self.users[usr_nmbrs.index(usr_id)].type = f_msk * int(
                math.copysign(1, self.users[usr_nmbrs.index(usr_id)].type)
            )

    async def set_automations(self):
        """Store automation entries to list and send to module."""
        list_lines = self.format_smc(self.list).split("\n")

        new_list = []
        new_line = ""
        for lchr in list_lines[0].split(";")[:-1]:
            new_line += chr(int(lchr))
        new_list.append(new_line)

        # insert automations
        automations = self.automtns_def
        for atmn in automations.local:
            if atmn.src_rt == 0:
                new_list.append(atmn.make_definition())
        for atmn in automations.external:
            new_list.append(atmn.make_definition())
        for atmn in automations.forward:
            new_list.append(atmn.make_definition())
        for atmn in automations.local:
            if atmn.src_rt != 0:
                new_list.append(atmn.make_definition())

        # copy rest of list
        for line in list_lines[1:]:
            if len(line) > 0:
                tok = line.split(";")
                if tok[0] in ["252", "253", "254", "255"]:
                    new_line = ""
                    for lchr in line.split(";")[:-1]:
                        new_line += chr(int(lchr))
                    new_list.append(new_line)
        return self.adapt_list_header(new_list)

    async def set_list(self) -> bytes:
        """Store config entries to new list, (await for ekey entries update)."""
        list_lines = self.format_smc(self.list).split("\n")
        if self.module._typ == b"\x1e\x01":
            await self.update_ekey_entries()

        new_list: list[str] = []
        new_line = ""
        for lchr in list_lines[0].split(";")[:-1]:
            new_line += chr(int(lchr))
        new_list.append(new_line)

        for line in list_lines[1:]:
            if len(line) > 0:
                tok = line.split(";")
                if tok[0] not in ["252", "253", "254", "255"]:
                    # copy other lines
                    new_line = ""
                    for lchr in line.split(";")[:-1]:
                        new_line += chr(int(lchr))
                    new_list.append(new_line)
        for dir_cmd in self.dir_cmds:
            desc = dir_cmd.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                desc = desc[:32]
                new_list.append(f"\xfd\0\xeb{chr(dir_cmd.nmbr)}\1\x23\0\xeb" + desc)
        for msg in self.messages:
            desc = msg.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                desc = desc[:32]
                new_list.append(
                    f"\xfe\0\xeb{chr(msg.nmbr)}{chr(msg.type)}\x23\0\xeb" + desc
                )
        for btn in self.buttons:
            desc = btn.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                desc = desc[:32]
                new_list.append(f"\xff\0\xeb{chr(9 + btn.nmbr)}\1\x23\0\xeb" + desc)
        for led in self.leds:
            if led.nmbr > 0:
                desc = led.name
                if len(desc.strip()) > 0:
                    desc += " " * (32 - len(desc))
                    desc = desc[:32]
                    new_list.append(
                        f"\xff\0\xeb{chr(17 + led.nmbr)}\1\x23\0\xeb" + desc
                    )
        if self.module._typ[0] == 1 or self.module._typ == b"\x32\x01":
            inpt_offs = 39
        else:
            inpt_offs = 9
        for inpt in self.inputs:
            desc = inpt.name
            if len(desc.strip()) > 0 or self.module._typ[0] == 11:
                # for input modules prepare all 8 lines
                desc += " " * (32 - len(desc))
                desc = desc[:32]
                new_list.append(
                    f"\xff{chr(inpt.area)}\xeb{chr(inpt_offs + inpt.nmbr)}\x01\x23\0\xeb"
                    + desc
                )
        for outpt in self.outputs:
            desc = outpt.name
            if len(desc.strip()) > 0:
                desc += " " * (32 - len(desc))
                desc = desc[:32]
                new_list.append(
                    f"\xff{chr(outpt.area)}\xeb{chr(59 + outpt.nmbr)}\1\x23\0\xeb"
                    + desc
                )
        for cnt in self.counters:
            desc = cnt.name
            desc += " " * (32 - len(desc))
            desc = desc[:32]
            new_list.append(f"\xff\0\xeb{chr(109 + cnt.nmbr)}\1\x23\0\xeb" + desc)
        for lgc in self.logic:
            desc = lgc.name
            desc += " " * (32 - len(desc))
            desc = desc[:32]
            new_list.append(f"\xff\0\xeb{chr(109 + lgc.nmbr)}\1\x23\0\xeb" + desc)
        for flg in self.flags:
            desc = flg.name
            desc += " " * (32 - len(desc))
            desc = desc[:32]
            new_list.append(f"\xff\0\xeb{chr(119 + flg.nmbr)}\1\x23\0\xeb" + desc)
        cnt = 0
        for vis in self.vis_cmds:
            desc = vis.name
            desc += " " * (30 - len(desc))
            desc = desc[:30]
            n_high = chr(vis.nmbr >> 8)
            n_low = chr(vis.nmbr & 0xFF)
            new_list.append(
                f"\xff\0\xeb{chr(140 + cnt)}\1\x23\0\xeb" + n_low + n_high + desc
            )
            cnt += 1
        for uid in self.users:
            desc = uid.name
            fgr_low = abs(uid.type) & 0xFF
            fgr_high = abs(uid.type) >> 8
            if uid.type > 0:
                # set enable bit
                fgr_high += 0x80
            desc += " " * (32 - len(desc))
            desc = desc[:32]
            new_list.append(
                f"\xfc{chr(uid.nmbr)}\xeb{chr(fgr_low)}{chr(fgr_high)}\x23\0\xeb" + desc
            )
        for nr in self.gsm_numbers:
            desc = nr.name
            desc += " " * (32 - len(desc))
            new_list.append(f"\xfe\0\xeb{chr(nr.nmbr)}\x01\x23\0\xeb" + desc)
        for msg in self.gsm_messages:
            desc = msg.name
            desc += " " * (32 - len(desc))
            new_list.append(f"\xff\0\xeb{chr(msg.nmbr)}\x01\x23\0\xeb" + desc)
        # append area member @ 136
        desc = self.module.get_area_name()
        desc += " " * (32 - len(desc))
        new_list.append(
            f"\xff{chr(self.area_member)}\xeb{chr(136)}\x01\x23\0\xeb" + desc
        )
        return self.adapt_list_header(new_list)

    def adapt_list_header(self, new_list: list[str]) -> bytes:
        """Adapt line and char numbers in header, sort, and return as byte."""
        if self.typ[0] != 11:  # don't sort Smart In 230, 24, 24-1
            sort_list = new_list[1:]
            sort_list.sort()
            new_list[1:] = sort_list
        no_lines = len(new_list) - 1
        no_chars = 0
        for line in new_list:
            no_chars += len(line)
        new_list[0] = (
            f"{chr(no_lines & 0xFF)}{chr(no_lines >> 8)}{chr(no_chars & 0xFF)}{chr(no_chars >> 8)}"
        )
        list_bytes = ""
        for line in new_list:
            list_bytes += line
        list_bytes = list_bytes.encode("iso8859-1")
        return list_bytes

    async def teach_new_finger(self, app, user_id: int, finger_id: int, time: int):
        """Teach new finger and add to fingers."""
        settings = app["settings"]
        res = await settings.module.hdlr.set_ekey_teach_mode(user_id, finger_id, time)
        if res == "OK":
            settings.all_fingers[user_id].append(
                IfDescriptor(FingerNames[finger_id], finger_id, user_id)
            )
            app["settings"] = settings

    def out_2_cvr(self, o_no: int) -> int:
        """Convert output to cover number based on module type, 0-based."""
        c_no = int(o_no / 2)
        if self.typ[0] != 1:
            return c_no
        c_no -= 2
        if c_no < 0:
            c_no += 5
        return c_no

    def cvr_2_out(self, c_no: int) -> int:
        """Convert cover to output number based on module type, 0-based"""
        o_no = c_no * 2
        if self.typ[0] != 1:
            return o_no
        o_no += 4
        if c_no > 2:
            o_no -= 10
        return o_no

    def unit_not_exists(self, mod_units: list[IfDescriptor], entry_no: int) -> bool:
        """Check for existing unit based on number."""
        for exist_unit in mod_units:
            if exist_unit.nmbr == entry_no:
                return False
        return True

    def get_interf_name(
        self, interfs: list[IfDescriptor], nmbr: int, default: str = ""
    ) -> str:
        """Return name of interface given its number."""

        for interf in interfs:
            if interf.nmbr == nmbr:
                return interf.name
        return default


class ModuleSettingsLight(ModuleSettings):
    """Object with all module settings, without automations."""

    def __init__(self, module):
        """Fill all properties with module's values."""
        self.id = module._id
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialzing module settings object")
        self.module = module
        self.name = dpcopy(module._name)
        self.typ = module._typ
        self.type = module._type
        self.list = dpcopy(module.list)
        self.status = dpcopy(module.status)
        self.smg = dpcopy(module.build_smg())
        # self.desc = dpcopy(module.get_rtr().descriptions)
        self.properties: dict = module.io_properties
        self.prop_keys = module.io_prop_keys
        self.area_member = 0
        self.cover_times = [0, 0, 0, 0, 0]
        self.blade_times = [0, 0, 0, 0, 0]
        self.user1_name = module.get_rtr().user_modes[1:11].decode("iso8859-1").strip()
        self.user2_name = module.get_rtr().user_modes[12:].decode("iso8859-1").strip()
        self.save_desc_file_needed: bool = False
        self.upload_desc_info_needed: bool = False
        self.group = dpcopy(module.get_group())
        self.get_io_interfaces()
        self.get_logic()
        self.get_names()
        self.get_settings()
        # self.get_descriptions()


class RouterSettings:
    """Object with all router settings."""

    def __init__(self, rtr):
        """Fill all properties with module's values."""
        self.id = rtr._id
        self.name = rtr._name
        self.type = "Smart Router"
        self.typ = b"\0\0"  # to distinguish from modules
        self.status = rtr.status
        self.smr = rtr.smr
        self.logger = logging.getLogger(__name__)
        self.channels = rtr.channels
        self.timeout = rtr.timeout[0] * 10
        self.cov_autostop_cnt = 1
        self.mode_dependencies = rtr.mode_dependencies[1:]
        self.user_modes = rtr.user_modes
        self.serial = rtr.serial
        self.day_night = rtr.day_night
        self.version = rtr.version
        self.user1_name = rtr.user_modes[1:11].decode("iso8859-1").strip()
        self.user2_name = rtr.user_modes[12:].decode("iso8859-1").strip()
        self.glob_flags: list[IfDescriptor] = []
        self.groups: list[IfDescriptor] = []
        self.coll_cmds: list[IfDescriptor] = []
        self.areas: list[IfDescriptor] = []
        self.chan_list = []
        self.module_grp = []
        self.max_group = 0
        self.get_definitions()
        self.get_rtr_descriptions(rtr)
        self.get_day_night()
        self.properties: dict = rtr.properties
        self.prop_keys = rtr.prop_keys

    def get_definitions(self) -> None:
        """Parse router smr info and set values."""
        # self.group_list = []
        if len(self.smr) == 0:
            return
        ptr = 1
        max_mod_no = 0
        for ch_i in range(4):
            count = self.smr[ptr]
            self.chan_list.append(sorted(self.smr[ptr + 1 : ptr + count + 1]))
            # pylint: disable-next=nested-min-max
            if count > 0:
                max_mod_no = max(max_mod_no, *self.chan_list[ch_i])
            ptr += 1 + count
        ptr += 2
        grp_cnt = self.smr[ptr - 1]
        self.max_group = max(list(self.smr[ptr : ptr + grp_cnt]))
        # self.group_list: list[int] = [[]] * (max_group + 1)
        for mod_i in range(max_mod_no):
            grp_no = int(self.smr[ptr + mod_i])
            self.module_grp.append(grp_no)
        ptr += 2 * grp_cnt + 1  # groups, group dependencies, timeout
        str_len = self.smr[ptr]
        self.name = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.user1_name = (
            self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        )
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.user2_name = (
            self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        )
        ptr += str_len + 1
        str_len = self.smr[ptr]
        self.serial = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()
        ptr += str_len + 71  # Korr von Hand, vorher 71 + 1
        str_len = self.smr[ptr]
        self.version = self.smr[ptr + 1 : ptr + 1 + str_len].decode("iso8859-1").strip()

    def get_rtr_descriptions(self, rtr) -> None:
        """Get descriptions of commands, etc."""

        for desc in rtr.descriptions:
            if desc.type == 1:  # FF 0A: areas
                self.areas.append(desc)
            elif desc.type == 2:  # FF 07: group names
                self.groups.append(desc)
            elif desc.type == 3:  # global flg (Merker)
                self.glob_flags.append(desc)
            elif desc.type == 4:  # FF 03: collective commands (Sammelbefehle)
                self.coll_cmds.append(desc)
            elif desc.type == 5:  # FF 08: alarm commands
                pass
            self.cov_autostop_cnt = rtr.cov_autostop_cnt
        if len(self.groups) == 0:
            self.groups.append(IfDescriptor("general", 0, 0))
        if len(self.areas) == 0:
            self.areas.append(IfDescriptor("House", 1, 0))

    def set_rtr_descriptions(self) -> tuple[list[IfDescriptor], int]:
        """Collect descriptions for router."""
        desc = []
        for area in self.areas:
            desc.append(IfDescriptor(area.name, area.nmbr, 1))
        for grp in self.groups:
            desc.append(IfDescriptor(grp.name, grp.nmbr, 2))
        for flg in self.glob_flags:
            desc.append(IfDescriptor(flg.name, flg.nmbr, 3))
        for cmd in self.coll_cmds:
            desc.append(IfDescriptor(cmd.name, cmd.nmbr, 4))
        return desc, self.cov_autostop_cnt

    def get_day_night(self) -> None:
        """Prepare day and night table."""
        self.day_sched: list[dict[str, int]] = []
        self.night_sched: list[dict[str, int]] = []
        ptr = 1
        for day in range(14):
            setting: dict[str, int] = {}
            setting["hour"] = self.day_night[ptr]
            setting["minute"] = self.day_night[ptr + 1]
            setting["light"] = self.day_night[ptr + 2]
            if setting["hour"] == 24:
                setting["mode"] = -1
            elif setting["light"] == 0:
                setting["mode"] = 0
            else:
                setting["mode"] = self.day_night[ptr + 3]
            setting["module"] = self.day_night[ptr + 4]
            self.day_sched.append(setting)
            ptr += 5
        self.night_sched = self.day_sched[7:]
        self.day_sched = self.day_sched[:7]

    def set_day_night(self) -> None:
        """Prepare day and night table."""
        day_night_str = chr(self.day_night[0])
        for day in range(14):
            if day < 7:
                sched = self.day_sched
                di = day
            else:
                sched = self.night_sched
                di = day - 7
            if sched[di]["mode"] != -1:
                day_night_str += chr(sched[di]["hour"])
            else:
                day_night_str += chr(24)
            day_night_str += chr(sched[di]["minute"])
            if sched[di]["mode"] > 0:
                day_night_str += chr(sched[di]["light"])
            else:
                day_night_str += chr(0)
            if sched[di]["mode"] > 0:
                day_night_str += chr(sched[di]["mode"])
            else:
                day_night_str += chr(0)
            day_night_str += chr(sched[di]["module"])
        self.day_night = day_night_str.encode("iso8859-1")


def replace_bytes(in_bytes: bytes, repl_bytes: bytes, idx: int) -> bytes:
    """Replaces bytes array from idx:idx+len(repl_bytes)."""
    return in_bytes[:idx] + repl_bytes + in_bytes[idx + len(repl_bytes) :]


def set_cover_output_name(old_name, new_name, state):
    """ "Set output name accdording to cover's name."""
    up_names = ["auf", "auf", "hoch", "öffnen", "up", "open"]
    dwn_names = ["ab", "zu", "runter", "schließen", "down", "close"]
    if len(old_name.split()) > 1:
        pf = old_name.split()[-1]
        base = old_name.replace(pf, "").strip()
        if pf in up_names:
            pf_idx = up_names.index(pf)
        elif pf in dwn_names:
            pf_idx = dwn_names.index(pf)
        else:
            pf_idx = 0
            base = old_name
    else:
        pf_idx = 0
        base = old_name
    pf_names = [up_names[pf_idx], dwn_names[pf_idx]]
    if new_name is not None:
        base = new_name
    if state == "up":
        return base + f" {pf_names[0]}"
    return base + f" {pf_names[1]}"


def set_cover_name(out_name):
    """Strip postfix from output name."""
    up_names = ["auf", "auf", "hoch", "öffnen", "up", "open"]
    dwn_names = ["ab", "zu", "runter", "schließen", "down", "close"]
    base = out_name
    for pf in up_names:
        base = base.replace(pf, "")
    for pf in dwn_names:
        base = base.replace(pf, "")
    return base.strip()
