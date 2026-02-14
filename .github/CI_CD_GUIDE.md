# CI/CD Guide for Vision Clip Generator

This document explains the GitHub Actions CI/CD pipeline and how to work with it as a contributor.

## Overview

The project uses GitHub Actions for continuous integration and deployment with the following workflows:

- **CI Pipeline**: Automated testing on every push and pull request
- **Staging Promotion**: Manual workflow to promote changes to staging branch
- **Dependency Updates**: Weekly automated dependency updates
- **Security Scanning**: CodeQL analysis for security vulnerabilities

## CI Pipeline (ci.yml)

### Triggers

The CI pipeline automatically runs on:
- Push to `main` branch
- Pull requests targeting `main` branch

### What It Tests

The pipeline runs a comprehensive test matrix:
- **Platforms**: Ubuntu Linux and macOS
- **Python versions**: 3.11 and 3.12
- **Total jobs**: 4 (2 platforms × 2 Python versions)

### Test Process

For each matrix combination, the workflow:
1. Checks out your code
2. Installs `uv` package manager with caching
3. Sets up Python environment
4. Installs dependencies (including dev dependencies)
5. Runs full test suite with coverage reporting
6. Uploads coverage reports to Codecov and GitHub artifacts
7. Archives test logs on failure

### Viewing Results

**In Pull Requests:**
- Check the "Checks" tab to see all 4 test jobs
- Green checkmarks = all tests passed
- Red X = failures (click for details)

**Coverage Reports:**
- Download from "Actions" → Select workflow run → "Artifacts"
- Coverage HTML reports retained for 30 days
- Test logs retained for 7 days (only on failure)

### Environment Variables

The CI workflow uses these secrets:
- `GOOGLE_API_KEY`: Google TTS API key for testing (configured in repository settings)
- `TTS_PROVIDER`: Set to "google" automatically

## Staging Promotion (staging-promotion.yml)

### Purpose

Safely promote tested code from `main` to `staging` branch with manual approval.

### How to Promote to Staging

1. **Navigate to Actions Tab**
   - Go to your repository → Actions
   - Select "Staging Promotion" workflow

2. **Trigger Workflow**
   - Click "Run workflow"
   - Select source branch (default: `main`)
   - Click green "Run workflow" button

3. **Validation**
   - Workflow validates source branch exists
   - Checks latest CI status on source branch
   - Ensures tests passed before allowing promotion

4. **Manual Approval**
   - Workflow pauses at "Request Manual Approval" step
   - Designated reviewers receive notification
   - Review changes and approve/reject

5. **Promotion**
   - Upon approval, workflow merges to staging
   - Creates staging branch if it doesn't exist
   - Pushes changes and creates summary report

### Who Can Approve?

Approvals are configured in repository Settings → Environments → staging:
- Only designated reviewers can approve
- Configure in repository settings (requires admin access)

### Handling Conflicts

If staging branch has diverged from main:
- Workflow will fail with merge conflict error
- Manually resolve conflicts locally:
  ```bash
  git checkout staging
  git pull origin staging
  git merge main
  # Resolve conflicts
  git commit
  git push origin staging
  ```
- Re-run staging promotion workflow

## Dependency Updates (dependency-update.yml)

### Schedule

Runs automatically every **Monday at midnight UTC**.

### Process

1. Updates `uv.lock` with latest compatible versions
2. Installs updated dependencies
3. Runs full test suite
4. If tests pass, creates PR automatically
5. PR includes:
   - List of updated packages
   - Test results
   - Link to dependency changes

### Review Process

1. Check the auto-generated PR in "Pull requests" tab
2. Review changed dependencies in `uv.lock`
3. Verify CI tests passed
4. Merge if satisfied, or close if issues found

### Manual Trigger

You can also manually trigger dependency updates:
- Actions → Dependency Updates → Run workflow

## Security Scanning (security.yml)

### What It Scans

**CodeQL Analysis:**
- Static code analysis for Python
- Security vulnerability detection
- Code quality checks

### When It Runs

- Push to `main` branch
- Pull requests to `main`
- Weekly on Sundays (scheduled)

### Viewing Results

1. Navigate to Security tab in repository
2. Click "Code scanning alerts"
3. Review any detected vulnerabilities
4. Follow remediation guidance

### Alert Levels

- **Critical/High**: Fix immediately
- **Medium**: Fix before next release
- **Low**: Fix when convenient

## Working with the CI Pipeline

### Before Creating a PR

1. **Run tests locally:**
   ```bash
   make test
   # Or: uv run --extra dev pytest -v
   ```

2. **Check coverage:**
   ```bash
   make test-cov
   ```

3. **Ensure tests pass on both platforms if possible**

### During PR Review

1. **Monitor CI status:**
   - All 4 matrix jobs must pass
   - Review coverage reports if needed
   - Check for any new security alerts

2. **If CI fails:**
   - Click on failed job for details
   - Download test logs if needed
   - Fix issues and push updates
   - CI re-runs automatically

3. **Platform-specific issues:**
   - macOS failures: May be audio library related
   - Linux failures: More common, usually code issues

### After PR Merge

1. **CI runs again on main branch**
2. **Security scan updates**
3. **Consider staging promotion if ready**

## Troubleshooting

### "Tests fail on macOS but pass on Linux"

**Common causes:**
- File path differences (`/` vs `\`)
- Audio library availability
- Platform-specific dependencies

**Solutions:**
- Check logs for specific error
- Test locally on macOS if available
- May need platform-specific conditionals

### "GOOGLE_API_KEY not found"

**Cause:** Secret not configured or workflow lacks access

**Solution:**
1. Verify secret exists: Settings → Secrets → Actions
2. Check secret name matches exactly: `GOOGLE_API_KEY`
3. Ensure workflow references it correctly in `env:` section

### "Environment 'staging' not found"

**Cause:** Staging environment not created in repository settings

**Solution:**
1. Go to Settings → Environments
2. Click "New environment"
3. Name: `staging`
4. Add required reviewers
5. Save

### "Workflow takes too long"

**Expected runtimes:**
- Linux jobs: ~2-3 minutes each
- macOS jobs: ~5-10 minutes each (slower runners)
- Total CI pipeline: ~10-15 minutes

**If much longer:**
- Check for stuck jobs (timeout after 30 minutes)
- Look for network issues downloading dependencies
- Cancel and re-run if stuck

### "Codecov upload fails"

**Impact:** Non-critical, workflow continues

**Solutions:**
- Often transient Codecov service issues
- Coverage still available in GitHub artifacts
- Check Codecov service status if persistent

## Cost and Resource Management

### GitHub Actions Minutes

**Current usage estimate:** ~1,270 minutes/month

**Breakdown:**
- Linux: ~250 minutes (1:1 billing ratio)
- macOS: ~1,020 minutes (10:1 billing ratio - expensive!)

**Free tier:**
- Public repo: Unlimited minutes
- Private repo: 2,000 minutes/month included

**To reduce costs (if needed):**

1. **Option 1: Reduce macOS testing**
   Edit `.github/workflows/ci.yml`:
   ```yaml
   exclude:
     - os: macos-latest
       python-version: '3.12'  # Only test macOS on 3.11
   ```

2. **Option 2: Run macOS only on main**
   ```yaml
   - os: macos-latest
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
   ```

3. **Monitor usage:**
   - Settings → Billing → Actions minutes
   - Review monthly usage trends

## Best Practices

### For Contributors

1. ✅ Run tests locally before pushing
2. ✅ Write tests for new features
3. ✅ Keep test coverage above 90%
4. ✅ Review CI failures promptly
5. ✅ Don't merge PRs with failing tests

### For Maintainers

1. ✅ Review security scan results weekly
2. ✅ Merge dependency update PRs promptly
3. ✅ Monitor Actions minutes usage monthly
4. ✅ Keep GOOGLE_API_KEY secret rotated (every 90 days)
5. ✅ Update workflow versions periodically

### Writing Tests

**Good test practices:**
- Use mocking for external API calls
- Test both success and failure paths
- Include platform-specific tests when needed
- Maintain high coverage (currently 93%+)
- Write descriptive test names

**Example:**
```python
def test_keyboard_interrupt_exits_gracefully(self, mocker, capsys):
    """Test that KeyboardInterrupt during main() is caught and exits with code 130"""
    mock_main = mocker.patch('main.main', side_effect=KeyboardInterrupt())

    with pytest.raises(SystemExit) as exc_info:
        # Test implementation

    assert exc_info.value.code == 130
```

## Getting Help

**CI/CD Issues:**
1. Check this guide first
2. Review workflow logs in Actions tab
3. Search existing GitHub issues
4. Create new issue with workflow run link

**Questions:**
- Create GitHub discussion
- Tag with `ci-cd` label
- Include relevant logs and error messages

## Workflow File Locations

All workflows are in `.github/workflows/`:
- `ci.yml` - Main CI pipeline
- `staging-promotion.yml` - Staging workflow
- `dependency-update.yml` - Automated updates
- `security.yml` - Security scanning

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv Documentation](https://github.com/astral-sh/uv)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)

---

**Last Updated:** 2026-02-14
**Questions?** Open an issue or discussion on GitHub
