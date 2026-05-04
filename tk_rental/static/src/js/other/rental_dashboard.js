/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

class RentalDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            rentOrderStats: { 'total_rent_orders': 0, 'draft_stages': 0, 'quotation_stages': 0, 'quotation_sent_stages': 0 },
            deliveryOrderStates: { 'delivery_orders': 0, 'done_delivery_orders': 0 },
            returnOrderStates: { 'return_orders': 0, 'return_delivery_orders': 0 },
            rentOrderStatusGraph: { 'x-axis': [], 'y-axis': [] },
        });

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });

        this.rentOrderStatusGraph = useRef('rent_order_status_graph');

        onWillStart(async () => {
            let rentOrderData = await this.orm.call('rental.dashboard', 'get_rental_dashboard', []);
            if (rentOrderData) {
                this.state.rentOrderStats = rentOrderData;
                this.state.deliveryOrderStates = rentOrderData;
                this.state.returnOrderStates = rentOrderData;
                this.state.rentOrderStatusGraph = { 'x-axis': rentOrderData['rent_order_status'][0], 'y-axis': rentOrderData['rent_order_status'][1] }
            }
        });
        onMounted(() => {
            this.renderRentOrderStatusGraph();
        })
    }

    viewRentOrderStatsDetails(status) {
        let domain, context;
        let orders = this.getRentalOrders(status);
        if (status === 'all') {
            domain = []
        } else {
            domain = [['status', '=', status]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: orders,
            res_model: 'rent.order',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'activity']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    getRentalOrders(status) {
        let orders;
        if (status === 'all') {
            orders = 'Órdenes Totales';
        } else if (status === 'draft') {
            orders = 'Órdenes Nuevas';
        } else if (status === 'quotation') {
            orders = 'Cotizaciones';
        } else if (status === 'quotation_sent') {
            orders = 'Cotizaciones Enviadas';
        } else if (status === 'approve') {
            orders = 'Cotización Aprobada';
        } else if (status === 'reject') {
            orders = 'Órdenes Rechazadas';
        } else if (status === 'in_progress') {
            orders = 'En Progreso';
        } else if (status === 'in_delivery') {
            orders = 'En Entrega';
        } else if (status === 'return') {
            orders = 'Devoluciones';
        } else if (status === 'close') {
            orders = 'Cerrado';
        } else if (status === 'cancel') {
            orders = 'Cancelado';
        }
        return orders;
    }

    viewDeliveryOrders(status) {
        let domain, context;
        let orders = this.getDeliverOrders(status);
        if (status === 'not_done') {
            domain = [['state', '!=', 'done'], ['rent_order_id', '!=', false], ['is_return_order', '=', false]]
        } else {
            domain = [['state', '=', 'done'], ['rent_order_id', '!=', false], ['is_return_order', '=', false]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: orders,
            res_model: 'stock.picking',
            domain: domain,
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }

    getDeliverOrders(status) {
        let orders;
        if (status != 'done') {
            orders = 'Draft Orders'
        } else if (status === 'done') {
            orders = 'Done Orders'
        }
        return orders;
    }

    viewReturnOrders(status) {
        let domain, context;
        let orders = this.getReturnOrders(status);
        if (status === 'not_done') {
            domain = [['state', '!=', 'done'], ['rent_order_id', '!=', false], ['is_return_order', '!=', false]]
        } else {
            domain = [['state', '=', 'done'], ['rent_order_id', '!=', false], ['is_return_order', '!=', false]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: orders,
            res_model: 'stock.picking',
            domain: domain,
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }

    getReturnOrders(status) {
        let orders;
        if (status != 'done') {
            orders = 'Draft Orders'
        } else if (status === 'done') {
            orders = 'Return Orders'
        }
        return orders;
    }

    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
    }

    renderRentOrderStatusGraph() {
        const options = {
            series: [
                {
                    name: 'Status',
                    data: this.state.rentOrderStatusGraph['y-axis'],
                }
            ],
            chart: {
                height: 440,
                type: 'bar',
            },
            colors: ['#f29e4c', '#f1c453', '#efea5a', '#b9e769', '#83e377', '#16db93', '#0db39e', '#048ba8', '#2c699a', '#54478c'],
            plotOptions: {
                bar: {
                    columnWidth: '30%',
                    distributed: true,
                }
            },
            dataLabels: {
                enabled: false
            },
            legend: {
                show: false
            },
            xaxis: {
                categories: this.state.rentOrderStatusGraph['x-axis'],
                labels: {
                    style: {
                        fontSize: '13px'
                    }
                }
            }
        };
        this.renderGraph(this.rentOrderStatusGraph.el, options);
    }

}
RentalDashboard.template = "tk_rental.rent_dashboard";
registry.category("actions").add("rental_dashboard", RentalDashboard);