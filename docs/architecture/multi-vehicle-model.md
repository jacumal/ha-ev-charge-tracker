# Multi-vehicle and multi-charger architecture

## Purpose

The integration must support several vehicles and several charging points without
assuming that one Home Assistant config entry represents one physical vehicle
forever. The first implementation remains profile-oriented for backward
compatibility, but profile identity must be separated from display names and
from Home Assistant's internal config-entry ID.

## Domain model

### Vehicle

A vehicle is a logical asset with a stable vehicle_id. Its display name is
editable and must not be used as a persistent storage key. Vehicle-level
telemetry can include SOC, odometer, usable battery capacity and optional 12 V
measurements. Some of these sensors may be shared by multiple charging profiles
belonging to the same vehicle.

### Charger

A charger is a physical charging point with a stable charger_id, a display
name, and optional hardware metadata. Charger-level telemetry can include
charging state, delivered energy, instantaneous power and dynamic electricity
price. A cumulative energy meter belongs to the charger, not to the vehicle.

### Charging profile

A profile links one vehicle to one charger and defines the sensor mapping and
session behavior for that pairing. The current config entry remains the
persistence and lifecycle boundary while the registry model is introduced.
The profile has its own entry_id; this remains the storage namespace for
sessions and history.

## Ownership and attribution rules

1. Every active profile must have one unambiguous charging-state source and one
   unambiguous delivered-energy source.
2. A charging-state entity or delivered-energy counter cannot be assigned to
   two profiles simultaneously. The first registry foundation enforces this
   during profile creation.
3. One vehicle may have several profiles for different chargers.
4. Vehicle telemetry such as SOC and odometer may be reused by profiles for
   the same vehicle; sharing across different vehicles must be explicit and
   should be warned about in a later registry UI.
5. A charger may serve different vehicles over time, but a single charger
   session must never be attributed to two vehicles at once. Shared-charger
   arbitration requires an explicit assignment signal or user selection and
   is not implemented by the current foundation.
6. A profile's history is immutable with respect to later changes in display
   names or sensor mappings. Each completed record should retain the vehicle
   and charger identity and display-name snapshots used at the time.

## Identity and compatibility

New profiles store normalized vehicle_id and charger_id values generated
from the initial names. The names remain presentation labels. Home Assistant
entry_id remains the key for coordinator storage, so adding identity fields
does not move or overwrite existing session history.

Existing entries created before these fields existed are legacy profiles.
They must continue to load using their existing entry IDs. A future migration
may backfill normalized identity fields, but it must be idempotent and must
never rename storage keys or discard history.

Changing a display name in a later options flow must not silently change the
stable ID. If explicit rename support is added, the user-facing operation must
preserve references and historical records.

## Implementation phases

1. Identity foundation (current PR): normalized IDs, profile resource
   conflict checks, pure unit tests.
2. Registry service: load all config entries into in-memory vehicle,
   charger and profile indexes; support legacy entries without rewriting them.
3. Config UX: explicit vehicle selection, create/select charger, edit
   display names, and show ownership conflicts before saving.
4. Session attribution: enforce one active session per physical charger and
   require explicit vehicle assignment for shared chargers.
5. History and entities: expose vehicle/charger identity on devices and
   session records; ensure unique entity/device identifiers.
6. Validation: test two vehicles/two chargers, one vehicle/two chargers,
   shared vehicle telemetry, conflicting meters, simultaneous charging and
   restart recovery.

## Non-goals and safety

The registry is read-only with respect to vehicle and charger controls. It
does not start or stop charging, change current limits, or control contactors.
A profile conflict must fail safely with a clear configuration error rather
than guessing which vehicle owns a charging session.
