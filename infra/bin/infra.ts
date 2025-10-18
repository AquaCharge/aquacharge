#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { InfraStack } from '../lib/infra-stack';

const app = new cdk.App();

const stage = (app.node.tryGetContext('stage') as string)
  ?? process.env.DEPLOY_STAGE
  ?? 'dev';

const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION;

if (!account || !region) {
  throw new Error(
    'CDK_DEFAULT_ACCOUNT and CDK_DEFAULT_REGION must be defined. Run "cdk bootstrap" or set the variables before synthesising.',
  );
}

const stack = new InfraStack(app, `InfraStack-${stage}`, {
  env: { account, region },
  stackName: `aquacharge-infra-${stage}`,
  description: `AquaCharge infrastructure stack for the ${stage} environment`,
});

cdk.Tags.of(stack).add('project', 'aquacharge');
cdk.Tags.of(stack).add('environment', stage);