const form_upload = document.getElementById("file_upload");
const form_download = document.getElementById("file_download");
const form_rtr_update = document.getElementById("rtr_fw_upload");
const form_mod_update = document.getElementById("mod_fw_upload");
const updates_butt = document.getElementById("updates_button");
const updates_pop = document.getElementById("updates_popup");
const close_updates_pop = document.getElementById("close_updates_popup");
const form_doc = document.getElementById("file_doc");
const mod_type_sel = document.getElementsByName("mod_type_select")[0];
const sys_download = document.getElementsByName("SysDownload")[0];
const sys_doc = document.getElementsByName("SysDoc")[0];

if (document.getElementById("form_doc")) {
    form_doc.addEventListener("submit", function () {
        file_popup.classList.remove("show");
    });
}
if (document.getElementById("form_upload")) {
    form_upload.addEventListener("submit", function () {
        openMsgPopup();
    });
}

if (document.getElementById("config_button")) {
    document.getElementById("config_button").addEventListener("click", function () {
        msg_popup.innerHTML = msg_popup.innerHTML.replace("ContentTitle", "Neue Initialisierung")
        msg_popup.innerHTML = msg_popup.innerHTML.replace("Upload", "Bitte warten...")
        openMsgPopup();
    });
}
if (sys_download) {
    sys_download.addEventListener("click", function () {
        file_popup.classList.remove("show");
    });
}
if (sys_doc) {
    sys_doc.addEventListener("click", function () {
        file_popup.classList.remove("show");
    });
}
files_button.addEventListener("click", function () {
    file_popup.classList.add("show");
});
close_file_popup.addEventListener("click", function () {
    file_popup.classList.remove("show");
});
form_upload.addEventListener("submit", function () {
    openMsgPopup();
});
if (updates_butt)
    updates_butt.addEventListener("click", function () {
        updates_pop.classList.add("show");
    });
if (close_updates_pop)
    close_updates_pop.addEventListener("click", function () {
        updates_pop.classList.remove("show");
    });
form_rtr_update.addEventListener("submit", function () {
    openMsgPopup();
});
form_mod_update.addEventListener("submit", function () {
    openMsgPopup();
});
if (mod_type_sel) {
    mod_type_sel.addEventListener("change", function () {
        document.getElementById("loc_mod_fw_update").requestSubmit();
    });
}
window.addEventListener("click", function (event) {
    if (event.target == file_popup) {
        openMsgPopup();
    };
});
function openMsgPopup() {
    file_popup.classList.remove("show");
    msg_popup.classList.add("show");
    if (updates_pop)
        updates_pop.classList.remove("show");
};