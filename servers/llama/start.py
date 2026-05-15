# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "python-dotenv"]
# ///
import os
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

HF_REPO_TEMPLATE = "unsloth/Qwen3.5-{size}-GGUF"
HF_SIZES = ("2B", "4B", "9B")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_YML = PROJECT_ROOT / "config" / "services.yml"
COMPOSE_FILE = Path(__file__).resolve().parent / "docker-compose.yml"


def hf_repo_for(model: str) -> str:
    size = next((s for s in HF_SIZES if f"-{s}-" in model), None)
    if size is None:
        sys.exit(f"Cannot determine model size from: {model}")
    return HF_REPO_TEMPLATE.format(size=size)


def main() -> None:
    profile = sys.argv[1] if len(sys.argv) > 1 else None
    if profile not in ("cpu", "gpu"):
        sys.exit("Usage: start.py {cpu|gpu}")

    load_dotenv(PROJECT_ROOT / ".env")

    backend = yaml.safe_load(SERVICES_YML.read_text())["local_llm"]["backend"]
    model = backend["model_name"]
    ctx_size = backend["ctx_size"]

    n_gpu_layers = os.environ.get("LLAMA_N_GPU_LAYERS")
    if not n_gpu_layers:
        n_gpu_layers = "99" if profile == "gpu" else "0"

    print(
        f"Starting llama-server-{profile}: "
        f"model={model} ctx={ctx_size} n_gpu_layers={n_gpu_layers}"
    )

    env = {
        **os.environ,
        "LLAMA_HF_REPO": hf_repo_for(model),
        "LLAMA_HF_FILE": f"{model}.gguf",
        "LLAMA_CTX_SIZE": str(ctx_size),
        "LLAMA_N_GPU_LAYERS": n_gpu_layers,
    }
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE),
         "--profile", profile, "up", "-d"],
        env=env, check=True,
    )


if __name__ == "__main__":
    main()
