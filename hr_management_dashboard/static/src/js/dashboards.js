/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class BaseDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    openRecords(name, model, domain) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }
}

export class EmployeeStatus extends BaseDashboard {
    static template = "hr_management_dashboard.EmployeeStatus";

    setup() {
        super.setup();
        this.state = useState({ data: null, months: 12, collapsed: {} });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call(
            "hr.mgmt.dashboard", "get_employee_status", [], { months: this.state.months }
        );
    }

    onMonthsChange(ev) {
        this.state.months = parseInt(ev.target.value);
        return this.load();
    }

    openEmployees(name, domain) {
        this.openRecords(name, "hr.employee", domain);
    }

    openAlert(alert) {
        this.openRecords(alert.label, alert.model || "hr.employee", alert.domain);
    }

    toggle(id) {
        this.state.collapsed[id] = !this.state.collapsed[id];
    }

    barHeight(count) {
        const max = Math.max(1, ...this.state.data.months.map((m) => m.count));
        return Math.round((count / max) * 120) + 4;
    }
}

export class IssuesDashboard extends BaseDashboard {
    static template = "hr_management_dashboard.Issues";

    setup() {
        super.setup();
        this.state = useState({ data: null });
        onWillStart(async () => {
            this.state.data = await this.orm.call("hr.mgmt.dashboard", "get_issues", []);
        });
    }

    openItem(item) {
        if (item.action) {
            this.actionService.doAction(item.action);
        } else {
            this.openRecords(item.label, item.model, item.domain);
        }
    }
}

registry.category("actions").add("hr_management_dashboard.employee_status", EmployeeStatus);
registry.category("actions").add("hr_management_dashboard.issues", IssuesDashboard);

// Rebuild the missing-data rows, then open the list (returned action is executed by the framework)
registry.category("actions").add("hr_management_dashboard.open_missing_data", async (env) => {
    return env.services.orm.call("hr.employee.data.issue", "action_open_report", []);
});

// Same pattern for the payslip billing snapshot
registry.category("actions").add("hr_management_dashboard.open_billing_status", async (env) => {
    return env.services.orm.call("hr.payslip.billing.status", "action_open_report", []);
});

// Skills & certificates snapshot
registry.category("actions").add("hr_management_dashboard.open_skill_report", async (env) => {
    return env.services.orm.call("hr.skill.report", "action_open_report", []);
});
