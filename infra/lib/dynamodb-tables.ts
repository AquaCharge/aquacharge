import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

export interface DynamoDbTablesProps {
  environmentName: string;
  useExistingTables: boolean;
}

/**
 * Creates or references all DynamoDB tables for the AquaCharge application.
 *
 * Tables are scoped to the provided `tableScope` so that their CloudFormation
 * logical IDs remain stable (unchanged from when they lived directly in the stack).
 */
export class DynamoDbTables {
  public readonly usersTable: dynamodb.ITable;
  public readonly stationsTable: dynamodb.ITable;
  public readonly chargersTable: dynamodb.ITable;
  public readonly vesselsTable: dynamodb.ITable;
  public readonly bookingsTable: dynamodb.ITable;
  public readonly contractsTable: dynamodb.ITable;
  public readonly portsTable: dynamodb.ITable;
  public readonly drEventsTable: dynamodb.ITable;
  public readonly orgsTable: dynamodb.ITable;

  constructor(tableScope: Construct, props: DynamoDbTablesProps) {
    const { environmentName, useExistingTables } = props;

    if (useExistingTables) {
      this.usersTable = dynamodb.Table.fromTableName(
        tableScope, 'UsersTable', `aquacharge-users-${environmentName}`
      );
      this.stationsTable = dynamodb.Table.fromTableName(
        tableScope, 'StationsTable', `aquacharge-stations-${environmentName}`
      );
      this.chargersTable = dynamodb.Table.fromTableName(
        tableScope, 'ChargersTable', `aquacharge-chargers-${environmentName}`
      );
      this.vesselsTable = dynamodb.Table.fromTableName(
        tableScope, 'VesselsTable', `aquacharge-vessels-${environmentName}`
      );
      this.bookingsTable = dynamodb.Table.fromTableName(
        tableScope, 'BookingsTable', `aquacharge-bookings-${environmentName}`
      );
      this.contractsTable = dynamodb.Table.fromTableName(
        tableScope, 'ContractsTable', `aquacharge-contracts-${environmentName}`
      );
      this.portsTable = dynamodb.Table.fromTableName(
        tableScope, 'PortsTable', `aquacharge-ports-${environmentName}`
      );
      this.drEventsTable = dynamodb.Table.fromTableName(
        tableScope, 'DREventsTable', `aquacharge-drevents-${environmentName}`
      );
      this.orgsTable = dynamodb.Table.fromTableName(
        tableScope, 'OrgsTable', `aquacharge-orgs-${environmentName}`
      );
    } else {
      // Users Table
      const usersTable = new dynamodb.Table(tableScope, 'UsersTable', {
        tableName: `aquacharge-users-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        pointInTimeRecovery: true,
      });
      usersTable.addGlobalSecondaryIndex({
        indexName: 'email-index',
        partitionKey: { name: 'email', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      usersTable.addGlobalSecondaryIndex({
        indexName: 'orgId-index',
        partitionKey: { name: 'orgId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.usersTable = usersTable;

      // Stations Table
      const stationsTable = new dynamodb.Table(tableScope, 'StationsTable', {
        tableName: `aquacharge-stations-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });
      stationsTable.addGlobalSecondaryIndex({
        indexName: 'city-index',
        partitionKey: { name: 'city', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'provinceOrState', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      stationsTable.addGlobalSecondaryIndex({
        indexName: 'status-index',
        partitionKey: { name: 'status', type: dynamodb.AttributeType.NUMBER },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.stationsTable = stationsTable;

      // Chargers Table
      const chargersTable = new dynamodb.Table(tableScope, 'ChargersTable', {
        tableName: `aquacharge-chargers-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });
      chargersTable.addGlobalSecondaryIndex({
        indexName: 'chargingStationId-index',
        partitionKey: { name: 'chargingStationId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      chargersTable.addGlobalSecondaryIndex({
        indexName: 'chargerType-index',
        partitionKey: { name: 'chargerType', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.chargersTable = chargersTable;

      // Vessels Table
      const vesselsTable = new dynamodb.Table(tableScope, 'VesselsTable', {
        tableName: `aquacharge-vessels-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });
      vesselsTable.addGlobalSecondaryIndex({
        indexName: 'userId-index',
        partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      vesselsTable.addGlobalSecondaryIndex({
        indexName: 'vesselType-index',
        partitionKey: { name: 'vesselType', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.vesselsTable = vesselsTable;

      // Bookings Table
      const bookingsTable = new dynamodb.Table(tableScope, 'BookingsTable', {
        tableName: `aquacharge-bookings-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        pointInTimeRecovery: true,
      });
      bookingsTable.addGlobalSecondaryIndex({
        indexName: 'userId-index',
        partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      bookingsTable.addGlobalSecondaryIndex({
        indexName: 'stationId-index',
        partitionKey: { name: 'stationId', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      bookingsTable.addGlobalSecondaryIndex({
        indexName: 'vesselId-index',
        partitionKey: { name: 'vesselId', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      bookingsTable.addGlobalSecondaryIndex({
        indexName: 'status-index',
        partitionKey: { name: 'status', type: dynamodb.AttributeType.NUMBER },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.bookingsTable = bookingsTable;

      // Contracts Table
      const contractsTable = new dynamodb.Table(tableScope, 'ContractsTable', {
        tableName: `aquacharge-contracts-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });
      contractsTable.addGlobalSecondaryIndex({
        indexName: 'bookingId-index',
        partitionKey: { name: 'bookingId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      contractsTable.addGlobalSecondaryIndex({
        indexName: 'vesselId-index',
        partitionKey: { name: 'vesselId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      contractsTable.addGlobalSecondaryIndex({
        indexName: 'drEventId-index',
        partitionKey: { name: 'drEventId', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      contractsTable.addGlobalSecondaryIndex({
        indexName: 'status-index',
        partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      contractsTable.addGlobalSecondaryIndex({
        indexName: 'createdBy-index',
        partitionKey: { name: 'createdBy', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.contractsTable = contractsTable;

      // Ports Table
      const portsTable = new dynamodb.Table(tableScope, 'PortsTable', {
        tableName: `aquacharge-ports-${environmentName}`,
        partitionKey: { name: 'portId', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });
      this.portsTable = portsTable;

      // DREvents Table
      const drEventsTable = new dynamodb.Table(tableScope, 'DREventsTable', {
        tableName: `aquacharge-drevents-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        pointInTimeRecovery: true,
      });
      drEventsTable.addGlobalSecondaryIndex({
        indexName: 'stationId-index',
        partitionKey: { name: 'stationId', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      drEventsTable.addGlobalSecondaryIndex({
        indexName: 'status-index',
        partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
        sortKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      drEventsTable.addGlobalSecondaryIndex({
        indexName: 'startTime-index',
        partitionKey: { name: 'startTime', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.drEventsTable = drEventsTable;

      // Orgs Table
      const orgsTable = new dynamodb.Table(tableScope, 'OrgsTable', {
        tableName: `aquacharge-orgs-${environmentName}`,
        partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });
      orgsTable.addGlobalSecondaryIndex({
        indexName: 'displayName-index',
        partitionKey: { name: 'displayName', type: dynamodb.AttributeType.STRING },
        projectionType: dynamodb.ProjectionType.ALL,
      });
      this.orgsTable = orgsTable;
    }
  }
}