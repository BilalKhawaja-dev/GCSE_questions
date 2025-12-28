# GCSE Question Generator - Terraform Infrastructure

This directory contains the Infrastructure as Code (IaC) configuration for the GCSE Question Generator platform using Terraform.

## Architecture Overview

The infrastructure deploys a serverless AI-powered platform with the following components:

- **Frontend**: S3 static website hosting + CloudFront CDN
- **API**: API Gateway with /interpret and /generate endpoints
- **Compute**: AWS Lambda functions (InterpretLambda + GenerateLambda)
- **AI**: AWS Bedrock (Claude Haiku + Claude Sonnet)
- **Storage**: S3 buckets for specifications and examples
- **Monitoring**: CloudWatch dashboards, alarms, and SNS notifications

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform >= 1.0** installed
3. **AWS Account** with Bedrock access in eu-west-2 region

## Required AWS Permissions

Your AWS credentials need the following permissions:
- S3: Full access for bucket creation and management
- Lambda: Full access for function creation and management
- API Gateway: Full access for API creation and management
- CloudFront: Full access for distribution creation
- IAM: Full access for role and policy management
- CloudWatch: Full access for monitoring setup
- Bedrock: Access to Claude models in eu-west-2
- DynamoDB: Access for Terraform state locking

## Quick Start

1. **Initialize the infrastructure:**
   ```bash
   cd terraform
   export ALERT_EMAIL="your-email@example.com"
   ./init.sh prod
   ```

2. **Review the plan:**
   ```bash
   terraform plan -var-file=environments/prod.tfvars
   ```

3. **Apply the infrastructure:**
   ```bash
   terraform apply -var-file=environments/prod.tfvars
   ```

## Configuration

### Environment Files

- `environments/prod.tfvars` - Production configuration
- `environments/dev.tfvars` - Development configuration

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `environment` | Environment name (dev/prod) | prod |
| `aws_region` | AWS region for deployment | eu-west-2 |
| `alert_email` | Email for CloudWatch alerts | Required |
| `bedrock_model_haiku` | Claude Haiku model ID | anthropic.claude-3-haiku-20240307 |
| `bedrock_model_sonnet` | Claude Sonnet model ID | anthropic.claude-3-sonnet-20240229 |
| `api_rate_limit` | Requests per user per hour | 100 |
| `daily_cost_threshold` | Daily cost alert threshold (GBP) | 20 |

## Module Structure

```
terraform/
├── main.tf                 # Root module configuration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── backend.tf              # Remote state configuration
├── modules/
│   ├── frontend/           # S3 + CloudFront
│   ├── api/                # API Gateway + Lambda
│   ├── ai/                 # Bedrock configurations
│   ├── knowledge/          # S3 buckets for content
│   └── monitoring/         # CloudWatch + SNS
└── environments/           # Environment-specific configs
```

## Deployment Process

### 1. Backend Setup
The `init.sh` script automatically:
- Creates S3 bucket for Terraform state
- Creates DynamoDB table for state locking
- Configures encryption and versioning
- Initializes Terraform with remote backend

### 2. Infrastructure Deployment
```bash
# Plan changes
terraform plan -var-file=environments/prod.tfvars -out=tfplan

# Apply changes
terraform apply tfplan
```

### 3. Verification
After deployment, verify:
- API Gateway endpoints are accessible
- Lambda functions are created and configured
- S3 buckets are created with proper policies
- CloudFront distribution is deployed
- CloudWatch alarms are configured

## Outputs

After successful deployment, Terraform outputs:

- `api_gateway_url` - API endpoint URL
- `cloudfront_domain_name` - Frontend URL
- `specifications_bucket_name` - S3 bucket for specifications
- `examples_bucket_name` - S3 bucket for examples
- `monitoring_dashboard_url` - CloudWatch dashboard

## Cost Optimization

The infrastructure is designed for cost optimization:
- **Serverless architecture** - Pay only for usage
- **Regional deployment** - eu-west-2 only
- **CloudFront PriceClass_100** - North America and Europe only
- **S3 lifecycle policies** - Automatic cleanup of old versions
- **Cost monitoring** - Alerts at £20/day and £50/month

**Estimated monthly cost: ~£14 for 100 users, 50 requests/user/month**

## Security Features

- **Least-privilege IAM roles** for all services
- **S3 bucket encryption** at rest (SSE-S3)
- **Public access blocked** on all S3 buckets
- **HTTPS-only** CloudFront distribution
- **VPC endpoints** not required (serverless architecture)
- **API Gateway request validation** with JSON schemas

## Monitoring and Alerting

### CloudWatch Alarms
- Lambda error rate > 5%
- API Gateway 5xx errors > 1%
- Lambda duration approaching timeout
- Daily cost exceeding threshold

### SNS Notifications
- Email alerts for critical issues
- Configurable alert email address

### Dashboard Metrics
- API Gateway request count and latency
- Lambda invocations, errors, and duration
- Cost tracking and usage metrics

## Disaster Recovery

### Backup Strategy
- **S3 versioning** enabled on all buckets
- **Terraform state** versioned in S3
- **90-day retention** for specification versions
- **30-day retention** for deleted content

### Recovery Procedures
- **RTO < 4 hours** for complete region failure
- **Terraform state recovery** from S3 versions
- **Cross-region replication** available for critical data

## Troubleshooting

### Common Issues

1. **Bedrock Access Denied**
   - Ensure Bedrock is enabled in eu-west-2
   - Request access to Claude models if needed

2. **S3 Bucket Name Conflicts**
   - Bucket names include random suffixes for uniqueness
   - Check AWS console if creation fails

3. **Lambda Deployment Package Missing**
   - Lambda functions reference S3 deployment packages
   - Packages will be created in Task 13.1

4. **CloudFront Distribution Slow**
   - CloudFront deployments take 15-20 minutes
   - Check AWS console for deployment status

### Useful Commands

```bash
# Check Terraform state
terraform show

# Import existing resources
terraform import aws_s3_bucket.example bucket-name

# Destroy infrastructure (careful!)
terraform destroy -var-file=environments/prod.tfvars

# Format Terraform files
terraform fmt -recursive

# Validate configuration
terraform validate
```

## Development Workflow

1. **Feature branches** for infrastructure changes
2. **Terraform plan** in pull requests
3. **Code review** before merging
4. **Automated testing** with integration tests
5. **Staged deployment** (dev → prod)

## Support

For issues with the infrastructure:
1. Check CloudWatch logs for Lambda functions
2. Review CloudWatch alarms for system health
3. Check Terraform state for resource status
4. Contact the development team with specific error messages

## License

This infrastructure code is part of the GCSE Question Generator project.