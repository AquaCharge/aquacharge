# Dev Demo Runbook

## Demo data commands

Preview the exact shared dev-table mutations:

```bash
make demo-data-dev
```

Apply the scoped cleanup and reseed:

```bash
make demo-data-dev ARGS="--apply"
```

Preview the exact shared prod-table mutations:

```bash
make demo-data-prod
```

Apply the scoped cleanup and reseed to prod:

```bash
make demo-data-prod ARGS="--apply --confirm-production"
```

Safety notes:

- `make demo-data-dev` runs with `ENVIRONMENT=dev`.
- `make demo-data-prod` runs with `ENVIRONMENT=prod`.
- It does not delete or recreate tables.
- It performs item-level cleanup only.
- For demo consistency, it treats the shared demo operational tables (`stations`, `chargers`, `drevents`, `contracts`, `bookings`, `measurements`) as seed-owned.
- Production apply requires the explicit `--confirm-production` flag.
- The current demo-account expectations are:
  - Dev VO: `sarah.chen@bayshipping.com`
  - Dev PSO: `robert.wilson@gridoperator.com`
  - Prod VO: `sarah.chen@aquacharge.demo`
  - Prod PSO: `alex.rivera@aquacharge.demo`
- Marco Rossi remains untouched by the current seed; the historical/live demo path is centered on Sarah Chen.

## Seeded scenario

After `--apply`, the shared dev environment should contain:

- Sarah Chen’s current vessel set to `Harbor Spirit`
- Demo stations in Moncton, Saint John, and Halifax
- Halifax as the known-good live demo station
- Six historical DR events across the previous week with statuses limited to `Completed` and `Archived`
- Historical bookings, contracts, and measurements tied to Sarah’s demo vessel

## Rehearsal flow

1. Log in as Robert Wilson and open the PSO Dashboard.
2. Confirm the latest seeded historical event appears with non-empty monitoring data.
3. Open Analytics, leave the DR event filter on `Aggregate across all DR events`, and confirm the seeded six-event history fills the 7-day view.
4. Go to DR Events and create a new Halifax event.
5. Dispatch the event and verify an offer is created for Sarah Chen’s vessel.
6. Log in as Sarah Chen.
7. Open My Contracts, accept the contract, add terms, and book the Halifax charger.
8. Return to Robert Wilson on the PSO Dashboard.
9. Select the committed live event and click `Start DR Event`.
10. Wait one polling cycle plus one 10-second dispatch interval and confirm live measurements appear on both PSO and VO dashboards.
11. When you want to stop the live stream for rehearsal/demo timing, click `End DR Event` on the PSO Dashboard.
