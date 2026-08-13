/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormCompiler } from "@web/views/form/form_compiler";
import { createElement } from "@web/core/utils/xml";
import { onWillStart, onMounted, useState } from "@odoo/owl";
import { user } from "@web/core/user";

const STICKY_NOTE_COLOR_PALETTE = [
    "#F06050",
    "#F4A460",
    "#F7CD1F",
    "#6CC1ED",
    "#814968",
    "#EB7E7F",
    "#2C8397",
    "#475577",
    "#D6145F",
    "#30C381",
    "#9365B8",
    "#8B8B8B",
];
const DEFAULT_STICKY_NOTE_COLOR = "#F7CD1F";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.sdStickyOrm = useService("orm");
        this.sdStickyAction = useService("action");
        this.sdStickyDialog = useService("dialog");
        this.sdStickyNotification = useService("notification");
        this.sdStickyState = useState({
            notes: [],
            hasGroup: false,
            mediaRecorder: null,
            recordingNoteId: null,
        });
        onWillStart(async () => {
            if (this.props.record.resModel !== "service.desk.ticket") {
                return;
            }
            this.sdStickyState.hasGroup = await user.hasGroup(
                "tv_service_desk.group_service_desk_sticky_note_user"
            );
            await this._sdLoadStickyNotes();
        });
        onMounted(() => {
            this._sdBindPinButton();
        });
    },

    async _sdLoadStickyNotes() {
        const record = this.props.record;
        if (record.resModel !== "service.desk.ticket" || !record.resId || !this.sdStickyState.hasGroup) {
            this.sdStickyState.notes = [];
            return;
        }
        this.sdStickyState.notes = await this.sdStickyOrm.call(
            "service.desk.sticky.note",
            "get_ticket_sticky_notes",
            [record.resId]
        );
    },

    _sdBindPinButton() {
        if (this.props.record.resModel !== "service.desk.ticket" || !this.sdStickyState.hasGroup) {
            return;
        }
        const controlPanel = document.querySelector(".o_control_panel");
        if (!controlPanel || controlPanel.querySelector(".o_sd_sticky_pin_btn")) {
            return;
        }
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-link o_sd_sticky_pin_btn ms-1";
        btn.title = _t("Pin");
        btn.innerHTML = '<i class="fa fa-thumb-tack"/>';
        btn.addEventListener("click", async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            await this.sdOpenStickyNoteWizard();
        });
        const breadcrumbs = controlPanel.querySelector(".o_breadcrumb");
        if (breadcrumbs) {
            breadcrumbs.appendChild(btn);
        }
    },

    async sdOpenStickyNoteWizard(noteId = false) {
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }
        const context = { default_ticket_id: resId };
        if (noteId) {
            context.default_note_id = noteId;
        }
        await this.sdStickyAction.doAction(
            {
                type: "ir.actions.act_window",
                name: noteId ? _t("Update") : _t("New Note"),
                res_model: "service.desk.sticky.note.wizard",
                views: [[false, "form"]],
                target: "new",
                context,
            },
            {
                onClose: async () => {
                    await this._sdLoadStickyNotes();
                },
            }
        );
    },

    sdNormalizeNoteColor(color) {
        if (color === null || color === undefined || color === "") {
            return DEFAULT_STICKY_NOTE_COLOR;
        }
        if (typeof color === "number") {
            return STICKY_NOTE_COLOR_PALETTE[color % STICKY_NOTE_COLOR_PALETTE.length];
        }
        if (typeof color === "string" && /^\d+$/.test(color)) {
            const index = parseInt(color, 10);
            return STICKY_NOTE_COLOR_PALETTE[index % STICKY_NOTE_COLOR_PALETTE.length];
        }
        if (typeof color === "string" && color.startsWith("#")) {
            return color;
        }
        return DEFAULT_STICKY_NOTE_COLOR;
    },

    sdNoteBorderStyle(color) {
        const hex = this.sdNormalizeNoteColor(color);
        return hex ? `border-left-color: ${hex}` : "";
    },

    async sdEditNote(noteId) {
        await this.sdOpenStickyNoteWizard(noteId);
    },

    sdConfirmArchive(noteId) {
        this.sdStickyDialog.add(ConfirmationDialog, {
            title: _t("Confirmation"),
            body: _t("Are you sure you want to archive this note?"),
            confirm: async () => {
                await this.sdStickyOrm.call("service.desk.sticky.note", "action_archive_note", [[noteId]]);
                this.sdStickyNotification.add(_t("Note Archived"), { type: "success" });
                await this._sdLoadStickyNotes();
            },
            cancel: () => {},
        });
    },

    sdConfirmDeleteAudio(noteId) {
        this.sdStickyDialog.add(ConfirmationDialog, {
            title: _t("Confirmation"),
            body: _t("Are you sure you want to delete this audio note?"),
            confirm: async () => {
                await this.sdStickyOrm.call("service.desk.sticky.note", "delete_audio_note", [noteId]);
                await this._sdLoadStickyNotes();
            },
            cancel: () => {},
        });
    },

    async sdPlayAudio(note) {
        if (!note.audio_url) {
            return;
        }
        this.sdStickyNotification.add(_t("Playing audio..."), { type: "info" });
        const audio = new Audio(note.audio_url);
        audio.onended = () => {
            this.sdStickyNotification.add(_t("Audio playback finished."), { type: "success" });
        };
        await audio.play();
    },

    async sdStartRecording(noteId) {
        if (!navigator.mediaDevices?.getUserMedia) {
            this.sdStickyNotification.add(_t("Audio recording is not supported in this browser."), {
                type: "warning",
            });
            return;
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        const chunks = [];
        recorder.ondataavailable = (ev) => chunks.push(ev.data);
        recorder.onstop = async () => {
            stream.getTracks().forEach((track) => track.stop());
            const blob = new Blob(chunks, { type: "audio/webm" });
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64 = reader.result.split(",")[1];
                await this.sdStickyOrm.call("service.desk.sticky.note", "save_audio_note", [noteId, base64]);
                this.sdStickyNotification.add(_t("Audio note recorded and saved!"), { type: "success" });
                await this._sdLoadStickyNotes();
            };
            reader.readAsDataURL(blob);
        };
        recorder.start();
        this.sdStickyState.mediaRecorder = recorder;
        this.sdStickyState.recordingNoteId = noteId;
        this.sdStickyNotification.add(_t("Recording started..."), { type: "info" });
    },

    sdStopRecording() {
        if (this.sdStickyState.mediaRecorder && this.sdStickyState.mediaRecorder.state !== "inactive") {
            this.sdStickyState.mediaRecorder.stop();
        }
        this.sdStickyState.mediaRecorder = null;
        this.sdStickyState.recordingNoteId = null;
    },

    sdIsRecording(noteId) {
        return this.sdStickyState.recordingNoteId === noteId;
    },

    sdNoteBody(note) {
        return markup(note.note || "");
    },
});

patch(FormCompiler.prototype, {
    compileSheet(el, params) {
        const sheetBG = super.compileSheet(el, params);
        if (sheetBG) {
            const stickyCallNode = createElement("t");
            stickyCallNode.setAttribute("t-call", "tv_service_desk.TicketStickyNotes");
            sheetBG.insertBefore(stickyCallNode, sheetBG.firstChild);
        }
        return sheetBG;
    },
});
