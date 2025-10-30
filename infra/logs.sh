#!/bin/bash

# Check application logs and status on EC2

set -e

ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="AquaChargeStack-${ENVIRONMENT}"

echo "🔍 AquaCharge Status Check"
echo "=========================="
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

# Check your current IP
YOUR_IP=$(curl -s https://api.ipify.org)
echo "Your current IP: $YOUR_IP"
echo ""

SSH_KEY="${SSH_KEY:-$HOME/.ssh/aquacharge-key.pem}"

echo "Connecting to instance..."
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
cd /home/ec2-user/aquacharge

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 CONTAINER STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo docker-compose ps
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔌 PORT MAPPINGS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo docker ps --format "{{.Names}}: {{.Ports}}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 LOCAL HEALTH CHECKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -n "Backend (port 5050): "
if curl -s -f http://localhost:5050/api/health > /dev/null 2>&1; then
  echo "✅ OK"
else
  echo "❌ FAILED"
fi

echo -n "Frontend (port 80): "
if curl -s -f -I http://localhost:80 > /dev/null 2>&1; then
  echo "✅ OK"
else
  echo "❌ FAILED"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 BACKEND LOGS (last 20 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo docker-compose logs --tail=20 backend 2>/dev/null || echo "No logs available"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 FRONTEND LOGS (last 20 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo docker-compose logs --tail=20 frontend 2>/dev/null || echo "No logs available"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  ENVIRONMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat .env 2>/dev/null || echo ".env file not found"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 ACCESS URLS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend:  http://$INSTANCE_IP"
echo "Backend:   http://$INSTANCE_IP:5050/api/health"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 TROUBLESHOOTING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If you can't access from browser:"
echo ""
echo "1. Check if your IP changed:"
echo "   Your IP: $YOUR_IP"
echo "   Redeploy if changed: ./deploy-simple.sh"
echo ""
echo "2. Check AWS Security Group:"
echo "   EC2 Console → Security Groups → aquacharge-sg-dev"
echo "   Should allow ports 80, 443, 5050 from $YOUR_IP/32"
echo ""
echo "3. Follow logs live:"
echo "   ssh -i $SSH_KEY ec2-user@$INSTANCE_IP"
echo "   cd /home/ec2-user/aquacharge"
echo "   sudo docker-compose logs -f"
echo ""
echo "4. Restart containers:"
echo "   ssh -i $SSH_KEY ec2-user@$INSTANCE_IP"
echo "   cd /home/ec2-user/aquacharge"
echo "   sudo docker-compose restart"
echo ""
