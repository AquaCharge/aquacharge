# AquaCharge Infrastructure Documentation

## Overview

This is a **simplified, cost-effective** infrastructure setup for AquaCharge using AWS CloudFormation (via CDK). The architecture is designed for internal use with a budget of $200 over 8 months.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  EC2 Instance (t3.micro - ~$7.50/month)                    │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │  Docker Compose Stack                                │  │   │
│  │  │  ┌──────────────┐   ┌──────────────┐               │  │   │
│  │  │  │   Backend    │   │   Frontend   │               │  │   │
│  │  │  │  Flask:5050  │   │  React:80    │               │  │   │
│  │  │  └──────┬───────┘   └──────────────┘               │  │   │
│  │  │         │                                            │  │   │
│  │  │         │ Uses IAM role to access DynamoDB          │  │   │
│  │  │         └────────────────────────────────────────┐  │  │   │
│  │  └──────────────────────────────────────────────────│──┘  │   │
│  └───────────────────────────────────────────────────────│─────┘   │
│                                                          │          │
│  ┌─────────────────────────────────────────────┐        │          │
│  │  Security Group (IP Whitelisting)           │        │          │
│  │  • SSH (22): Only whitelisted IPs           │        │          │
│  │  • HTTP (80): Only whitelisted IPs          │        │          │
│  │  • HTTPS (443): Only whitelisted IPs        │        │          │
│  └─────────────────────────────────────────────┘        │          │
│                                                          ▼          │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              DynamoDB Tables (Pay-per-request)              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │
│  │  │  Users   │ │ Stations │ │ Chargers │ │ Vessels  │      │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │  │
│  │  ┌──────────┐                                              │  │
│  │  │ Bookings │                                              │  │
│  │  └──────────┘                                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Cost Breakdown

| Resource                   | Monthly Cost      | Notes                      |
| -------------------------- | ----------------- | -------------------------- |
| EC2 t3.micro               | ~$7.50            | On-demand pricing          |
| EBS Storage (30GB GP3)     | ~$2.40            | For instance storage       |
| DynamoDB (Pay-per-request) | ~$1-3             | Based on usage             |
| Data Transfer              | ~$1               | Minimal for internal use   |
| **Total**                  | **~$12-14/month** | **~$96-112 over 8 months** |

**Budget remaining:** ~$88-104 for development/testing

## Security Features

### 1. IP Whitelisting

Only specified IP addresses can access the application:

- SSH access (port 22)
- HTTP access (port 80)
- HTTPS access (port 443)

### 2. Rate Limiting

Backend implements Flask-Limiter:

- **200 requests per day per IP**
- **50 requests per hour per IP**
- Prevents abuse and resource exhaustion

### 3. IAM Roles

EC2 instance uses IAM roles (not access keys) to access DynamoDB securely.

### 4. Encryption

- DynamoDB tables: Encrypted at rest with AWS managed keys
- EBS volumes: Encrypted
- Point-in-time recovery enabled for all tables

## Deployment

### Prerequisites

1. AWS CLI configured with credentials
2. Node.js and npm installed
3. Your IP address (for whitelisting)

### Step 1: Deploy Infrastructure

```bash
cd infra

# Set your IP address for whitelisting (IMPORTANT!)
export ALLOWED_IPS="YOUR_IP/32"  # e.g., "203.0.113.42/32"

# Optional: Add multiple IPs (comma-separated)
export ALLOWED_IPS="203.0.113.42/32,198.51.100.0/24"

# Deploy
./deploy-ec2.sh
```

The script will:

- Create VPC and security groups
- Launch EC2 instance with Docker installed
- Create all DynamoDB tables with indexes
- Configure IAM roles and permissions

### Step 2: Get Instance Information

After deployment, note the outputs:

```bash
# Get instance IP
aws cloudformation describe-stacks \
  --stack-name AquaChargeStack-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIp`].OutputValue' \
  --output text
```

### Step 3: Deploy Application to EC2

```bash
# SSH into the instance
ssh -i your-key.pem ec2-user@<INSTANCE_IP>

# Create docker-compose.yaml
cat > /home/ec2-user/aquacharge/docker-compose.yaml << 'EOF'
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "5050:5050"
    environment:
      - FLASK_ENV=development
      - AWS_REGION=${AWS_REGION}
      - DYNAMODB_USERS_TABLE=${DYNAMODB_USERS_TABLE}
      - DYNAMODB_STATIONS_TABLE=${DYNAMODB_STATIONS_TABLE}
      - DYNAMODB_CHARGERS_TABLE=${DYNAMODB_CHARGERS_TABLE}
      - DYNAMODB_VESSELS_TABLE=${DYNAMODB_VESSELS_TABLE}
      - DYNAMODB_BOOKINGS_TABLE=${DYNAMODB_BOOKINGS_TABLE}
    env_file:
      - .env
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:5173"
    environment:
      - VITE_API_URL=http://localhost:5050
    depends_on:
      - backend
    restart: unless-stopped
EOF

# Copy your application code (from your local machine)
# Use SCP or git clone
git clone https://github.com/AquaCharge/aquacharge.git /home/ec2-user/aquacharge

# Start the application
cd /home/ec2-user/aquacharge
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 4: Initialize Sample Data

```bash
# From your local machine
cd infra
python3 scripts/init-dynamodb-data.py
```

## Accessing the Application

After deployment:

- **Frontend:** `http://<INSTANCE_IP>`
- **Backend API:** `http://<INSTANCE_IP>:5050/api`
- **Health Check:** `http://<INSTANCE_IP>:5050/api/health`

## Adding/Removing Whitelisted IPs

### To add your current IP:

```bash
CURRENT_IP=$(curl -s https://api.ipify.org)/32
echo "Your IP: $CURRENT_IP"

# Redeploy with new IP
export ALLOWED_IPS="$CURRENT_IP"
./deploy-ec2.sh
```

### To add team member IPs:

```bash
export ALLOWED_IPS="203.0.113.42/32,198.51.100.5/32,192.0.2.10/32"
./deploy-ec2.sh
```

### To allow all IPs (not recommended):

Leave `ALLOWED_IPS` empty - the script will warn you.

## Monitoring

### View Application Logs

```bash
ssh -i your-key.pem ec2-user@<INSTANCE_IP>
cd /home/ec2-user/aquacharge
docker-compose logs -f
```

### Check Resource Usage

```bash
# CPU and Memory
docker stats

# Disk space
df -h

# Rate limit violations (in backend logs)
docker-compose logs backend | grep "Rate limit"
```

### CloudWatch Metrics

The instance sends metrics to CloudWatch via the CloudWatch agent installed during setup.

## Rate Limiting Configuration

Rate limits are configured in `backend/app.py`:

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
```

**To adjust limits:**

1. Edit `backend/app.py`
2. Rebuild and restart: `docker-compose up -d --build backend`

**Recommended limits for internal use:**

- Development: `500/day, 100/hour`
- Production: `200/day, 50/hour`

## Troubleshooting

### Cannot connect to instance

1. Check security group has your IP whitelisted
2. Verify instance is running: `aws ec2 describe-instances`
3. Ensure you're using the correct SSH key

### Rate limit errors

1. Check logs: `docker-compose logs backend | grep "429"`
2. Increase limits in `backend/app.py` if legitimate traffic
3. Verify no automated scripts are hammering the API

### DynamoDB access errors

1. Verify IAM role is attached to EC2 instance
2. Check environment variables in `.env` file
3. Ensure tables were created successfully

### High costs

1. Stop EC2 instance when not in use:
   ```bash
   aws ec2 stop-instances --instance-ids <INSTANCE_ID>
   ```
2. Check DynamoDB usage in AWS console
3. Review CloudWatch metrics for unusual activity

## Cleanup

To delete all resources:

```bash
cd infra
npx cdk destroy AquaChargeStack-dev
```

**Warning:** This will delete:

- EC2 instance and all data
- DynamoDB tables (unless `RETAIN` policy prevents it)
- VPC and security groups

**DynamoDB tables are retained by default** to prevent data loss. To manually delete:

```bash
aws dynamodb delete-table --table-name aquacharge-users-dev
aws dynamodb delete-table --table-name aquacharge-stations-dev
# ... repeat for other tables
```

## Advanced Configuration

### Change Instance Type

```bash
export INSTANCE_TYPE="t3.small"  # More power: ~$15/month
./deploy-ec2.sh
```

### Enable HTTPS

1. Get a domain name
2. Configure Route 53 or external DNS
3. Install Let's Encrypt certificate on EC2
4. Update docker-compose to use nginx with SSL

### Backup Strategy

DynamoDB point-in-time recovery is enabled. To create manual backup:

```bash
aws dynamodb create-backup \
  --table-name aquacharge-users-dev \
  --backup-name users-backup-$(date +%Y%m%d)
```

## Architecture Decisions

### Why EC2 instead of Fargate?

- **Cost:** ~$12/month vs ~$50-100/month
- **Simplicity:** Direct SSH access for debugging
- **Control:** Full control over Docker environment
- **Learning:** Better for understanding infrastructure

### Why DynamoDB?

- **Serverless:** Pay only for what you use
- **Scalability:** Can handle growth without changes
- **Reliability:** Managed backups and replication
- **Cost:** ~$1-3/month for low usage

### Why IP Whitelisting?

- **Security:** Prevents public access
- **Cost Protection:** Prevents abuse and excessive charges
- **Simplicity:** No need for VPN or complex network setup

## Support

For issues or questions:

1. Check CloudWatch logs
2. Review this documentation
3. Check AWS cost explorer for unexpected charges
4. Contact team lead

---

**Last Updated:** October 27, 2025
