# Catalog Business System - vendored copy, test-only

This directory is **not** the authoritative source for Catalog anymore. Catalog has its
own fully independent repository - separate git history, separate deploy pipeline,
separate production database, with zero sharing with ShopDeck's:

https://github.com/Sums0907/aarambooks-catalog

(ShopDeck was split out the same way, into https://github.com/Sums0907/aarambooks-shopdeck
- the two used to share a combined `aarambooks-business-systems` repo, which is now
superseded and should not be used for new work.)

This copy is kept here solely because `tests/intelligence_domains/catalog_intelligence/test_catalog_integration.py`
and `tests/architecture/test_boundary_corrections.py` run real, in-process integration
tests against Catalog's actual FastAPI app (`api.py`) and real database via
`httpx.ASGITransport` - that requires Catalog's code to be physically importable from
within this repo. No production code path imports anything from this directory: Brain
reaches Catalog only over HTTP now, via `src/infrastructure/adapters/catalog_cem_adapter.py`
and the `CATALOG_URL`/`CATALOG_INTERNAL_TOKEN` settings in `src/shared/config.py`.

**If you change Catalog's code, make the change in the `aarambooks-catalog` repo first,
then copy it here to keep the test fixtures in sync.** Nothing enforces this
automatically - a drift between the two copies means these tests stop proving anything
real about the deployed Catalog service.
