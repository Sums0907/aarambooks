# ShopDeck NDR Database Schema

**Source:** Live VPS Postgres Database (`shopdeck_bs_prod`)
**Capture Date:** 2026-09-13

---

### 1. `shipment_ndr_reports`
This table stores the high-level summary of an NDR (Non-Delivery Report) for a specific shipment. There is exactly one row per `awb_no` (enforced by a unique index).

| Column | Type | Description / Notes |
| :--- | :--- | :--- |
| `_id` | text | ShopDeck internal ID |
| `seller_group_id` | text | The "NS..." Order ID (Primary join key for line items) |
| `seller_clubbed_id` | text | ID used if multiple orders were clubbed together |
| `awb_no` | text | The tracking number (**Unique Index**) |
| `order_status` | text | Current status |
| `courier_partner` | text | e.g. Delhivery, Ecom Express |
| `courier_company_id` | text | Courier's internal ID |
| `payment_mode` | text | COD / Prepaid / etc. |
| `customer_id` | text | ShopDeck Customer ID |
| `customer_name` | text | Customer's Name |
| `seller_id` | text | ShopDeck Seller ID |
| `pickup_time` | timestamp (tz) | When the courier picked it up |
| `latest_ndr_time` | timestamp (tz) | Timestamp of the most recent NDR |
| `latest_ndr_reason` | text | Reason for NDR (e.g. "Customer unavailable") |
| `latest_ofd_time` | timestamp (tz) | When it was last Out For Delivery |
| `delivery_time` | timestamp (tz) | Delivery timestamp (if resolved) |
| `ndr_count` | integer | Total times delivery was attempted and failed |
| `ofd_count` | integer | Total times marked Out For Delivery |
| `seller_actions` | text | Actions taken by the seller (JSON string or text) |
| `ndr_status` | text | Current NDR resolution status |


### 2. `ndr_action_log`
This table stores the historical log of every single action taken on an NDR (such as the seller requesting a reattempt, or an automated IVR call to the customer). Multiple rows can exist for a single `awb_no`. The unique index is strictly on `_id`.

| Column | Type | Description / Notes |
| :--- | :--- | :--- |
| `_id` | text | ShopDeck internal ID (**Unique Index**) |
| `awb_no` | text | The tracking number |
| `ndr_count` | integer | Which NDR attempt this action relates to |
| `action_type` | text | e.g. "Reattempt Requested", "RTO Requested" |
| `action_by` | text | Who took the action (Seller, IVR, etc.) |
| `action_time` | timestamp (tz) | When the action occurred |
| `response_status` | text | Courier's response to the action |
| `response_time` | timestamp (tz) | When the courier responded |
| `remarks` | text | Any notes regarding the action |
| `message_text` | text | Text of messages sent to customer (if applicable) |
| `reattempt_date` | timestamp (tz) | Scheduled date for the next delivery attempt |
| `is_priority_escalate` | boolean | Flag if escalated |
| `is_first_response` | boolean | Flag if this was the first action taken |
| `source` | text | Source of the action |
| `createdat` | timestamp (tz) | When this log was created |
| `updatedat` | timestamp (tz) | When this log was updated |
| `ivr_count` | integer | Number of IVR calls made |
| `call_sid` | text | Twilio/Exotel call session ID |
| `ivr_call_time` | timestamp (tz) | Timestamp of the IVR call |
| `ivr_language` | text | Language used for IVR |
| `caller_id` | text | Phone number used to call the customer |
| `app_id` | text | App ID used for IVR routing |
| `call_duration` | text | Duration of the IVR call |
| `media` | text | Link to call recording or media |
