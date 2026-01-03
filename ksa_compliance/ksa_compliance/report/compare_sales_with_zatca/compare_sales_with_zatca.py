# Copyright (c) 2025, LavaLoon and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    # Define columns
    columns = [
        {
            "fieldname": "posting_date",
            "label": "Date",
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "name",
            "label": "Invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 170
        },
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180
        },
        {
            "fieldname": "grand_total",
            "label": "Grand Total",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "total_taxes_and_charges",
            "label": "Tax Amount",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "integration_status",
            "label": "(ZATCA)",
            "fieldtype": "Data",
            "width": 200
        }
    ]

    from_date = filters.get("from_date") or frappe.datetime.month_start()
    to_date = filters.get("to_date") or frappe.datetime.now_date()
    customer = filters.get("customer")
    integration_status = filters.get("integration_status")

    query = """
	SELECT
	  `tabSales Invoice`.`posting_date`,
	  `tabSales Invoice`.`name`,
	  `tabSales Invoice`.`customer`,
	  `tabSales Invoice`.`grand_total`,
	  `tabSales Invoice`.`total_taxes_and_charges`,
	  CASE
	    WHEN `tabSales Invoice Additional Fields`.`sales_invoice` = `tabSales Invoice`.`name`
	      THEN `tabSales Invoice Additional Fields`.`integration_status`
	    WHEN `tabSales Invoice Additional Fields`.`sales_invoice` IS NULL
	      THEN 'Not Sended'
	    ELSE 'No Sales Invoice'
	  END AS `integration_status`
	FROM `tabSales Invoice`
	LEFT JOIN `tabSales Invoice Additional Fields`
	  ON `tabSales Invoice Additional Fields`.`sales_invoice` = `tabSales Invoice`.`name`
	"""

    where_conditions = []
    params = {}

    if from_date and to_date:
        where_conditions.append("`tabSales Invoice`.`posting_date` BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    if customer:
        where_conditions.append("`tabSales Invoice`.`customer` = %(customer)s")
        params["customer"] = customer

    if integration_status:
        where_conditions.append("""
		(
		    CASE
		        WHEN `tabSales Invoice Additional Fields`.`sales_invoice` = `tabSales Invoice`.`name`
		            THEN `tabSales Invoice Additional Fields`.`integration_status`
		        WHEN `tabSales Invoice Additional Fields`.`sales_invoice` IS NULL
		            THEN 'Not Sended'
		        ELSE 'No Sales Invoice'
		    END
		) = %(integration_status)s
		""")
        params["integration_status"] = integration_status

    if where_conditions:
        query = query + " WHERE " + " AND ".join(where_conditions)

    mydata = frappe.db.sql(query, params, as_dict=True)

    return columns, mydata
