from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator
import uuid
import datetime
import decimal
from decimal import Decimal

class ConversationalIntent(str, Enum):
    RETRIEVE = "RETRIEVE"
    SEARCH = "SEARCH"
    COMPARE = "COMPARE"
    IDENTIFY = "IDENTIFY"
    DECIDE = "DECIDE"
    ACTION = "ACTION"
    EXPLAIN = "EXPLAIN"
    SUMMARIZE = "SUMMARIZE"
    CALCULATE = "CALCULATE"
    RECOMMEND = "RECOMMEND"
    CONFIRMATION = "CONFIRMATION"
    REJECTION = "REJECTION"
    UNKNOWN = "UNKNOWN"

class InformationSource(str, Enum):
    EXPLICIT = "EXPLICIT"
    CONTEXTUAL = "CONTEXTUAL"
    INFERRED = "INFERRED"

class SemanticEntityReference(BaseModel):
    reference_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_expression: str
    source: InformationSource = InformationSource.EXPLICIT
    inferred_type: Optional[str] = None # e.g. "product", "warehouse", "customer"

class SemanticAttribute(BaseModel):
    attribute_name: str
    original_expression: str
    source: InformationSource = InformationSource.EXPLICIT

class SemanticOperator(str, Enum):
    EQUALS = "EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT_IN"
    NOT_EQUALS = "NOT_EQUALS"
    SIMILAR_TO = "SIMILAR_TO"
    AROUND = "AROUND"

class SemanticCondition(BaseModel):
    attribute_or_entity: str
    operator: SemanticOperator
    value: Any
    source: InformationSource = InformationSource.EXPLICIT

class SemanticScope(BaseModel):
    scope_expression: str
    source: InformationSource = InformationSource.EXPLICIT

class SemanticRelationship(BaseModel):
    source_reference_id: str
    target_reference_id: str
    relationship_type: str

class ParameterDataType(str, Enum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    STRING = "STRING"

class NormalizedParameter(BaseModel):
    parameter_name: str
    data_type: ParameterDataType
    value: Any
    original_expression: str

    @model_validator(mode='after')
    def validate_and_coerce_value(self):
        dt = self.data_type
        v = self.value
        
        try:
            if dt == ParameterDataType.INTEGER:
                if not isinstance(v, int):
                    self.value = int(v)
            elif dt == ParameterDataType.DECIMAL:
                if not isinstance(v, Decimal):
                    self.value = Decimal(str(v))
            elif dt == ParameterDataType.BOOLEAN:
                if not isinstance(v, bool):
                    if isinstance(v, str):
                        if v.lower() in ('true', '1', 't', 'yes', 'y'):
                            self.value = True
                        elif v.lower() in ('false', '0', 'f', 'no', 'n'):
                            self.value = False
                        else:
                            raise ValueError(f"Cannot coerce {v} to boolean")
                    else:
                        self.value = bool(v)
            elif dt == ParameterDataType.DATE:
                if not isinstance(v, datetime.date):
                    if isinstance(v, str):
                        self.value = datetime.date.fromisoformat(v)
                    elif isinstance(v, datetime.datetime):
                        self.value = v.date()
                    else:
                        raise ValueError(f"Cannot coerce {v} to date")
            elif dt == ParameterDataType.DATETIME:
                if not isinstance(v, datetime.datetime):
                    if isinstance(v, str):
                        self.value = datetime.datetime.fromisoformat(v)
                    elif isinstance(v, datetime.date):
                        self.value = datetime.datetime.combine(v, datetime.time.min)
                    else:
                        raise ValueError(f"Cannot coerce {v} to datetime")
            elif dt == ParameterDataType.STRING:
                if not isinstance(v, str):
                    self.value = str(v)
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            raise ValueError(f"Value '{v}' is invalid for data_type {dt}: {e}")
            
        return self

class ConversationalUnderstanding(BaseModel):
    understanding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str
    intent: ConversationalIntent = ConversationalIntent.UNKNOWN
    domain: Optional[str] = None
    
    entities: List[SemanticEntityReference] = Field(default_factory=list)
    attributes: List[SemanticAttribute] = Field(default_factory=list)
    conditions: List[SemanticCondition] = Field(default_factory=list)
    parameters: List[NormalizedParameter] = Field(default_factory=list)
    scope: Optional[SemanticScope] = None
    relationships: List[SemanticRelationship] = Field(default_factory=list)
    
    user_supplied_criteria: List[str] = Field(default_factory=list)
    desired_outcome: Optional[str] = None

class ConversationalResponseType(str, Enum):
    SUCCESS = "SUCCESS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    EXECUTION_LIMITATION = "EXECUTION_LIMITATION"
    SYSTEM_FAILURE = "SYSTEM_FAILURE"

class ConversationalResponse(BaseModel):
    response_type: ConversationalResponseType
    message: str
    clarification_options: Optional[List[Dict[str, Any]]] = None
    missing_parameters: Optional[List[str]] = None
    render_directives: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
