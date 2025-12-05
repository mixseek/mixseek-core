# Security Policy

## Supported Versions

Currently supported versions for security updates:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| < 1.0   | :x:                |

We recommend always using the latest version for the best security posture.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Please DO NOT create a public issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting:

#### GitHub Private Vulnerability Reporting (Recommended)

1. Go to the [Security tab](https://github.com/mixseek/mixseek-core/security/advisories)
2. Click "Report a vulnerability"
3. Fill out the form with details about the vulnerability

This is the preferred method as it keeps the vulnerability private until we can address it.

**For non-security issues**, please use our [issue tracker](https://github.com/mixseek/mixseek-core/issues).

### What to Include

Please include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Potential impact
- Any suggested fixes (if available)

### Response Timeline

- **Initial Response**: Within 7 days
- **Status Update**: Within 14 days
- **Fix Timeline**: Depends on severity (we'll work with you to establish a reasonable timeline)

### Disclosure Policy

- Please do not publicly disclose the vulnerability until we have addressed it
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We will notify you when the fix is released

## Security Features

This project implements multiple layers of security:

- **GitHub Secret Scanning**: Automatic detection of leaked credentials with push protection
- **Dependabot**: Automated dependency vulnerability scanning and security updates
- **GitHub Code Scanning**: Static analysis for security issues (CodeQL)
- **CI/CD Security**: Automated security checks in pull requests

## Security Best Practices

When contributing to this project:
- Never commit API keys, passwords, or tokens
- Use environment variables for sensitive configuration
- Follow secure coding practices
- Keep dependencies up to date
- Report security issues privately (see above)

## Questions?

For security-related questions (not vulnerability reports):
- Open a discussion in [GitHub Discussions](https://github.com/mixseek/mixseek-core/discussions)
- Tag it with relevant labels

Thank you for helping keep MixSeek-Core secure!
