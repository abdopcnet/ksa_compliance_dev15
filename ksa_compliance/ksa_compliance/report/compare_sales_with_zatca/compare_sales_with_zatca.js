// Copyright (c) 2025, LavaLoon and contributors
// For license information, please see license.txt

frappe.query_reports['compare_Sales_with_zatca'] = {
	filters: [
		{
			fieldname: 'from_date',
			label: 'من تاريخ',
			fieldtype: 'Date',
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: 'to_date',
			label: 'إلى تاريخ',
			fieldtype: 'Date',
			default: frappe.datetime.now_date(),
		},
		{
			fieldname: 'customer',
			label: 'العميل',
			fieldtype: 'Link',
			options: 'Customer',
		},
		{
			fieldname: 'integration_status',
			label: 'حالة التكامل',
			fieldtype: 'Select',
			options: '\nAccepted\nAccepted with warnings\nNot Sended\nNo Sales Invoice',
		},
	],
};
