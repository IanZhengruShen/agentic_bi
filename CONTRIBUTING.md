# Contributing to Agentic BI

We follow **trunk-based development** practices. This guide will help you understand our workflow and contribute effectively.

## Trunk-Based Development Principles

1. **Main is always deployable** - The `main` branch should always be in a releasable state
2. **Small, frequent commits** - Make small changes that can be integrated quickly
3. **Short-lived branches** - Feature branches should live no longer than 1-3 days
4. **Continuous integration** - All changes trigger automated tests and checks
5. **Feature flags** - Use feature flags for incomplete features rather than long-lived branches

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd agentic_bi

# Install pre-commit hooks (if using)
# pip install pre-commit
# pre-commit install

# Create a short-lived feature branch
git checkout -b feature/your-feature-name

# Make your changes, commit frequently
git add .
git commit -m "Add feature X"

# Push and create a PR
git push -u origin feature/your-feature-name
```

## Development Workflow

### 1. Before Starting Work

- Pull the latest changes from `main`:
  ```bash
  git checkout main
  git pull origin main
  ```

- Create a short-lived feature branch:
  ```bash
  git checkout -b feature/brief-description
  # or
  git checkout -b fix/bug-description
  # or
  git checkout -b yourname/task-description
  ```

### 2. Making Changes

- **Keep changes small and focused** - One feature/fix per branch
- **Commit frequently** - Small, atomic commits are easier to review and debug
- **Write clear commit messages** - Explain the "why" not just the "what"
- **Test locally** - Run tests before pushing
- **Keep your branch updated** - Regularly rebase on main to avoid merge conflicts

```bash
# Rebase frequently to stay current
git fetch origin
git rebase origin/main
```

### 3. Opening a Pull Request

- Push your branch:
  ```bash
  git push -u origin feature/your-feature-name
  ```

- Open a PR against `main` immediately (use draft if not ready)
- Fill out the PR template completely
- Link any relevant issues
- Request reviews from teammates

### 4. Pull Request Guidelines

**Good PRs are:**
- Small (< 20 files changed, < 500 lines changed)
- Focused on a single concern
- Well-tested with passing CI
- Clearly documented
- Ready to merge within 1-3 days

**If your PR is getting large:**
- Break it into multiple smaller PRs
- Use feature flags to merge incomplete features
- Consider refactoring as a separate PR

### 5. Code Review Process

- Reviews should happen quickly (within a few hours)
- Reviewers: prioritize unblocking teammates
- Authors: respond to feedback promptly
- Use "Resolve conversation" to track addressed feedback
- Re-request review after addressing comments

### 6. Merging

Once approved and CI passes:
- **Squash and merge** (preferred) - Keeps history clean
- **Rebase and merge** (alternative) - If commits are well-structured
- **Never merge without CI passing**
- **Delete your branch immediately after merging**

### 7. After Merging

```bash
# Switch back to main and pull
git checkout main
git pull origin main

# Delete local branch
git branch -d feature/your-feature-name
```

## Feature Flags

For features that take longer than a few days to complete:

1. **Hide behind a feature flag** - Use environment variables or a feature flag service
2. **Merge frequently** - Integrate your work even if incomplete
3. **Enable progressively** - Test in production with a small percentage of users

Example:
```python
# Using a simple feature flag
if os.getenv('FEATURE_NEW_DASHBOARD', 'false').lower() == 'true':
    return new_dashboard()
else:
    return legacy_dashboard()
```

## Testing

- Write tests for all new code
- Ensure all tests pass locally before pushing
- Add integration tests for user-facing features
- Aim for meaningful test coverage, not just high percentages

## Code Style

- Follow the project's linting rules
- Run formatters before committing
- CI will check code style automatically

## Getting Help

- Ask questions in team chat
- Review existing code for patterns
- Refer to architecture documentation
- Pair program for complex changes

## Emergency Hotfixes

For critical production issues:

1. Create a branch from `main`
2. Make the minimal fix necessary
3. Open a PR and request immediate review
4. After merging, create follow-up tasks for proper fixes

## Common Scenarios

### My branch is out of date

```bash
git fetch origin
git rebase origin/main
# Resolve any conflicts
git push --force-with-lease
```

### I need to make changes to my PR

```bash
# Make your changes
git add .
git commit -m "Address review feedback"
git push
```

### I want to test someone else's PR

```bash
git fetch origin
git checkout pr-branch-name
```

## Anti-Patterns to Avoid

- Long-lived feature branches (> 3 days)
- Large PRs (> 500 lines changed)
- Committing directly to `main` (except emergencies)
- Letting PRs sit without review
- Merging with failing tests
- Working in isolation without integrating

## Resources

- [Branch Protection Guidelines](.github/BRANCH_PROTECTION.md)
- [Trunk-Based Development](https://trunkbaseddevelopment.com/)

---

Remember: **Integrate early, integrate often!**
