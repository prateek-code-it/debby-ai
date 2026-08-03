"""
DEBBY! -- core/airllm_bridge.py
Optional future upgrade path: AirLLM lets you run models far bigger
than your VRAM by streaming one transformer layer at a time, instead
of loading the whole model. Built for GPU setups -- on your current
CPU-only hardware it would likely be SLOWER than Ollama, not faster,
so this stays disabled by default (config.json: "airllm_enabled").

Deliberately does NOT import airllm/torch at the top of this file --
those are heavy (multi-GB) dependencies. They're only imported inside
ask_airllm(), and only reached at all if the config flag is on. This
means leaving it disabled costs you nothing: no extra install, no
extra disk space, no extra RAM.

TO ENABLE LATER (e.g. once you have a real GPU):
  1. pip install airllm torch
  2. Set "airllm_enabled": true in config.json
  3. Set "airllm_model" to whatever model you want to run
That's it -- no code changes needed, brain.py already checks the flag.
"""

_airllm_model_cache = None


def is_enabled(config: dict) -> bool:
    return config.get("airllm_enabled", False)


def ask_airllm(question: str, config: dict, max_new_tokens: int = 256) -> dict:
    global _airllm_model_cache

    if not is_enabled(config):
        return {
            "success": False,
            "error": (
                "AirLLM is disabled. This is intentional on CPU-only hardware -- "
                "it's built for squeezing huge models onto small GPUs, and would "
                "likely be slower than your current models without one.\n"
                "To enable later (e.g. once you have a GPU): set "
                "'airllm_enabled': true in config.json, then "
                "'pip install airllm torch'."
            ),
        }

    try:
        if _airllm_model_cache is None:
            from airllm import AutoModel
            print(f"[Loading AirLLM model '{config['airllm_model']}' -- this can take a while on first load]")
            _airllm_model_cache = AutoModel.from_pretrained(config["airllm_model"])

        input_tokens = _airllm_model_cache.tokenizer(
            [question], return_tensors="pt", padding=True
        )
        output = _airllm_model_cache.generate(
            input_tokens["input_ids"],
            max_new_tokens=max_new_tokens,
            use_cache=True,
        )
        answer = _airllm_model_cache.tokenizer.decode(output[0], skip_special_tokens=True)
        return {"success": True, "answer": answer}
    except ImportError:
        return {"success": False, "error": "Run: pip install airllm torch"}
    except Exception as e:
        return {"success": False, "error": str(e)}
