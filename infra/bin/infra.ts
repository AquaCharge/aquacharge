#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { InfraStack } from '../lib/infra-stack-ec2';

const app = new cdk.App();

// Get configuration from context or environment variables
const environmentName = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const allowedIps = app.node.tryGetContext('allowedIps') || process.env.ALLOWED_IPS || '';
const instanceType = app.node.tryGetContext('instanceType') || process.env.INSTANCE_TYPE || 't3.micro';
const useExistingTables = app.node.tryGetContext('useExistingTables') === 'true' || app.node.tryGetContext('useExistingTables') === true;

// Parse allowed IPs (comma-separated CIDR blocks)
const allowedIpAddresses = allowedIps ? allowedIps.split(',').map((ip: string) => ip.trim()) : [];

new InfraStack(app, `AquaChargeStack-${environmentName}`, {
  environmentName: environmentName,
  allowedIpAddresses: allowedIpAddresses,
  instanceType: instanceType,
  useExistingTables: useExistingTables,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: `AquaCharge Infrastructure Stack (EC2) - ${environmentName}`,
});