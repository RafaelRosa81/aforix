# User batch workspace

This folder is reserved for local, user-defined Aforix batch YAML files.

Use it when you want to keep custom workflows separate from the official examples in:

```text
configs/batches/examples/
```

## Recommended workflow

1. Copy an existing example from `configs/batches/examples/` or `configs/batches/examples/atomic/`.
2. Paste it into this folder with a descriptive name.
3. Edit the `batch.id`, `batch.name`, `description`, variables, steps, and parameters.
4. Validate before running:

```bash
aforix batch check -b configs/batches/user/my_batch.yaml
aforix batch plan -b configs/batches/user/my_batch.yaml
aforix batch run -b configs/batches/user/my_batch.yaml --dry-run
```

5. Run when ready:

```bash
aforix batch run -b configs/batches/user/my_batch.yaml
```

## Windows launcher usage

After launchers are installed, you can run a custom batch by dragging your YAML file onto:

```text
launchers/windows/run_batch_file.bat
```

Or copy this template:

```text
launchers/windows/run_custom_batch_template.bat
```

rename it, and point `BATCH_FILE` to your YAML.

## Linux launcher usage

After launchers are installed:

```bash
chmod +x launchers/linux/*.sh
./launchers/linux/run_batch_file.sh configs/batches/user/my_batch.yaml
```

Or copy this template:

```text
launchers/linux/run_custom_batch_template.sh
```

rename it, and point `BATCH_FILE` to your YAML.

## Notes

- Keep YAML files small and focused when possible.
- Prefer `batch check`, `batch plan`, and `--dry-run` before a real run.
- Review `runs/batch/<run_id>/manifest.json` after each execution.
- Official examples are versioned references. Personal files in this folder may be project-specific.
