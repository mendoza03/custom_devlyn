/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { addLoadingEffect } from "@web/core/utils/ui";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

class SignatureFormCustom extends Component {
    static template = "portal.SignatureForm";
    static components = { NameAndSignature };
    static props = ["*"];

    setup() {
        this.rootRef = useRef("root");
        this.csrfToken = odoo.csrf_token;

        this.state = useState({
            error: false,
            success: false,
        });

        this.signature = useState({ name: this.props.defaultName });

        this.nameAndSignatureProps = {
            signature: this.signature,
            fontColor: this.props.fontColor || "black",
        };

        if (this.props.signatureRatio) {
            this.nameAndSignatureProps.displaySignatureRatio = this.props.signatureRatio;
        }
        if (this.props.signatureType) {
            this.nameAndSignatureProps.signatureType = this.props.signatureType;
        }
        if (this.props.mode) {
            this.nameAndSignatureProps.mode = this.props.mode;
        }

        onMounted(() => {
            const modal = this.rootRef.el.closest('.modal');
            if (modal) {
                modal.addEventListener('shown.bs.modal', () => {
                    this.signature.resetSignature();
                    this.toggleSignatureFormVisibility();
                });
            }

            this.loadLegalStatusOptions(); // ← cargamos las opciones del modelo sign.template
        });
    }

    toggleSignatureFormVisibility() {
        this.rootRef.el.classList.toggle('d-none', document.querySelector('.editor_enable'));
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

    async loadLegalStatusOptions() {
        const select = document.querySelector('#legal_status');
        if (!select) return;

        try {
            const templates = await rpc('/web/dataset/call_kw', {
                model: 'sign.template',
                method: 'search_read',
                args: [[]],
                kwargs: {
                    fields: ['id', 'name'],
                    limit: 100,
                },
            });

            for (const tmpl of templates) {
                const option = document.createElement('option');
                option.value = tmpl.id;
                option.textContent = tmpl.name;
                select.appendChild(option);
            }
        } catch (error) {
            console.error('[SignatureFormCustom] Error loading sign.template options:', error);
        }
    }

    async onClickSubmit() {
        const button = document.querySelector('.o_portal_sign_submit');
        const icon = button?.firstChild;
        if (icon) button.removeChild(icon);
        const restoreBtnLoading = addLoadingEffect(button);

        const name = this.signature.name;
        const signature = this.signature.getSignatureImage().split(",")[1];

        const legalInput = document.querySelector('#legal_status');
        const legal_status_template_id = legalInput?.value ? parseInt(legalInput.value) : null;

        console.log('[SignatureFormCustom] legal_status_template_id:', legal_status_template_id);

        const data = await rpc(this.props.callUrl, {
            name,
            signature,
            legal_status_template_id, // ← lo enviamos como ID
        });

        restoreBtnLoading();
        if (icon) button.prepend(icon);

        if (data.force_refresh) {
            if (data.redirect_url) {
                redirect(data.redirect_url);
            } else {
                window.location.reload();
            }
            return new Promise(() => {});
        }

        this.state.error = data.error || false;
        this.state.success = !data.error && {
            message: data.message,
            redirectUrl: data.redirect_url,
            redirectMessage: data.redirect_message,
        };
    }
}

registry.category("public_components").remove("portal.signature_form");
registry.category("public_components").add("portal.signature_form", SignatureFormCustom);
