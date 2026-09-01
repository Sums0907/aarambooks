from src.shared.semantic_resolution_contracts import SemanticConcept

NDR_CONCEPTS = [
    # Entities
    SemanticConcept(
        concept_id="ndr.entity.awb",
        concept_name="AWB",
        concept_type="ENTITY",
        aliases=["awb", "awb_no", "tracking number", "tracking id", "waybill", "shipment"],
        description="Air Waybill number for tracking a shipment."
    ),
    SemanticConcept(
        concept_id="ndr.entity.order_id",
        concept_name="Order ID",
        concept_type="ENTITY",
        aliases=["order id", "order", "order number"],
        description="Unique identifier for a customer order."
    ),
    SemanticConcept(
        concept_id="ndr.entity.customer",
        concept_name="Customer",
        concept_type="ENTITY",
        aliases=["customer", "buyer", "recipient", "consignee"],
        description="Customer or recipient associated with the delivery."
    ),
    SemanticConcept(
        concept_id="ndr.entity.courier_partner",
        concept_name="Courier Partner",
        concept_type="ENTITY",
        aliases=["courier", "carrier", "delivery partner", "3pl", "delivery agent"],
        description="Third-party logistics carrier assigned to transport the shipment."
    ),

    # Vocabularies / States
    SemanticConcept(
        concept_id="ndr.vocabulary.rto",
        concept_name="RTO",
        concept_type="VOCABULARY",
        aliases=["rto", "return to origin", "failed delivery", "undelivered"],
        description="Return to Origin when delivery fails and parcel returns to warehouse."
    ),
    SemanticConcept(
        concept_id="ndr.vocabulary.ndr_status",
        concept_name="NDR Status",
        concept_type="VOCABULARY",
        aliases=["ndr status", "delivery status", "delivery state", "attempt status"],
        description="Current operational status of an NDR exception."
    ),
    SemanticConcept(
        concept_id="ndr.vocabulary.fake_attempt",
        concept_name="Fake Attempt",
        concept_type="VOCABULARY",
        aliases=["fake attempt", "doorstep skip", "no visit", "false scan", "driver skip"],
        description="A suspected delivery exception where the courier skipped visiting the customer."
    ),

    # Capabilities / Actions
    SemanticConcept(
        concept_id="ndr.capability.reschedule_delivery",
        concept_name="Reschedule Delivery",
        concept_type="CAPABILITY",
        aliases=["reschedule", "reattempt", "retry delivery", "change delivery date"],
        description="Request the carrier to reattempt delivery on a committed date.",
        metadata={
            "urn": "urn:aarambooks:ndr:capability:reschedule_delivery",
            "required_constraints": ["ndr.entity.awb"]
        }
    ),
    SemanticConcept(
        concept_id="ndr.capability.dispute_courier",
        concept_name="Dispute Courier Attempt",
        concept_type="CAPABILITY",
        aliases=["dispute", "escalate courier", "report fake attempt", "carrier dispute"],
        description="Raise a formal carrier dispute for unattempted or false exception scans.",
        metadata={
            "urn": "urn:aarambooks:ndr:capability:dispute_courier",
            "required_constraints": ["ndr.entity.awb"]
        }
    ),
    SemanticConcept(
        concept_id="ndr.capability.update_address",
        concept_name="Update Delivery Address",
        concept_type="CAPABILITY",
        aliases=["update address", "add landmark", "fix address", "enrich location"],
        description="Enrich or correct delivery address with landmarks or alternate contacts.",
        metadata={
            "urn": "urn:aarambooks:ndr:capability:update_address",
            "required_constraints": ["ndr.entity.awb"]
        }
    )
]

NDR_PUBLIC_VIEWS = {
    "vw_shopdeck_shipment_ndr_reports": {
        "description": "Summary view of all shipments that have encountered a delivery exception (NDR).",
        "columns": {
            "awb_no": "STRING - Air Waybill tracking number (Primary key for shipment)",
            "order_status": "STRING - Current status of the shipment (e.g. dispatched, rto_initiated, delivered)",
            "courier_partner": "STRING - Name of the 3PL courier partner (e.g. Delhivery, Amazon Shipping, Bluedart)",
            "payment_mode": "STRING - Payment mode (cod, prepaid, partial-cod)",
            "customer_id": "STRING - Customer unique identifier",
            "customer_name": "STRING - Recipient customer name",
            "pickup_time": "TIMESTAMP - Time the parcel was picked up from warehouse",
            "latest_ndr_time": "TIMESTAMP - Timestamp of the most recent delivery failure scan",
            "latest_ndr_reason": "STRING - Reason text recorded for the latest NDR (e.g. customer unavailable, exception, otp-based cancellation)",
            "latest_ofd_time": "TIMESTAMP - Timestamp when the parcel was last marked Out For Delivery",
            "delivery_time": "TIMESTAMP - Timestamp of successful delivery if recovered",
            "ndr_count": "INTEGER - Total number of failed delivery attempts so far (1, 2, 3)",
            "ofd_count": "INTEGER - Total number of times marked Out For Delivery",
            "seller_actions": "STRING - Actions recorded by the seller or system",
            "ndr_status": "STRING - High-level NDR state"
        }
    },
    "vw_shopdeck_ndr_action_log": {
        "description": "Historical log of all resolution actions, customer outreach, IVR calls, and carrier instructions taken on an NDR case.",
        "columns": {
            "_id": "STRING - Unique action log record ID",
            "awb_no": "STRING - AWB number linking to the shipment",
            "ndr_count": "INTEGER - The attempt count when this action was performed",
            "action_type": "STRING - Type of action taken (e.g. ivr_call, whatsapp_hsm, seller_reattempt, dispute)",
            "action_by": "STRING - Initiator of the action (e.g. AI_AGENT, SYSTEM, SUPPORT_AGENT)",
            "action_time": "TIMESTAMP - When the action was performed",
            "response_status": "STRING - Customer or carrier response status (e.g. completed, no-answer, positive, negative)",
            "response_time": "TIMESTAMP - When the response was received",
            "remarks": "STRING - Notes or customer feedback details",
            "message_text": "STRING - Content of the message sent",
            "reattempt_date": "TIMESTAMP - Reattempt date committed by customer/seller",
            "is_priority_escalate": "BOOLEAN - Whether this case was escalated to human support",
            "call_duration": "STRING - Duration of voice call if applicable"
        }
    },
    "vw_shopdeck_customer_info": {
        "description": "Customer contact and delivery address context.",
        "columns": {
            "customer_id": "STRING - Customer ID",
            "customer_number": "STRING - Customer telephone/WhatsApp number",
            "drop_city": "STRING - Destination delivery city",
            "drop_pincode": "STRING - Destination 6-digit postal pincode",
            "drop_state": "STRING - Destination state"
        }
    },
    "vw_shopdeck_order_line_items": {
        "description": "Order items and financial totals associated with shipments.",
        "columns": {
            "order_id": "STRING - Order identifier",
            "product_name": "STRING - Name of the product item in the package",
            "selling_price": "NUMERIC - Sale price of the line item",
            "quantity": "INTEGER - Quantity ordered",
            "payment_mode": "STRING - Payment method (cod, prepaid)"
        }
    }
}
