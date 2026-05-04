/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
    // Default key
var default_key = "AIzaSyCLe7MRT7q5Rkd3kuyOoNSLb7wL-bk0Ip4";

jsonrpc({
    model: "gmap.config",
    method: "get_key_api",
    args: [],
}).then(function (key) {
    if (!key) {
        key = default_key;
    }
    $.getScript("https://maps.googleapis.com/maps/api/js?key=" + key + "&libraries=places&callback=Function.prototype");
});
