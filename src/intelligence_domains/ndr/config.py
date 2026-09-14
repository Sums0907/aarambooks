"""
NDR-domain-specific configuration, kept separate from src/shared/config.py's global
Settings on purpose - these are NDR business-policy values, not cross-domain infrastructure
config, and should be changeable (and reviewable) without touching the global settings file.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# All NDR customers are in India - calling-hours checks are always against India Standard
# Time regardless of what timezone the server itself runs in (production runs in UTC).
_IST = ZoneInfo("Asia/Kolkata")


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

    # After a call is dispatched, the poller's dispatch slot (see max_concurrent_calls) is
    # held until the live conversation actually reaches a terminal state (COMPLETED/FAILED/
    # ESCALATED, set by the Exotel/Sarvam webhook handler when the call really ends) - not
    # just until the dispatch API call returns. Added 2026-09-14: previously the slot freed
    # immediately after dispatch, so with a backlog of eligible NDRs the poller could fire
    # the next call within one poll_interval_seconds of the last, while the previous call was
    # still ringing or in progress on the same phone (a real risk when TEST_PHONE_OVERRIDE
    # routes every call to one test number). NDR_CALL_COMPLETION_POLL_SECONDS is how often the
    # poller re-checks the engagement's status while waiting; NDR_CALL_COMPLETION_MAX_WAIT_SECONDS
    # is a safety ceiling so a webhook that never arrives (e.g. dropped call, provider outage)
    # can't hang the dispatch slot forever - after this, the wait gives up and the slot frees
    # regardless, logged as a warning since it likely means a live call's true outcome was
    # never recorded.
    call_completion_poll_seconds: int = 5
    call_completion_max_wait_seconds: int = 600

    @field_validator("call_completion_poll_seconds", "call_completion_max_wait_seconds")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Call-completion wait settings must be >= 1 second")
        return v

    # Calling-hours window, in India Standard Time, 24-hour clock. Nothing in this pipeline
    # checked this before 2026-09-13 - an NDR becoming eligible at 2 AM would have been
    # called at 2 AM. Start moved from 9 AM to 11 AM on 2026-09-13 per business decision -
    # not a confirmed legal/regulatory boundary - the user should adjust these via
    # NDR_CALLING_HOURS_START_IST / NDR_CALLING_HOURS_END_IST if a different window is
    # actually required (e.g. matching TRAI's commercial-communication hours, if this class
    # of call falls under them).
    calling_hours_start_ist: int = 11
    calling_hours_end_ist: int = 19

    @field_validator("calling_hours_start_ist", "calling_hours_end_ist")
    @classmethod
    def validate_hour(cls, v: int) -> int:
        if not (0 <= v <= 24):
            raise ValueError("Calling-hours values must be between 0 and 24")
        return v

    def is_within_calling_hours(self, now: datetime | None = None) -> bool:
        """
        True if `now` (default: real current time) falls inside the allowed IST calling
        window. Used to gate the NDR Queue Poller's claim attempts, not just its dispatch
        logic - the item is left unclaimed and untouched in ShopDeck's queue entirely outside
        this window, rather than claimed and then held or rejected (which would burn into the
        limited max_retries budget for no reason).
        """
        current = (now or datetime.now(_IST)).astimezone(_IST)
        return self.calling_hours_start_ist <= current.hour < self.calling_hours_end_ist

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="NDR_", extra="ignore"
    )

ndr_settings = NDRSettings()
