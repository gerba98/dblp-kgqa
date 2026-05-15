import os
import sys
from pathlib import Path

import runpod
import yaml
from dotenv import load_dotenv

# Pod config
GPU = "NVIDIA GeForce RTX 3090"
CLOUD_TYPE = "COMMUNITY"
IMAGE = "ghcr.io/ggml-org/llama.cpp:server-cuda"
ALLOWED_CUDA = ["12.8", "12.9"]
CONTAINER_DISK_GB = 15
HTTP_PORT = 8080

# Model source
HF_REPO_TEMPLATE = "unsloth/Qwen3.5-{size}-GGUF"
HF_SIZES = ("2B", "4B", "9B")

# llama-server
N_GPU_LAYERS = 99
CACHE_TYPE = "bf16"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_YML = PROJECT_ROOT / "config" / "services.yml"
POD_ID_FILE = PROJECT_ROOT / ".runpod" / "pod_id"


def llama_args(model, ctx_size):
    size = next((s for s in HF_SIZES if f"-{s}-" in model), None)
    if size is None:
        sys.exit(f"Cannot determine model size from: {model}")
    repo = HF_REPO_TEMPLATE.format(size=size)
    return (
        f"--hf-repo {repo} --hf-file {model}.gguf "
        f"--host 0.0.0.0 --port {HTTP_PORT} --ctx-size {ctx_size} "
        f"--n-gpu-layers {N_GPU_LAYERS} "
        f"--cache-type-k {CACHE_TYPE} --cache-type-v {CACHE_TYPE}"
    )


def pod_url(pod_id):
    return f"https://{pod_id}-{HTTP_PORT}.proxy.runpod.net"


def cmd_start():
    if POD_ID_FILE.exists():
        sys.exit(f"Pod already active: {POD_ID_FILE.read_text().strip()}")

    backend = yaml.safe_load(SERVICES_YML.read_text())["local_llm"]["backend"]
    model, ctx_size = backend["model_name"], backend["ctx_size"]
    print(f"Creating pod: model={model} ctx={ctx_size} gpu={GPU}")

    pod = runpod.create_pod(
        name=f"llama-{model}",
        image_name=IMAGE,
        gpu_type_id=GPU,
        cloud_type=CLOUD_TYPE,
        container_disk_in_gb=CONTAINER_DISK_GB,
        ports=f"{HTTP_PORT}/http",
        docker_args=llama_args(model, ctx_size),
        allowed_cuda_versions=ALLOWED_CUDA,
        country_code="FR,CZ,NL,RO"
    )
    pod_id = pod["id"]
    POD_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    POD_ID_FILE.write_text(pod_id)
    print(f"Pod: {pod_id}  URL: {pod_url(pod_id)}")


def cmd_stop():
    if not POD_ID_FILE.exists():
        print("No active pod.")
        return
    pod_id = POD_ID_FILE.read_text().strip()
    runpod.terminate_pod(pod_id)
    POD_ID_FILE.unlink()
    print(f"Terminated: {pod_id}")


def cmd_status():
    if not POD_ID_FILE.exists():
        sys.exit("No active pod.")
    pod = runpod.get_pod(POD_ID_FILE.read_text().strip())
    print(yaml.safe_dump({
        "id": pod["id"],
        "url": pod_url(pod["id"]),
        "status": pod.get("desiredStatus"),
        "uptime_s": pod.get("uptimeSeconds"),
        "cost_per_hr": pod.get("costPerHr"),
    }, sort_keys=False))


def cmd_url():
    if not POD_ID_FILE.exists():
        sys.exit("No active pod.")
    print(pod_url(POD_ID_FILE.read_text().strip()))


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        sys.exit("RUNPOD_API_KEY not set in .env")
    runpod.api_key = api_key

    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "url": cmd_url,
    }
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd not in commands:
        sys.exit(f"Usage: runpod_llm.py {{{'|'.join(commands)}}}")
    commands[cmd]()


if __name__ == "__main__":
    main()
