/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { GraphRenderer } from "@web/views/graph/graph_renderer";

const HELPDESK_GRAPH_MODELS = new Set([
    "service.desk.ticket",
    "service.desk.ticket.analysis",
    "service.desk.stage.log",
]);

/** High-contrast palette (Odoo chart colors, light-background friendly). */
const HELPDESK_PALETTE = [
    "#4EA7F2",
    "#EA6175",
    "#43C5B1",
    "#F4A261",
    "#8481DD",
    "#FFD86D",
    "#3188E6",
    "#CE4257",
    "#00A78D",
    "#5752D1",
    "#FFBC2C",
    "#056BD9",
];

const HELPDESK_TEXT = "#1f2937";
const HELPDESK_TEXT_MUTED = "#4b5563";
const HELPDESK_GRID = "rgba(15, 23, 42, 0.1)";
const HELPDESK_SUM_LINE = "#714b67";
const HELPDESK_BORDER = "#ffffff";

function sdPaletteColor(index, total = HELPDESK_PALETTE.length) {
    return HELPDESK_PALETTE[index % HELPDESK_PALETTE.length];
}

function sdIsLineOverlayDataset(dataset) {
    return dataset?.type === "line";
}

function sdApplyDatasetColor(dataset, color) {
    dataset.backgroundColor = color;
    dataset.borderColor = HELPDESK_BORDER;
    dataset.borderWidth = dataset.type === "line" ? 2 : 1;
    dataset.hoverBackgroundColor = color;
    if ("pointBackgroundColor" in dataset || dataset.type === "line") {
        dataset.pointBackgroundColor = color;
        dataset.pointBorderColor = HELPDESK_BORDER;
    }
}

function sdRecolorChartData(data) {
    let colorIndex = 0;
    for (const dataset of data.datasets) {
        if (sdIsLineOverlayDataset(dataset)) {
            dataset.backgroundColor = HELPDESK_SUM_LINE;
            dataset.borderColor = HELPDESK_SUM_LINE;
            dataset.pointBackgroundColor = HELPDESK_SUM_LINE;
            dataset.pointBorderColor = HELPDESK_BORDER;
            continue;
        }
        sdApplyDatasetColor(dataset, sdPaletteColor(colorIndex++, data.datasets.length));
    }
    return data;
}

patch(GraphRenderer.prototype, {
    _sdIsHelpdeskGraph() {
        return HELPDESK_GRAPH_MODELS.has(this.props?.model?.metaData?.resModel);
    },

    getBarChartData() {
        const data = super.getBarChartData(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return data;
        }
        return sdRecolorChartData(data);
    },

    getLineChartData() {
        const data = super.getLineChartData(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return data;
        }
        return sdRecolorChartData(data);
    },

    getPieChartData() {
        const data = super.getPieChartData(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return data;
        }
        for (const dataset of data.datasets) {
            const colors = data.labels.map((_, index) => sdPaletteColor(index, data.labels.length));
            dataset.backgroundColor = colors;
            dataset.hoverBackgroundColor = colors;
            dataset.borderColor = HELPDESK_BORDER;
        }
        return data;
    },

    getScaleOptions() {
        const options = super.getScaleOptions(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return options;
        }
        if (options.x?.ticks) {
            options.x.ticks.color = HELPDESK_TEXT;
            options.x.ticks.font = { size: 12, weight: "600" };
        }
        if (options.x?.border) {
            options.x.border.color = HELPDESK_GRID;
            options.x.border.display = true;
        }
        if (options.y?.ticks) {
            options.y.ticks.color = HELPDESK_TEXT_MUTED;
            options.y.ticks.font = { size: 11 };
        }
        if (options.y?.title) {
            options.y.title.color = HELPDESK_TEXT;
            options.y.title.font = { size: 12, weight: "600" };
        }
        if (options.y?.grid) {
            options.y.grid.color = HELPDESK_GRID;
        }
        return options;
    },

    getLegendOptions() {
        const legendOptions = super.getLegendOptions(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return legendOptions;
        }
        legendOptions.labels = legendOptions.labels || {};
        legendOptions.labels.color = HELPDESK_TEXT;
        legendOptions.labels.font = { size: 12, weight: "500" };
        legendOptions.labels.boxWidth = 14;
        legendOptions.labels.padding = 14;
        if (legendOptions.labels.generateLabels) {
            const originalGenerate = legendOptions.labels.generateLabels;
            legendOptions.labels.generateLabels = (chart) => {
                const labels = originalGenerate(chart);
                return labels.map((item) => ({
                    ...item,
                    fontColor: HELPDESK_TEXT,
                    color: HELPDESK_TEXT,
                }));
            };
        }
        return legendOptions;
    },

    prepareOptions() {
        const options = super.prepareOptions(...arguments);
        if (!this._sdIsHelpdeskGraph()) {
            return options;
        }
        if (options.plugins?.legend?.labels) {
            options.plugins.legend.labels.color = HELPDESK_TEXT;
        }
        options.plugins = options.plugins || {};
        options.plugins.tooltip = {
            ...options.plugins.tooltip,
            backgroundColor: "rgba(31, 41, 55, 0.94)",
            titleColor: "#f9fafb",
            bodyColor: "#f9fafb",
            borderColor: "rgba(15, 23, 42, 0.2)",
            borderWidth: 1,
            padding: 10,
        };
        return options;
    },
});
