const prio_trg = new Set([4])
const flag_trg = new Set([6])
const logic_trg = new Set([8])
const count_trg = new Set([9])
const output_trg = new Set([10])
const dimmval_trg = new Set([15])
const cover_trg = new Set([17])
const remote_trg = new Set([23])
const perc_trg = new Set([30])
const viscmd_trg = new Set([31])
const move_trg = new Set([40, 41])
const collcmd_trg = new Set([50])
const mode_trg = new Set([137])
const dimm_trg = new Set([149])
const button_trg = new Set([150, 151, 154])
const switch_trg = new Set([152, 153])
const ekey_trg = new Set([169])
const time_trg = new Set([170])
const sensor_trg = new Set([201, 202, 203, 204, 205, 206, 213, 214, 215, 216, 217])
const ad_trg = new Set([218, 219, 224, 225, 226, 227])
const temp_sens = new Set([201, 213])
const perc_sens = new Set([202, 215, 217])
const light_sens = new Set([203, 216])
const wind_sens = new Set([204])
const rain_sens = new Set([205])
const windpk_sens = new Set([206])
const ad_sens = new Set([218, 219])
const climate_trg = new Set([220, 221, 222])
const sys_trg = new Set([12, 101, 249])
const dircmd_trg = new Set([253])

function initTrigElements(trg_code, trg_arg1, trg_arg2, trg_time) {
    if (button_trg.has(trg_code)) {
        setElement("trigger-select", 150);
        setElement("button-select", trg_arg1);
        setElement("shortlong-select", trg_code - 149);
    }
    else if (prio_trg.has(trg_code)) {
        setElement("trigger-select", 4);
        setElement("number-select", trg_arg1);
        setElement("prio-chng-vals", trg_arg2);
    }
    else if (switch_trg.has(trg_code)) {
        setElement("trigger-select", 152);
        setElement("switch-select", trg_arg1);
        setElement("onoff-select", trg_code - 151);
    }
    else if (dimmval_trg.has(trg_code)) {
        setElement("trigger-select", 15);
        dim_md = Math.round(trg_arg1 / 10) * 10;
        dim_no = trg_arg1 - dim_md;
        setElement("dimmer-select", dim_no);
        setElement("covpos-select", dim_md);
        setElement("cov_pos_val", trg_arg2);
    }
    else if (cover_trg.has(trg_code)) {
        setElement("trigger-select", 17);
        cov_md = Math.round(trg_arg1 / 10) * 10;
        cov_no = trg_arg1 - cov_md;
        setElement("cover-select", cov_no);
        setElement("covpos-select", cov_md);
        setElement("cov_pos_val", trg_arg2);
    }
    else if (dimm_trg.has(trg_code)) {
        setElement("trigger-select", 149);
        setElement("button-select", trg_arg1);
    }
    else if (remote_trg.has(trg_code)) {
        setElement("trigger-select", 23);
        setElement("ir-high", trg_arg1);
        setElement("ir-low", trg_arg2);
    }
    else if (output_trg.has(trg_code)) {
        setElement("trigger-select", 10);
        setElement("output-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("onoff-select", 1);
        else
            setElement("onoff-select", 2);
    }
    else if (climate_trg.has(trg_code)) {
        setElement("trigger-select", 220);
        setElement("clim-sens-select", trg_code - 220);
        setElement("clim-mode-select", trg_arg1);
    }
    else if (dircmd_trg.has(trg_code)) {
        setElement("trigger-select", 253);
        setElement("dircmd-select", trg_arg1);
    }
    else if (collcmd_trg.has(trg_code)) {
        setElement("trigger-select", 50);
        setElement("collcmd-select", trg_arg1);
    }
    else if (perc_trg.has(trg_code)) {
        setElement("trigger-select", 30);
        setElement("number-select", trg_arg1);
    }
    else if (viscmd_trg.has(trg_code)) {
        setElement("trigger-select", 31);
        setElement("viscmd-select", trg_arg1 * 256 + trg_arg2);
    }
    else if (flag_trg.has(trg_code)) {
        setElement("trigger-select", 6);
        setElement("flag-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("flag2-select", 1);
        else
            setElement("flag2-select", 2);
    }
    else if (logic_trg.has(trg_code)) {
        setElement("trigger-select", 8);
        setElement("logic-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("logic2-select", 1);
        else
            setElement("logic2-select", 2);
    }
    else if (mode_trg.has(trg_code)) {
        setElement("trigger-select", 137);
        setElement("mode-select", trg_arg2 & 0xF8);
        setElement("mode2-select", trg_arg2 & 0x07);
    }
    else if (ekey_trg.has(trg_code)) {
        setElement("trigger-select", 169);
        setEkeyUser(trg_arg1);
        setElement("finger-select", trg_arg2);
    }
    else if (move_trg.has(trg_code)) {
        setElement("trigger-select", 40);
        if (trg_arg2 == 0) {
            setElement("mov-select", 0);
            setElement("mov-intens", trg_arg1);
        }
        else {
            setElement("mov-select", trg_code - 39);
            setElement("mov-intens", trg_arg1);
            setElement("mov-light", trg_arg2 * 10);
        }

    }
    else if (sensor_trg.has(trg_code)) {
        setElement("trigger-select", 203);
        setElement("sensor-select", trg_code);
        if (temp_sens.has(trg_code)) {
            setElement("sens-low-temp", u2sign7(trg_arg1));
            setElement("sens-high-temp", u2sign7(trg_arg2));
        }
        if (perc_sens.has(trg_code)) {
            setElement("sens-low-perc", trg_arg1);
            setElement("sens-high-perc", trg_arg2);
        }
        if (light_sens.has(trg_code)) {
            setElement("sens-low-lux", trg_arg1 * 10);
            setElement("sens-high-lux", trg_arg2 * 10);
        }
        if (wind_sens.has(trg_code)) {
            setElement("sens-low-wind", trg_arg1);
            setElement("sens-high-wind", trg_arg2);
        }
        if (windpk_sens.has(trg_code)) {
            setElement("sens-low-wind", trg_arg1);
            setElement("sens-high-wind", trg_arg2);
        }
        if (rain_sens.has(trg_code)) {
            setElement("rain-select", trg_arg1);
        }
    }
    else if (ad_trg.has(trg_code)) {
        setElement("trigger-select", 218);
        setElement("ad-select", trg_code);
        setElement("sens-low-ad", trg_arg1 / 25);
        setElement("sens-high-ad", trg_arg2 / 25);
    }
    else if (count_trg.has(trg_code)) {
        setElement("trigger-select", 9);
        var counter_no = Math.floor((trg_arg1 - 96) / 16);
        var count_val = trg_arg1 - 95 - counter_no * 16
        setElement("counter-select", counter_no + 1);
        setElement("count-vals", count_val);
    }
    else if (time_trg.has(trg_code)) {
        setElement("trigger-select", 170);
        setElement("day-vals", trg_arg1);
        setElement("month-vals", trg_arg2);
        setElement("time-vals", trg_time);
    }
    else if (sys_trg.has(trg_code)) {
        setElement("trigger-select", 249);
        setElement("sys-select", trg_code);
        if (trg_code == 12) {
            setElement("supply-select", trg_arg1);
        }
        else if (trg_code == 101) {
            setElement("syserr-no", trg_arg1 * 256 + trg_arg2);
        }
    }
    trig_sel.dispatchEvent(new Event("change"));
}

function setTriggerSels() {
    var idx = trig_sel.selectedIndex
    var selectn = trig_sel[idx].value
    setElementVisibility("button-select", "hidden");
    setElementVisibility("switch-select", "hidden");
    setElementVisibility("output-select", "hidden");
    setElementVisibility("flag-select", "hidden");
    setElementVisibility("flag2-select", "hidden");
    setElementVisibility("logic-select", "hidden");
    setElementVisibility("logic2-select", "hidden");
    setElementVisibility("mode-select", "hidden");
    setElementVisibility("mode2-select", "hidden");
    setElementVisibility("viscmd-select", "hidden");
    setElementVisibility("collcmd-select", "hidden");
    setElementVisibility("dircmd-select", "hidden");
    setElementVisibility("sensor-select", "hidden");
    setElementVisibility("ad-select", "hidden");
    setElementVisibility("counter-select", "hidden");
    setElementVisibility("mov-select", "hidden");
    setElementVisibility("mov-params", "hidden");
    setElementVisibility("mov-light", "hidden");
    setElementVisibility("mov-light-lbl", "hidden");
    setElementVisibility("shortlong-select", "hidden");
    setElementVisibility("onoff-select", "hidden");
    setElementVisibility("count-vals", "hidden");
    setElementVisibility("sens-lims-wind", "hidden");
    setElementVisibility("sens-lims-lux", "hidden");
    setElementVisibility("sens-lims-temp", "hidden");
    setElementVisibility("sens-lims-perc", "hidden");
    setElementVisibility("rain-select", "hidden");
    setElementVisibility("sens-lims-ad", "hidden");
    setElementVisibility("time-vals", "hidden");
    setElementVisibility("day-vals", "hidden");
    setElementVisibility("month-vals", "hidden");
    setElementVisibility("ekey-select", "hidden");
    setElementVisibility("finger-select", "hidden");
    setElementVisibility("clim-sens-select", "hidden");
    setElementVisibility("clim-mode-select", "hidden");
    setElementVisibility("remote-codes", "hidden");
    setElementVisibility("sys-select", "hidden");
    setElementVisibility("supply-select", "hidden");
    setElementVisibility("syserr-div", "hidden");
    setElementVisibility("dimmer-select", "hidden");
    setElementVisibility("cover-select", "hidden");
    setElementVisibility("covpos-select", "hidden");
    setElementVisibility("cov-pos-val", "hidden");
    setElementVisibility("number-select", "hidden");
    setElementVisibility("prio-chng-vals", "hidden");

    if (selectn == "150") {
        setElementVisibility("button-select", "visible");
        setElementVisibility("shortlong-select", "visible");
    }
    if (selectn == "152") {
        setElementVisibility("switch-select", "visible");
        setElementVisibility("onoff-select", "visible");
    }
    if (selectn == "149") {
        setElementVisibility("button-select", "visible");
    }
    if (selectn == "23") {
        setElementVisibility("remote-codes", "visible");
    }
    if (selectn == "10") {
        setElementVisibility("output-select", "visible");
        setElementVisibility("onoff-select", "visible");
    }
    if (selectn == "15") {
        setElementVisibility("dimmer-select", "visible");
        setElementVisibility("covpos-select", "visible");
        setDimmvalModes();
        setCoverValues();
    }
    if (selectn == "17") {
        setElementVisibility("cover-select", "visible");
        setElementVisibility("covpos-select", "visible");
        setBladeModes();
        setCoverValues();
    }
    if (selectn == "50") {
        setElementVisibility("collcmd-select", "visible");
    }
    if (selectn == "4") {
        setElementVisibility("number-select", "visible");
        setElementVisibility("prio-chng-vals", "visible");
    }
    if (selectn == "30") {
        setElementVisibility("number-select", "visible");
    }
    if (selectn == "31") {
        setElementVisibility("viscmd-select", "visible");
    }
    if (selectn == "253") {
        setElementVisibility("dircmd-select", "visible");
    }
    if (selectn == "6") {
        setElementVisibility("flag-select", "visible");
        setElementVisibility("flag2-select", "visible");
    }
    if (selectn == "8") {
        setElementVisibility("logic-select", "visible");
        setElementVisibility("logic2-select", "visible");
    }
    if (selectn == "137") {
        setElementVisibility("mode-select", "visible");
        setElementVisibility("mode2-select", "visible");
    }
    if (selectn == "203") {
        setElementVisibility("sensor-select", "visible");
        setSensorNums();
    }
    if (selectn == "218") {
        setElementVisibility("ad-select", "visible");
        setElementVisibility("sens-lims-ad", "visible");
    }
    if (selectn == "9") {
        setElementVisibility("counter-select", "visible");
        setElementVisibility("count-vals", "visible");
        setMaxCount();
    }
    if (selectn == "40") {
        setElementVisibility("mov-select", "visible");
        setElementVisibility("mov-params", "visible");
        setMovLight();
    }
    if (selectn == "169") {
        setElementVisibility("ekey-select", "visible");
        setElementVisibility("finger-select", "visible");
        setEkeyUsrFingers();
    }
    if (selectn == "170") {
        setElementVisibility("time-vals", "visible");
        setElementVisibility("day-vals", "visible");
        setElementVisibility("month-vals", "visible");
    }
    if (selectn == "220") {
        setElementVisibility("clim-sens-select", "visible");
        setElementVisibility("clim-mode-select", "visible");
    }
    if (selectn == "249") {
        setElementVisibility("sys-select", "visible");
        setSysTrigger()
    }
    enablePercentActions()
}

function setMaxCount() {
    var idx = counter_sel.selectedIndex
    var max_cnt_val = max_count[idx - 1]
    var cnt_sel = document.getElementById("count-vals")
    for (var i = 0; i < cnt_sel.length; i++) {
        if (i > max_cnt_val)
            cnt_sel.options[i].disabled = true;
        else
            cnt_sel.options[i].disabled = false;
    }
    if (cnt_sel.selectedIndex > max_cnt_val)
        cnt_sel.selectedIndex = 0
};

function setEkeyUser(sel_usr) {
    for (var i = 0; i < ekey_sel.length; i++) {
        selectn = ekey_sel[i].value;
        if (selectn.split("-")[0] == sel_usr) {
            ekey_sel.value = selectn;
            break;
        }
    }
}
function setEkeyUsrFingers() {
    var idx = ekey_sel.selectedIndex;
    var selectn = ekey_sel[idx].value;
    var usr_parts = selectn.split("-");
    var finger_mask = usr_parts[1]
    var finger_sel = document.getElementById("finger-select")
    for (var i = 0; i < 10; i++) {
        var mask = 1 << i;
        if (finger_mask & mask)
            finger_sel.options[i + 1].disabled = false;
        else
            finger_sel.options[i + 1].disabled = true;
    }
    if (finger_sel.options[finger_sel.selectedIndex].disabled)
        finger_sel.selectedIndex = 0
    if (usr_parts[0] == 255)
        finger_sel.style.visibility = "hidden";
    else
        finger_sel.style.visibility = "visible";
}
function setSysTrigger() {
    var idx = sys_sel.selectedIndex;
    var selectn = sys_sel[idx].value;
    if (selectn == 249) {
        setElementVisibility("supply-select", "hidden");
        setElementVisibility("syserr-div", "hidden");
    }
    else if (selectn == 12) {
        setElementVisibility("supply-select", "visible");
        setElementVisibility("syserr-div", "hidden");
    }
    else if (selectn == 101) {
        setElementVisibility("supply-select", "hidden");
        setElementVisibility("syserr-div", "visible");
    }
}
document.getElementById("covpos-select").addEventListener("change", function () {
    setCoverValues();
});
document.getElementById("cover-select").addEventListener("change", function () {
    setBladeModes();
});
function setCoverValues() {
    if (document.getElementById("covpos-select").value >= 20)
        setElementVisibility("cov-pos-val", "visible");
    else
        setElementVisibility("cov-pos-val", "hidden");
}
function setDimmvalModes() {
    const cov_md = document.getElementById("covpos-select")
    cov_md.options[2].hidden = true;
    cov_md.options[6].hidden = true;
    cov_md.options[7].hidden = true;
    cov_md.options[8].hidden = true;
}

function setBladeModes() {
    let cov_no = document.getElementById("cover-select").value
    const cov_md = document.getElementById("covpos-select")
    if (is_blades[cov_no - 1]) {
        cov_md.options[2].hidden = false;
        cov_md.options[6].hidden = false;
        cov_md.options[7].hidden = false;
        cov_md.options[8].hidden = false;
    }
    else {
        cov_md.options[2].hidden = true;
        cov_md.options[6].hidden = true;
        cov_md.options[7].hidden = true;
        cov_md.options[8].hidden = true;
        if ((cov_md.value > 40) || (cov_md.value == 10)) {
            cov_md.options[0].selected = true;
            setElementVisibility("cov-pos-val", "hidden");
        }
    }
}
function enablePercentActions() {
    const act_select = document.getElementById("action-select")
    const dimm_opt = document.getElementById("dimmopt-act")
    const cov_opt = document.getElementById("covopt-act")
    const perc_opt = document.getElementById("perc-act")
    const perc_val = document.getElementById("perc-val")
    if (document.getElementById("trigger-select").value == 30) {
        act_select.options[1].hidden = true;
        act_select.options[4].hidden = true;
        act_select.options[5].hidden = true;
        act_select.options[6].hidden = true;
        act_select.options[7].hidden = true;
        act_select.options[8].hidden = true;
        act_select.options[9].hidden = true;
        act_select.options[10].hidden = true;
        act_select.options[12].hidden = true;
        act_select.options[13].hidden = true;
        act_select.options[14].hidden = true;
        dimm_opt.options[1].hidden = true;
        dimm_opt.options[3].hidden = true;
        dimm_opt.options[4].hidden = true;
        dimm_opt.options[5].hidden = true;
        cov_opt.options[0].hidden = true;
        cov_opt.options[2].hidden = true;
        cov_opt.options[3].hidden = true;
        cov_opt.options[5].hidden = true;
        perc_opt.options[1].hidden = true;
        perc_opt.options[2].hidden = true;
        perc_val.style.visibility = "hidden";
        dimm_opt.value = 10;
        cov_opt.value = 11;
        perc_opt.value = 31
        if ((act_select.value != 17) && (act_select.value != 20) && (act_select.value != 30)) {
            act_select.selectedIndex = 0;
            setActionSels();
        }
    }
    else {
        act_select.options[1].hidden = false;
        act_select.options[4].hidden = false;
        act_select.options[5].hidden = false;
        act_select.options[6].hidden = false;
        act_select.options[7].hidden = false;
        act_select.options[8].hidden = false;
        act_select.options[9].hidden = false;
        act_select.options[10].hidden = false;
        act_select.options[12].hidden = false;
        act_select.options[13].hidden = false;
        act_select.options[14].hidden = false;
        dimm_opt.options[1].hidden = false;
        dimm_opt.options[3].hidden = false;
        dimm_opt.options[4].hidden = false;
        dimm_opt.options[5].hidden = false;
        cov_opt.options[0].hidden = false;
        cov_opt.options[2].hidden = false;
        cov_opt.options[3].hidden = false;
        cov_opt.options[5].hidden = false;
        perc_opt.options[1].hidden = false;
        perc_opt.options[2].hidden = false;
        dimm_opt.value = 20;
        cov_opt.value = 1;
        perc_opt.value = 30
        if ((act_select.value == 17) || (act_select.value == 20)) {
            perc_val.style.visibility = "visible";
        }
    }
}

function u2sign7(uint_in) {
    if (uint_in > 60) {
        return uint_in - 128
    }
    return uint_in
}
