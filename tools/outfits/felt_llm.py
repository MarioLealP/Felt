"""Talk to felt-llm (Gemma 4 12B on the server's P104, vision via mmproj) -
as Felt (her compiled persona) or plainly. It only listens on the server's
docker network, so requests go through `ssh clockmost-claude`.

    ask(prompt, images=[pil_img], schema={...}, persona=True) -> dict | str
"""

import base64
import io
import json
import random
import subprocess
from functools import cache

_LLM_CMD = ("IP=$(docker inspect -f '{{.NetworkSettings.Networks.edge.IPAddress}}' felt-llm) && "
            "curl -sS --max-time 300 -H 'Content-Type: application/json' -d @- http://$IP:8080/v1/chat/completions")
_PERSONA_CMD = ("docker exec -w /app felt-core-felt-core-1 /app/.venv/bin/python -c "
                "'import random; from felt_core.brain.persona import compile_persona; "
                "print(compile_persona(rng=random.Random(0)))'")


@cache
def persona() -> str:
    """Felt's compiled persona, straight from felt-core (so it tracks her
    current character sheet)."""
    out = subprocess.run(["ssh", "clockmost-claude", _PERSONA_CMD], capture_output=True, text=True, check=True, timeout=120)
    return out.stdout.strip()


def _image_part(img) -> dict:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}}


def ask(prompt: str, images=(), schema: dict | None = None, persona_on: bool = True,
        temperature: float = 0.8, max_tokens: int = 700, seed: int | None = None):
    messages = []
    if persona_on:
        messages.append({"role": "system", "content": persona()})
    messages.append({"role": "user", "content": [*(_image_part(i) for i in images), {"type": "text", "text": prompt}]})
    payload = {"model": "felt", "temperature": temperature, "max_tokens": max_tokens, "messages": messages,
               "seed": seed if seed is not None else random.randrange(1 << 30)}
    if schema:
        payload["response_format"] = {"type": "json_schema", "json_schema": {"schema": schema}}
    res = subprocess.run(["ssh", "clockmost-claude", _LLM_CMD], input=json.dumps(payload).encode(),
                         capture_output=True, check=True, timeout=360)
    content = json.loads(res.stdout)["choices"][0]["message"]["content"]
    return json.loads(content) if schema else content
