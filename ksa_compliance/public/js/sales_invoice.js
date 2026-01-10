frappe.ui.form.on('Sales Invoice', {
	setup: function (frm) {
		frm.set_query('custom_return_against_additional_references', function (doc) {
			// Similar to logic in erpnext/public/js/controllers/transaction.js for return_against
			let filters = {
				docstatus: 1,
				is_return: 0,
				company: doc.company,
			};
			if (frm.fields_dict['customer'] && doc.customer) filters['customer'] = doc.customer;
			if (frm.fields_dict['supplier'] && doc.supplier) filters['supplier'] = doc.supplier;

			return {
				filters: filters,
			};
		});
	},
	async refresh(frm) {
		await set_zatca_integration_status(frm);
		await set_zatca_discount_reason(frm);

		// Add Resend to Zatca button for Administrator only
		if (frappe.session.user === 'Administrator') {
			if (
				frm.doc.custom_integration_status &&
				frm.doc.custom_integration_status !== 'Accepted' &&
				frm.doc.custom_integration_status !== 'Accepted with warnings'
			) {
				frm.add_custom_button(__('Resend To Zatca'), async function () {
					// Find the latest Sales Invoice Additional Fields for this invoice
					let result = await frappe.call({
						method: 'frappe.client.get_list',
						args: {
							doctype: 'Sales Invoice Additional Fields',
							filters: {
								sales_invoice: frm.doc.name,
								is_latest: 1,
							},
							fields: ['name'],
							limit_page_length: 1,
						},
					});

					if (result.message && result.message.length > 0) {
						let siaf_name = result.message[0].name;
						let invoice_link = `<a target="_blank" href="${frappe.router.make_url([
							'Form',
							'Sales Invoice',
							frm.doc.name,
						])}">${frm.doc.name}</a>`;
						let message = __(
							"<p>This will create a new Sales Invoice Additional Fields document for the invoice '{0}' and " +
								'submit it to ZATCA. <strong>Make sure you have updated any bad configuration that lead to the initial rejection</strong>.</p>' +
								'<p>Do you want to proceed?</p>',
							[invoice_link],
						);

						frappe.confirm(message, async () => {
							await frappe.call({
								method: 'ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.fix_rejection',
								args: { id: siaf_name },
								freeze: true,
								freeze_message: __('Please wait...'),
							});
							frappe.show_alert({
								message: __(
									'New Sales Invoice Additional Fields created and submitted to ZATCA',
								),
								indicator: 'green',
							});
							frm.reload_doc();
						});
					} else {
						frappe.msgprint(
							__('No Sales Invoice Additional Fields found for this invoice'),
						);
					}
				}).addClass('btn-success');
			}
		}
	},
});

async function set_zatca_discount_reason(frm) {
	const zatca_discount_reasons = await get_zatca_discount_reason_codes();
	frm.fields_dict.custom_zatca_discount_reason.set_data(zatca_discount_reasons);
}

async function set_zatca_integration_status(frm) {
	const res = await frappe.call({
		method: 'ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.get_zatca_integration_status',
		args: {
			invoice_id: frm.doc.name,
			doctype: frm.doc.doctype,
		},
	});

	const status = res.integration_status;
	if (status) {
		let color = 'blue';
		if (status === 'Accepted') {
			color = 'green';
		} else if (['Rejected', 'Resend'].includes(status)) {
			color = 'red';
		}
		frm.set_intro(`<b>Zatca Status: ${status}</b>`, color);
	}
}

async function get_zatca_discount_reason_codes() {
	const res = await frappe.call({
		method: 'ksa_compliance.invoice.get_zatca_invoice_discount_reason_list',
	});
	return res.message;
}
