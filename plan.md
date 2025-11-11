## Task Plan

- Review existing ZATCA-related custom field definitions for `Sales Invoice` and `POS Invoice` to confirm whether `custom_zatca_siaf`, `custom_qr_image_src`, and `custom_integration_status` are provisioned.
- If missing, add a database patch that creates the required custom fields using Frappe utilities, ensuring idempotent execution.
- Consider safeguarding runtime updates by checking for column availability before calling `frappe.db.set_value`, preventing OperationalError during submission.
