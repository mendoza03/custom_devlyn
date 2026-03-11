/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { onMounted } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const tryOpen = () => {
                try {
                    if (typeof this.OnClickMainMenu === "function") {
                        const el = this.app_components?.el;
                        const isOpen = el && el.style && el.style.display === "block";
                        if (!isOpen) {
                            this.OnClickMainMenu();
                        }
                    }
                } catch (e) {
                    console.warn("jazzy_backend_theme_home: auto-open apps failed", e);
                }
            };

            tryOpen();
            setTimeout(tryOpen, 300);
        });
    },
});