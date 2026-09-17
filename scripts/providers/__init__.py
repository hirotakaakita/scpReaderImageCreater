"""Legacy image-provider registry.

Local image-generation provider implementations were removed. This repository now
exports prompts and accepts externally generated images via scripts/accept_external_panel.py.
"""

PROVIDERS = {}


def get(name):
    raise RuntimeError(
        "Local image-generation providers have been removed. "
        "Use `python scripts/run_pipeline.py --id <id> --export-prompts`, "
        "generate images externally, then import them with "
        "`python scripts/accept_external_panel.py --id <id> --panel <N> --source <image>`.")
