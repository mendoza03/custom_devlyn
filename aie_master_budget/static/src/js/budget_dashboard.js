/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { registry} from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
export class MasterBudgetDashboard extends Component {
    static defaultProps = {
        title: _t("Dashboard"),
    };

	setup(){
        this.orm = useService("orm");
        this.state = useState({
            data: [],
            totals: [],
        });
        this.loadData();
	}

    async loadData(){
        await this.orm.call('master.budget', 'get_values', []).then((data) => {
            this.state.data = data[0];
            this.state.totals = data[1];
        });
        console.log(this.state.data);
    }

    formatCurrency(value) {
        return value ? `$${value.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,')}` : '';
    }

    toggleClasses(nodeList, classes) {
        nodeList.forEach(node => {
            classes.forEach(cls => {
                node.classList.toggle(cls);
            });
        });
    }

    toggleGroup(event){
        const key = event.currentTarget.id.replace('btn_', '');
        const button = event.currentTarget;
        const rows = document.querySelectorAll(`tr[data-group-key="${key}"]`);
        const icons = document.querySelectorAll(`i[i-button-group-key="${key}"]`);
        const trs = document.querySelectorAll(`tr[tr-button-group-key="${key}"]`);

        button.classList.toggle('btn_foldable');
        this.toggleClasses(rows, ['d-none']);
        this.toggleClasses(trs, ['unfolded']);
        this.toggleClasses(icons, ['fa-caret-right', 'fa-caret-down']);

        if (rows.length > 0) {
            rows[rows.length - 1].classList.toggle('total');
        }
    }
}

MasterBudgetDashboard.template = "aie_master_budget.dashboard_template"
MasterBudgetDashboard.props = {
    title: { type: String, optional: true },
    action: { type: Object },
    actionId: { type: Number },
    className: { type: String },
    updateActionState: { optional: true },
}
registry.category("actions").add("aie_master_budget.master_budget_dashboard_tag", MasterBudgetDashboard)