import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { DynamoDbTables } from './dynamodb-tables';

export interface InfraStackProps extends cdk.StackProps {
  environmentName?: string;
  allowedIpAddresses?: string[]; // Whitelist of IPs that can access the application
  instanceType?: string; // Default: t3.micro
  useExistingTables?: boolean; // If true, reference existing tables instead of creating new ones
  keyPairName?: string; // EC2 key pair name for SSH access
}

export class InfraStack extends cdk.Stack {
  public readonly ec2Instance: ec2.Instance;
  public readonly securityGroup: ec2.SecurityGroup;
  public readonly usersTable: dynamodb.ITable;
  public readonly stationsTable: dynamodb.ITable;
  public readonly chargersTable: dynamodb.ITable;
  public readonly vesselsTable: dynamodb.ITable;
  public readonly bookingsTable: dynamodb.ITable;
  public readonly contractsTable: dynamodb.ITable;
  public readonly drEventsTable: dynamodb.ITable;
  public readonly portsTable: dynamodb.ITable;

  constructor(scope: Construct, id: string, props?: InfraStackProps) {
    super(scope, id, props);

    const environmentName = props?.environmentName || 'dev';
    // Always include the hardcoded IP, and add any additional IPs from props
    const allowedIps = ['131.202.255.236/32', ...(props?.allowedIpAddresses || [])];
    const instanceTypeString = props?.instanceType || 't3.micro';
    const useExistingTables = props?.useExistingTables ?? false; // Default to false to allow CDK to manage tables
    const keyPairName = props?.keyPairName || 'aquacharge-key';

    // ===== DynamoDB Tables =====
    const tables = new DynamoDbTables(this, { environmentName, useExistingTables });

    this.usersTable = tables.usersTable;
    this.stationsTable = tables.stationsTable;
    this.chargersTable = tables.chargersTable;
    this.vesselsTable = tables.vesselsTable;
    this.bookingsTable = tables.bookingsTable;
    this.contractsTable = tables.contractsTable;
    this.drEventsTable = tables.drEventsTable;
    this.portsTable = tables.portsTable;

    // ===== VPC (Simplified - only public subnets, no NAT Gateway) =====
    const vpc = new ec2.Vpc(this, 'AquaChargeVpc', {
      vpcName: `aquacharge-vpc-${environmentName}`,
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      maxAzs: 1, // Cost optimization: single AZ
      natGateways: 0, // Cost optimization: no NAT gateway needed
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // ===== Security Group with IP Whitelisting =====
    this.securityGroup = new ec2.SecurityGroup(this, 'AquaChargeSecurityGroup', {
      vpc: vpc,
      securityGroupName: `aquacharge-sg-${environmentName}`,
      description: 'Security group for AquaCharge EC2 instance with IP whitelisting',
      allowAllOutbound: true,
    });

    // Add SSH access for whitelisted IPs
    if (allowedIps.length > 0) {
      allowedIps.forEach((ip, index) => {
        this.securityGroup.addIngressRule(
          ec2.Peer.ipv4(ip),
          ec2.Port.tcp(22),
          `SSH access from whitelisted IP ${index + 1}`
        );
        this.securityGroup.addIngressRule(
          ec2.Peer.ipv4(ip),
          ec2.Port.tcp(80),
          `HTTP access from whitelisted IP ${index + 1}`
        );
        this.securityGroup.addIngressRule(
          ec2.Peer.ipv4(ip),
          ec2.Port.tcp(443),
          `HTTPS access from whitelisted IP ${index + 1}`
        );
        this.securityGroup.addIngressRule(
          ec2.Peer.ipv4(ip),
          ec2.Port.tcp(5050),
          `Backend API access from whitelisted IP ${index + 1}`
        );
      });
    } else {
      // If no IPs specified, allow from anywhere (not recommended for production)
      this.securityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(22),
        'SSH access (WARNING: open to all)'
      );
      this.securityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(80),
        'HTTP access (WARNING: open to all)'
      );
      this.securityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(443),
        'HTTPS access (WARNING: open to all)'
      );
      this.securityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(5050),
        'Backend API access (WARNING: open to all)'
      );
    }

    // ===== IAM Role for EC2 =====
    const ec2Role = new iam.Role(this, 'EC2Role', {
      // Remove roleName to let CDK auto-generate unique name
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'), // For Systems Manager
      ],
    });

    // Grant EC2 access to DynamoDB tables
    this.usersTable.grantReadWriteData(ec2Role);
    this.stationsTable.grantReadWriteData(ec2Role);
    this.chargersTable.grantReadWriteData(ec2Role);
    this.vesselsTable.grantReadWriteData(ec2Role);
    this.bookingsTable.grantReadWriteData(ec2Role);
    this.contractsTable.grantReadWriteData(ec2Role);
    this.drEventsTable.grantReadWriteData(ec2Role);
    this.portsTable.grantReadWriteData(ec2Role);

    // Grant additional permissions for GSI queries (indexes)
    // grantReadWriteData only covers the table, not the indexes
    ec2Role.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:Scan',
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:BatchGetItem',
        'dynamodb:BatchWriteItem',
      ],
      resources: [
        this.usersTable.tableArn + '/index/*',
        this.stationsTable.tableArn + '/index/*',
        this.chargersTable.tableArn + '/index/*',
        this.vesselsTable.tableArn + '/index/*',
        this.bookingsTable.tableArn + '/index/*',
        this.contractsTable.tableArn + '/index/*',
        this.drEventsTable.tableArn + '/index/*',
        this.portsTable.tableArn + '/index/*',
      ],
    }));

    // ===== EC2 Instance =====
    // User data script to install Docker and Docker Compose
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      '#!/bin/bash',
      'set -e',
      '',
      '# Update system',
      'yum update -y',
      '',
      '# Install Docker',
      'yum install -y docker',
      'systemctl start docker',
      'systemctl enable docker',
      'usermod -a -G docker ec2-user',
      '',
      '# Install Docker Compose v2 (as Docker plugin)',
      'mkdir -p /usr/local/lib/docker/cli-plugins',
      'curl -SL "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose',
      'chmod +x /usr/local/lib/docker/cli-plugins/docker-compose',
      '',
      '# Create docker-compose alias for compatibility',
      'ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose',
      '',
      '# Create application directory',
      'mkdir -p /home/ec2-user/aquacharge',
      'chown ec2-user:ec2-user /home/ec2-user/aquacharge',
      '',
      '# Set environment variables for DynamoDB',
      'cat > /home/ec2-user/aquacharge/.env << EOF',
      `AWS_REGION=${this.region}`,
      `DYNAMODB_USERS_TABLE=${this.usersTable.tableName}`,
      `DYNAMODB_STATIONS_TABLE=${this.stationsTable.tableName}`,
      `DYNAMODB_CHARGERS_TABLE=${this.chargersTable.tableName}`,
      `DYNAMODB_VESSELS_TABLE=${this.vesselsTable.tableName}`,
      `DYNAMODB_BOOKINGS_TABLE=${this.bookingsTable.tableName}`,
      `DYNAMODB_PORTS_TABLE=${this.portsTable.tableName}`,
      `FLASK_ENV=${environmentName === 'prod' ? 'production' : 'development'}`,
      'EOF',
      'chown ec2-user:ec2-user /home/ec2-user/aquacharge/.env',
      '',
      '# Install CloudWatch agent for monitoring',
      'wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm',
      'rpm -U ./amazon-cloudwatch-agent.rpm',
      '',
      '# Create a note for the user',
      'cat > /home/ec2-user/SETUP-INSTRUCTIONS.txt << EOF',
      'AquaCharge EC2 Instance Setup Complete!',
      '',
      'Next steps:',
      '1. Copy your docker-compose.yaml to /home/ec2-user/aquacharge/',
      '2. Copy your backend and frontend code to /home/ec2-user/aquacharge/',
      '3. Run: cd /home/ec2-user/aquacharge && docker-compose up -d',
      '',
      'Environment variables are set in /home/ec2-user/aquacharge/.env',
      '',
      'To monitor logs: docker-compose logs -f',
      'To restart services: docker-compose restart',
      'EOF',
      'chown ec2-user:ec2-user /home/ec2-user/SETUP-INSTRUCTIONS.txt'
    );

    // Create the EC2 instance
    this.ec2Instance = new ec2.Instance(this, 'AquaChargeInstance', {
      instanceName: `aquacharge-instance-${environmentName}`,
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      instanceType: new ec2.InstanceType(instanceTypeString),
      machineImage: ec2.MachineImage.latestAmazonLinux2023({
        cpuType: ec2.AmazonLinuxCpuType.X86_64,
      }),
      securityGroup: this.securityGroup,
      role: ec2Role,
      keyName: keyPairName, // Add SSH key pair
      userData: userData,
      userDataCausesReplacement: true,
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(30, { // 30 GB storage
            encrypted: true,
            volumeType: ec2.EbsDeviceVolumeType.GP3,
          }),
        },
      ],
      requireImdsv2: true, // Security best practice
    });

    // ===== Outputs =====
    new cdk.CfnOutput(this, 'InstanceId', {
      value: this.ec2Instance.instanceId,
      description: 'EC2 Instance ID',
      exportName: `aquacharge-instance-id-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'InstancePublicIp', {
      value: this.ec2Instance.instancePublicIp,
      description: 'EC2 Instance Public IP',
      exportName: `aquacharge-instance-ip-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'InstancePublicDnsName', {
      value: this.ec2Instance.instancePublicDnsName,
      description: 'EC2 Instance Public DNS Name',
      exportName: `aquacharge-instance-dns-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'SSHCommand', {
      value: `ssh -i <your-key.pem> ec2-user@${this.ec2Instance.instancePublicIp}`,
      description: 'SSH command to connect to the instance',
    });

    new cdk.CfnOutput(this, 'ApplicationUrl', {
      value: `http://${this.ec2Instance.instancePublicIp}`,
      description: 'Application URL',
    });

    // DynamoDB Table Outputs
    new cdk.CfnOutput(this, 'UsersTableName', {
      value: this.usersTable.tableName,
      description: 'Users DynamoDB table name',
      exportName: `aquacharge-users-table-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'StationsTableName', {
      value: this.stationsTable.tableName,
      description: 'Stations DynamoDB table name',
      exportName: `aquacharge-stations-table-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'ChargersTableName', {
      value: this.chargersTable.tableName,
      description: 'Chargers DynamoDB table name',
      exportName: `aquacharge-chargers-table-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'VesselsTableName', {
      value: this.vesselsTable.tableName,
      description: 'Vessels DynamoDB table name',
      exportName: `aquacharge-vessels-table-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'BookingsTableName', {
      value: this.bookingsTable.tableName,
      description: 'Bookings DynamoDB table name',
      exportName: `aquacharge-bookings-table-${environmentName}`,
    });

    new cdk.CfnOutput(this, 'PortsTableName', {
      value: this.portsTable.tableName,
      description: 'Ports DynamoDB table name',
      exportName: `aquacharge-ports-table-${environmentName}`,
    });

    // Security Information
    new cdk.CfnOutput(this, 'SecurityGroupId', {
      value: this.securityGroup.securityGroupId,
      description: 'Security Group ID',
    });

    if (allowedIps.length > 0) {
      new cdk.CfnOutput(this, 'WhitelistedIPs', {
        value: allowedIps.join(', '),
        description: 'Whitelisted IP addresses',
      });
    } else {
      new cdk.CfnOutput(this, 'SecurityWarning', {
        value: 'WARNING: No IP whitelist configured - instance is accessible from anywhere',
        description: 'Security Warning',
      });
    }
  }
}
