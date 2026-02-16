# AquaCharge Ticket Sequencing (Unblock-First)

This sequencing is designed to minimize team blocking by completing shared dependencies early.

---

## Person B — DynamoDB Migration (do this first overall)

1. **SCRUM-157** — Create DynamoClient abstraction layer for Flask  
2. **SCRUM-160** — Create DynamoDB Org table and model  
3. **SCRUM-158** — Create DynamoDB Users table and migrate auth  
4. **SCRUM-161** — Create DynamoDB Vessels table and fix model  
5. **SCRUM-159** — Create DynamoDB Stations and Chargers tables  
6. **SCRUM-162** — Create DynamoDB Bookings table  
7. **SCRUM-163** — Create DynamoDB DREvents table and model  
8. **SCRUM-164** — Create DynamoDB Contracts table and fix model  
9. **SCRUM-165** — Enable DynamoDB encryption, backups, and pay-per-request mode  

**Why:** Everyone else depends on stable models + tables.

---

## Person C — Auth + Monitoring/Infra (start after Users table exists)

1. **SCRUM-173** — Create AuthService with proper separation from API  
2. **SCRUM-195** — Add account type selection to registration flow  
3. **SCRUM-196** — Implement email verification flow  
4. **SCRUM-197** — Implement proper JWT invalidation and type-based auth  
5. **SCRUM-177** — Create MonitoringService for analytics and progress  
6. **SCRUM-200** — Implement CloudWatch 60-second heartbeat monitoring  
7. **SCRUM-202** — Implement error rate tracking and CloudWatch logging  
8. **SCRUM-201** — Add API latency tracking with CloudWatch  
9. **SCRUM-203** — Implement load testing for 100 concurrent users  

**Why:** Get auth stable early; monitoring/logging before load testing.

---

## Person D — Booking + DR Execution + Telemetry + Notifications Backend

**Service layer + core flows first, then automation/notifications**

1. **SCRUM-174** — Create BookingService with business logic separation  
2. **SCRUM-175** — Create ContractService for DR event management  
3. **SCRUM-176** — Create EligibilityService for vessel evaluation  
4. **SCRUM-166** — Create DREvents API endpoints and model  
5. **SCRUM-167** — Implement DR event lifecycle state machine  
6. **SCRUM-168** — Build SOC & location forecasting for vessel eligibility  
7. **SCRUM-169** — Implement contract dispatch and VO acceptance flow  
8. **SCRUM-170** — Build smart contract validation (pre and post event)  
9. **SCRUM-191** — Implement FCFS booking queue system  
10. **SCRUM-193** — Implement port availability enforcement for DR events  
11. **SCRUM-192** — Add booking purpose tracking field  
12. **SCRUM-194** — Implement historical booking data retention (6+ months)  
13. **SCRUM-188** — Add vessel operational states to model  
14. **SCRUM-189** — Add geographic coordinates and SOC tracking to vessel model  
15. **SCRUM-190** — Build vessel telemetry simulation  
16. **SCRUM-179** — Implement 5-minute control loop for active DR events  
17. **SCRUM-178** — Create SettlementService for payment processing  
18. **SCRUM-183** — Build settlement processing after DR event completion  
19. **SCRUM-184** — Create notification data model and backend API  
20. **SCRUM-187** — Implement scheduled booking reminder notifications  
21. **SCRUM-186** — Implement email notification integration  

**Why:** You need event + booking primitives before telemetry loop, settlement, and notifications.

---

## Person A — Frontend (start with auth/core UI, then dashboards/analytics)

1. **SCRUM-204** — Optimize login and home page load time to under 3 seconds  
2. **SCRUM-172** — Build VO contract review and acceptance UI  
3. **SCRUM-171** — Build DR event creation UI for PSO dashboard  
4. **SCRUM-181** — Build VO real-time dashboard with active contracts  
5. **SCRUM-180** — Build PSO real-time DR monitoring dashboard  
6. **SCRUM-182** — Implement 5-minute frontend polling for DR event status updates  
7. **SCRUM-185** — Build in-app notification dropdown UI component  
8. **SCRUM-209** — Build VO contract history view  
9. **SCRUM-210** — Build VO earnings summary view  
10. **SCRUM-211** — Build VO transaction history view  
11. **SCRUM-212** — Build VO V2G participation settings view  
12. **SCRUM-206** — Build PSO historical view for past DR events  
13. **SCRUM-207** — Build PSO financial view for historic financial returns  
14. **SCRUM-208** — Build PSO statistical view for DR events and data trends  
15. **SCRUM-205** — Build PSO analytical dashboards with real data  

**Why:** Real-time + core flows first; analytics last once backend data/monitoring is stable.