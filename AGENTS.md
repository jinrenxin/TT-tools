# AGENTS.md
Guidance for agentic coding assistants working in this repository.

## 1) Repo Snapshot
- Project type: Python ComfyUI custom node pack.
- ComfyUI registration entrypoint: `__init__.py`.
- Primary nodes: `tt_img_*_node.py`.
- Shared helpers: `tt_img_utils.py`.
- Packaging files: `setup.py`, `requirements.txt`.
- Validation scripts currently in repo: `performance_test.py`, `performance_compare.py`.
- No committed `tests/` suite and no enforced lint/type config files were found.

## 2) Setup Commands
Prefer Python 3.9+ (setup allows `>=3.7`).

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional editable install:

```bash
pip install -e .
```

## 3) Build / Packaging Commands
Build source and wheel distributions:

```bash
python setup.py sdist bdist_wheel
```

Quick metadata check:

```bash
python setup.py --name --version
```

## 4) Lint / Static Checks
No repo-specific config was found for `ruff`, `black`, `mypy`, or `flake8`.

Baseline syntax/compile check (safe default):

```bash
python -m compileall .
```

Optional local checks if tools are installed:

```bash
ruff check .
black --check .
```

## 5) Test Commands (Single-Test Focus)
Current state:
- There is no canonical `pytest` suite in this repository yet.
- Existing test-like validation uses script execution.

Run current script-based checks:

```bash
python performance_test.py
python performance_compare.py
```

Run a single targeted test invocation:

```bash
python -c "from performance_test import test_decode_performance; test_decode_performance('pw_test.png', '123456')"
```

If `pytest` tests are added later, use:

```bash
pytest
pytest tests/test_some_module.py
pytest tests/test_some_module.py::test_specific_case
pytest -k "keyword_expr"
```

## 6) Codebase Architecture Conventions

### 6.1 ComfyUI Node Contract
- Node classes follow `TTImg...Node` naming.
- Implement `INPUT_TYPES` as `@classmethod` with `required` and optional `optional` sections.
- Define class constants consistently: `RETURN_TYPES`, `FUNCTION`, `CATEGORY`, and `OUTPUT_NODE` where needed.
- Node execution methods must return tuples for ComfyUI compatibility, e.g. `(image_tensor,)` or `()`.
- Register new nodes in `__init__.py` under both:
  - `NODE_CLASS_MAPPINGS`
  - `NODE_DISPLAY_NAME_MAPPINGS`

### 6.2 Imports
- Prefer import order: standard library -> third-party -> local modules.
- Keep imports explicit and stable; avoid wildcard imports.
- Preserve local fallback import pattern when needed:
  - `from .tt_img_utils import TTImgUtils`
  - fallback `from tt_img_utils import TTImgUtils`

### 6.3 Types and Signatures
- Keep function signatures stable to avoid breaking ComfyUI workflows.
- Use type hints in helper/internal methods where practical.
- Typical data types:
  - `np.ndarray` for image processing internals.
  - `torch.Tensor` at ComfyUI boundaries.
- Be explicit with return shapes and tuple returns.

### 6.4 Formatting and Structure
- Follow existing Python style (PEP 8-like, 4 spaces).
- Keep functions focused (convert input -> process -> convert output).
- Prefer small private helpers (e.g. `_apply_lut_to_image`).
- Avoid unrelated broad refactors in feature/fix changes.

### 6.5 Naming
- Classes: `PascalCase` (`TTImgEncNode`).
- Functions/variables: `snake_case`.
- Constants / ComfyUI class attributes: uppercase (`RETURN_TYPES`, `FUNCTION`).
- Use descriptive argument names (`output_filename`, `lut_strength`, `watermark_height`).

### 6.6 Image and Tensor Handling
- Respect value ranges explicitly:
  - ComfyUI tensors are typically float in `[0, 1]`.
  - OpenCV/PIL file paths often require `uint8` in `[0, 255]`.
- Handle RGB/RGBA/grayscale conversions intentionally.
- Preserve alpha only when behavior explicitly requires it.
- Clamp transformed values with `np.clip` before returning.

### 6.7 Error Handling
- Existing code favors resilience with broad exception guards.
- Keep execution robust in graph runs (avoid crashing the whole node graph).
- On failure, prefer safe fallback outputs (`(images,)` or `()` by node contract).
- Print concise messages that help debugging without excessive noise.
- Do not introduce behavior changes that silently break established workflows.

### 6.8 File I/O and Paths
- Use `os.path.join` and `os.makedirs(..., exist_ok=True)`.
- Resolve ComfyUI output directory via `folder_paths` when available.
- Keep transient artifacts in `temp/` and clean generated temp files.
- Avoid committing generated binaries/images unless intentionally updating fixtures/docs.

## 7) Agent-Specific Operating Guidance
- Make minimal, surgical changes aligned with existing patterns.
- Preserve Chinese user-facing strings unless explicitly asked to translate.
- Maintain backward compatibility for node keys and display names.
- For new nodes, mirror structure from existing node files.
- After edits, run at least `python -m compileall .`.

## 8) Cursor / Copilot Instruction Files
Checked locations:
- `.cursor/rules/`
- `.cursorrules`
- `.github/copilot-instructions.md`

Status at the time of writing:
- No Cursor rules or Copilot instruction files were found.
- If those files are added later, treat them as high-priority policy and merge guidance into this file.

## 9) Pre-PR Checklist for Agents
- Run install/setup steps needed for touched areas.
- Run `python -m compileall .`.
- Run relevant script-based checks (or targeted single-case command).
- If adding `pytest` tests, include at least one single-test command in notes.
- Confirm `__init__.py` mappings for any new node class.
- Keep diffs focused; avoid incidental formatting churn.
