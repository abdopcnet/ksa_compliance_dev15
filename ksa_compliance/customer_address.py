import frappe
from frappe import _


def validate_customer_fields(doc, method):
    """Trim whitespace from customer fields."""
    fields_to_trim = ['customer_name', 'customer_name_in_arabic', 'tax_id']
    for field in fields_to_trim:
        if doc.get(field):
            trimmed = str(doc.get(field)).strip()
            if doc.get(field) != trimmed:
                doc.set(field, trimmed)


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
