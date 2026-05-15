# %% Init ---------------------------------------------------------------------

import os
import shutil
from datetime import datetime

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.experiment.evaluate import (
    evaluate,
    print_metrics,
    save_metrics,
    send_metrics_to_discord,
)
from dblp_kgqa.experiment.logger import setup_logging
from dblp_kgqa.experiment.schemas import ExpConfig, ExpResult, ExpResults
from dblp_kgqa.pipeline.factory import PipelineFactory
from dblp_kgqa.services.dblp_quad import DblpQuadService, DblpQuadSplitType
from dblp_kgqa.services.registry import ServiceRegistry, ServiceRegistryConfig
from dblp_kgqa.utils.yaml import yaml_dump, yaml_load

# **** CONFIG *****************************************************************
CONFIG_DIR = PROJECT_ROOT / "config"
services_config = yaml_load(ServiceRegistryConfig, CONFIG_DIR / "services.yml")
exp_config = yaml_load(ExpConfig, CONFIG_DIR / "experiment.yml")
# *****************************************************************************

# Dirs & files
OUTPUT_DIR = PROJECT_ROOT / "experiment_output"
RESULTS_DIR = OUTPUT_DIR / "results"
CURRENT_DIR = OUTPUT_DIR / "current"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_DIR.mkdir(parents=True, exist_ok=True)

checkpoint_path = CURRENT_DIR / "exp_results.json"
log_file_path = CURRENT_DIR / "experiment.log"

# Services
service_registry = ServiceRegistry()
service_registry.load_services(services_config)

# Dataset
split_type: DblpQuadSplitType = exp_config.split
dblp_quad = service_registry.get("dblp_quad", DblpQuadService)
dataset_questions = dblp_quad.load(split_type, "questions")
dataset_answers = dblp_quad.load(split_type, "answers")
samples = dataset_questions.questions
total = len(samples)

# Pipeline
pipeline = PipelineFactory.create(exp_config.pipeline_config, service_registry)

# ExpResult
exp_results = ExpResults()

# Checkpoint
resuming = checkpoint_path.exists()
if resuming:
    exp_results = ExpResults.model_validate_json(
        checkpoint_path.read_text(encoding="utf-8")
    )
    last_id = exp_results.exp_results[-1].id
    for i, s in enumerate(samples):
        if s.id == last_id:
            samples = samples[i + 1 :]
            break

print(
    "Starting experiment: "
    f"{total} samples, {len(exp_results.exp_results)} already processed"
)

# Logging
logger = setup_logging(log_file_path, append=resuming)

# %% Run ----------------------------------------------------------------------

for sample in samples:
    try:
        result = pipeline.run(sample.question.string)
        exp_results.exp_results.append(ExpResult(id=sample.id, result=result))
        logger.info(f"== SAMPLE {sample.id} OF {total} PROCESSED ==")
    except Exception:
        logger.exception(f"XXXX ERROR SAMPLE {sample.id}")
        continue

    done = len(exp_results.exp_results)
    print(f"{sample.id}/{total} ({done} ok)")

    # Checkpoint every 50 samples (atomic: write to tmp + rename)
    if done % 50 == 0:
        tmp_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
        tmp_path.write_text(
            exp_results.model_dump_json(indent=4), encoding="utf-8"
        )
        os.replace(tmp_path, checkpoint_path)

print(f"\nDone: {len(exp_results.exp_results)}/{total} processed")

# Save results
timestamp = datetime.now().strftime("%y-%m-%d_%H-%M-%S")
exp_dir = RESULTS_DIR / f"{timestamp}_{split_type}"
exp_dir.mkdir()
(exp_dir / "exp_config.yml").write_text(
    yaml_dump(exp_config), encoding="utf-8"
)
(exp_dir / "services.yml").write_text(
    yaml_dump(services_config), encoding="utf-8"
)
(exp_dir / "exp_results.json").write_text(
    exp_results.model_dump_json(indent=4), encoding="utf-8"
)
shutil.copy2(log_file_path, exp_dir)
checkpoint_path.unlink(missing_ok=True)
print(f"Results saved to: {exp_dir}")


# %% Evaluate -----------------------------------------------------------------
results = evaluate(exp_results, dataset_questions, dataset_answers, "qa")
save_metrics(results, exp_dir)
print_metrics(results)
send_metrics_to_discord(results, exp_config)
