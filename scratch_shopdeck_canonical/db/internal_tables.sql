-- ShopDeck Business System: Private Internal Tables
-- ShopDeck Business System Postgres Schema
-- Generated from MCP_Server_List_Table.json

-- ==========================================
-- TABLE: order_summary
-- Stores detailed information about customer orders, including payment details, total amounts, discounts, and associated user and session tracking data.
-- ==========================================
CREATE TABLE IF NOT EXISTS order_summary (
    order_id TEXT,
    payment_mode TEXT,
    total_aggr_discount NUMERIC,
    payment_status BOOLEAN,
    return_order_item_id TEXT,
    total_amount NUMERIC,
    updatedat TIMESTAMP WITH TIME ZONE,
    createdat TIMESTAMP WITH TIME ZONE,
    user_agent TEXT,
    user_ip_address TEXT,
    fb_analytics_attributes_fbc TEXT,
    fb_analytics_attributes_fbp TEXT,
    fb_analytics_attributes_external_id TEXT,
    visitor_id TEXT,
    session_id TEXT,
    checkout_session_id TEXT
);



-- ==========================================
-- TABLE: order_line_items
-- Stores detailed information about individual customer orders, including product details, pricing, payment status, shipping logistics, and order lifecycle events such as creation, updates, delivery, cancellation, and returns.
-- ==========================================
CREATE TABLE IF NOT EXISTS order_line_items (
    order_id TEXT,
    seller_group_id TEXT,
    sku_id TEXT,
    payment_mode TEXT,
    is_deal BOOLEAN,
    platform TEXT,
    seller_payment_state TEXT,
    reseller_payment_state TEXT,
    customer_last_status TEXT,
    seller_last_status TEXT,
    total_discount NUMERIC,
    customer_id TEXT,
    quantity INTEGER,
    awb_no TEXT,
    customer_name TEXT,
    seller_price NUMERIC,
    selling_price NUMERIC,
    customer_product_short_id TEXT,
    customer_sku_short_id TEXT,
    product_id TEXT,
    seller_id TEXT,
    seller_name TEXT,
    pincode TEXT,
    updatedat TIMESTAMP WITH TIME ZONE,
    createdat TIMESTAMP WITH TIME ZONE,
    lattitude TEXT,
    longitude TEXT,
    delivery_time TIMESTAMP WITH TIME ZONE,
    rto_initiated TIMESTAMP WITH TIME ZONE,
    coupon_code TEXT,
    rto_delivered_at TIMESTAMP WITH TIME ZONE,
    seller_clubbed_id TEXT,
    pickup_time TIMESTAMP WITH TIME ZONE,
    cod_charge NUMERIC,
    delivery_fees NUMERIC,
    online_discount NUMERIC,
    coupon_id TEXT,
    coupon_type TEXT,
    coupon_discount NUMERIC,
    expected_delivery_date TIMESTAMP WITH TIME ZONE,
    prepaid_amount NUMERIC,
    logistics_reference_number TEXT,
    in_house_status TEXT,
    tpl_rates_template_id TEXT,
    latest_awb_time TIMESTAMP WITH TIME ZONE,
    product_name TEXT,
    pod_url TEXT,
    cancelled_by TEXT,
    cancellation_reason_code TEXT,
    cancel_remarks TEXT,
    cancellation_source TEXT,
    payment_status TEXT,
    cancel_time TIMESTAMP WITH TIME ZONE,
    exchange_charge INTEGER,
    is_exchange_order BOOLEAN,
    product_color TEXT,
    product_size TEXT,
    product_return_condition TEXT,
    rto_requested_time TIMESTAMP WITH TIME ZONE,
    is_return_initiated BOOLEAN,
    cod_remittance_id TEXT,
    cod_remittance_date TIMESTAMP WITH TIME ZONE,
    billing_invoice_id TEXT,
    is_return_created BOOLEAN,
    shipping_label TEXT,
    wm_invoice_shipping_label_url TEXT,
    order_last_error TEXT,
    manifest_short_id TEXT,
    refund_status TEXT,
    earlier_state_cancel TEXT,
    product_price NUMERIC,
    product_customisation TEXT,
    inhouse_courier_name TEXT,
    meta TEXT,
    call_status TEXT,
    duplicate_flag BOOLEAN,
    order_acceptance_type TEXT,
    order_accepted_at TIMESTAMP WITH TIME ZONE,
    shopdeck_warehouse_address_id TEXT,
    pickup_pincode TEXT,
    courier_allocation_type TEXT
);



-- ==========================================
-- TABLE: customer_info
-- One row per customer shipment: the customer and their contact number, the seller's pickup address, and the delivery destination, keyed by AWB number. Use it to look up who an order went to and where it was shipped from and to. Note that customer_number is stored encrypted and is decrypted only on the way out, in the rows returned to you — so filtering, joining or grouping on it matches ciphertext and will not work, and selecting it under a different name (SELECT customer_number AS phone) returns it still encrypted. Select it as customer_number and do any matching on customer_id or awb_no instead.
-- ==========================================
CREATE TABLE IF NOT EXISTS customer_info (
    seller_group_id TEXT,
    awb_no TEXT,
    seller_id TEXT,
    customer_id TEXT,
    customer_number TEXT,
    pickup_address_id TEXT,
    pickup_city TEXT,
    pickup_state TEXT,
    pickup_pincode TEXT,
    pickup_phone TEXT,
    drop_pincode TEXT,
    drop_city TEXT,
    drop_state TEXT,
    createdat TIMESTAMP WITH TIME ZONE,
    updatedat TIMESTAMP WITH TIME ZONE
);



-- ==========================================
-- TABLE: cancel_reason_events
-- Records the cancellation reason a customer submits after choosing to cancel an order, along with the order, session and device context.
-- ==========================================
CREATE TABLE IF NOT EXISTS cancel_reason_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    cancellation_reason TEXT,
    remarks TEXT,
    order_id TEXT
);



-- ==========================================
-- TABLE: checkout_external_events
-- Records checkout events raised by external or third-party checkout integrations, along with the session, device and marketing context of the checkout.
-- ==========================================
CREATE TABLE IF NOT EXISTS checkout_external_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    user_id TEXT,
    flow_id TEXT,
    checkout_session_id TEXT,
    event_name TEXT
);



-- ==========================================
-- TABLE: checkout_input_error_events
-- This event gets triggered when any error occurs while filling number , address in checkout journey
-- ==========================================
CREATE TABLE IF NOT EXISTS checkout_input_error_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    user_id TEXT,
    flow_id TEXT,
    checkout_session_id TEXT,
    page_id TEXT,
    error_field TEXT,
    error_message TEXT,
    error_type TEXT
);



-- ==========================================
-- TABLE: order_cancellation_events
-- Records each time an order is cancelled, capturing the order and the session, device and marketing context in which the cancellation happened.
-- ==========================================
CREATE TABLE IF NOT EXISTS order_cancellation_events (
    order_id TEXT,
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    user_id TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT
);



-- ==========================================
-- TABLE: payment_gateway_events
-- Records events reported by the payment gateway during an order's payment attempt, along with the order, session and device context.
-- ==========================================
CREATE TABLE IF NOT EXISTS payment_gateway_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    user_id TEXT,
    payment_gateway TEXT,
    event_name TEXT,
    order_id TEXT,
    checkout_session_id TEXT,
    response JSONB
);



-- ==========================================
-- TABLE: rating_review_feedback_submit_events
-- Records each time a customer submits their rating and review feedback, capturing the rating given along with the order, session and device context.
-- ==========================================
CREATE TABLE IF NOT EXISTS rating_review_feedback_submit_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    user_id TEXT,
    stars NUMERIC,
    review TEXT,
    image TEXT,
    video TEXT,
    stars_edit BOOLEAN,
    review_edit BOOLEAN,
    image_edit BOOLEAN,
    video_edit BOOLEAN,
    cta TEXT,
    feedback_status TEXT,
    seller_group_id TEXT,
    feedback_id TEXT
);



-- ==========================================
-- TABLE: return_exchange_events
-- This event get triggered when return exchange button is clicked from order detail page
-- ==========================================
CREATE TABLE IF NOT EXISTS return_exchange_events (
    connectionRtt INTEGER,
    connectionDownlink INTEGER,
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    user_id TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    event_datum JSONB,
    event_label TEXT,
    connectionSaveData BOOLEAN,
    browserName TEXT,
    utm_campaign TEXT
);



-- ==========================================
-- TABLE: post_order_survey_submit_events
-- Records each time a customer submits the post-order survey form, capturing the submitted responses along with the order and session context.
-- ==========================================
CREATE TABLE IF NOT EXISTS post_order_survey_submit_events (
    platform TEXT,
    language TEXT,
    browserVer TEXT,
    useragent TEXT,
    connectionEffectiveType TEXT,
    connectionSaveData BOOLEAN,
    connectionRtt NUMERIC,
    connectionDownlink NUMERIC,
    visitor_id TEXT,
    device TEXT,
    previous_screen_source TEXT,
    browserName TEXT,
    seller_id TEXT,
    seller_name TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    website_name TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    screen_source TEXT,
    user_id TEXT,
    delivery_reason TEXT,
    product_confidence TEXT,
    website_issue TEXT,
    availability TEXT
);



-- ==========================================
-- TABLE: shipment_ndr_reports
-- One row per shipment that has failed delivery at least once. Current-state summary.
-- ==========================================
CREATE TABLE IF NOT EXISTS shipment_ndr_reports (
    _id TEXT,
    seller_group_id TEXT,
    seller_clubbed_id TEXT,
    awb_no TEXT,
    order_status TEXT,
    courier_partner TEXT,
    courier_company_id TEXT,
    payment_mode TEXT,
    customer_id TEXT,
    customer_name TEXT,
    seller_id TEXT,
    pickup_time TIMESTAMP WITH TIME ZONE,
    latest_ndr_time TIMESTAMP WITH TIME ZONE,
    latest_ndr_reason TEXT,
    latest_ofd_time TIMESTAMP WITH TIME ZONE,
    delivery_time TIMESTAMP WITH TIME ZONE,
    ndr_count INTEGER,
    ofd_count INTEGER,
    seller_actions TEXT,
    ndr_status TEXT
);



-- ==========================================
-- TABLE: ndr_action_log
-- One row per action taken on a failed delivery. Outreach history, responses, seller actions.
-- ==========================================
CREATE TABLE IF NOT EXISTS ndr_action_log (
    _id TEXT,
    awb_no TEXT,
    ndr_count INTEGER,
    action_type TEXT,
    action_by TEXT,
    action_time TIMESTAMP WITH TIME ZONE,
    response_status TEXT,
    response_time TIMESTAMP WITH TIME ZONE,
    remarks TEXT,
    message_text TEXT,
    reattempt_date TIMESTAMP WITH TIME ZONE,
    is_priority_escalate BOOLEAN,
    is_first_response BOOLEAN,
    source TEXT,
    createdat TIMESTAMP WITH TIME ZONE,
    updatedat TIMESTAMP WITH TIME ZONE,
    ivr_count INTEGER,
    call_sid TEXT,
    ivr_call_time TIMESTAMP WITH TIME ZONE,
    ivr_language TEXT,
    caller_id TEXT,
    app_id TEXT,
    call_duration TEXT,
    media TEXT
);

-- ==========================================
-- TABLE: sync_checkpoints
-- Internal tracking for synchronization engine.
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    table_name TEXT PRIMARY KEY,
    last_watermark TIMESTAMP WITH TIME ZONE
);

-- ==========================================
-- TABLE: shopdeck_ndr_intelligence_log
-- Stores canonical NDR intelligence results pushed from the Brain. 
-- MOCK SHOPDECK BS PERSISTENCE
-- ==========================================
CREATE TABLE IF NOT EXISTS shopdeck_ndr_intelligence_log (
    normalization_id TEXT PRIMARY KEY,
    brain_decision_id TEXT,
    target_identity TEXT,
    recommendation TEXT,
    authorized_action TEXT,
    action_parameters JSONB,
    reasoning TEXT,
    diagnosis TEXT,
    risk_score TEXT,
    source_event_ids JSONB,
    provenance TEXT,
    normalization_status TEXT,
    created_at TIMESTAMP WITH TIME ZONE
);
