const menu_btn = document.getElementById("acc_img")
const el_left = document.getElementById("left")

if (el_left.getBoundingClientRect().height < 220) {
    menu_btn.style.width = "0px"
}
else {
    if (menu_btn)
        {menu_btn.addEventListener("click", function () {
            toggle_acc_btn();
        });
    }
}


function toggle_acc_btn() {
    if (el_left.getBoundingClientRect().width < 50) {
        el_left.style.width = "180px"
        el_left.style.visibility = "visible"
    }
    else {
        el_left.style.width = "0px"
        el_left.style.visibility = "hidden"
    }
};