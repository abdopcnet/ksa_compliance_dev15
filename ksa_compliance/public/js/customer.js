// Frontend logging: console.log('[customer.js] method: function_name')

// Constants
const VALIDATION_FIELDS = [
	{ field: 'customer_name', label: 'Customer Name' },
	{ field: 'customer_name_in_arabic', label: 'Customer Name in Arabic' },
	{ field: 'tax_id', label: 'Tax ID' },
	{ field: 'custom_vat_registration_number', label: 'VAT Registration Number' },
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
		// Setup real-time validation only (main validation in Python)
		setup_field_validation(frm);
		setup_child_table_validation(frm);
	},
	tax_id: (frm) => {
		// Sync tax_id to custom_vat_registration_number (real-time)
		if (frm.doc.tax_id && frm.doc.tax_id !== frm.doc.custom_vat_registration_number) {
			frm.set_value('custom_vat_registration_number', frm.doc.tax_id);
		}
	},
	custom_vat_registration_number: (frm) => {
		// Sync custom_vat_registration_number to tax_id (real-time)
		if (
			frm.doc.custom_vat_registration_number &&
			frm.doc.custom_vat_registration_number !== frm.doc.tax_id
		) {
			frm.set_value('tax_id', frm.doc.custom_vat_registration_number);
		}
	},
	custom_passport_no: (frm) => sync(frm, 'PAS', frm.doc.custom_passport_no),
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

function setup_child_table_validation(frm) {
	// Setup real-time validation for child table custom_additional_ids value field
	if (!frm.fields_dict.custom_additional_ids?.grid) return;

	const grid = frm.fields_dict.custom_additional_ids.grid;

	// Add validation when grid refreshes
	function add_validation_to_rows() {
		if (grid.grid_rows) {
			grid.grid_rows.forEach(function (row) {
				const value_field = row.on_grid_fields_dict?.value;
				if (
					value_field &&
					value_field.$input &&
					!value_field.$input.data('validation-added')
				) {
					value_field.$input.data('validation-added', true);
					value_field.$input.on('input', function () {
						if (!ALLOWED_PATTERN.test(this.value)) {
							frappe.show_alert(
								{
									message: __(
										'Only letters and numbers are allowed in Value field',
									),
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
	}

	// Apply validation on refresh
	add_validation_to_rows();

	// Re-apply validation when grid refreshes
	grid.wrapper.on('grid-row-render', function () {
		setTimeout(add_validation_to_rows, 100);
	});
}

function sync(frm, code, val) {
	// Sync passport number to additional IDs table (UI-only helper)
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
