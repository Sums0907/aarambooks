"""
NDR-domain-specific configuration, kept separate from src/shared/config.py's global
Settings on purpose - these are NDR business-policy values, not cross-domain infrastructure
config, and should be changeable (and reviewable) without touching the global settings file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class NDRSettings(BaseSettings):
    # Reschedule window, in days ahead of "now", keyed by NDR attempt number (string keys,
    # since env-provided JSON dicts key everything as strings). Confirmed directly against
    # ShopDeck's own NDR console: attempts 1 and 2 both offer a 2-day window (today+1,
    # today+2). 0 means no reschedule date is offered for that attempt - matches the
    # 3rd-attempt policy of not placing an NDR recovery call at all (see
    # NDRPriorityRiskEngine.evaluate_priority_and_risk's policy_allows_autonomous_action
    # check in knowledge.py), but is read here too so this computation never hardcodes an
    # attempt-specific value of its own.
    # Override with NDR_RESCHEDULE_WINDOW_DAYS='{"1": 2, "2": 2, "3": 0}' in .env.
    reschedule_window_days: dict[str, int] = {"1": 2, "2": 2, "3": 0}

    # NDR_MAX_CONCURRENT_CALLS determines how many simultaneous dispatch orchestration
    # pipelines the poller can run at once. 1 means strict sequential processing.
    max_concurrent_calls: int = 1

    @field_validator("max_concurrent_calls")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v < 1:
            raise ValueError("NDR_MAX_CONCURRENT_CALLS must be >= 1")
        return v

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="NDR_", extra="ignore"
    )

ndr_settings = NDRSettings()
