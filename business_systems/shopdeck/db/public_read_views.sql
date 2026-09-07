-- ShopDeck Business System: Public Read Contracts
-- The Aaram Brain is ONLY allowed to query these views.

CREATE OR REPLACE VIEW vw_shopdeck_order_summary AS
SELECT * FROM order_summary;
CREATE OR REPLACE VIEW vw_shopdeck_order_line_items AS
SELECT * FROM order_line_items;
CREATE OR REPLACE VIEW vw_shopdeck_customer_info AS
SELECT * FROM customer_info;
CREATE OR REPLACE VIEW vw_shopdeck_cancel_reason_events AS
SELECT * FROM cancel_reason_events;
CREATE OR REPLACE VIEW vw_shopdeck_checkout_external_events AS
SELECT * FROM checkout_external_events;
CREATE OR REPLACE VIEW vw_shopdeck_checkout_input_error_events AS
SELECT * FROM checkout_input_error_events;
CREATE OR REPLACE VIEW vw_shopdeck_order_cancellation_events AS
SELECT * FROM order_cancellation_events;
CREATE OR REPLACE VIEW vw_shopdeck_payment_gateway_events AS
SELECT * FROM payment_gateway_events;
CREATE OR REPLACE VIEW vw_shopdeck_rating_review_feedback_submit_events AS
SELECT * FROM rating_review_feedback_submit_events;
CREATE OR REPLACE VIEW vw_shopdeck_return_exchange_events AS
SELECT * FROM return_exchange_events;
CREATE OR REPLACE VIEW vw_shopdeck_post_order_survey_submit_events AS
SELECT * FROM post_order_survey_submit_events;
CREATE OR REPLACE VIEW vw_shopdeck_shipment_ndr_reports AS
SELECT * FROM shipment_ndr_reports;
CREATE OR REPLACE VIEW vw_shopdeck_ndr_action_log AS
SELECT * FROM ndr_action_log;
