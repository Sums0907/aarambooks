from sqlalchemy.orm import declarative_base

# The Context Engine does not own customer/order/product truth.
# Any models here should be strictly restricted to internal engine state (if any).
# Currently, it is a stateless aggregation engine.

Base = declarative_base()
