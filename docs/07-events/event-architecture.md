# Event Architecture

## Purpose

The Event Architecture defines how meaningful business occurrences are communicated across the AaramBooks ecosystem.

Events allow independent business systems, Aaram Brain, intelligence domains, and intelligence applications to understand changes while preserving ownership boundaries.

## Core Principle

Business systems create truth.
Aaram Brain creates intelligence from that truth.

Events communicate changes in business truth. They do not create or transfer ownership.

Events communicate business truth changes and collaboration signals.
Events do not own business truth and must not become duplicate operational databases.

## Role of Events

Events provide ecosystem awareness of meaningful business occurrences.

They enable:

- Loose coupling between domains.
- Business context propagation.
- Intelligence generation from trusted changes.
- Future ecosystem evolution.

## Relationship With API Contracts

API Contracts define direct capability interaction.

Events define communication of completed business changes.

APIs answer:
"What capability can be requested?"

Events answer:
"What meaningful business change occurred?"

Both coexist and serve different purposes.

## Ownership Model

Business systems own operational truth.

Aaram Brain consumes business events and creates intelligence.

Intelligence domains consume relevant events to generate domain intelligence.

Events do not replace domain ownership.

## Architectural Boundary

This document defines conceptual architecture only.

It does not define:
- Event payloads.
- Schemas.
- Brokers.
- Infrastructure.
- Deployment decisions.
