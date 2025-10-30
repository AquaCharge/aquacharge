# AquaCharge Infrastructure Overview

## Phase 1: Foundation & Data Layer

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud (us-east-1)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      VPC (10.0.0.0/16)                            │ │
│  │                                                                   │ │
│  │  ┌─────────────────────┐      ┌─────────────────────┐           │ │
│  │  │   Availability      │      │   Availability      │           │ │
│  │  │      Zone A         │      │      Zone B         │           │ │
│  │  ├─────────────────────┤      ├─────────────────────┤           │ │
│  │  │                     │      │                     │           │ │
│  │  │ Public Subnet       │      │ Public Subnet       │           │ │
│  │  │ (10.0.0.0/24)      │      │ (10.0.1.0/24)      │           │ │
│  │  │                     │      │                     │           │ │
│  │  │  [NAT Gateway]      │      │                     │           │ │
│  │  │                     │      │                     │           │ │
│  │  ├─────────────────────┤      ├─────────────────────┤           │ │
│  │  │                     │      │                     │           │ │
│  │  │ Private Subnet      │      │ Private Subnet      │           │ │
│  │  │ (10.0.2.0/24)      │      │ (10.0.3.0/24)      │           │ │
│  │  │                     │      │                     │           │ │
│  │  │  [ECS Cluster]      │      │                     │           │ │
│  │  │  (Ready for Tasks)  │      │                     │           │ │
│  │  │                     │      │                     │           │ │
│  │  ├─────────────────────┤      ├─────────────────────┤           │ │
│  │  │                     │      │                     │           │ │
│  │  │ Isolated Subnet     │      │ Isolated Subnet     │           │ │
│  │  │ (10.0.4.0/24)      │      │ (10.0.5.0/24)      │           │ │
│  │  │                     │      │                     │           │ │
│  │  │  [Database Layer]   │      │                     │           │ │
│  │  │                     │      │                     │           │ │
│  │  └─────────────────────┘      └─────────────────────┘           │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      DynamoDB Tables                              │ │
│  │                  (Serverless - No VPC)                            │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │ │
│  │  │   Users Table   │  │ Stations Table  │  │ Chargers Table  │ │ │
│  │  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │ │
│  │  │ PK: id          │  │ PK: id          │  │ PK: id          │ │ │
│  │  │ GSI: email      │  │ GSI: city       │  │ GSI: stationId  │ │ │
│  │  │ GSI: orgId      │  │ GSI: status     │  │ GSI: type       │ │ │
│  │  │                 │  │                 │  │                 │ │ │
│  │  │ • username      │  │ • name          │  │ • chargerType   │ │ │
│  │  │ • email         │  │ • address       │  │ • status        │ │ │
│  │  │ • password_hash │  │ • city          │  │ • powerOutput   │ │ │
│  │  │ • role          │  │ • coords        │  │ • voltage       │ │ │
│  │  │ • orgId         │  │ • amenities     │  │ • currentType   │ │ │
│  │  │ • timestamps    │  │ • status        │  │ • availability  │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────┐  ┌─────────────────┐                       │ │
│  │  │  Vessels Table  │  │ Bookings Table  │                       │ │
│  │  ├─────────────────┤  ├─────────────────┤                       │ │
│  │  │ PK: id          │  │ PK: id          │                       │ │
│  │  │ GSI: userId     │  │ GSI: userId     │                       │ │
│  │  │ GSI: type       │  │ GSI: stationId  │                       │ │
│  │  │                 │  │ GSI: vesselId   │                       │ │
│  │  │ • userId        │  │ GSI: status     │                       │ │
│  │  │ • name          │  │                 │                       │ │
│  │  │ • vesselType    │  │ • userId        │                       │ │
│  │  │ • manufacturer  │  │ • stationId     │                       │ │
│  │  │ • model         │  │ • vesselId      │                       │ │
│  │  │ • batterySize   │  │ • chargerId     │                       │ │
│  │  │ • chargerType   │  │ • startTime     │                       │ │
│  │  │ • timestamps    │  │ • endTime       │                       │ │
│  │  └─────────────────┘  │ • status        │                       │ │
│  │                       │ • totalCost     │                       │ │
│  │                       └─────────────────┘                       │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Container Registries (ECR)                     │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  ┌──────────────────────────┐  ┌──────────────────────────┐     │ │
│  │  │  Backend Repository      │  │  Frontend Repository     │     │ │
│  │  ├──────────────────────────┤  ├──────────────────────────┤     │ │
│  │  │ aquacharge-backend-dev   │  │ aquacharge-frontend-dev  │     │ │
│  │  │                          │  │                          │     │ │
│  │  │ • Flask API              │  │ • React + Vite           │     │ │
│  │  │ • Port: 5050             │  │ • Port: 5173             │     │ │
│  │  │ • DynamoDB Integration   │  │ • SPA                    │     │ │
│  │  │                          │  │                          │     │ │
│  │  │ Status: Empty (Phase 1)  │  │ Status: Empty (Phase 1)  │     │ │
│  │  │ Ready for image push     │  │ Ready for image push     │     │ │
│  │  └──────────────────────────┘  └──────────────────────────┘     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Secrets Manager                                │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  aquacharge-app-secrets-dev                              │   │ │
│  │  ├──────────────────────────────────────────────────────────┤   │ │
│  │  │  • jwt_secret (auto-generated)                           │   │ │
│  │  │  • Encrypted at rest                                     │   │ │
│  │  │  • Accessed by ECS tasks via IAM roles                   │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phase 2: Application Services (After Docker Images Pushed)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Application Load Balancers                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────┐          ┌────────────────────────┐       │
│  │   Backend ALB          │          │   Frontend ALB         │       │
│  │   (Port 80)            │          │   (Port 80)            │       │
│  │                        │          │                        │       │
│  │   Health Check:        │          │   Health Check:        │       │
│  │   /api/health          │          │   /                    │       │
│  └───────────┬────────────┘          └───────────┬────────────┘       │
│              │                                   │                     │
│              ▼                                   ▼                     │
│  ┌────────────────────────┐          ┌────────────────────────┐       │
│  │  Backend Target Group  │          │ Frontend Target Group  │       │
│  └───────────┬────────────┘          └───────────┬────────────┘       │
│              │                                   │                     │
│              ▼                                   ▼                     │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │               ECS Cluster (Fargate)                        │       │
│  │                                                             │       │
│  │  ┌──────────────────┐          ┌──────────────────┐       │       │
│  │  │  Backend Service │          │ Frontend Service │       │       │
│  │  ├──────────────────┤          ├──────────────────┤       │       │
│  │  │ Task Count: 1-4  │          │ Task Count: 1-4  │       │       │
│  │  │ CPU: 256         │          │ CPU: 256         │       │       │
│  │  │ Memory: 512 MB   │          │ Memory: 512 MB   │       │       │
│  │  │                  │          │                  │       │       │
│  │  │ Auto-scaling:    │          │ Auto-scaling:    │       │       │
│  │  │ • CPU > 70%      │          │ • CPU > 70%      │       │       │
│  │  │ • Memory > 80%   │          │ • Memory > 80%   │       │       │
│  │  │                  │          │                  │       │       │
│  │  │ Environment:     │          │ Environment:     │       │       │
│  │  │ • FLASK_ENV      │          │ • VITE_API_URL   │       │       │
│  │  │ • AWS_REGION     │          │                  │       │       │
│  │  │ • TABLE_NAMES    │          │                  │       │       │
│  │  │ • JWT_SECRET     │          │                  │       │       │
│  │  │   (from Secrets) │          │                  │       │       │
│  │  └──────────────────┘          └──────────────────┘       │       │
│  └────────────────────────────────────────────────────────────┘       │
│              │                                   │                     │
│              │ Read/Write                        │                     │
│              ▼                                   │                     │
│  ┌────────────────────────┐                     │                     │
│  │   DynamoDB Tables      │◄────────────────────┘                     │
│  │   (All 5 tables)       │    (Frontend calls Backend API)           │
│  └────────────────────────┘                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Resource Summary

### Phase 1 - Foundation (Current Deployment)

- ✅ **VPC**: 1 VPC with 6 subnets across 2 AZs
- ✅ **NAT Gateway**: 1 NAT Gateway for private subnet internet access
- ✅ **ECS Cluster**: Empty cluster ready for tasks
- ✅ **DynamoDB Tables**: 5 tables with GSIs
  - Users (3 GSIs)
  - Stations (2 GSIs)
  - Chargers (2 GSIs)
  - Vessels (2 GSIs)
  - Bookings (4 GSIs)
- ✅ **ECR Repositories**: 2 empty repositories
- ✅ **Secrets Manager**: 1 secret with auto-generated JWT key
- ✅ **CloudWatch Log Groups**: Ready for application logs

### Phase 2 - Application (After Image Push)

- ⏳ **Application Load Balancers**: 2 ALBs (frontend + backend)
- ⏳ **ECS Services**: 2 Fargate services
- ⏳ **Target Groups**: 2 target groups with health checks
- ⏳ **Auto Scaling**: CPU and memory-based scaling policies
- ⏳ **IAM Roles**: Task execution and task roles with DynamoDB permissions

## Cost Estimate (Monthly - Phase 1)

```
┌──────────────────────────────────┬──────────────┐
│ Resource                         │ Est. Cost    │
├──────────────────────────────────┼──────────────┤
│ VPC (NAT Gateway)                │ ~$32/month   │
│ DynamoDB (Pay-per-request)       │ ~$1-5/month  │
│ ECR Storage                      │ ~$0.10/GB    │
│ Secrets Manager                  │ ~$0.40/month │
│ CloudWatch Logs                  │ ~$0.50/month │
├──────────────────────────────────┼──────────────┤
│ Total Phase 1                    │ ~$34-38      │
└──────────────────────────────────┴──────────────┘

Phase 2 will add:
- ECS Fargate: ~$15-60/month (depends on usage)
- ALB: ~$16/month per ALB
- Data Transfer: Variable
Estimated Phase 2 addition: ~$47-92/month
```

## Next Steps

1. **Deploy Phase 1** (Current)

   ```bash
   cd /Users/lucassavoie/Documents/EngProject/aquacharge/infra
   ./deploy-phase1.sh
   ```

2. **Build & Push Docker Images**

   ```bash
   ./build-and-push.sh
   ```

3. **Deploy Phase 2** (Application Services)

   ```bash
   ./deploy-phase2.sh
   ```

4. **Initialize Sample Data** (Optional)
   ```bash
   python3 scripts/init-dynamodb-data.py
   ```
