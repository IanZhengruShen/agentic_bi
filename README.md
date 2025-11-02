# Agentic BI

An intelligent business intelligence platform with agentic capabilities.

## Development Workflow

This project follows **trunk-based development** practices:

- All development happens on short-lived feature branches
- Main branch is always deployable
- Small, frequent merges to main
- Feature flags for work-in-progress features

### Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd agentic_bi

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Start working
git checkout -b feature/your-feature
# Make changes, commit, and push
# Open a PR to main
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed workflow guidelines.

## CI/CD

All PRs must pass:
- Automated tests
- Security scanning
- Code quality checks
- Branch age and size checks

Status checks are enforced on the `main` branch.

## Branch Protection

The `main` branch is protected with:
- Required pull request reviews
- Required status checks
- No direct pushes (except emergencies)
- Linear history enforcement

See [.github/BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md) for details.

## Resources

- [Contributing Guide](CONTRIBUTING.md) - Development workflow and best practices
- [Branch Protection Guidelines](.github/BRANCH_PROTECTION.md) - Branch protection rules
- [CI/CD Pipeline](.github/workflows/trunk-ci.yml) - Automated checks configuration

## Getting Help

- Review the contributing guide
- Check existing issues and PRs
- Ask questions in team channels

---

**Remember:** Integrate early, integrate often!
