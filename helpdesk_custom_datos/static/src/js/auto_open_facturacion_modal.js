/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService, useBus } from "@web/core/utils/hooks";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this._hcd_last_opened_for = null;

        useBus(this.model.bus, "update", async () => {
            const record = this.model.root;
            if (!record || record.resModel !== "helpdesk.ticket") return;

            const xmlidCategory = "helpdesk_custom_datos.helpdesk_ticket_category_facturacion_reenvio_pdf_xml";
            const categoryResId = await this.orm.call("ir.model.data", "xmlid_to_res_id", [xmlidCategory]);

            const catValue = record.data.x_category_id;
            const selectedId = Array.isArray(catValue) ? catValue[0] : catValue;

            if (!selectedId || selectedId !== categoryResId) {
                this._hcd_last_opened_for = null;
                return;
            }

            const virtualId = record.id;
            if (this._hcd_last_opened_for === virtualId) return;
            this._hcd_last_opened_for = virtualId;

            if (!record.resId) {
                await record.save();
            }

            if (!record.resId) return;

            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Facturación - Reenvío PDF/XML",
                res_model: "helpdesk.ticket",
                res_id: record.resId,
                views: [[false, "form"]],
                target: "new",
            });
        });
    },
});