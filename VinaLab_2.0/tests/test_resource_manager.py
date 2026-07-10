from __future__ import annotations

import importlib


def _resource_manager_type():
    try:
        module = importlib.import_module("vinalab_core.tools.resource_manager")
    except ModuleNotFoundError:
        return None
    return getattr(module, "ResourceManager", None)


def test_resource_manager_is_available_to_budget_cpu_and_gpu_work() -> None:
    assert _resource_manager_type() is not None


def test_resource_manager_rejects_a_request_that_exceeds_active_cpu_budget() -> None:
    resource_manager_type = _resource_manager_type()
    assert resource_manager_type is not None
    manager = resource_manager_type(cpu_budget=6, gpu_device_ids=(0,))

    first = manager.reserve(cpu_threads=4, gpu_device_ids=(0,))

    assert manager.can_reserve(cpu_threads=2, gpu_device_ids=())
    assert not manager.can_reserve(cpu_threads=3, gpu_device_ids=())

    manager.release(first)
    assert manager.can_reserve(cpu_threads=6, gpu_device_ids=(0,))


def test_resource_manager_prevents_two_heavy_jobs_using_the_same_gpu() -> None:
    resource_manager_type = _resource_manager_type()
    assert resource_manager_type is not None
    manager = resource_manager_type(cpu_budget=8, gpu_device_ids=(0, 1))

    reservation = manager.reserve(cpu_threads=2, gpu_device_ids=(1,))

    assert not manager.can_reserve(cpu_threads=2, gpu_device_ids=(1,))
    assert manager.can_reserve(cpu_threads=2, gpu_device_ids=(0,))
    manager.release(reservation)
