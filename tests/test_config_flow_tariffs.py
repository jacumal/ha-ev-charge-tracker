import asyncio\n

def test_sensor_edit_preserves_profile_identity_tariffs_and_visual_options():
    from types import SimpleNamespace

    flow = object.__new__(EVChargeTrackerOptionsFlow)
    flow.config_entry = SimpleNamespace(
        data={
            "vehicle_id": "leapmotor_c10",
            "charger_id": "garage",
            "vehicle_name": "Leapmotor C10",
            "charger_name": "Garaje",
        },
        options={
            "tariff_periods": [{"name": "Valle", "start": "00:00", "end": "24:00",
                                "days": list(range(7)), "price": 0.11}],
            "visual_model": "C10",
            "visual_port_x": 58,
        },
    )
    flow.async_create_entry = lambda **kwargs: kwargs
    result = asyncio.run(flow.async_step_profile({
        "charging_entity": "binary_sensor.new_charging",
        "energy_entity": "sensor.new_energy",
        "energy_mode": "session",
        "odometer_unit": "km",
        "finalization": "immediate",
    }))

    assert result["data"]["charging_entity"] == "binary_sensor.new_charging"
    assert result["data"]["energy_entity"] == "sensor.new_energy"
    assert result["data"]["tariff_periods"] == flow.config_entry.options["tariff_periods"]
    assert result["data"]["visual_model"] == "C10"
    assert result["data"]["visual_port_x"] == 58
    assert result["data"]["vehicle_id"] == "leapmotor_c10"
    assert result["data"]["charger_id"] == "garage"
\n"""Tests for conditional tariff price forms in the options flow."""

from custom_components.ev_charge_tracker.config_flow import EVChargeTrackerOptionsFlow
from custom_components.ev_charge_tracker.tariff import default_periods


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


def test_profile_form_does_not_duplicate_tariff_price_settings():
    schema = EVChargeTrackerOptionsFlow._profile_schema({
        "charging_entity": "binary_sensor.charging",
        "energy_entity": "sensor.energy",
    })

    fields = _field_names(schema)
    assert "price_mode" not in fields
    assert "price_per_kwh" not in fields
    assert "price_entity" not in fields
    assert "charging_entity" in fields
    assert "energy_entity" in fields


def test_changing_from_single_to_two_periods_refreshes_default_names():
    drafts = EVChargeTrackerOptionsFlow._build_period_drafts(
        [{"name": "Único", "start": "00:00", "end": "00:00",
          "price": 0.2, "days": list(range(7))}],
        2,
    )

    assert [period["name"] for period in drafts] == ["Valle", "Punta"]
    assert drafts[0]["price"] == 0.2


def test_changing_to_three_periods_uses_three_period_default_names():
    saved = [
        {"name": "Único", "start": "00:00", "end": "00:00",
         "price": 0.2, "days": list(range(7))}
    ]
    drafts = EVChargeTrackerOptionsFlow._build_period_drafts(saved, 3)

    assert [period["name"] for period in drafts] == ["Valle", "Llano", "Punta"]


def test_same_period_count_preserves_custom_period_names():
    saved = [
        {"name": "Supervalle", "start": "00:00", "end": "08:00",
         "price": 0.1, "days": list(range(7))},
        {"name": "Punta personalizada", "start": "08:00", "end": "00:00",
         "price": 0.3, "days": list(range(7))},
    ]
    drafts = EVChargeTrackerOptionsFlow._build_period_drafts(saved, 2)

    assert [period["name"] for period in drafts] == [
        "Supervalle", "Punta personalizada"
    ]
