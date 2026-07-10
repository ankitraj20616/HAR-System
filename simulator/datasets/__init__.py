"""Public dataset loader factory for sensor replay."""

from __future__ import annotations

from pathlib import Path

from .base import DatasetError, DatasetFormatError, DatasetLoader, DatasetWindow
from .sisfall import SisFallLoader
from .uci_har import UciHarLoader
from .wisdm import WisdmLoader


def load_dataset(name: str, path: str | Path, **options: object) -> DatasetLoader:
    """Create a loader by CLI-friendly dataset name."""

    normalized = name.strip().lower().replace("_", "-")
    loaders = {
        "uci": UciHarLoader,
        "uci-har": UciHarLoader,
        "wisdm": WisdmLoader,
        "sisfall": SisFallLoader,
    }
    try:
        loader_type = loaders[normalized]
    except KeyError as exc:
        message = f"unsupported dataset {name!r}; choose uci-har, wisdm, or sisfall"
        raise DatasetError(message) from exc
    return loader_type(path=path, **options)  # type: ignore[arg-type,call-arg,return-value]


__all__ = [
    "DatasetError",
    "DatasetFormatError",
    "DatasetLoader",
    "DatasetWindow",
    "SisFallLoader",
    "UciHarLoader",
    "WisdmLoader",
    "load_dataset",
]
