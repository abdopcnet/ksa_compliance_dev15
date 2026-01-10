import frappe
from frappe import _
import re


# Validation pattern: only letters, numbers, Arabic characters, and spaces
ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9\u0600-\u06FF ]*$')
INVALID_PATTERN = re.compile(r'[^a-zA-Z0-9\u0600-\u06FF ]')
# Child table value field: only numbers
CHILD_VALUE_ALLOWED_PATTERN = re.compile(r'^[0-9]*$')
CHILD_VALUE_INVALID_PATTERN = re.compile(r'[^0-9]')

# Fields to validate and trim
VALIDATION_FIELDS = ['customer_name', 'customer_name_in_arabic', 'tax_id', 'custom_vat_registration_number']


def validate_customer_fields(doc, method):
    """Validate and trim customer fields."""
    # Trim whitespace
    for field in VALIDATION_FIELDS:
        if doc.get(field):
            trimmed = str(doc.get(field)).strip()
            if doc.get(field) != trimmed:
                doc.set(field, trimmed)

    # Validate field values: only letters, numbers, and Arabic characters
    invalid_fields = []
    meta = frappe.get_meta(doc.doctype)
    for field in VALIDATION_FIELDS:
        value = doc.get(field)
        if value:
            value_str = str(value).strip()
            if value_str and INVALID_PATTERN.search(value_str):
                field_df = meta.get_field(field)
                field_label = field_df.label if field_df else field.replace('_', ' ').title()
                invalid_fields.append(field_label)

    # Validate child table custom_additional_ids value field (numbers only)
    invalid_child_fields = []
    if doc.get('custom_additional_ids'):
        for idx, row in enumerate(doc.custom_additional_ids, start=1):
            if row.get('value'):
                value_str = str(row.value).strip()
                if value_str and CHILD_VALUE_INVALID_PATTERN.search(value_str):
                    row_label = f"{_('Additional IDs')} - {_('Row')} {idx} ({row.get('type_name', _('Value'))})"
                    invalid_child_fields.append(row_label)

    if invalid_fields:
        frappe.throw(
            _('Only letters and numbers are allowed in the following fields:') +
            '<ul style="margin-top:8px">' +
            ''.join([f'<li>{field}</li>' for field in invalid_fields]) +
            '</ul>',
            title=_('Input Error')
        )

    if invalid_child_fields:
        frappe.throw(
            _('Only numbers are allowed in the following fields:') +
            '<ul style="margin-top:8px">' +
            ''.join([f'<li>{field}</li>' for field in invalid_child_fields]) +
            '</ul>',
            title=_('Input Error')
        )


def initialize_additional_ids(doc, method):
    """Initialize additional IDs list for new customers."""
    if doc.is_new() and len(doc.get('custom_additional_ids', [])) == 0:
        buyer_id_list = [
            {'type_name': 'Tax Identification Number', 'type_code': 'TIN'},
            {'type_name': 'Commercial Registration Number', 'type_code': 'CRN'},
            {'type_name': 'MOMRAH License', 'type_code': 'MOM'},
            {'type_name': 'MHRSD License', 'type_code': 'MLS'},
            {'type_name': '700 Number', 'type_code': '700'},
            {'type_name': 'MISA License', 'type_code': 'SAG'},
            {'type_name': 'National ID', 'type_code': 'NAT'},
            {'type_name': 'GCC ID', 'type_code': 'GCC'},
            {'type_name': 'Iqama', 'type_code': 'IQA'},
            {'type_name': 'Passport ID', 'type_code': 'PAS'},
            {'type_name': 'Other ID', 'type_code': 'OTH'},
        ]
        for item in buyer_id_list:
            doc.append('custom_additional_ids', item)


@frappe.whitelist()
def initialize_customer_additional_ids(customer):
    """Initialize Additional Buyer IDs table for existing customer if empty."""
    try:
        if not frappe.db.exists('Customer', customer):
            return {'status': 'error', 'message': 'Customer not found'}

        customer_doc = frappe.get_doc('Customer', customer)

        # Check if table is empty
        has_no_rows = not customer_doc.get('custom_additional_ids') or len(
            customer_doc.get('custom_additional_ids', [])) == 0

        if has_no_rows:
            # Initialize all standard rows
            buyer_id_list = [
                {'type_name': 'Tax Identification Number', 'type_code': 'TIN'},
                {'type_name': 'Commercial Registration Number', 'type_code': 'CRN'},
                {'type_name': 'MOMRAH License', 'type_code': 'MOM'},
                {'type_name': 'MHRSD License', 'type_code': 'MLS'},
                {'type_name': '700 Number', 'type_code': '700'},
                {'type_name': 'MISA License', 'type_code': 'SAG'},
                {'type_name': 'National ID', 'type_code': 'NAT'},
                {'type_name': 'GCC ID', 'type_code': 'GCC'},
                {'type_name': 'Iqama', 'type_code': 'IQA'},
                {'type_name': 'Passport ID', 'type_code': 'PAS'},
                {'type_name': 'Other ID', 'type_code': 'OTH'},
            ]
            for item in buyer_id_list:
                customer_doc.append('custom_additional_ids', item)

            customer_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {'status': 'initialized', 'message': 'Additional Buyer IDs initialized successfully'}

        return {'status': 'ok', 'message': 'Table already exists'}
    except Exception as e:
        frappe.log_error(
            message=f"Error initializing Additional Buyer IDs for Customer {customer}: {str(e)}\n{frappe.get_traceback()}",
            title=_("initialize_customer_additional_ids failed")
        )
        return {'status': 'error', 'message': str(e)}


def customer_address_link(doc, method):
    """Create independent customer address based on company address when saving Customer."""
    try:
        frappe.logger().info(
            f"[customer_address.py] method: customer_address_link - Customer: {doc.name}, Method: {method}")
        # Get company address (first available company address)
        company_address = frappe.get_all(
            "Address",
            filters={"is_your_company_address": 1},
            fields=["name"],
            limit=1
        )

        if not company_address:
            # No company address found, skip creation
            return

        company_address_name = company_address[0].name
        company_address_doc = frappe.get_doc("Address", company_address_name)

        # Check if customer already has an address with same data (avoid duplicates)
        customer_name = doc.name
        existing_address = _find_existing_customer_address(customer_name, company_address_doc)

        if existing_address:
            # Address already exists for this customer with same data, skip
            return

        # Create new independent address for customer
        new_address = frappe.new_doc("Address")

        # Copy all fields from company address using as_dict() to include all fields including custom fields
        company_address_dict = company_address_doc.as_dict()

        # Copy all fields except specific ones we need to override
        exclude_fields = {"name", "address_title", "is_your_company_address", "links",
                          "doctype", "docstatus", "owner", "creation", "modified", "modified_by"}

        for field, value in company_address_dict.items():
            if field not in exclude_fields and value is not None:
                # Skip system fields and links (will be set separately)
                if field.startswith("_") or field == "amended_from":
                    continue
                try:
                    new_address.set(field, value)
                except Exception:
                    # Skip fields that can't be set (read-only, computed, etc.)
                    continue

        # Set customer-specific values
        new_address.address_title = doc.customer_name or doc.name
        new_address.is_your_company_address = 0

        # Link to Customer only (not Company)
        new_address.append("links", {
            "link_doctype": "Customer",
            "link_name": customer_name
        })

        # Save address
        new_address.insert(ignore_permissions=True)

        frappe.logger().info(
            f"[[contact_address_quick_entry.py]] Created address {new_address.name} for customer {customer_name}"
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error creating customer address: {str(e)}\n{frappe.get_traceback()}",
            title=_("customer_address_link failed for Customer {0}").format(doc.name)
        )


def _find_existing_customer_address(customer_name, company_address_doc):
    """Check if customer already has an address with same data as company address."""
    try:
        # Get all addresses linked to this customer
        customer_addresses = frappe.get_all(
            "Dynamic Link",
            filters={
                "link_doctype": "Customer",
                "link_name": customer_name,
                "parenttype": "Address"
            },
            fields=["parent"],
            pluck="parent"
        )

        if not customer_addresses:
            return None

        # Check each address to see if it matches company address data
        for addr_name in customer_addresses:
            addr_doc = frappe.get_doc("Address", addr_name)

            # Compare key fields
            key_fields = ["address_line1", "city", "country", "pincode"]
            matches = True

            for field in key_fields:
                company_value = company_address_doc.get(field) or ""
                addr_value = addr_doc.get(field) or ""
                if company_value != addr_value:
                    matches = False
                    break

            if matches:
                return addr_name

        return None

    except Exception:
        # If error in comparison, return None to allow creation
        return None
