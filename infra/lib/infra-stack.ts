import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create a DynamoDB table
    const table = new dynamodb.Table(this, 'BookingTable', {
      partitionKey: { name: 'bookingId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      removalPolicy: cdk.RemovalPolicy.RETAIN, 
    });

    // Output the table name
    new cdk.CfnOutput(this, 'BookingTableName', {
      value: table.tableName,
      description: 'The name of the Booking DynamoDB table',
    });


    const ec2Role = new iam.Role(this, 'EC2DynamoDBRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
    });

    // Grant the role read/write permissions to the DynamoDB table
    table.grantReadWriteData(ec2Role);

    // Output the IAM Role ARN
    new cdk.CfnOutput(this, 'EC2DynamoDBRoleARN', {
      value: ec2Role.roleArn,
      description: 'The ARN of the EC2 IAM Role with DynamoDB access',
    });
    
    const vpc = new ec2.Vpc(this, 'AquaChargeVPC', {
      maxAzs: 2, // Default is all AZs in the region
    });
    
    // Output the VPC ID
    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'Aquacharge VPC ID',
    });
    
    const ec2Instance = new ec2.Instance(this,
      'AquaChargeInstance', {
        instanceType: new ec2.InstanceType('t2.micro'),
        machineImage: new ec2.AmazonLinuxImage(),
        vpc,
        role: ec2Role,
      }
    );
    
    // Output the EC2 Instance ID
    new cdk.CfnOutput(this, 'EC2InstanceId', {
      value: ec2Instance.instanceId,
      description: 'Aquacharge EC2 Instance ID',
    });
  }
}
