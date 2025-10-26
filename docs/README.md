# Documentation Index

Complete documentation for Security Central.

## 📚 Getting Started

Start here if you're new to Security Central:

1. **[Main README](../README.md)** - Project overview and features
2. **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
3. **[SETUP.md](SETUP.md)** - Detailed setup and configuration guide

## 🛠️ Development

For contributors and developers:

1. **[CONTRIBUTING.md](../CONTRIBUTING.md)** - How to contribute
2. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide and best practices
3. **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - Current project status

## 📖 Operations

For running and maintaining Security Central:

1. **[RUNBOOK.md](RUNBOOK.md)** - Operational runbook and troubleshooting
2. **[SECRET_ROTATION.md](SECRET_ROTATION.md)** - Secret and token rotation guide
3. **[WORKFLOW_UPDATES.md](WORKFLOW_UPDATES.md)** - GitHub Actions workflow updates

## 🎯 Planning & Architecture

Long-term vision and technical details:

1. **[MASTER_PLAN.md](MASTER_PLAN.md)** - Long-term roadmap and vision
2. **[MAGIC_NUMBERS_REPORT.md](MAGIC_NUMBERS_REPORT.md)** - Code quality analysis
3. **[SUGGESTED_CONSTANTS.py](SUGGESTED_CONSTANTS.py)** - Constant definitions

## 📊 Reports

Generated reports are stored in `reports/`:

```
reports/
├── daily/      # Daily scan reports
└── weekly/     # Weekly audit reports
```

Reports are generated automatically by workflows and should not be committed to the repository.

---

## Quick Reference

### Common Tasks

| Task | Documentation |
|------|--------------|
| First-time setup | [QUICKSTART.md](QUICKSTART.md) |
| Add a new repository | [SETUP.md](SETUP.md#adding-repositories) |
| Configure scanning | [SETUP.md](SETUP.md#configuration) |
| Troubleshoot issues | [RUNBOOK.md](RUNBOOK.md#troubleshooting) |
| Rotate secrets | [SECRET_ROTATION.md](SECRET_ROTATION.md) |
| Contribute code | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Run tests | [DEVELOPMENT.md](../DEVELOPMENT.md#testing-strategy) |

### Architecture Overview

Security Central consists of:

- **Core Scripts** (`scripts/`): Scanning, analysis, reporting
- **Configuration** (`config/`): Repository and policy definitions
- **Workflows** (`.github/workflows/`): Automated CI/CD pipelines
- **Tests** (`tests/`): Comprehensive test suite

### Key Features

✅ Multi-ecosystem scanning (Python, JVM, npm, PowerShell)
✅ Automated vulnerability patching
✅ SARIF export to GitHub Security
✅ PagerDuty integration for CRITICAL alerts
✅ Daily scans with weekly comprehensive audits
✅ Smart auto-merge with confidence scoring

---

## Need Help?

1. **Check existing documentation** - Use the index above
2. **Search issues** - [GitHub Issues](https://github.com/cboyd0319/security-central/issues)
3. **Ask questions** - Open a new issue or discussion

---

**Last Updated:** 2025-10-26
**Documentation Version:** 2.0
