from typing import Optional
from fastapi import HTTPException
from ..repositories.ndr import NDRRepository
from ..schemas.ndr import NDRShipmentContext, NDRActionHistory, OrderLineItem

class NDRService:
    """
    Business logic layer for the NDR domain.
    Aggregates data from repositories and transforms it into public API schemas.
    """
    def __init__(self, repository: NDRRepository):
        self.repository = repository

    async def get_shipment_ndr_context(self, awb_no: str) -> NDRShipmentContext:
        """
        Retrieves the canonical business representation of a shipment's NDR context.
        Aggregates current state and chronological action history.
        """
        # Check if AWB even exists in order_line_items
        if not await self.repository.check_awb_exists(awb_no):
            raise HTTPException(status_code=404, detail="AWB_NOT_FOUND")

        # Fetch operational state
        report_data = await self.repository.get_shipment_ndr_report(awb_no)
        if not report_data:
            if not await self.repository.is_ndr_table_populated():
                raise HTTPException(status_code=503, detail="NDR_DATA_UNAVAILABLE")
            else:
                raise HTTPException(status_code=404, detail="NO_NDR_RECORD")

        # Fetch action timeline
        history_records = await self.repository.get_ndr_action_history(awb_no)
        
        # Transform history into business schemas
        action_history = [
            NDRActionHistory(**record) for record in history_records
        ]

        # Fetch and map order items
        item_records = await self.repository.get_order_items(awb_no)
        items = []
        cod_amount = 0.0
        
        for record in item_records:
            qty = record.get("quantity", 0)
            price = float(record.get("selling_price") or 0.0)
            items.append(
                OrderLineItem(
                    sku_id=record.get("sku_id"),
                    product_code=record.get("product_id") or record.get("customer_product_short_id"),
                    product_name=record.get("product_name"),
                    quantity=qty,
                    selling_price=price
                )
            )
            cod_amount += (qty * price)
            
        # Add delivery and COD charges from the first item (assuming same for the shipment)
        if item_records:
            cod_amount += float(item_records[0].get("cod_charge") or 0.0)
            cod_amount += float(item_records[0].get("delivery_fees") or 0.0)

        order_id = item_records[0].get("order_id") if item_records else None
        order_date = item_records[0].get("createdat") if item_records else None

        # Assemble canonical context
        return NDRShipmentContext(
            **report_data,
            order_id=order_id,
            order_date=order_date,
            cod_amount=cod_amount,
            items=items,
            action_history=action_history
        )
