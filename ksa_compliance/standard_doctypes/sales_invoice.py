from datetime import date
from typing import Dict, Optional, cast

import frappe
import frappe.utils.background_jobs
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.selling.doctype.customer.customer import Customer
from frappe import _
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
    is_b2b_customer,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings import (
    ZATCAPhase1BusinessSettings,
)
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)
from ksa_compliance.jinja import get_zatca_phase_1_qr_for_invoice

from ksa_compliance.translation import ft

IGNORED_INVOICES = set()


def ignore_additional_fields_for_invoice(name: str) -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.add(name)


def clear_additional_fields_ignore_list() -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.clear()


def create_sales_invoice_additional_fields_doctype(self: SalesInvoice | POSInvoice, method):
    if self.doctype == 'Sales Invoice' and not _should_enable_zatca_for_invoice(self.name):
        logger.info(
            f"Skipping additional fields for {self.name} because it's before start date")
        return

    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not settings:
        if ZATCABusinessSettings.is_revoked_for_company(self.company):
            logger.info(
                f'Skipping additional fields for {self.name} because of revoked ZATCA settings')
            return
        logger.info(
            f'Skipping additional fields for {self.name} because of missing ZATCA settings')
        return

    if not settings.enable_zatca_integration:
        logger.info(
            f'Skipping additional fields for {self.name} because ZATCA integration is disabled in settings')
        return

    global IGNORED_INVOICES
    if self.name in IGNORED_INVOICES:
        logger.info(
            f"Skipping additional fields for {self.name} because it's in the ignore list")
        return

    if self.doctype == 'Sales Invoice' and self.is_consolidated:
        logger.info(
            f"Skipping additional fields for {self.name} because it's consolidated")
        return

    si_additional_fields_doc = SalesInvoiceAdditionalFields.create_for_invoice(
        self.name, self.doctype)
    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(
            f'Using precomputed invoice {precomputed_invoice.name} for {self.name}')
        si_additional_fields_doc.use_precomputed_invoice(precomputed_invoice)

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(
                f'Could not find EGS for device {precomputed_invoice.device_id}')
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync

    si_additional_fields_doc.insert()
    if is_live_sync:
        # We're running in the context of invoice submission (on_submit hook). We only want to run our ZATCA logic if
        # the invoice submits successfully after on_submit is run successfully from all apps.
        frappe.utils.background_jobs.enqueue(
            _submit_additional_fields, doc=si_additional_fields_doc, enqueue_after_commit=True
        )


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')


def _should_enable_zatca_for_invoice(invoice_id: str) -> bool:
    start_date = date(2024, 3, 1)

    if frappe.db.table_exists('Vehicle Booking Item Info'):
        # noinspection SqlResolve
        records = frappe.db.sql(
            'SELECT bv.local_trx_date_time FROM `tabVehicle Booking Item Info` bvii '
            'JOIN `tabBooking Vehicle` bv ON bvii.parent = bv.name WHERE bvii.sales_invoice = %(invoice)s',
            {'invoice': invoice_id},
            as_dict=True,
        )
        if records:
            local_date = records[0]['local_trx_date_time'].date()
            return local_date >= start_date

    posting_date = frappe.db.get_value(
        'Sales Invoice', invoice_id, 'posting_date')
    return posting_date >= start_date


def prevent_cancellation_of_sales_invoice(self: SalesInvoice | POSInvoice, method) -> None:
    is_phase_2_enabled_for_company = ZATCABusinessSettings.is_enabled_for_company(
        self.company)
    if is_phase_2_enabled_for_company:
        frappe.throw(
            msg=_('You cannot cancel sales invoice according to ZATCA Regulations.'),
            title=_('This Action Is Not Allowed'),
        )


def validate_sales_invoice(self: SalesInvoice | POSInvoice, method) -> None:
    valid = True
    is_phase_2_enabled_for_company = ZATCABusinessSettings.is_enabled_for_company(
        self.company)
    if ZATCAPhase1BusinessSettings.is_enabled_for_company(self.company) or is_phase_2_enabled_for_company:
        if len(self.taxes) == 0:
            frappe.msgprint(
                msg=_('Please include tax rate in Sales Taxes and Charges Table'),
                title=_('Validation Error'),
                indicator='red',
            )
            valid = False

    if is_phase_2_enabled_for_company:
        settings = ZATCABusinessSettings.for_company(self.company)
        if settings.type_of_business_transactions == 'Standard Tax Invoices':
            customer = cast(Customer, frappe.get_doc(
                'Customer', self.customer))
            if not is_b2b_customer(customer):
                frappe.msgprint(
                    ft(
                        'Company <b>$company</b> is configured to use Standard Tax Invoices, which require customers to '
                        'define a VAT number or one of the other IDs. Please update customer <b>$customer</b>',
                        company=self.company,
                        customer=self.customer,
                    )
                )
                valid = False

    if not valid:
        message_log = frappe.get_message_log()
        error_messages = '\n'.join(log['message'] for log in message_log)
        raise frappe.ValidationError(error_messages)


def update_sales_invoice_fields(
    self: SalesInvoice | POSInvoice, method: str, siaf_doc: Optional[SalesInvoiceAdditionalFields] = None
) -> None:
    """Populate ZATCA-specific custom fields on the invoice after submission."""
    is_phase_1_enabled = ZATCAPhase1BusinessSettings.is_enabled_for_company(
        self.company)
    is_phase_2_enabled = ZATCABusinessSettings.is_enabled_for_company(
        self.company)

    if is_phase_2_enabled:
        _update_phase_2_fields(self, siaf_doc)
    elif is_phase_1_enabled:
        _update_phase_1_fields(self)


def _update_phase_1_fields(invoice: SalesInvoice | POSInvoice) -> None:
    qr_code = (get_zatca_phase_1_qr_for_invoice(invoice.name) or '').strip()
    update_values: Dict[str, str] = {
        'custom_qr_image_src': f'data:image/png;base64,{qr_code}' if qr_code else '',
    }

    frappe.db.set_value(invoice.doctype, invoice.name,
                        update_values, update_modified=False)


def _update_phase_2_fields(
    invoice: SalesInvoice | POSInvoice, siaf_doc: Optional[SalesInvoiceAdditionalFields] = None
) -> None:
    if siaf_doc and siaf_doc.docstatus == 1 and siaf_doc.sales_invoice == invoice.name:
        siaf_name = siaf_doc.name
        integration_status = siaf_doc.integration_status
        qr_image_src = siaf_doc.qr_image_src
    else:
        siaf_info = frappe.db.get_value(
            'Sales Invoice Additional Fields',
            {'sales_invoice': invoice.name, 'docstatus': 1},
            ['name', 'integration_status'],
            as_dict=True,
        )

        if not siaf_info:
            return

        siaf_name = siaf_info['name']
        integration_status = siaf_info.get('integration_status')

        try:
            siaf_doc = cast(
                SalesInvoiceAdditionalFields,
                frappe.get_doc('Sales Invoice Additional Fields', siaf_name),
            )
            qr_image_src = siaf_doc.qr_image_src
        except Exception:
            qr_image_src = None

    update_values: Dict[str, str] = {'custom_zatca_siaf': siaf_name}

    if qr_image_src:
        update_values['custom_qr_image_src'] = qr_image_src

    if integration_status:
        update_values['custom_integration_status'] = integration_status

    frappe.db.set_value(invoice.doctype, invoice.name,
                        update_values, update_modified=False)


def update_sales_invoice_from_siaf(doc: SalesInvoiceAdditionalFields, method: str) -> None:
    """Update the linked Sales Invoice after Sales Invoice Additional Fields submission."""
    invoice_doctype = doc.invoice_doctype or 'Sales Invoice'
    if invoice_doctype not in {'Sales Invoice', 'POS Invoice'} or not doc.sales_invoice:
        return

    try:
        invoice = cast(SalesInvoice | POSInvoice, frappe.get_doc(
            invoice_doctype, doc.sales_invoice))
    except frappe.DoesNotExistError:
        logger.error(
            f"SIAF {doc.name} references missing {invoice_doctype} {doc.sales_invoice}")
        return

    update_sales_invoice_fields(invoice, method, doc)
