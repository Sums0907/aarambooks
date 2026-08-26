# Application Composition Boundary

## 1. Purpose
The Application Composition Root pattern is the strict boundary that dictates how components in AaramBooks are configured, instantiated, and wired together. Its primary purpose is to isolate domain logic (Brain Core) from infrastructure concerns, external configurations, and specific adapter implementations.

## 2. Who Owns Construction and Configuration?
- **Ownership:** The Application Composition Root (`src/main.py` or dedicated bootstrap modules in the application root).
- **Configuration Source:** Validated configuration settings (`src/shared/config.py`), completely driven by injected environment variables.
- Brain Core and Intelligence Domains must **never** instantiate concrete infrastructure components or directly read environment variables.

## 3. Configuration Flow
1. OS environment variables (or `.env` file) are loaded into the application context.
2. `src/shared/config.py` validates the existence and types of all required credentials using strict schemas (e.g., Pydantic). Any missing or invalid configuration causes an immediate startup crash.
3. The Composition Root extracts the validated credentials and injects them directly into the constructors of concrete Business Adapters (e.g., `ShopDeckAdapter(api_key=settings.shopdeck_api_key)`).

## 4. Provider Lifecycle and Eager Construction
- **Eager Construction:** Providers are instantiated **eagerly at startup**, not lazily upon first request. 
- **Fail-Fast Safety:** Eager construction ensures that misconfigurations (like missing API keys) or duplicate registry mappings trigger an immediate crash during deployment, completely avoiding silent runtime failures in production.
- **State:** Once successfully constructed and registered, providers remain stateless, thread-safe singletons for the duration of the server's lifecycle.

## 5. Development vs. Production
Following the Environment Isolation Standard, the Composition Root executes identically across all environments (Development, CI, Staging, Production). Environment transitions require **zero code changes**—only the external environment variables change.

## 6. Integrating Future Providers
To add a new integration (e.g., ShopDeck, Amazon, AaramInventory):
1. Create the concrete adapter in `src/business_adapters`.
2. Add the required API URLs/Keys to `.env.example` and `src/shared/config.py`.
3. Instantiate the adapter in the Composition Root passing the new configuration.
4. Wire it into the `ProviderRegistry`.
**Brain Core source code remains untouched during this process.**
