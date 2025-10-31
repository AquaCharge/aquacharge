#!/bin/bash

# Quick update script - deploys code changes without redeploying infrastructure

set -e

ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="AquaChargeStack-${ENVIRONMENT}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/aquacharge-key.pem}"

echo "🔄 Quick Application Update"
echo "============================"
echo ""

# Get instance IP
INSTANCE_IP=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIp`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$INSTANCE_IP" ]; then
  echo "❌ No instance found. Run: ./deploy-simple.sh"
  exit 1
fi

echo "Instance IP: $INSTANCE_IP"
echo ""

# Copy files
echo "📦 Copying files to EC2..."
cd ..
rsync -av --progress \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.vscode' \
  --exclude='*.log' \
  --exclude='.DS_Store' \
  --exclude='cdk.out' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  backend frontend docker-compose.prod.yaml \
  ec2-user@$INSTANCE_IP:/home/ec2-user/aquacharge/

# Restart containers
echo ""
echo "🐳 Restarting containers..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
cd /home/ec2-user/aquacharge
sudo docker-compose -f docker-compose.prod.yaml down
sudo docker-compose -f docker-compose.prod.yaml up -d --build
sleep 5
sudo docker-compose -f docker-compose.prod.yaml ps
EOF

echo ""
echo "✅ UPDATED!"
echo ""
echo "Frontend: http://$INSTANCE_IP"
echo "Backend:  http://$INSTANCE_IP:5050/api/health"
echo ""
