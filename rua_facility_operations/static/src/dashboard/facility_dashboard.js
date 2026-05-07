/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class FacilityDashboard extends Component {
    static template = "rua_facility_operations.FacilityDashboard";
    static props = { ...Component.props };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            // KPIs
            totalRequests: 0,
            openRequests: 0,
            inProgressRequests: 0,
            overdueRequests: 0,
            solvedRequests: 0,
            closedRequests: 0,
            totalWorkOrders: 0,
            openWorkOrders: 0,
            avgRating: 0,
            // Breakdowns
            typeBreakdown: [],
            stateBreakdown: [],
            priorityBreakdown: [],
            woStateBreakdown: [],
            // Recent
            recentRequests: [],
            recentWorkOrders: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            // -- Request KPIs --
            const reqModel = "facility.request";
            this.state.totalRequests = await this.orm.searchCount(reqModel, []);
            this.state.openRequests = await this.orm.searchCount(reqModel, [
                ["state", "not in", ["closed", "cancelled"]],
            ]);
            this.state.inProgressRequests = await this.orm.searchCount(reqModel, [
                ["state", "=", "in_progress"],
            ]);
            this.state.overdueRequests = await this.orm.searchCount(reqModel, [
                ["is_overdue", "=", true],
            ]);
            this.state.solvedRequests = await this.orm.searchCount(reqModel, [
                ["state", "=", "solved"],
            ]);
            this.state.closedRequests = await this.orm.searchCount(reqModel, [
                ["state", "=", "closed"],
            ]);

            // -- Work Order KPIs --
            const woModel = "facility.work.order";
            this.state.totalWorkOrders = await this.orm.searchCount(woModel, []);
            this.state.openWorkOrders = await this.orm.searchCount(woModel, [
                ["state", "not in", ["closed", "cancelled"]],
            ]);

            // -- Average Rating --
            try {
                const ratings = await this.orm.searchRead(
                    "facility.rating", [], ["overall_rating"], { limit: 200 }
                );
                if (ratings.length) {
                    const sum = ratings.reduce((s, r) => s + (r.overall_rating || 0), 0);
                    this.state.avgRating = (sum / ratings.length).toFixed(1);
                }
            } catch {
                this.state.avgRating = 0;
            }

            // -- Type Breakdown --
            const types = [
                ["maintenance_report", _t("Maintenance")],
                ["observation", _t("Observation")],
                ["service_request", _t("Service")],
                ["event_preparation", _t("Event")],
                ["safety_report", _t("Safety")],
                ["cleaning_request", _t("Cleaning")],
            ];
            const typeBreakdown = [];
            for (const [key, label] of types) {
                const cnt = await this.orm.searchCount(reqModel, [["request_type", "=", key]]);
                typeBreakdown.push({ key, label, count: cnt });
            }
            this.state.typeBreakdown = typeBreakdown;

            // -- State Breakdown --
            const states = [
                ["draft", _t("Draft"), "#9CA3AF"],
                ["submitted", _t("Submitted"), "#3B82F6"],
                ["accepted", _t("Accepted"), "#6366F1"],
                ["in_progress", _t("In Progress"), "#F59E0B"],
                ["solved", _t("Solved"), "#10B981"],
                ["closed", _t("Closed"), "#6B7280"],
                ["cancelled", _t("Cancelled"), "#EF4444"],
            ];
            const stateBreakdown = [];
            for (const [key, label, color] of states) {
                const cnt = await this.orm.searchCount(reqModel, [["state", "=", key]]);
                if (cnt > 0) stateBreakdown.push({ key, label, color, count: cnt });
            }
            this.state.stateBreakdown = stateBreakdown;

            // -- Priority Breakdown --
            const priorities = [
                ["low", _t("Low"), "#10B981"],
                ["medium", _t("Medium"), "#F59E0B"],
                ["high", _t("High"), "#EF4444"],
                ["urgent", _t("Urgent"), "#7F1D1D"],
            ];
            const priorityBreakdown = [];
            for (const [key, label, color] of priorities) {
                const cnt = await this.orm.searchCount(reqModel, [["priority", "=", key]]);
                if (cnt > 0) priorityBreakdown.push({ key, label, color, count: cnt });
            }
            this.state.priorityBreakdown = priorityBreakdown;

            // -- WO State Breakdown --
            const woStates = [
                ["new", _t("New"), "#9CA3AF"],
                ["assigned", _t("Assigned"), "#3B82F6"],
                ["in_progress", _t("In Progress"), "#F59E0B"],
                ["completed", _t("Completed"), "#10B981"],
                ["closed", _t("Closed"), "#6B7280"],
            ];
            const woStateBreakdown = [];
            for (const [key, label, color] of woStates) {
                const cnt = await this.orm.searchCount(woModel, [["state", "=", key]]);
                if (cnt > 0) woStateBreakdown.push({ key, label, color, count: cnt });
            }
            this.state.woStateBreakdown = woStateBreakdown;

            // -- Recent Requests --
            this.state.recentRequests = await this.orm.searchRead(
                reqModel, [],
                ["name", "request_type", "state", "priority", "requester_id", "create_date", "building_id"],
                { order: "create_date desc", limit: 7 }
            );

            // -- Recent Work Orders --
            this.state.recentWorkOrders = await this.orm.searchRead(
                woModel, [],
                ["name", "title", "state", "priority", "assigned_user_id", "create_date"],
                { order: "create_date desc", limit: 5 }
            );

        } catch (e) {
            console.error("Dashboard load error:", e);
        }
        this.state.loading = false;
    }

    get completionRate() {
        if (!this.state.totalRequests) return 0;
        return Math.round(
            ((this.state.solvedRequests + this.state.closedRequests) / this.state.totalRequests) * 100
        );
    }

    getMaxTypeCount() {
        return Math.max(...this.state.typeBreakdown.map(t => t.count), 1);
    }

    getBarWidth(count) {
        const max = this.getMaxTypeCount();
        return `${(count / max) * 100}%`;
    }

    getStateTotal() {
        return this.state.stateBreakdown.reduce((s, b) => s + b.count, 0) || 1;
    }

    getStatePct(count) {
        return Math.round((count / this.getStateTotal()) * 100);
    }

    getTypeColor(type) {
        const map = {
            maintenance_report: "#064E3B",
            observation: "#1E40AF",
            service_request: "#6D28D9",
            event_preparation: "#92400E",
            safety_report: "#DC2626",
            cleaning_request: "#0E7490",
        };
        return map[type] || "#6B7280";
    }

    getTypeIcon(type) {
        const map = {
            maintenance_report: "build",
            observation: "visibility",
            service_request: "rebase_edit",
            event_preparation: "event_seat",
            safety_report: "health_and_safety",
            cleaning_request: "cleaning_services",
        };
        return map[type] || "description";
    }

    getStateColor(state) {
        const map = {
            draft: "#9CA3AF", submitted: "#3B82F6", accepted: "#6366F1",
            in_progress: "#F59E0B", solved: "#10B981", closed: "#6B7280",
            cancelled: "#EF4444", new: "#9CA3AF", assigned: "#3B82F6",
            completed: "#10B981", paused: "#F59E0B", verified: "#8B5CF6",
        };
        return map[state] || "#6B7280";
    }

    getPriorityColor(priority) {
        const map = { low: "#10B981", medium: "#F59E0B", high: "#EF4444", urgent: "#7F1D1D" };
        return map[priority] || "#6B7280";
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    }

    // Navigation actions
    openRequests(state) {
        const domain = state ? [["state", "=", state]] : [];
        this.action.doAction({
            name: _t("Requests"),
            type: "ir.actions.act_window",
            res_model: "facility.request",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openWorkOrders(state) {
        const domain = state ? [["state", "=", state]] : [];
        this.action.doAction({
            name: _t("Work Orders"),
            type: "ir.actions.act_window",
            res_model: "facility.work.order",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openOverdue() {
        this.action.doAction({
            name: _t("Overdue Requests"),
            type: "ir.actions.act_window",
            res_model: "facility.request",
            views: [[false, "list"], [false, "form"]],
            domain: [["is_overdue", "=", true]],
        });
    }

    openRequestsByType(type) {
        this.action.doAction({
            name: _t("Requests"),
            type: "ir.actions.act_window",
            res_model: "facility.request",
            views: [[false, "list"], [false, "form"]],
            domain: [["request_type", "=", type]],
        });
    }
}

registry.category("actions").add("facility_dashboard", FacilityDashboard);
