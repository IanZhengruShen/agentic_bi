# Branch Protection Guidelines

This document outlines the branch protection rules for trunk-based development in this repository.

## Protected Branch: `main`

The `main` branch serves as the trunk and should be configured with the following protections:

### Required Protections

1. **Require Pull Request Reviews**
   - Minimum 1 approval required
   - Dismiss stale reviews when new commits are pushed
   - Require review from code owners (if CODEOWNERS file exists)

2. **Require Status Checks**
   - All CI checks must pass before merging
   - Required checks:
     - Build/Compile
     - Unit tests
     - Integration tests
     - Linting
     - Security scanning
   - Require branches to be up to date before merging

3. **Require Linear History**
   - Enforce either squash merging or rebase merging
   - This keeps the trunk history clean and linear

4. **No Force Pushes**
   - Prevent force pushes to main branch
   - Protects against accidental history rewrites

5. **Require Signed Commits** (Recommended)
   - Ensures commit authenticity
   - Adds accountability to changes

### Short-Lived Feature Branches

- Feature branches should be short-lived (1-3 days maximum)
- Branch naming convention: `feature/description`, `fix/description`, or `username/description`
- Delete branches immediately after merging

### Configuration

To apply these settings on GitHub:
```
Settings > Branches > Add rule > Branch name pattern: main
```

To apply these settings on GitLab:
```
Settings > Repository > Protected Branches > main
```

## Direct Commits to Main

Direct commits to `main` are allowed only for:
- Hotfixes in emergency situations (must be reviewed post-merge)
- Documentation updates (at team's discretion)
- CI/CD configuration fixes

All other changes must go through pull requests.
