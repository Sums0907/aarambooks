# ADR-007: Context Capability Abstraction

## Status
Accepted

## Decision

Aaram Brain Core Intelligence Domains must request abstract "Context Capabilities" from the Brain Core Context Layer rather than coupling directly to underlying business system APIs, databases, or transport mechanisms.

When an Intelligence Domain (such as Inventory Intelligence) requires business truth, it formulates a `ContextAssemblyRequest` specifying the required `ProviderCapability` (e.g., `INVENTORY_MOVEMENTS`, `JOBWORK_CONTEXT`).

The Brain Core Context Layer (specifically the `ContextAssembler` and `ProviderRegistry`) owns the responsibility of resolving that capability request. It determines the `SourceSystem`, authenticates, invokes the appropriate physical transport (REST, gRPC, DB read), normalizes the truth into a standard Pydantic model with exact provenance (`SourceSystem`, `retrieval_timestamp`), and returns it to the domain.

If a requested capability does not currently have an implementation in the Context Layer, the Context Layer throws a `ProviderNotRegisteredError`. This constitutes a formal **Context Capability Gap**, allowing the domain to safely fall back without hallucinating.

## Architectural Intent

This decision enforces a strict decoupling between **Intelligence Reasoning** and **Data Transport**.

Intelligence Domains:
- Own natural language understanding.
- Own intent classification.
- Own determining *what* business facts are required.
- Own business insight synthesis.
- Do *not* own or know about APIs, REST routes, or HTTP clients.

Brain Core Context Layer:
- Owns determining *how* business facts are obtained.
- Owns ecosystem integration and M2M authentication.
- Owns context normalization and provenance tracking.

This prevents domains from becoming hard-coded API clients and allows Brain Core to swap physical transports (e.g., moving from REST to an Event-Stream read model) without altering a single line of domain reasoning logic.

## Governance Principle

Future architecture decisions must preserve:

Intelligence Domains request capabilities. 
Brain Core Context Layer resolves transport. 
Business systems own truth.
