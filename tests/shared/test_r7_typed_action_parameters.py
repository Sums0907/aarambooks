import pytest
from decimal import Decimal
import datetime

from src.shared.conversational_contracts import (
    NormalizedParameter, 
    ParameterDataType,
    ConversationalUnderstanding,
    ConversationalIntent
)

def test_normalized_parameter_integer():
    param = NormalizedParameter(
        parameter_name="test.int",
        data_type=ParameterDataType.INTEGER,
        value="42",
        original_expression="forty two"
    )
    assert param.value == 42
    assert isinstance(param.value, int)

def test_normalized_parameter_decimal():
    param = NormalizedParameter(
        parameter_name="test.decimal",
        data_type=ParameterDataType.DECIMAL,
        value="42.5",
        original_expression="42.5"
    )
    assert param.value == Decimal("42.5")
    assert isinstance(param.value, Decimal)

def test_normalized_parameter_boolean():
    param = NormalizedParameter(
        parameter_name="test.bool",
        data_type=ParameterDataType.BOOLEAN,
        value="yes",
        original_expression="yes"
    )
    assert param.value is True

    param2 = NormalizedParameter(
        parameter_name="test.bool2",
        data_type=ParameterDataType.BOOLEAN,
        value="False",
        original_expression="no"
    )
    assert param2.value is False

def test_normalized_parameter_date():
    param = NormalizedParameter(
        parameter_name="test.date",
        data_type=ParameterDataType.DATE,
        value="2026-08-29",
        original_expression="today"
    )
    assert param.value == datetime.date(2026, 8, 29)
    assert isinstance(param.value, datetime.date)

def test_normalized_parameter_datetime():
    param = NormalizedParameter(
        parameter_name="test.datetime",
        data_type=ParameterDataType.DATETIME,
        value="2026-08-29T10:00:00",
        original_expression="today at 10"
    )
    assert param.value == datetime.datetime(2026, 8, 29, 10, 0, 0)
    assert isinstance(param.value, datetime.datetime)

def test_normalized_parameter_string():
    param = NormalizedParameter(
        parameter_name="test.string",
        data_type=ParameterDataType.STRING,
        value=123,
        original_expression="123"
    )
    assert param.value == "123"
    assert isinstance(param.value, str)

def test_invalid_type_combinations():
    with pytest.raises(ValueError):
        NormalizedParameter(
            parameter_name="test.invalid",
            data_type=ParameterDataType.INTEGER,
            value="not_an_int",
            original_expression="something"
        )
        
    with pytest.raises(ValueError):
        NormalizedParameter(
            parameter_name="test.invalid",
            data_type=ParameterDataType.DECIMAL,
            value="not_a_decimal",
            original_expression="something"
        )
        
    with pytest.raises(ValueError):
        NormalizedParameter(
            parameter_name="test.invalid",
            data_type=ParameterDataType.DATE,
            value="not_a_date",
            original_expression="something"
        )

def test_conversational_understanding_with_parameters():
    param = NormalizedParameter(
        parameter_name="inventory.numeric.quantity",
        data_type=ParameterDataType.DECIMAL,
        value="50",
        original_expression="50 units"
    )
    
    understanding = ConversationalUnderstanding(
        original_query="Receive 50 units",
        intent=ConversationalIntent.ACTION,
        parameters=[param]
    )
    
    assert len(understanding.parameters) == 1
    assert understanding.parameters[0].parameter_name == "inventory.numeric.quantity"
    assert understanding.parameters[0].value == Decimal("50")

    # Test serialization / deserialization
    dumped = understanding.model_dump()
    assert "parameters" in dumped
    
    reloaded = ConversationalUnderstanding(**dumped)
    assert len(reloaded.parameters) == 1
    assert reloaded.parameters[0].value == Decimal("50")
