import frappe


def execute():
    """Dynamically validate all custom fields with fetch_from relationships."""

    validate_all_fetch_from_relationships()
    frappe.db.commit()


def validate_all_fetch_from_relationships():
    """Validate all custom fields that use fetch_from to ensure source fields exist."""

    # Get all custom fields that have fetch_from set
    fields_with_fetch_from = frappe.get_all(
        "Custom Field",
        filters={"fetch_from": ["!=", ""]},
        fields=["name", "dt", "fieldname", "fetch_from"]
    )

    if not fields_with_fetch_from:
        print("ℹ No custom fields with fetch_from found")
        return

    print(f"📋 Found {len(fields_with_fetch_from)} custom fields with fetch_from")

    errors = []
    warnings = []
    ok_count = 0

    for field in fields_with_fetch_from:
        fetch_from = field.fetch_from
        # Parse fetch_from format: "doctype.fieldname" or "link_field.fieldname"
        parts = fetch_from.split(".")

        if len(parts) != 2:
            warnings.append(f"{field.name}: Invalid fetch_from format '{fetch_from}'")
            continue

        source_link_field, source_fieldname = parts

        # Determine source doctype
        # If source_link_field is a link field in the same doctype, get its options
        source_doctype = None

        # First check standard DocField (most common case)
        try:
            meta = frappe.get_meta(field.dt)
            df = meta.get_field(source_link_field)
            if df and df.fieldtype == "Link":
                source_doctype = df.options
        except:
            pass

        # If not found in standard fields, check Custom Fields
        if not source_doctype:
            link_field = frappe.db.get_value(
                "Custom Field",
                {"dt": field.dt, "fieldname": source_link_field},
                ["fieldtype", "options"],
                as_dict=True
            )

            if link_field and link_field.fieldtype == "Link":
                source_doctype = link_field.options

        if not source_doctype:
            warnings.append(f"{field.name}: Cannot determine source doctype for '{source_link_field}'")
            continue

        # Check if source field exists (Custom Field or standard field)
        source_field_name = f"{source_doctype}-{source_fieldname}"
        source_exists = False

        # Check if it's a Custom Field
        if frappe.db.exists("Custom Field", source_field_name):
            source_exists = True
        else:
            # Check if it's a standard field in the source doctype
            try:
                source_meta = frappe.get_meta(source_doctype)
                if source_meta.has_field(source_fieldname):
                    source_exists = True
            except:
                pass

        if source_exists:
            ok_count += 1
            print(f"✓ {field.name}: Source field {source_fieldname} exists in {source_doctype}")
        else:
            errors.append(
                f"{field.name} (fetches from {fetch_from}): Source field {source_fieldname} missing in {source_doctype}")
            print(f"✗ {field.name}: Source field {source_fieldname} missing in {source_doctype}")

    print(f"\n📊 Summary:")
    print(f"  ✓ Valid relationships: {ok_count}")
    print(f"  ✗ Missing source fields: {len(errors)}")
    print(f"  ⚠ Warnings: {len(warnings)}")

    if errors:
        print(f"\n❌ Errors found:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print(f"\n⚠ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
