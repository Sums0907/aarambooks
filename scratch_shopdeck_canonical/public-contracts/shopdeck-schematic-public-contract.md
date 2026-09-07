---
source_bs: "shopdeck"
namespace_name: "shopdeck"
namespace_classification: "EXTERNAL_CHANNEL"
namespace_description: "ShopDeck Business System"
contract_version: "1.0"
---

# ShopDeck Schematic Public Contract

### View: vw_shopdeck_order_summary
- **Description:** Exposes aggregate order financial totals and checkout session contexts.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| order_id | TEXT | false | false | shopdeck.entity.order | Order ID |
| payment_mode | TEXT | false | false | shopdeck.entity.payment | Payment Mode |
| payment_status | BOOLEAN | false | false | shopdeck.entity.payment.status | Payment Status |
| total_amount | NUMERIC | false | false | shopdeck.entity.order.gross_value | Total amount |
| visitor_id | TEXT | false | false | shopdeck.event.checkout_session | Visitor ID |
| session_id | TEXT | false | false | shopdeck.event.checkout_session | Session ID |

### View: vw_shopdeck_order_line_items
- **Description:** Exposes distinct line items representing purchased units, pricing, and external SKU references.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| order_id | TEXT | false | false | shopdeck.entity.order | Order ID |
| sku_id | TEXT | false | false | shopdeck.entity.order_item | SKU ID |
| customer_id | TEXT | false | false | shopdeck.entity.customer | Customer ID |
| awb_no | TEXT | false | false | shopdeck.entity.shipment | AWB No |
| quantity | INTEGER | false | false | shopdeck.entity.order_quantity | Quantity |
| customer_sku_short_id | TEXT | false | true | None | ShopDeck customer_sku_short_id |
| payment_status | TEXT | false | false | shopdeck.entity.payment.status | Payment Status |

### View: vw_shopdeck_customer_info
- **Description:** Provides buyer identity, encrypted contact information, and geographic destination data.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| customer_id | TEXT | false | false | shopdeck.entity.customer | Customer ID |
| customer_number | TEXT | false | false | shopdeck.entity.customer_contact | Encrypted customer number |
| awb_no | TEXT | false | false | shopdeck.entity.shipment | AWB No |
| drop_city | TEXT | false | false | shopdeck.entity.delivery_destination | Drop City |
| drop_state | TEXT | false | false | shopdeck.entity.delivery_destination | Drop State |
| drop_pincode | TEXT | false | false | shopdeck.entity.delivery_destination | Drop Pincode |

### View: vw_shopdeck_shipment_ndr_reports
- **Description:** The authoritative source for aggregate shipment states and external courier failure logs.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| awb_no | TEXT | false | false | shopdeck.entity.shipment | AWB No |
| courier_partner | TEXT | false | false | shopdeck.entity.shipment.carrier | Courier Partner |
| order_status | TEXT | false | false | shopdeck.entity.shipment.state | Order Status |
| latest_ndr_reason | TEXT | false | false | shopdeck.event.delivery_exception.reason | Latest NDR Reason |
| ndr_count | INTEGER | false | false | shopdeck.metric.ndr_count | NDR Count |

### View: vw_shopdeck_ndr_action_log
- **Description:** A chronological log of ShopDeck automated or manual outreach actions per AWB.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| awb_no | TEXT | false | false | shopdeck.entity.shipment | AWB No |
| action_type | TEXT | false | false | shopdeck.action.outreach | Action Type |
| ndr_count | INTEGER | false | false | shopdeck.metric.ndr_count | NDR Count |
### View: vw_shopdeck_cancel_reason_events
- **Description:** Records the cancellation reason a customer submits after choosing to cancel an order, along with the order, session and device context.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| cancellation_reason | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| remarks | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| order_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_checkout_external_events
- **Description:** Records checkout events raised by external or third-party checkout integrations, along with the session, device and marketing context of the checkout.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| flow_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| checkout_session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| event_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_checkout_input_error_events
- **Description:** This event gets triggered when any error occurs while filling number , address in checkout journey

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| flow_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| checkout_session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| page_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| error_field | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| error_message | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| error_type | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_order_cancellation_events
- **Description:** Records each time an order is cancelled, capturing the order and the session, device and marketing context in which the cancellation happened.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| order_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_payment_gateway_events
- **Description:** Records events reported by the payment gateway during an order's payment attempt, along with the order, session and device context.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| payment_gateway | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| event_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| order_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| checkout_session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| response | JSONB | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_rating_review_feedback_submit_events
- **Description:** Records each time a customer submits their rating and review feedback, capturing the rating given along with the order, session and device context.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| stars | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| review | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| image | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| video | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| stars_edit | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| review_edit | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| image_edit | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| video_edit | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| cta | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| feedback_status | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_group_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| feedback_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_return_exchange_events
- **Description:** This event get triggered when return exchange button is clicked from order detail page

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| connectionRtt | INTEGER | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | INTEGER | false | false | None | PROVISIONAL / UNRESOLVED |
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| event_datum | JSONB | false | false | None | PROVISIONAL / UNRESOLVED |
| event_label | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |

### View: vw_shopdeck_post_order_survey_submit_events
- **Description:** Records each time a customer submits the post-order survey form, capturing the submitted responses along with the order and session context.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| platform | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| language | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserVer | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| useragent | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionEffectiveType | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionSaveData | BOOLEAN | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionRtt | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| connectionDownlink | NUMERIC | false | false | None | PROVISIONAL / UNRESOLVED |
| visitor_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| device | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| previous_screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| browserName | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| seller_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| session_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| created_at | TIMESTAMP | false | false | None | PROVISIONAL / UNRESOLVED |
| website_name | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_medium | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_campaign | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_content | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| utm_term | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| screen_source | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| user_id | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| delivery_reason | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| product_confidence | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| website_issue | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |
| availability | TEXT | false | false | None | PROVISIONAL / UNRESOLVED |


