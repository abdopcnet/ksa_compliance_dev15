# KSA Compliance

![Version](https://img.shields.io/badge/version-10.12.2025-blue)


KSA Compliance is a free and open-source Frappe application designed for full compliance with ZATCA (Saudi Tax Authority) Phase 1 & 2 e-invoicing requirements.

## App Logic & Functions

- Supports both Phase 1 and Phase 2 invoice formats and workflows
- Generates and embeds QR codes and XML for invoices as per ZATCA specs
- Provides onboarding wizard for easy setup
- Handles simplified and standard invoices
- Direct and batch integration with ZATCA
- Manages tax exemption reasons and compliance logs
- Multi-company and multi-device support
- Built-in validation and audit trail for all compliance actions
- Sandbox environment for safe testing

## Quick Installation

```bash
bench get-app --branch master https://github.com/abdopcnet/ksa_compliance_dev15.git
bench setup requirements
bench --site your_site_name install-app ksa_compliance
bench --site your_site_name migrate
bench restart
```

## References

- app_name: ksa_compliance
- app_title: ksa_compliance
- app_publisher: future_support
- app_description: ksa_compliance
- app_email: abdopcnet@gmail.com
- app_license: mit
- GitHub: https://github.com/abdopcnet/ksa_compliance_dev15.git

## Support & Contribution

- Community: [GitHub Discussions](https://github.com/abdopcnet/ksa_compliance_dev15/discussions)
- Issues & Features: [GitHub Issues](https://github.com/abdopcnet/ksa_compliance_dev15/issues)
- Paid features/support: abdopcnet@gmail.com
- Contribution guidelines: [ERPNext Guidelines](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)

## License

Copyright © 2025 future_support. Licensed under MIT.
