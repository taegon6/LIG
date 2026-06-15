# Safety Statement

Aegis-Swarm v2 is a local-only cyber-defense simulation MVP. The public
repository is designed for DAH preliminary review and does not contain real
offensive cyber capability.

## Explicitly Excluded

- Real exploit code
- Network or port probing
- Brute force or credential attacks
- Credential theft
- Malware, persistence, destructive behavior, or lateral movement
- External target interaction
- Shell-based attack behavior
- Real firewall, service, or system changes as defensive actions

## What Red Actually Does

The Red Agent chooses one of six safe event types and inserts a synthetic local
event into the application. These events model traffic, auth, telemetry,
service, command, and log-noise pressure without contacting outside systems.

## What Blue Actually Does

The Blue Agent calculates local risk and records a simulated defensive action.
The action registry updates local mission state only. No operating-system
security controls are changed.

## Adapter Boundary

The default adapter is local. The competition adapter in the public repository
is a stub. Any official runtime integration must be implemented privately after
rules and access are available.
