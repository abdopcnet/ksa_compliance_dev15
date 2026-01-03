// Frontend logging: console.log('[customer.js] method: function_name')

// Constants
const VALIDATION_FIELDS = [
	{ field: 'customer_name', label: 'Customer Name' },
	{ field: 'customer_name_in_arabic', label: 'Customer Name in Arabic' },
	{ field: 'tax_id', label: 'Tax ID' },
];

const ALLOWED_PATTERN = /^[a-zA-Z0-9\u0600-\u06FF ]*$/;
const INVALID_PATTERN = /[^a-zA-Z0-9\u0600-\u06FF ]/;

// Form Events
frappe.ui.form.on('Customer', {
	setup: function (frm) {
		// Workaround for a change introduced in frappe v15.38.0: https://github.com/frappe/frappe/issues/27430
		if (frm.is_dialog) return;

		frm.set_df_property('custom_additional_ids', 'cannot_delete_rows', 1);
		frm.set_df_property('custom_additional_ids', 'cannot_add_rows', 1);
	},
	refresh: function (frm) {
		add_other_ids_if_new(frm);
		setup_field_validation(frm);
	},
	tax_id: (frm) => {
		// Sync tax_id to custom_vat_registration_number
		if (frm.doc.tax_id && frm.doc.tax_id !== frm.doc.custom_vat_registration_number) {
			frm.set_value('custom_vat_registration_number', frm.doc.tax_id);
		}
	},
	custom_vat_registration_number: (frm) => {
		// Sync custom_vat_registration_number to tax_id
		if (
			frm.doc.custom_vat_registration_number &&
			frm.doc.custom_vat_registration_number !== frm.doc.tax_id
		) {
			frm.set_value('tax_id', frm.doc.custom_vat_registration_number);
		}
	},
	custom_passport_no: (frm) => sync(frm, 'PAS', frm.doc.custom_passport_no),
	validate: function (frm) {
		// Validate fields: only letters, numbers, and Arabic characters allowed
		const invalid_fields = VALIDATION_FIELDS.filter((obj) => {
			const value = (frm.doc[obj.field] || '').toString().trim();
			return value && INVALID_PATTERN.test(value);
		});

		if (invalid_fields.length) {
			frappe.msgprint({
				title: __('Input Error'),
				message:
					__('Only letters and numbers are allowed in the following fields:') +
					'<ul style="margin-top:8px">' +
					invalid_fields.map((l) => `<li>${l.label}</li>`).join('') +
					'</ul>',
				indicator: 'red',
			});
			frappe.validated = false;
			return false;
		}

		console.log('[customer.js] method: validate');
	},
});

// Helper Functions
function setup_field_validation(frm) {
	// Setup real-time validation on input: filter invalid characters
	VALIDATION_FIELDS.forEach(function (obj) {
		const field = frm.fields_dict[obj.field];
		if (field && field.$input) {
			field.$input.on('input', function () {
				if (!ALLOWED_PATTERN.test(this.value)) {
					frappe.show_alert(
						{
							message:
								__('Only letters and numbers are allowed in field: ') + obj.label,
							indicator: 'orange',
						},
						3,
					);
					this.value = this.value.replace(/[^a-zA-Z0-9\u0600-\u06FF ]/g, '');
				}
			});
		}
	});
}

function add_other_ids_if_new(frm) {
	// Initialize additional IDs list for new customers
	if (frm.doc.custom_additional_ids.length === 0) {
		var buyer_id_list = [];
		buyer_id_list.push(
			{
				type_name: 'Tax Identification Number',
				type_code: 'TIN',
			},
			{
				type_name: 'Commercial Registration Number',
				type_code: 'CRN',
			},
			{
				type_name: 'MOMRAH License',
				type_code: 'MOM',
			},
			{
				type_name: 'MHRSD License',
				type_code: 'MLS',
			},
			{
				type_name: '700 Number',
				type_code: '700',
			},
			{
				type_name: 'MISA License',
				type_code: 'SAG',
			},
			{
				type_name: 'National ID',
				type_code: 'NAT',
			},
			{
				type_name: 'GCC ID',
				type_code: 'GCC',
			},
			{
				type_name: 'Iqama',
				type_code: 'IQA',
			},
			{
				type_name: 'Passport ID',
				type_code: 'PAS',
			},
			{
				type_name: 'Other ID',
				type_code: 'OTH',
			},
		);
		frm.set_value('custom_additional_ids', buyer_id_list);
	}
}

function sync(frm, code, val) {
	// Sync passport number to additional IDs table
	const rows = frm.doc.custom_additional_ids || [];
	if (!val || !rows.length) return;

	let updated = false;
	rows.forEach((row) => {
		if (row.type_code === code) {
			frappe.model.set_value(row.doctype, row.name, 'value', val);
			updated = true;
		}
	});
	if (updated) frm.refresh_field('custom_additional_ids');
}
