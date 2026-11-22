"""Tests for conditional tariff price forms in the options flow."""

from custom_components.ev_charge_tracker.config_flow import EVChargeTrackerOptionsFlow


def _field_names(schema):
    return {key.schema for key in schema.schema}


def test_tariff_details_form_selects_a_single_price_source():
    flow = object.__new__(EVChargeTrackerOptionsFlow)
    flow._period_count = 1
    schema = flow._period_details_schema([
        {
            "name": "Valle",
            "start": "00:00",
            "end": "24:00",
            "days": list(range(7)),
            "price": 0.11,
            "price_entity": "sensor.price",
            "_price_source": "sensor",
        }
    ])

    fields = _field_names(schema)
    assert "period_1_price_source" in fields
    assert "period_1_price" not in fields
    assert "period_1_price_entity" not in fields


def test_manual_price_step_shows_only_manual_price_and_keeps_default():
    schema = EVChargeTrackerOptionsFlow._period_price_schema(
        {"price": 0.17, "price_entity": "sensor.old_price"}, "manual"
    )

    assert _field_names(schema) == {"price"}
    key = next(iter(schema.schema))
    assert key.default() == 0.17


def test_sensor_price_step_shows_only_entity_selector_and_keeps_selection():
    schema = EVChargeTrackerOptionsFlow._period_price_schema(
        {"price": 0.17, "price_entity": "sensor.old_price"}, "sensor"
    )

    assert _field_names(schema) == {"price_entity"}
    key = next(iter(schema.schema))
    assert key.default() == "sensor.old_price"


def test_sensor_price_step_requires_entity_when_none_was_saved():
    schema = EVChargeTrackerOptionsFlow._period_price_schema(
        {"price": 0.17}, "sensor"
    )

    assert _field_names(schema) == {"price_entity"}

def test_sensor_price_step_restores_previously_selected_sensor_after_switching():
    schema = EVChargeTrackerOptionsFlow._period_price_schema(
        {"price": 0.17, "price_entity_backup": "sensor.previously_selected"}, "sensor"
    )

    assert _field_names(schema) == {"price_entity"}
    key = next(iter(schema.schema))
    assert key.default() == "sensor.previously_selected"
