frappe.ui.form.on('Customer', {
  setup: function (frm) {
    // Workaround for a change introduced in frappe v15.38.0: https://github.com/frappe/frappe/issues/27430
    if (frm.is_dialog) return;

    frm.set_df_property('custom_additional_ids', 'cannot_delete_rows', 1);
    frm.set_df_property('custom_additional_ids', 'cannot_add_rows', 1);
  },
  refresh: function (frm) {
    add_other_ids_if_new(frm);
    // تحقق الحقول أثناء الكتابة
    const fields_to_filter = [
      { field: 'customer_name', label: 'اسم العميل' },
      { field: 'tax_id', label: 'الرقم الضريبي' },
    ];
    fields_to_filter.forEach(function (obj) {
      const field = frm.fields_dict[obj.field];
      if (field && field.$input) {
        field.$input.on('input', function () {
          const allowed = /^[a-zA-Z0-9\u0600-\u06FF ]*$/;
          if (!allowed.test(this.value)) {
            frappe.show_alert(
              {
                message: __('مسموح إدخال أحرف أو أرقام فقط في حقل: ') + obj.label,
                indicator: 'orange',
              },
              3,
            );
            this.value = this.value.replace(/[^a-zA-Z0-9\u0600-\u06FF ]/g, '');
          }
        });
      }
    });
  },
  tax_id: (frm) =>
    frm.doc.tax_id && frm.set_value('custom_vat_registration_number', frm.doc.tax_id),
  custom_passport_no: (frm) => sync(frm, 'PAS', frm.doc.custom_passport_no),
  before_save: function (frm) {
    const fields_to_filter = [
      { field: 'customer_name', label: 'اسم العميل' },
      { field: 'tax_id', label: 'الرقم الضريبي' },
    ];
    let invalid_fields = [];
    let has_error = false;
    fields_to_filter.forEach(function (obj) {
      if (frm.doc[obj.field] === undefined) return;
      let value = frm.doc[obj.field] || '';
      value = value.toString().replace(/^\s+/, '').replace(/\s+$/, '');
      value = value.replace(/\s+/g, ' ');
      frm.set_value(obj.field, value);
      if (/[^a-zA-Z0-9\u0600-\u06FF ]/.test(value)) {
        invalid_fields.push(obj.label);
        has_error = true;
        if (frm.fields_dict[obj.field]) {
          frm.set_df_property(obj.field, 'description', __('مسموح بإدخال أحرف وأرقام فقط'));
          frm.fields_dict[obj.field].$wrapper?.addClass('has-error');
        }
      } else if (frm.fields_dict[obj.field]) {
        frm.set_df_property(obj.field, 'description', '');
        frm.fields_dict[obj.field].$wrapper?.removeClass('has-error');
      }
    });
    if (has_error) {
      frappe.msgprint({
        title: __('خطأ في الإدخال'),
        message:
          __('مسموح إدخال أحرف أو أرقام فقط في الحقول التالية:') +
          '<ul style="margin-top:8px">' +
          invalid_fields.map((l) => `<li>${l}</li>`).join('') +
          '</ul>',
        indicator: 'red',
      });
      frappe.validated = false;
      return false;
    }
  },
});

function add_other_ids_if_new(frm) {
  // TODO: update permissions for child doctype
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
  const rows = frm.doc.custom_additional_ids || [];
  if (!val || !rows.length) return; // لا داعي لأي عملية إذا كانت القيمة فارغة أو لا توجد صفوف

  let updated = false;
  rows.forEach((row) => {
    if (row.type_code === code) {
      frappe.model.set_value(row.doctype, row.name, 'value', val);
      updated = true;
    }
  });
  if (updated) frm.refresh_field('custom_additional_ids');
}
