from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class SourceSystem(str, Enum):
    aaram_identity = "aaram_identity"
    shopdeck = "shopdeck"
    amazon = "amazon"
    flipkart = "flipkart"
    aaram_inventory = "aaram_inventory"
    aaram_packing = "aaram_packing"
    memory_framework = "memory_framework"
    shiprocket = "shiprocket"

class ContextSource(BaseModel):
    source_system_name: SourceSystem
    retrieval_timestamp: datetime

ContextSourceURN = str
