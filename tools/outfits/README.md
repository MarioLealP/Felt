# tools/outfits - Felt's wardrobe tooling (WP-27)

The WSL scripts run in the `~/.venvs/felt-outfits` venv. The review app runs on Windows Python.

| file | what |
|------|------|
| `combine.py` | Mix-and-match. It splices garments from VRoid "part" exports (the underwear base plus one piece each) onto the base. Skin hidden under clothes, skin-painted legwear, physics bones and `:#rrggbb` white-fabric tints are all handled. |
| `name_parts.py` | Auto-names part exports. It renders each piece and asks felt-llm (local Gemma vision) what it is, then renames the file `<type>_<name>.vrm`. **WIP**: some pieces are still misnamed. |
| `render_preview.py` | Headless pyrender front/back renders, with cut-out (MASK) alpha done right. |
| `vrm_textures.py` | GLB/VRM read/write and texture helpers. |
| `recolor.py`, `comfy_restyle.py`, `build_batch.py`, `gallery.py` | The Tier-A recolour/restyle batch-1 pipeline. `gallery.py` is superseded by the review app. |
| `review/` | **Review app.** A local window for keep/reject: three.js + three-vrm, rotate/zoom, Felt's .vrma animations, a grid recheck, and Finalize (moves approved files). Batches live in `E:\Felt\review\<batch>\` (gitignored). Launch with `Review.cmd`, or from WSL: `powershell.exe Start-Process python -ArgumentList 'E:\Felt\tools\outfits\review\server.py'`. |

Part exports live in `E:\Felt\Model\OutfitBuilder\`. That folder is inside the overlay's `characters/` through the `Model` junction, so it carries a `.gdignore` to keep Godot from importing it.
