/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
// var rpc = require("web.rpc"); //ORM
import { _t } from "@web/core/l10n/translation";

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";

export class DashBoard extends Component {
  static template = "RealEstateDashboard"
  setup() {
    this.dashboard_data = {};
    this.charts = {};
    this.orm = useService("orm");
    this.action = useService("action");

    onMounted(async () => {
      await this.update_project();
    });
  }

  async update_project() {
    var self = this;
    const res = await this.orm.call(
      "res.users",
      "get_real_estate_dashboard_data",
      []
    );
    //self.update_dashboard_data(res);

    const res1 = await this.orm.call(
      "res.users",
      "get_real_estate_dashboard_chart_data",
      []
    );
    //self.dashboard_charts(res1);
    // rpc
    //   .query({
    //     model: "res.users",
    //     method: "get_real_estate_dashboard_data",
    //   })
    //   .then(function (result) {
    //     self.update_dashboard_data(result);
    //   });

    // rpc
    //   .query({
    //     model: "res.users",
    //     method: "get_real_estate_dashboard_chart_data",
    //   })
    //   .then(function (result) {
    //     self.dashboard_charts(result);
    //   });
  }

  update_dashboard_data(data) {
    $("#welcome_msg").html(data.company_name);
    var project_names = [];
    var project_selection = "<div class='check-box'>";
    data.projects.forEach(function (project) {
      if (project.is_enabled) {
        project_selection +=
          "<div class='row'><div class='col-2'><input class='check_project' type='checkbox' data-id='" +
          project.id +
          "' data-name='" +
          project.name +
          "' checked='true'/></div>";
        project_names.push(project.name);
      } else {
        project_selection +=
          "<div class='row'><div class='col-2'><input class='check_project' type='checkbox' data-id='" +
          project.id +
          "' data-name='" +
          project.name +
          "'/></div>";
      }
      project_selection +=
        "<div class='col-10'><label class='check_project' data-id='" +
        project.id +
        "' data-name='" +
        project.name +
        "' t-att-for='" +
        project.name +
        "'>" +
        project.name +
        "</label></div></div>";
    });
    project_selection += "</div>";
    $("#project_names").html(project_names.join(", "));
    $("#project_selection").html(project_selection);
    $(".check_project").on("click", this.checkProject.bind(this));
    
    var cards = "";
    data.cards.forEach(function (card) {
      cards +=
        "<div class='col mb-4 stretch-card transparent' data-id='" +
        card.id +
        "'>";
      cards += "<div class='card card-reb " + card.class + "'>";
      cards += "<div class='card-body card-body-reb'>";
      cards += "<p class='mb-5'>" + card.name + "</p>";
      cards += "<p class='mb-2'>" + card.value + "</p>";
      cards += "</div></div></div>";
    });
    $("#cards").html(cards);

    var sft_chart_data = "";
    data.sft_chart_data.forEach(function (data) {
      sft_chart_data += "<div class='col text-center mt-3'>";
      sft_chart_data += "<p class='text-muted-reb'>" + data.name + "</p>";
      sft_chart_data +=
        "<h3 class='text-primary-reb fs-30-reb font-weight-medium-reb'>" +
        data.value;
      sft_chart_data += "</h3></div>";
    });
    $("#sft_chart_data").html(sft_chart_data);

    var renting_revenue_data = "";
    data.renting_revenue_data.forEach(function (data) {
      renting_revenue_data += "<div class='col text-center mt-3'>";
      renting_revenue_data += "<p class='text-muted-reb'>" + data.name + "</p>";
      renting_revenue_data +=
        "<h3 class='text-primary-reb fs-30-reb font-weight-medium-reb'>" +
        data.value;
      renting_revenue_data += "</h3></div>";
    });
    $("#renting-revenue-data").html(renting_revenue_data);

    var brochures = "";
    data.brochures.forEach(function (brochure) {
      brochures +=
        "<a href='/web/content/attachment.line/" +
        brochure.id +
        "/file' target='_blank'>" +
        brochure.name +
        "</a><hr/>";
    });
    $("#brochure-list").html(brochures);
  }

  get_bar_options(min, max) {
    return {
      cornerRadius: 5,
      responsive: true,
      maintainAspectRatio: true,
      layout: {
        padding: {
          left: 0,
          right: 0,
          top: 20,
          bottom: 0,
        },
      },
      scales: {
        yAxes: [
          {
            display: true,
            gridLines: {
              display: true,
              drawBorder: false,
              color: "#F2F2F2",
            },
            ticks: {
              display: true,
              min: min,
              max: max,
              callback(value, index, values) {
                return value + "$";
              },
              autoSkip: true,
              maxTicksLimit: 10,
              fontColor: "#6C7383",
            },
          },
        ],
        xAxes: [
          {
            stacked: false,
            ticks: {
              beginAtZero: true,
              fontColor: "#6C7383",
            },
            gridLines: {
              color: "rgba(0, 0, 0, 0)",
              display: false,
            },
          },
        ],
      },
      legend: {
        display: false,
      },
      elements: {
        point: {
          radius: 0,
        },
      },
    };
  }

  dashboard_charts(data) {
    var self = this;

    $("#sft_chart_bits").html('<canvas id="sft-chart"/>');
    var sft_chart_ctx = document.getElementById("sft-chart").getContext("2d");
    var sft_chart = new Chart(sft_chart_ctx, data.sft_chart);

    $("#renting_revenue_chart").html(
      '<canvas id="renting-revenue-chart-bits"/>'
    );
    var renting_revenue_ctx = document
      .getElementById("renting-revenue-chart-bits")
      .getContext("2d");
    var renting_revenue = new Chart(renting_revenue_ctx, {
      type: "bar",
      data: data.renting_revenue_chart,
      options: self.get_bar_options(
        data.renting_revenue_chart_options.min,
        data.renting_revenue_chart_options.max
      ),
    });

    $("#property_type_chart").html('<canvas id="chart-property-type"/>');
    var property_type_ctx = document
      .getElementById("chart-property-type")
      .getContext("2d");
    var property_type_chart = new Chart(
      property_type_ctx,
      data.property_type_chart
    );
  }

  async checkProject(ev) {
    var self = this;
    const res = await this.orm.call(
        "project.worksite",
        "set_is_enabled",
        [parseInt(ev.target.dataset.id)]
      );
      self.update_project();
    // rpc
    //   .query({
    //     model: "project.worksite",
    //     method: "set_is_enabled",
    //     args: [parseInt(ev.target.dataset.id)],
    //   })
    //   .then(function () {
    //     self.update_project();
    //   });
  }

  btnNewProject() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("Project"),
      res_model: "project.worksite",
      views: [[false, "form"]],
    });
  }

  btnNewBooking() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("Property Booking"),
      res_model: "property.reservation",
      views: [[false, "form"]],
    });
  }

  btnNewRentContract() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("Rental Contract"),
      res_model: "property.contract",
      views: [[false, "form"]],
      domain: [["is_rental", "=", true]],
      context: { default_is_rental: true },
    });
  }

  btnNewOwnershipContract() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("Ownership Contract"),
      res_model: "property.contract",
      views: [[false, "form"]],
      domain: [["is_ownership", "=", true]],
      context: { default_is_ownership: true },
    });
  }

  btnNewRegisterPayment() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("Register Payment"),
      res_model: "account.payment",
      views: [[false, "form"]],
    });
  }
}

registry.category("actions").add("real_estate", DashBoard);

// var DashBoard = AbstractAction.extend({
//   contentTemplate: "RealEstateDashboard",

//   events: {
//     "click #btn_new_project": "btnNewProject",
//     "click #btn_new_booking": "btnNewBooking",
//     "click #btn_new_rent_contract": "btnNewRentContract",
//     "click #btn_new_ownership_contract": "btnNewOwnershipContract",
//     "click #btn_new_register_payment": "btnNewRegisterPayment",
//     "click .check_project": "checkProject",
//   },

//   init(parent, context) {
//     this._super(parent, context);
//     this.dashboard_data = {};
//     this.charts = {};
//   },

//   start() {
//     var self = this;
//     this.set("title", "Dashboard");
//     return this._super().then(function () {});
//   },

//   willStart() {
//     var self = this;
//     return this._super().then(function () {
//       self.update_project();
//     });
//   },

//   renderElement() {
//     var self = this;
//     $.when(this._super()).then(function () {
//       self.update_project();
//     });
//   },

//   update_project() {
//     var self = this;

//     rpc
//       .query({
//         model: "res.users",
//         method: "get_real_estate_dashboard_data",
//       })
//       .then(function (result) {
//         self.update_dashboard_data(result);
//       });

//     rpc
//       .query({
//         model: "res.users",
//         method: "get_real_estate_dashboard_chart_data",
//       })
//       .then(function (result) {
//         self.dashboard_charts(result);
//       });
//   },

//   update_dashboard_data(data) {
//     $("#welcome_msg").html(data.company_name);
//     var project_names = [];
//     var project_selection = "<div class='check-box'>";
//     data.projects.forEach(function (project) {
//       if (project.is_enabled) {
//         project_selection +=
//           "<div class='row'><div class='col-2'><input class='check_project' type='checkbox' data-id='" +
//           project.id +
//           "' data-name='" +
//           project.name +
//           "' checked='true'/></div>";
//         project_names.push(project.name);
//       } else {
//         project_selection +=
//           "<div class='row'><div class='col-2'><input class='check_project' type='checkbox' data-id='" +
//           project.id +
//           "' data-name='" +
//           project.name +
//           "'/></div>";
//       }
//       project_selection +=
//         "<div class='col-10'><label class='check_project' data-id='" +
//         project.id +
//         "' data-name='" +
//         project.name +
//         "' t-att-for='" +
//         project.name +
//         "'>" +
//         project.name +
//         "</label></div></div>";
//     });
//     project_selection += "</div>";
//     $("#project_names").html(project_names.join(", "));
//     $("#project_selection").html(project_selection);

//     var cards = "";
//     data.cards.forEach(function (card) {
//       cards +=
//         "<div class='col mb-4 stretch-card transparent' data-id='" +
//         card.id +
//         "'>";
//       cards += "<div class='card card-reb " + card.class + "'>";
//       cards += "<div class='card-body card-body-reb'>";
//       cards += "<p class='mb-5'>" + card.name + "</p>";
//       cards += "<p class='mb-2'>" + card.value + "</p>";
//       cards += "</div></div></div>";
//     });
//     $("#cards").html(cards);

//     var sft_chart_data = "";
//     data.sft_chart_data.forEach(function (data) {
//       sft_chart_data += "<div class='col text-center mt-3'>";
//       sft_chart_data += "<p class='text-muted-reb'>" + data.name + "</p>";
//       sft_chart_data +=
//         "<h3 class='text-primary-reb fs-30-reb font-weight-medium-reb'>" +
//         data.value;
//       sft_chart_data += "</h3></div>";
//     });
//     $("#sft_chart_data").html(sft_chart_data);

//     var renting_revenue_data = "";
//     data.renting_revenue_data.forEach(function (data) {
//       renting_revenue_data += "<div class='col text-center mt-3'>";
//       renting_revenue_data += "<p class='text-muted-reb'>" + data.name + "</p>";
//       renting_revenue_data +=
//         "<h3 class='text-primary-reb fs-30-reb font-weight-medium-reb'>" +
//         data.value;
//       renting_revenue_data += "</h3></div>";
//     });
//     $("#renting-revenue-data").html(renting_revenue_data);

//     var brochures = "";
//     data.brochures.forEach(function (brochure) {
//       brochures +=
//         "<a href='/web/content/attachment.line/" +
//         brochure.id +
//         "/file' target='_blank'>" +
//         brochure.name +
//         "</a><hr/>";
//     });
//     $("#brochure-list").html(brochures);
//   },

//   get_bar_options(min, max) {
//     return {
//       cornerRadius: 5,
//       responsive: true,
//       maintainAspectRatio: true,
//       layout: {
//         padding: {
//           left: 0,
//           right: 0,
//           top: 20,
//           bottom: 0,
//         },
//       },
//       scales: {
//         yAxes: [
//           {
//             display: true,
//             gridLines: {
//               display: true,
//               drawBorder: false,
//               color: "#F2F2F2",
//             },
//             ticks: {
//               display: true,
//               min: min,
//               max: max,
//               callback(value, index, values) {
//                 return value + "$";
//               },
//               autoSkip: true,
//               maxTicksLimit: 10,
//               fontColor: "#6C7383",
//             },
//           },
//         ],
//         xAxes: [
//           {
//             stacked: false,
//             ticks: {
//               beginAtZero: true,
//               fontColor: "#6C7383",
//             },
//             gridLines: {
//               color: "rgba(0, 0, 0, 0)",
//               display: false,
//             },
//           },
//         ],
//       },
//       legend: {
//         display: false,
//       },
//       elements: {
//         point: {
//           radius: 0,
//         },
//       },
//     };
//   },

//   dashboard_charts(data) {
//     var self = this;

//     $("#sft_chart_bits").html('<canvas id="sft-chart"/>');
//     var sft_chart_ctx = document.getElementById("sft-chart").getContext("2d");
//     var sft_chart = new Chart(sft_chart_ctx, data.sft_chart);

//     $("#renting_revenue_chart").html(
//       '<canvas id="renting-revenue-chart-bits"/>'
//     );
//     var renting_revenue_ctx = document
//       .getElementById("renting-revenue-chart-bits")
//       .getContext("2d");
//     var renting_revenue = new Chart(renting_revenue_ctx, {
//       type: "bar",
//       data: data.renting_revenue_chart,
//       options: self.get_bar_options(
//         data.renting_revenue_chart_options.min,
//         data.renting_revenue_chart_options.max
//       ),
//     });

//     $("#property_type_chart").html('<canvas id="chart-property-type"/>');
//     var property_type_ctx = document
//       .getElementById("chart-property-type")
//       .getContext("2d");
//     var property_type_chart = new Chart(
//       property_type_ctx,
//       data.property_type_chart
//     );
//   },

//   checkProject(ev) {
//     var self = this;
//     rpc
//       .query({
//         model: "project.worksite",
//         method: "set_is_enabled",
//         args: [parseInt(ev.target.dataset.id)],
//       })
//       .then(function () {
//         self.update_project();
//       });
//   },

//   btnNewProject() {
//     this.do_action({
//       type: "ir.actions.act_window",
//       name: _t("Project"),
//       res_model: "project.worksite",
//       views: [[false, "form"]],
//     });
//   },

//   btnNewBooking() {
//     this.do_action({
//       type: "ir.actions.act_window",
//       name: _t("Property Booking"),
//       res_model: "property.reservation",
//       views: [[false, "form"]],
//     });
//   },

//   btnNewRentContract() {
//     this.do_action({
//       type: "ir.actions.act_window",
//       name: _t("Rental Contract"),
//       res_model: "property.contract",
//       views: [[false, "form"]],
//       domain: [["is_rental", "=", true]],
//       context: { default_is_rental: true },
//     });
//   },

//   btnNewOwnershipContract() {
//     this.do_action({
//       type: "ir.actions.act_window",
//       name: _t("Ownership Contract"),
//       res_model: "property.contract",
//       views: [[false, "form"]],
//       domain: [["is_ownership", "=", true]],
//       context: { default_is_ownership: true },
//     });
//   },

//   btnNewRegisterPayment() {
//     this.do_action({
//       type: "ir.actions.act_window",
//       name: _t("Register Payment"),
//       res_model: "account.payment",
//       views: [[false, "form"]],
//     });
//   },
// });
