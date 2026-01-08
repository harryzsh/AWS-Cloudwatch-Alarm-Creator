# AWS Infrastructure Development Guidelines

## Kiro Powers for AWS

When working with AWS infrastructure, CloudFormation templates, or CDK code, you should use the installed Kiro Powers as first priority order:

### aws-infrastructure-as-code Power

Use this power for:
- **Validating CloudFormation templates** (cfn-lint)
- **Checking security compliance** (cfn-guard)
- **Troubleshooting failed CloudFormation deployments**
- **Searching CDK documentation and code samples**
- **Reading AWS documentation pages**
- **Getting CDK best practices**

### cloud-architect Power

Use this power for:
- **Building AWS infrastructure with CDK in Python**
- **Following AWS Well-Architected framework best practices**
- **Getting AWS pricing information**
- **Accessing AWS knowledge base**

## Best Practices

1. **Always validate CloudFormation templates** before deployment using the aws-infrastructure-as-code power
2. **Check security compliance** for all templates
3. **Search CDK documentation** when writing CDK code
4. **Follow CDK best practices** from the power
5. **Use the powers proactively** - don't wait to be asked

## Documentation Rules

1. **Keep documentation minimal** - ONE README.md is enough
2. **Update README.md whenever changes are made** - Keep it current
3. **Do not create multiple documentation files** - Consolidate everything into README.md
4. **Avoid documentation bloat** - Only essential information

## Example Usage

When creating or modifying CloudFormation templates:
1. Write the template
2. Validate with `validate_cloudformation_template` tool
3. Check compliance with `check_cloudformation_template_compliance` tool
4. Deploy with confidence

When writing CDK code:
1. Search CDK documentation for constructs
2. Get CDK best practices
3. Find code samples in your language
4. Synthesize and validate the generated CloudFormation
