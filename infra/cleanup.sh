#!/bin/bash

# Delete AquaCharge infrastructure (keeps DynamoDB tables)

set -e

ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="AquaChargeStack-${ENVIRONMENT}"

echo "🗑️  Cleanup AquaCharge Infrastructure"
echo "======================================"
echo ""
echo "⚠️  This will delete:"
echo "  - EC2 instance"
echo "  - VPC and networking"
echo "  - Security groups"
echo "  - IAM roles"
echo ""
echo "✅ This will NOT delete:"
echo "  - DynamoDB tables (kept for data preservation)"
echo ""

read -p "Continue? (type 'yes'): " -r
if [ "$REPLY" != "yes" ]; then
  echo "Cancelled"
  exit 0
fi

echo ""
echo "Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name $STACK_NAME

echo "Waiting for deletion..."
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "DynamoDB tables preserved:"
echo "  - aquacharge-users-$ENVIRONMENT"
echo "  - aquacharge-stations-$ENVIRONMENT"
echo "  - aquacharge-chargers-$ENVIRONMENT"
echo "  - aquacharge-vessels-$ENVIRONMENT"
echo "  - aquacharge-bookings-$ENVIRONMENT"
echo ""
