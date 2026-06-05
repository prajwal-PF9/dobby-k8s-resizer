import pytest
from controller.cost_calculator import (
    parse_cpu_to_millicores,
    parse_memory_to_bytes,
    calculate_monthly_saving,
    cpu_delta_percent,
    mem_delta_percent,
)


def test_parse_cpu_millicores():
    assert parse_cpu_to_millicores("500m") == 500.0


def test_parse_cpu_cores():
    assert parse_cpu_to_millicores("2") == 2000.0


def test_parse_cpu_decimal():
    assert parse_cpu_to_millicores("0.5") == 500.0


def test_parse_memory_mebibytes():
    assert parse_memory_to_bytes("256Mi") == 256 * 1024 * 1024


def test_parse_memory_gibibytes():
    assert parse_memory_to_bytes("1Gi") == 1024 * 1024 * 1024


def test_parse_memory_kilobytes():
    assert parse_memory_to_bytes("100Ki") == 100 * 1024


def test_calculate_monthly_saving_cpu_only():
    # 400m CPU saving on m5.xlarge: (400/1000) * 0.048 * 730 = 14.02
    saving = calculate_monthly_saving(
        current_cpu_m=500.0, rec_cpu_m=100.0,
        current_mem_bytes=0, rec_mem_bytes=0,
        instance_type="m5.xlarge",
    )
    assert abs(saving - 14.02) < 0.01


def test_calculate_monthly_saving_no_saving_when_rec_higher():
    saving = calculate_monthly_saving(
        current_cpu_m=100.0, rec_cpu_m=500.0,
        current_mem_bytes=0, rec_mem_bytes=0,
        instance_type="m5.xlarge",
    )
    assert saving == 0.0


def test_cpu_delta_percent():
    assert cpu_delta_percent(current_m=500.0, rec_m=100.0) == pytest.approx(80.0)


def test_mem_delta_percent():
    assert mem_delta_percent(
        current_bytes=1024 * 1024 * 1024,
        rec_bytes=256 * 1024 * 1024,
    ) == pytest.approx(75.0)
