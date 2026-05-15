import json

from pydantic import BaseModel

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.demo.schemas import DemoConfig
from dblp_kgqa.experiment.schemas import ExpConfig
from dblp_kgqa.modules.entity_linker.gold import GoldEntityLinkerConfig
from dblp_kgqa.modules.info_extractor.gold import GoldInfoExtractorConfig
from dblp_kgqa.services.registry import ServiceRegistryConfig
from dblp_kgqa.utils.yaml import yaml_dump

# CONFIG ----------------------------------------------------------------------

CONFIG_DIR = PROJECT_ROOT / "config"

CONFIGS: list[tuple[str, type[BaseModel], bool]] = [
    # (filename, config class, apply EXPERIMENT_OVERRIDES)
    ("services.yml", ServiceRegistryConfig, True),
    ("experiment.yml", ExpConfig, True),
    ("demo.yml", DemoConfig, False),
]

EXPERIMENT_OVERRIDES: dict[str, object] = {
    "info_extractor_config": GoldInfoExtractorConfig(),
    "entity_linker_config": GoldEntityLinkerConfig(),
    "schema_version": "dblp_quad",
    "endpoint": "http://virtuoso:8890/sparql",
    "use_vertexai": True,
}

# UTILS -----------------------------------------------------------------------
def _override_field(model: BaseModel, field: str, value: object) -> None:
    for name in model.__class__.model_fields:
        attr = getattr(model, name)
        if name == field:
            setattr(model, name, value)
        elif isinstance(attr, BaseModel):
            _override_field(attr, field, value)


def _build_config(
    config_cls: type[BaseModel], apply_overrides: bool
) -> BaseModel:
    config = config_cls()
    if apply_overrides:
        for field, value in EXPERIMENT_OVERRIDES.items():
            _override_field(config, field, value)
    return config

# MAIN ------------------------------------------------------------------------
def main() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    for filename, config_cls, apply_overrides in CONFIGS:
        path = CONFIG_DIR / filename
        schema_name = path.stem + ".schema.json"
        schema_path = CONFIG_DIR / schema_name

        # YAML config
        if path.exists():
            print(f"  Already exists: {path}")
        else:
            header = f"# yaml-language-server: $schema={schema_name}\n"
            content = header + yaml_dump(
                _build_config(config_cls, apply_overrides)
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"  Created: {path}")

        # JSON Schema
        schema = config_cls.model_json_schema()
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        print(f"  Schema: {schema_path}")


if __name__ == "__main__":
    main()
