# Business Adapter Contract Pattern

## Purpose
The Business Adapter Contract Pattern defines how the Context Engine retrieves information from external Business Systems without tightly coupling the Brain Core to specific vendors or platforms.

## Provider Contract Concept
Instead of the Context Engine calling specific systems (like ShopDeck), it defines a generic **Provider Contract** (e.g., `CustomerContextProvider`, `OrderContextProvider`). 

The Context Engine depends exclusively on these contracts, not on the concrete implementations.

## Adapter Responsibility
Business Adapters are responsible for:
- Implementing the generic Provider Contracts.
- Translating the generic request into a system-specific API call (e.g., HTTP request to ShopDeck).
- Formatting the specific response back into the generic `Shared Context Contract` format.

## Future Extensibility
Because the Context Engine only knows about the contract, the system is fully extensible. We can seamlessly swap or support additional providers in the future:
- ShopDeck
- Amazon
- Flipkart
- Other marketplaces

## Core Rule
> Brain Core defines the required context. Business Adapters define how that context is obtained.
