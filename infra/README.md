# AquaCharge Infrastructure

This directory contains the AWS CDK infrastructure code for deploying the AquaCharge application to AWS.

## Architecture Overview

The stack creates the following AWS resources:

- **VPC**: Multi-AZ VPC with public and private subnets
- **ECS Cluster**: Fargate cluster for running containerized applications
- **Backend Service**: Flask API running on ECS Fargate behind an Application Load Balancer
- **Frontend Service**: React application running on ECS Fargate behind an Application Load Balancer
- **DynamoDB Tables**: NoSQL database tables for Users, Stations, Chargers, Vessels, and Bookings
- **ECR Repositories**: Container registries for backend and frontend images
- **Secrets Manager**: Secure storage for JWT secrets and application credentials
- **CloudWatch Logs**: Centralized logging for all services
- **Auto Scaling**: CPU and memory-based auto-scaling for both services

## Database Schema

The stack creates the following DynamoDB tables based on your backend models:

### Users Table

- **Partition Key**: `id` (String)
- **GSI**: `email-index` - For authentication lookups
- **GSI**: `orgId-index` - For organization-based queries
- **Attributes**: username, email, passwordHash, role, active, orgId, createdAt, updatedAt

### Stations Table

- **Partition Key**: `id` (String)
- **GSI**: `city-index` - Partition: city, Sort: provinceOrState
- **GSI**: `status-index` - For filtering by station status
- **Attributes**: displayName, longitude, latitude, city, provinceOrState, country, status

### Chargers Table

- **Partition Key**: `id` (String)
- **GSI**: `chargingStationId-index` - For station-based queries
- **GSI**: `chargerType-index` - For filtering by charger type
- **Attributes**: chargingStationId, chargerType, maxRate, active

### Vessels Table

- **Partition Key**: `id` (String)
- **GSI**: `userId-index` - For user-based queries
- **GSI**: `vesselType-index` - For filtering by vessel type
- **Attributes**: userId, displayName, vesselType, chargerType, capacity, maxChargeRate, minChargeRate, rangeMeters, active, createdAt, updatedAt

### Bookings Table

- **Partition Key**: `id` (String)
- **GSI**: `userId-index` - Partition: userId, Sort: startTime
- **GSI**: `stationId-index` - Partition: stationId, Sort: startTime
- **GSI**: `vesselId-index` - Partition: vesselId, Sort: startTime
- **GSI**: `status-index` - Partition: status, Sort: startTime
- **Attributes**: userId, vesselId, stationId, startTime, endTime, status, chargerType, createdAt

## Prerequisites

1. AWS CLI installed and configured with credentials
2. AWS CDK CLI installed: `npm install -g aws-cdk`
3. Docker installed (for building container images)
4. Node.js and npm installed

## Setup

1. Install dependencies:

```bash
cd infra
npm install
```

2. Bootstrap your AWS account (first time only):

```bash
cdk bootstrap
```

## Deployment

### Deploy to Development Environment

```bash
# Synthesize CloudFormation template
cdk synth

# Deploy the stack
cdk deploy

# Or deploy with a specific environment
cdk deploy -c environment=dev
```

### Deploy to Production Environment

```bash
cdk deploy -c environment=prod
```

## Building and Pushing Docker Images

Before deploying, you need to build and push your Docker images to ECR:

```bash
# Get ECR login credentials
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
cd ../backend
docker build -t aquacharge-backend-dev .
docker tag aquacharge-backend-dev:latest <backend-repo-uri>:latest
docker push <backend-repo-uri>:latest

# Build and push frontend
cd ../frontend
docker build -t aquacharge-frontend-dev .
docker tag aquacharge-frontend-dev:latest <frontend-repo-uri>:latest
docker push <frontend-repo-uri>:latest
```

You can get the ECR repository URIs from the CDK outputs after deployment.

## Useful Commands

- `npm run build` - Compile TypeScript to JavaScript
- `npm run watch` - Watch for changes and compile
- `npm run test` - Run unit tests
- `cdk diff` - Compare deployed stack with current state
- `cdk synth` - Emit the synthesized CloudFormation template
- `cdk deploy` - Deploy this stack to your default AWS account/region
- `cdk destroy` - Remove the stack from your AWS account

## Stack Outputs

After deployment, the stack outputs the following values:

- **VpcId**: VPC identifier
- **ClusterName**: ECS cluster name
- **BackendServiceUrl**: URL to access the backend API
- **FrontendServiceUrl**: URL to access the frontend application
- **BackendRepositoryUri**: ECR repository URI for backend images
- **FrontendRepositoryUri**: ECR repository URI for frontend images
- **AppSecretArn**: ARN of the application secrets
- **UsersTableName/Arn**: DynamoDB Users table information
- **StationsTableName/Arn**: DynamoDB Stations table information
- **ChargersTableName/Arn**: DynamoDB Chargers table information
- **VesselsTableName/Arn**: DynamoDB Vessels table information
- **BookingsTableName/Arn**: DynamoDB Bookings table information

## Configuration

You can customize the stack by modifying the properties in `bin/infra.ts`:

- `environmentName`: Environment name (dev, staging, prod)
- `vpcCidr`: VPC CIDR block

## Environment Variables

The following environment variables are available for configuration:

- `ENVIRONMENT`: Set the deployment environment (default: dev)
- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)

## Cost Optimization

For development environments:

- Single NAT Gateway is used (instead of one per AZ)
- DynamoDB uses pay-per-request billing mode (no minimum costs)
- ECS tasks start with minimal resources (256 CPU, 512 MB memory)
- Auto-scaling is configured to scale down during low usage

For production environments:

- Consider provisioned capacity for DynamoDB if usage is predictable
- Increase task resources based on load testing
- Enable deletion protection on critical resources
- Enable Point-in-Time Recovery for DynamoDB tables

## Security

- DynamoDB tables use AWS-managed encryption
- Secrets are stored in AWS Secrets Manager
- Security groups restrict traffic between services
- ECR images are scanned on push
- CloudWatch Logs for audit trails
- DynamoDB Streams enabled for Users and Bookings tables for audit/event processing

## Troubleshooting

### ECS Tasks Not Starting

Check CloudWatch Logs for the service:

```bash
aws logs tail /ecs/backend --follow
```

### Health Check Failures

Ensure your application responds to health check endpoints:

- Backend: `/api/health`
- Frontend: `/`

### DynamoDB Access Issues

Verify that the ECS task role has the correct IAM permissions to access the DynamoDB tables. Check CloudWatch Logs for any permission errors.

## Cleanup

To remove all resources:

```bash
cdk destroy
```

Note: Some resources (like ECR repositories and DynamoDB tables in production) may be retained based on the environment configuration.

## Support

For issues or questions, please refer to the main project README or contact the development team.
