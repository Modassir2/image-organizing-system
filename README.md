# Image Organizing System

Point it at a folder full of images. A vision model reads each one and files it into the categories **you** define — live progress and all.

Works with **any OpenAI-compatible vision endpoint** — a local `llama.cpp` server, Ollama, LM Studio, vLLM, or a cloud API. Run it fully offline and your images never leave your machine.

```
Current Directory:             ./Photos/2024                        ['C:\Photos\2024']
Dir Progress:                  ###############################------------------- | 62.00% [31/50]
Total Progress:                ################---------------------------------- | 33.67% [101/300]
Processing:                    IMG_0432.jpg                        ['C:\Photos\2024\IMG_0432.jpg']
Estimated Time Remaining:      4 Min(s) 12 Sec  [7.4 sec per Image]
```

---

## Why use it

- **Local-first.** With a local server, no image or prompt ever leaves your machine. Nothing is uploaded, nothing is logged by a third party.
- **Copy, never move.** Your originals stay exactly where they are. Sorted files land in `output/<category>/`.
- **Bring your own categories.** Any list you write in one JSON file, described in one Markdown file. Nothing is hardcoded — documents, screenshots, receipts, memes, whatever you actually have. Need a category handled differently? There's a per-category hook in `main.py`.
- **No silent failures.** Every warning and error goes to a JSON-lines log you can actually parse.
- **Resumable.** Interrupted a 5,000 image run? Restart and pick up where you stopped.
- **Handles flaky setups.** Unplugged the external drive mid-run? It waits and retries instead of dying. Server dropped? Same.

---

## How it works

```
image folder ──► base64 data URL ──► vision model (tool call: sort_image)
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
              valid category from enum                    BadRequest ×3
                        │                                           │
                        ▼                                           ▼
           output/<category>/<filename>                        skipped + logged
```

1. Recursively walks the folder you give it and counts `.jpg`, `.jpeg`, `.png` files.
2. Base64-encodes each image and sends it with your instructions to the model.
3. Forces the model to answer through a single `sort_image` tool call whose `category` argument is an `enum` built from `categories.json`. The enum steers the model, and anything outside it is rejected and retried.
4. Verifies the returned category against the list, copies the file to `save_location/<category>/`, and moves on.

---

## Requirements

| | |
|---|---|
| Python | 3.9+ (developed and tested on 3.13.3) |
| Model | **`qwen3.5:2b`** recommended; any vision-capable model with **function/tool calling** works |
| Server | An OpenAI-compatible endpoint (local or cloud) |

Tool calling is not optional. The classifier only reads the model's `sort_image` tool call, so a model without tool support will produce `Category not generated` warnings forever.

### Recommended model: `qwen3.5:2b`

The sweet spot for this tool — small enough to run on a laptop (CPU included), good at reading printed and handwritten document text, and it supports tool calling without extra configuration. Every config example below uses it, and it handles the bundled document categories without prompt tuning.

Need higher accuracy on dense or low-quality scans? Step up to a larger vision model. Need more speed? Use a quantized build — just keep the same model ID.

Naming varies by server — some builds report `qwen3.5:2b`, others use different punctuation. Copy the exact ID from `ollama list` or the llama-server startup log into `model`.

---

## Quick start

```bash
git clone https://github.com/Modassir2/image-organizing-system.git
cd image-organizing-system
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your config, start your model server (see [Connecting a model](#connecting-a-model)), then:

```bash
python main.py
```

On Windows you can also double-click **`run.bat`**, which activates the venv and launches the script.

You'll be asked for two things:

```
Enter Path to Images: C:\Users\me\Pictures\Scans
Resume Progress?(Y/n): n
```

A quoted path works too (`"C:\My Photos\Scans"` is accepted). Then just let it run. `Ctrl+C` exits cleanly at any time.

---

## Configuration

`main.py` reads `config.json` from its own folder. Copy the template and edit it:

```bash
cp config.example.json config.json     # macOS / Linux
copy config.example.json config.json   # Windows
```

```json
{
  "base_url": "http://127.0.0.1:8002/v1",
  "model": "qwen3.5:2b",
  "api_key": "local",
  "save_location": "./output",
  "connection_retry": 10
}
```

| Key | Required | Default | Meaning |
|---|---|---|---|
| `base_url` | ✅ | — | OpenAI-compatible base URL. For local servers this usually ends in `/v1`. |
| `model` | ✅ | — | Exact model identifier the server expects. |
| `api_key` | ✅ | — | Basic auth token. Local servers accept any non-empty string; cloud providers need the real key. |
| `port` | ❌ | none | If set, it is appended to `base_url` as `base_url:port` and the two are combined. Use this only when you want the port split out. |
| `save_location` | ❌ | `./output` | Where sorted folders are created, relative to the project folder. |
| `connection_retry` | ❌ | `60` | Seconds to wait before retrying a dropped connection. |

> **Pick one style.** Either put the full URL in `base_url` (`http://127.0.0.1:8002/v1`, no `port` key), or omit the port from `base_url` and set `"port": 8002`. Do both and the client calls the wrong URL.

`api_key` is read from this file, so **keep `config.json` out of version control** — commit only `config.example.json`.

---

## Connecting a model

Any server that speaks the OpenAI Chat Completions API with image input and tool calling will work. Three local options, plus the cloud:

### llama.cpp

```bash
llama-server -m Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf \
             --mmproj mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf \
             --host 127.0.0.1 --port 8002
```

```json
{ "base_url": "http://127.0.0.1:8002/v1", "model": "qwen3.5:2b", "api_key": "local" }
```

Both the model file and its `mmproj` vision projector are required — without the projector the server accepts images but sees nothing useful.

### Ollama

```bash
ollama pull qwen3.5:2b
ollama serve
```

```json
{ "base_url": "http://127.0.0.1:11434/v1", "model": "qwen3.5:2b", "api_key": "ollama" }
```

Pick a vision model that also advertises tool support; older LLaVA builds do not and will fail at the tool-call step.

### LM Studio

Load a vision model in the app, start the **Local Server** (Developer tab), and copy the model identifier shown there.

```json
{ "base_url": "http://127.0.0.1:1234/v1", "model": "<model-id-from-lm-studio>", "api_key": "lm-studio" }
```

### Cloud (OpenAI and compatible)

```json
{ "base_url": "https://api.openai.com/v1", "model": "<vision model>", "api_key": "sk-..." }
```

The same config shape works for Groq, Together, OpenRouter, and other OpenAI-compatible providers — change the URL, key, and model name. **This is the one case where your images leave your machine.** Every image is sent in full as base64, so use a local server if that matters to you.

---

## Categories

**You define the categories, not the app.** Nothing in the code knows the word "medical" or "legal" — the five labels shipped in `categories.json` are just a starting point for document sorting. Swap them for anything you want to organize by: `receipts`, `screenshots`, `memes`, `wallpapers`, `pets`, `whiteboards`.

Categories live in `categories.json`:

```json
{
  "categories": [
    "important_documents",
    "medical_documents",
    "legal_documents",
    "other_documents",
    "not_documents"
  ]
}
```

This list is injected straight into the tool schema as an `enum`. That makes it the single source of truth for what the model is allowed to answer, and every category becomes a folder under `save_location`. A completely different set works the same way, with no code changes:

```json
{
  "categories": ["receipts", "screenshots", "memes", "wallpapers", "other"]
}
```

`instructions.md` explains what the labels *mean*. That's where the real accuracy comes from — describe each category in plain language, with concrete examples and a tie-breaker:

```markdown
- `receipts`: photos of purchase receipts, invoices, order confirmations.
- `screenshots`: phone or desktop UI captures, chat screenshots, app screens.
- `memes`: joke images, image macros, reaction pictures.
- `wallpapers`: artwork or scenery meant to be used as a background.
- `other`: anything that doesn't clearly fit the above.
```

If `instructions.md` is missing, the app falls back to `Sort the given image.` — which works, but is vague.

### Rules for category names

- **Exact strings.** Case, spaces, punctuation, and accents are preserved. `Receipts` and `receipts` are two different categories.
- **Don't use `skip`.** It's reserved. The app returns `"skip"` internally when a model rejects an image three times, so a category with that name is never copied.
- **Folder-safe characters only.** Every label becomes a directory name, so avoid `\ / : * ? " < > |`.
- **Restart after editing.** Categories are read once at startup.

### Adding a category

1. Add the label to `categories.json`.
2. Add a line describing it to `instructions.md`.
3. Restart the script.

Never rename a label mid-run — old folders won't merge.

### Custom logic per category

By default every image is copied to `save_location/<category>/`. When a category needs different behaviour, `main.py` has a hook immediately before the copy:

```python
if category == "skip":
    utils.log(level="WARN", line=f"Skipping image {count} - {img} due to BadRequestError [...]")
    continue
#Custom Category Logic Here:
#if category=="x":
#    continue #Skips and ignores if category = "x"
#----------------------------------

save_category = os.path.join(save, category)
copy(source=path, destination_dir=save_category)
```

At that point `category`, `img`, `path`, `root`, `count` and `save` are all in scope. `continue` skips the image and leaves it in place; anything else falls through to the two lines that do the copying.

**Leave a category where it is** — uncomment the shipped example and swap `x`:

```python
if category == "not_documents":
    continue
```

**Group several categories into one folder** — replace the last two default lines with:

```python
if category in ("medical_documents", "legal_documents"):
    save_category = os.path.join(save, "sensitive")
else:
    save_category = os.path.join(save, category)
copy(source=path, destination_dir=save_category)
```

**Prefix filenames with their category** — replace the `copy(...)` line with:

```python
copy(source=path, destination_dir=save_category, name=f"{category}_{img}")
```

`copy()` accepts `name=`, so you can rename on the way out without touching the original. Only ever call it once per image, or you'll write the file twice.

Keep the `skip` branch above your own rules — it's how the three-strikes `BadRequestError` fallback stays quiet.

---

## Output layout

```
output/
├── important_documents/
│   ├── scan_001.jpg
│   └── passport.png
├── medical_documents/
│   └── lab_result.jpg
└── legal_documents/
    └── lease(1).jpg      ← duplicate name, auto-numbered
```

- Files are **copied**, so the source folder is never modified.
- Every category the model returns gets its own folder — including `not_documents`. To leave a category's images where they are, add a rule with the [custom logic](#custom-logic-per-category) hook.
- A name collision in the destination becomes `name(1).ext`, `name(2).ext`, and so on.
- `save_location` is resolved relative to the project folder, not the image folder.

---

## Resuming an interrupted run

At the prompt choose `Y` and enter how many images were already processed:

```
Resume Progress?(Y/n): y
Resume Progress From(0 to cancel): 340
```

`340` means "skip the first 340 images and continue". The script counts images in the same fixed order every run — directories sorted, then filenames sorted — so the number stays meaningful between runs. Enter `0` to start the current run from scratch.

Resume does **not** re-verify the output folder. If you deleted or moved anything in `output/`, the files you skipped won't be recreated.

---

## Logs

Everything is appended to `logs.log` next to `main.py`, one JSON object per line:

```json
{"timestamp": "Thursday, 27-August-2026, 03:55 AM", "level": "WARN", "details": "Category not generated; line 46. [Content: ]"}
```

`INFO` for lifecycle events, `WARN` for recoverable oddities, `ERROR` for real failures. Filter it with:

```bash
grep '"level": "ERROR"' logs.log     # macOS / Linux
Select-String 'ERROR' logs.log       # Windows PowerShell
```

The file grows across runs — delete it whenever you like.

---

## Project structure

```
image-organizing-system/
├── main.py               # CLI, progress UI, copy logic, retry handling
├── utils.py              # config loading, logging, tool schema, system prompt
├── categories.json       # allowed labels (feeds the tool enum)
├── instructions.md       # plain-language definition of each category
├── config.example.json   # safe template to commit
├── config.json           # your real config — do not commit
├── requirements.txt
├── run.bat               # Windows one-click launcher
├── LICENSE               # MIT
└── logs.log              # JSON-lines run log (generated)
```

---

## Troubleshooting

**`Config Not Found!`**
`config.json` isn't next to `main.py`. Copy `config.example.json` and rename it.

**`Invalid config.json, required fields: 'url', 'api', 'model'`**
One of `base_url`, `api_key`, or `model` is missing or empty.

**`Category not generated` / `Tool_call has no args` warnings repeating**
The model isn't returning a tool call. Check, in order: the model supports function calling; the server has tool use enabled; your `model` string matches the server exactly (`ollama list`, LM Studio's model list, llama-server startup log).

**`Incorrect category generated`**
The model replied with a label outside your enum. Usually a sign that `instructions.md` names a category you removed from `categories.json`.

**Images get skipped as `skip`**
Three `BadRequestError`s in a row and the image is dropped. Typically an unsupported or corrupt file. Only `.jpg`, `.jpeg`, `.png` are read, and **extensions must be lowercase** — `PHOTO.JPG` is invisible to the scanner. Bulk-rename first if your camera produces uppercase names.

**`Image Source Not Found, Did you disconnect the disk?`**
The file vanished mid-run. It retries every 30 seconds indefinitely, so replug the drive or `Ctrl+C` out.

**`Connection Error. Retrying in Nsec...`**
The server is unreachable. It retries forever, waiting `connection_retry` seconds each time. Fix the server and it resumes on the same image.

**Every image lands in one category**
Your `instructions.md` is too vague, or the model is too small to separate the labels. Sharpen the descriptions and add a concrete tie-breaker rule per category before blaming the loader.

---

## Limitations

- Only `.jpg`, `.jpeg`, `.png`, lowercase extensions.
- One image, one category — no multi-label output.
- No EXIF/OCR/metadata awareness; the model sees pixels only.
- Sequential processing; throughput is bounded by your model's latency. A 3B model on CPU is roughly 2–10 s per image.
- No dry-run mode yet. Point `save_location` at a scratch folder for a test pass.

---

## Contributing

Issues and PRs are welcome. If you're changing classification behaviour, keep `categories.json` and `instructions.md` in sync — the README describes them as a pair because they only work as a pair.

---

## License

Released under the [MIT License](LICENSE) — free to use, modify, and redistribute as long as the copyright notice is kept.
