# deploy
Ship a service to staging or production.

## Commands

Staging deploys are safe and do not need approval:

```
./scripts/deploy.sh staging <service>
```

Production deploys require a green staging run within the last hour:

```
./scripts/deploy.sh prod <service> --confirm
```

## Rules

Never deploy to production on a Friday after 3pm.
Always check `./scripts/status.sh` before and after a production deploy.
