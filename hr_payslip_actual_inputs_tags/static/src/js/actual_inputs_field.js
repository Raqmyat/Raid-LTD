/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ActualInputsTagsField extends Component {
    static template = "hr_payslip_actual_inputs_tags.ActualInputsTagsField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            open: false,
            availableTypes: [],
            pickingAmountFor: null,
            amount: 0,
        });
    }

    // Helper: relational field values can come back as [id, name] or
    // {id, display_name} depending on context - handle both defensively.
    _relId(val) {
        if (!val) return false;
        if (Array.isArray(val)) return val[0];
        if (typeof val === "object") return val.id;
        return val;
    }
    _relName(val) {
        if (!val) return "";
        if (Array.isArray(val)) return val[1] || "";
        if (typeof val === "object") return val.display_name || "";
        return "";
    }

    get lines() {
        const list = this.props.record.data[this.props.name];
        return (list && list.records) || [];
    }

    get payslipId() {
        return this.props.record.resId;
    }

    get structId() {
        return this._relId(this.props.record.data.struct_id);
    }

    tagLabel(line) {
        const name = this._relName(line.data.input_type_id);
        return `${name}: ${line.data.amount}`;
    }

    async toggleDropdown() {
        if (this.state.open) {
            this.state.open = false;
            this.state.pickingAmountFor = null;
            return;
        }
        const domain = [["struct_ids", "in", [this.structId]]];
        const usedTypeIds = this.lines
            .map((l) => this._relId(l.data.input_type_id))
            .filter(Boolean);
        if (usedTypeIds.length) {
            domain.push(["id", "not in", usedTypeIds]);
        }
        this.state.availableTypes = await this.orm.searchRead(
            "hr.payslip.input.type",
            domain,
            ["id", "name"]
        );
        this.state.pickingAmountFor = null;
        this.state.open = true;
    }

    pickType(type) {
        this.state.pickingAmountFor = type;
        this.state.amount = 0;
    }

    async confirmAmount() {
        if (!this.state.pickingAmountFor || !this.payslipId) {
            return;
        }
        await this.orm.create("hr.payslip.input", [
            {
                payslip_id: this.payslipId,
                input_type_id: this.state.pickingAmountFor.id,
                amount: this.state.amount,
            },
        ]);
        this.state.open = false;
        this.state.pickingAmountFor = null;
        await this.props.record.load();
        this.render();
    }

    onAmountKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.confirmAmount();
        }
    }

    cancelAmount() {
        this.state.pickingAmountFor = null;
        this.state.open = false;
    }

    async removeLine(line, ev) {
        ev.preventDefault();
        ev.stopPropagation();
        await this.orm.unlink("hr.payslip.input", [line.resId]);
        await this.props.record.load();
        this.render();
    }
}

registry.category("fields").add("actual_inputs_tags", ActualInputsTagsField);
