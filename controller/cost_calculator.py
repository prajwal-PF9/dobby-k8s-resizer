INSTANCE_PRICING = {
    "m5.large":   {"cpu_per_core_per_hour": 0.048, "mem_per_gib_per_hour": 0.006},
    "m5.xlarge":  {"cpu_per_core_per_hour": 0.048, "mem_per_gib_per_hour": 0.006},
    "m5.2xlarge": {"cpu_per_core_per_hour": 0.048, "mem_per_gib_per_hour": 0.006},
    "m5.4xlarge": {"cpu_per_core_per_hour": 0.048, "mem_per_gib_per_hour": 0.006},
    "c5.xlarge":  {"cpu_per_core_per_hour": 0.043, "mem_per_gib_per_hour": 0.005},
    "r5.xlarge":  {"cpu_per_core_per_hour": 0.040, "mem_per_gib_per_hour": 0.010},
}

HOURS_PER_MONTH = 730


def parse_cpu_to_millicores(cpu_str: str) -> float:
    s = str(cpu_str).strip()
    if s.endswith("m"):
        return float(s[:-1])
    return float(s) * 1000


def parse_memory_to_bytes(mem_str: str) -> int:
    s = str(mem_str).strip()
    units = [
        ("Ki", 1024),
        ("Mi", 1024 ** 2),
        ("Gi", 1024 ** 3),
        ("Ti", 1024 ** 4),
        ("K",  1000),
        ("M",  1000 ** 2),
        ("G",  1000 ** 3),
    ]
    for suffix, multiplier in units:
        if s.endswith(suffix):
            return int(float(s[: -len(suffix)]) * multiplier)
    return int(s)


def calculate_monthly_saving(
    current_cpu_m: float,
    rec_cpu_m: float,
    current_mem_bytes: int,
    rec_mem_bytes: int,
    instance_type: str,
) -> float:
    pricing = INSTANCE_PRICING.get(instance_type, INSTANCE_PRICING["m5.xlarge"])
    cpu_delta_cores = max(0.0, (current_cpu_m - rec_cpu_m) / 1000)
    mem_delta_gib = max(0.0, (current_mem_bytes - rec_mem_bytes) / (1024 ** 3))
    cpu_saving = cpu_delta_cores * pricing["cpu_per_core_per_hour"] * HOURS_PER_MONTH
    mem_saving = mem_delta_gib * pricing["mem_per_gib_per_hour"] * HOURS_PER_MONTH
    return round(cpu_saving + mem_saving, 2)


def cpu_delta_percent(current_m: float, rec_m: float) -> float:
    if current_m == 0:
        return 0.0
    return abs(current_m - rec_m) / current_m * 100


def mem_delta_percent(current_bytes: int, rec_bytes: int) -> float:
    if current_bytes == 0:
        return 0.0
    return abs(current_bytes - rec_bytes) / current_bytes * 100
