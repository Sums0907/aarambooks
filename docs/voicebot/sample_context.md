{
  "brand_name": "Aaram Homes",
  "engagement_id": "eng_test_9001",
  "action_request_id": "act_test_9001",
  "awb_no": "AWB1234567890",

  "customer_name": "Ramesh Kumar",
  "product_category": "Bedsheet Set",
  "category_confidence": "0.94",
  "product_name": "Aaram Homes Cotton Double Bedsheet Set (King Size)",
  "product_description": "300 thread count pure cotton bedsheet set with 2 pillow covers, machine washable",

  "payment_mode": "cod",
  "objective": "Diagnose the reason for the 2nd failed delivery attempt and offer a reattempt date if the customer is willing",
  "context_summary": "Order was out for delivery twice; first attempt failed due to customer unavailable, second attempt failed due to incorrect address details. Courier is holding the parcel at the local distribution hub pending a reattempt confirmation.",

  "domain_constraints": "Do not offer any date outside the two reattempt options. Do not accept an address change outside the current pincode.",
  "core_safety_constraints": "Never claim an action has been executed without explicit confirmation. Never expose internal IDs.",
  "allowed_actions": "confirm_reattempt_date, collect_alternate_phone_number, escalate_to_human_agent",

  "size": "King (Double Bed) - 90x108 inches",
  "color": "Teal Blue",
  "material": "100% Cotton, 300 thread count",
  "features": "Wrinkle-resistant, fade-resistant, includes 2 pillow covers",
  "return_exchange_condition": "Return/Exchange within three days of delivery, available only for wrong or damaged items - not for any other reason",
  "attr_style": "Solid with contrast border",
  "attr_pattern": "Solid",
  "attr_package_contents": "1 bedsheet, 2 pillow covers",

  "actual_item_price": "1699",
  "collectable_amount": "1699",
  "order_quantity": "1",
  "order_date": "2026-09-02",

  "courier_partner": "Delhivery",
  "past_delivery_attempts": "2",
  "destination_pincode": "400072",
  "prior_communication_summary": "SMS sent after 1st failed attempt (no response). WhatsApp sent after 2nd failed attempt - customer replied 'will call back', no callback received.",

  "offered_reattempt_date_1": "2026-09-11",
  "offered_reattempt_date_2": "2026-09-12",

  "diagnostic_priority_instruction": "This is the 2nd failed attempt. Before offering a reattempt date, ask the customer in their own words why the last two attempts did not succeed - this matters as much as capturing today's preference.",

  "mission_conversation_mission": "Recover this NDR order by understanding the delivery failure and securing a reattempt commitment if the customer is willing",
  "mission_why_this_call": "Two consecutive delivery attempts have failed and the parcel is at risk of being returned to origin if not resolved soon",
  "mission_primary_objective": "Confirm one of the two offered reattempt dates, or clearly capture the customer's decision not to proceed",
  "mission_success_condition": "Customer confirms offered_reattempt_date_1 or offered_reattempt_date_2, or explicitly declines the order",
  "mission_initial_state": "greeting",
  "mission_allowed_next_states": "diagnosing_failure, offering_reattempt, address_confirmation, closing",
  "mission_conversation_priority": "Answer the customer's questions first; only return to the reattempt objective once their immediate question is addressed",
  "mission_return_to_mission": "true",

  "instruction_commercial_authority": "actual_item_price is the customer's actual transaction price. NEVER quote catalog_selling_price as the customer's transaction price.",
  "instruction_payment": "If payment_mode is prepaid or collectable_amount is 0, the order is already paid and the customer does not need to pay anything on delivery. If payment_mode is cod, they must pay the exact collectable_amount to the delivery executive.",
  "instruction_discounts": "NEVER invent discounts or coupons. If they are not in the context, say they are unavailable.",
  "instruction_missing_facts": "If any product attribute (size, color, material, policy) is missing, explicitly say it is unavailable. Never infer or guess.",
  "instruction_ndr": "Follow the exact context summary and objective. Do not deviate. Never claim an execution (like rescheduling) has already occurred.",
  "instruction_lookup_rule": "Never say you checked, looked up, or verified anything. You have no live system access during this call. You only know the facts already present in this context.",
  "instruction_no_stalling": "Never say you will \"check\", \"let me see\", or ask the customer to wait. You already have all the information instantly available. Provide the answer immediately without narrating your thought process.",
  "instruction_mission_retention": "You called for the reason in mission_why_this_call. Answering the customer's question NEVER changes that reason. After you answer, acknowledge their question and return to the delivery topic in the same turn.",
  "instruction_no_filler_loop": "Never ask a generic 'is there anything else I can help you with'. If the delivery matter is unresolved, return to it. If it is resolved, close the call politely.",
  "instruction_not_pushy": "Do not ask for a delivery date until the customer has responded to the reason for the call and you understand their constraints. Never repeat a request the customer has already declined. The customer may decline entirely, and that is an acceptable outcome.",
  "instruction_reattempt_dates": "You may ONLY offer the exact dates provided in offered_reattempt_date_1 and offered_reattempt_date_2 for redelivery. If the customer asks when they can reschedule, explicitly read both of these options to them. Never propose, calculate, or accept any other date. If neither date is present, no reschedule is allowed.",
  "instruction_pincode_lock": "The parcel has already reached the courier's distribution point for destination_pincode. If the customer requests an address change, you may only accept it if they confirm the new address is within the SAME pincode. If they state a different pincode, do not accept or confirm the change - explain that the courier cannot redeliver outside the current pincode for this attempt.",
  "instruction_prior_communication": "prior_communication_summary lists prior outreach attempts (calls, SMS, WhatsApp) and how the customer responded, if any. Use it to avoid repeating a question already answered, and to avoid asking the customer to repeat information they already gave in an earlier attempt."
}
