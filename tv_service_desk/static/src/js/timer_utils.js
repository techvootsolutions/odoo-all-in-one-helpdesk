/** @odoo-module **/

import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

/**
 * Parse Odoo datetime values from RPC, form records, or DOM attributes.
 * Odoo 19 uses Luxon DateTime objects in the web client.
 */
export function parseOdooDatetime(value) {
    if (value === false || value === null || value === undefined) {
        return null;
    }
    if (DateTime.isDateTime(value)) {
        return value.isValid ? new Date(value.toMillis()) : null;
    }
    if (value instanceof Date) {
        return Number.isNaN(value.getTime()) ? null : value;
    }
    if (typeof value === "number") {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? null : date;
    }
    if (typeof value === "string") {
        const dt = deserializeDateTime(value);
        if (dt?.isValid) {
            return new Date(dt.toMillis());
        }
        const normalized = value.includes("T") ? value : value.replace(" ", "T");
        const fallback = new Date(normalized);
        return Number.isNaN(fallback.getTime()) ? null : fallback;
    }
    if (typeof value === "object" && typeof value.toMillis === "function") {
        const date = new Date(value.toMillis());
        return Number.isNaN(date.getTime()) ? null : date;
    }
    return null;
}

export function formatElapsed(startValue) {
    const start = parseOdooDatetime(startValue);
    if (!start) {
        return "00:00:00";
    }
    const elapsed = Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000));
    const hours = String(Math.floor(elapsed / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
    const seconds = String(elapsed % 60).padStart(2, "0");
    return `${hours}:${minutes}:${seconds}`;
}
