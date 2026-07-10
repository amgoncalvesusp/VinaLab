"""Safe shared CPU/GPU scheduling for VinaLab subprocesses."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ResourceReservation:
    id: str
    cpu_threads: int
    gpu_device_ids: tuple[int, ...]


class ResourceManager:
    """Tracks active work so plugins cannot oversubscribe user-selected resources."""

    def __init__(self, *, cpu_budget: int, gpu_device_ids: tuple[int, ...] = ()) -> None:
        if cpu_budget < 1:
            raise ValueError("cpu_budget must be at least one")
        if len(set(gpu_device_ids)) != len(gpu_device_ids):
            raise ValueError("gpu_device_ids must not contain duplicates")
        self.cpu_budget = cpu_budget
        self.gpu_device_ids = frozenset(gpu_device_ids)
        self._reservations: dict[str, ResourceReservation] = {}

    def can_reserve(self, *, cpu_threads: int, gpu_device_ids: tuple[int, ...] = ()) -> bool:
        self._validate_request(cpu_threads, gpu_device_ids)
        used_cpu = sum(item.cpu_threads for item in self._reservations.values())
        used_gpus = {gpu for item in self._reservations.values() for gpu in item.gpu_device_ids}
        return used_cpu + cpu_threads <= self.cpu_budget and not used_gpus.intersection(gpu_device_ids)

    def reserve(self, *, cpu_threads: int, gpu_device_ids: tuple[int, ...] = ()) -> ResourceReservation:
        if not self.can_reserve(cpu_threads=cpu_threads, gpu_device_ids=gpu_device_ids):
            raise RuntimeError("requested CPU/GPU resources are not currently available")
        reservation = ResourceReservation(str(uuid4()), cpu_threads, gpu_device_ids)
        self._reservations[reservation.id] = reservation
        return reservation

    def release(self, reservation: ResourceReservation) -> None:
        self._reservations.pop(reservation.id, None)

    def _validate_request(self, cpu_threads: int, gpu_device_ids: tuple[int, ...]) -> None:
        if cpu_threads < 1:
            raise ValueError("cpu_threads must be at least one")
        if len(set(gpu_device_ids)) != len(gpu_device_ids):
            raise ValueError("gpu_device_ids must not contain duplicates")
        unknown_devices = set(gpu_device_ids) - self.gpu_device_ids
        if unknown_devices:
            raise ValueError(f"unknown GPU device ids: {sorted(unknown_devices)}")
