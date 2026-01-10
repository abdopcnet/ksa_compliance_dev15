import frappe


def execute():
    """Create branch_cr_no field on Sales Invoice if Branch accounting dimension exists."""

    check_and_create_branch_cr_no_field()
    frappe.db.commit()


def check_and_create_branch_cr_no_field():
    """Check Branch accounting dimension and create branch_cr_no field if needed"""

    try:
        # Check if Branch accounting dimension exists
        branch_accounting_dimension = frappe.get_all(
            "Accounting Dimension",
            filters={"document_type": "Branch"},
            fields=["name", "document_type", "label", "disabled"]
        )

        if branch_accounting_dimension:
            dimension = branch_accounting_dimension[0]
            if dimension.get('disabled'):
                print("⚠ Branch accounting dimension exists but is disabled")
                print("Branch CR field will not be created")
            else:
                print("✓ Branch accounting dimension exists and is enabled")
                # Create branch_cr_no field
                create_branch_cr_no_field_if_needed()
        else:
            print("ℹ Branch accounting dimension not found")
            print("Branch CR field will not be created")

    except Exception as e:
        print(f"Error checking Branch accounting dimension: {e}")


def create_branch_cr_no_field_if_needed():
    """Create or update branch_cr_no field if needed"""

    field_name = "Sales Invoice-branch_cr_no"

    # Check if field exists
    if frappe.db.exists('Custom Field', field_name):
        print(f"✓ Field {field_name} already exists, updating properties...")

        # Update existing field properties
        existing_field = frappe.get_doc('Custom Field', field_name)
        existing_field.fetch_from = "branch.custom_cr_no"
        existing_field.fetch_if_empty = 1
        existing_field.read_only = 1
        existing_field.insert_after = "company_cr_no"
        existing_field.label = "Branch Commercial Registration Number"
        existing_field.placeholder = "Must be 10 digits"
        existing_field.save(ignore_permissions=True)
        print(f"✓ Updated {field_name} field successfully")
        return

    # Check if Branch-custom_cr_no exists
    if not frappe.db.exists('Custom Field', 'Branch-custom_cr_no'):
        print("✗ Branch-custom_cr_no field not found, cannot create branch_cr_no with fetch_from")
        return

    try:
        # Create the field
        field = frappe.new_doc('Custom Field')
        field.update({
            'dt': 'Sales Invoice',
            'fieldname': 'branch_cr_no',
            'fieldtype': 'Data',
            'label': 'Branch Commercial Registration Number',
            'fetch_from': 'branch.custom_cr_no',
            'fetch_if_empty': 1,
            'read_only': 1,
            'insert_after': 'company_cr_no',
            'module': 'KSA Compliance',
            'placeholder': 'Must be 10 digits',
            'allow_on_submit': 1
        })
        field.insert(ignore_permissions=True)
        print(f"✓ Created {field_name} field successfully")
        print("✓ Field configured with fetch_from branch.custom_cr_no")

    except Exception as e:
        print(f"✗ Error creating {field_name} field: {e}")
