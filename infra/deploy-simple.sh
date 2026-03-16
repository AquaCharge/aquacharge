#!/bin/bash

# AquaCharge Simple Deployment
# Deploys infrastructure and application to EC2 in one command

set -e

ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="AquaChargeStack-${ENVIRONMENT}"

if [ -z "$JWT_SECRET_KEY" ]; then
  echo "⚠️  JWT_SECRET_KEY is not set."
  if [ "$ENVIRONMENT" = "prod" ]; then
    echo "❌ JWT_SECRET_KEY is required for production deployments."
    echo "   Set it with: export JWT_SECRET_KEY=\"\$(openssl rand -hex 32)\""
    exit 1
  else
    JWT_SECRET_KEY="dev-jwt-secret-key-change-in-production"
    echo "   Using default dev JWT secret."
  fi
fi

echo "🚀 AquaCharge Deployment"
echo "========================"
echo ""

# Check for SSH key, create if doesn't exist
SSH_KEY="${SSH_KEY:-$HOME/.ssh/aquacharge-key.pem}"
KEY_NAME="aquacharge-key"

# Check if key exists in AWS
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME &>/dev/null; then
  echo "🔑 Creating SSH key pair in AWS..."
  aws ec2 create-key-pair \
    --key-name $KEY_NAME \
    --query 'KeyMaterial' \
    --output text > "$SSH_KEY"
  chmod 400 "$SSH_KEY"
  echo "✅ Key created: $SSH_KEY"
else
  echo "✅ Key pair exists in AWS: $KEY_NAME"
  if [ ! -f "$SSH_KEY" ]; then
    echo "⚠️  Key file not found locally at: $SSH_KEY"
    echo "Please download it from AWS Console or specify: SSH_KEY=/path/to/key.pem ./deploy-simple.sh"
    exit 1
  fi
fi

# Get IP for whitelisting
if [ -z "$ALLOWED_IPS" ]; then
  CURRENT_IP=$(curl -s https://api.ipify.org)/32
  echo "Using your IP: $CURRENT_IP"
  ALLOWED_IPS="$CURRENT_IP"
fi

# Deploy infrastructure
echo ""
echo "📦 Installing dependencies..."
npm install --silent

echo ""
echo "🏗️  Deploying infrastructure..."

npx cdk deploy \
  -c environment=$ENVIRONMENT \
  -c allowedIps="$ALLOWED_IPS" \
  -c useExistingTables=false \
  --require-approval never

echo "✅ Infrastructure deployed"

# Get instance IP
INSTANCE_IP=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIp`].OutputValue' \
  --output text)

echo ""
echo "Instance IP: $INSTANCE_IP"

# Wait for instance to be ready
echo ""
echo "⏳ Waiting for instance to be ready..."
sleep 30

# Wait for Docker to be installed
echo "⏳ Waiting for Docker installation to complete..."
for i in {1..12}; do
  if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    ec2-user@$INSTANCE_IP "command -v docker-compose" &>/dev/null; then
    echo "✅ Docker Compose is ready"
    break
  fi
  echo "   Still installing... ($i/12)"
  sleep 10
done

# Copy files
echo ""
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

# Start containers
echo ""
echo "🐳 Starting containers..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
cd /home/ec2-user/aquacharge

# Verify docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo "⚠️  Docker Compose not installed yet. Checking installation status..."
  sudo tail -30 /var/log/cloud-init-output.log
  exit 1
fi

# Always write the .env so it reflects the current deployment environment
echo "Creating .env file..."
cat > .env << ENVEOF
AWS_REGION=us-east-1
ENVIRONMENT=${ENVIRONMENT}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
FLASK_ENV=production
CLOUDWATCH_ENABLED=true
ENVEOF

# Start containers with sudo (ec2-user is in docker group but needs re-login)
sudo docker-compose -f docker-compose.prod.yaml down 2>/dev/null || true
sudo docker-compose -f docker-compose.prod.yaml up -d --build
sleep 5
sudo docker-compose -f docker-compose.prod.yaml ps
EOF

echo ""
echo "✅ DEPLOYED!"
echo ""
echo "Frontend: http://$INSTANCE_IP"
echo "Backend:  http://$INSTANCE_IP:5050/api/health"
echo ""
