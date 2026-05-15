from pathlib import Path

import yaml
from pydantic import BaseModel


def yaml_dump(model: BaseModel) -> str:
    return yaml.dump(model.model_dump(mode="json"), sort_keys=False)


def yaml_load[T: BaseModel](cls: type[T], path: Path) -> T:
    config_dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config_dict is None:
        config_dict = {}
    return cls.model_validate(config_dict)
