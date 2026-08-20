# Contributing to DeepSeeLite

DeepSeeLite accepts code, documentation, and test contributions. Keep changes narrowly scoped,
preserve unrelated worktree changes, and run the focused checks for the area you modify.

## Release Identity

DeepSee releases the full `seedeep` distribution and owns the DSH Release assets. DeepSeeLite
publishes the converged lite edition to PyPI under its own name, `deepseelite`; it must never
publish under the `seedeep` name. Both distributions share the `deepsee` import package, the
`deepsee-server` command, and the `~/.config/deepsee` configuration namespace, so they cannot
be installed into the same environment. This repository remains the convergence and
verification source; keep its package metadata compatible with the canonical source so focused
tests exercise the same API.

## DSH Installer Maintenance

The DSH integration is intentionally limited to the DSH Web profile. The README is the
user-facing entry point: keep the DSH startup, install, mode selection, verification, and
uninstall workflow at the top. DeepSeeLite remains standalone-compatible for local validation,
so its public configuration, API, protocol, and security reference may follow that DSH section;
put contributor-only operational rules in this file and the DSH installation guides.

The installer responsibilities are split deliberately:

- `scripts/install-dsh-dsv.sh` downloads and verifies the pinned Release asset, selects the
  install mode, checks the embedded verifier against its pinned SHA-256, snapshots mutable
  files, runs `pnpm`, validates the Loader, and rolls back on failure. Update the verifier hash
  in the installer whenever a release changes `verify-dsh-dsv-assets.py`.
- `scripts/dsh-profile.py` owns the managed `llm-dsv` package entries and patch block. It
  updates only its marked block and must not replace a hand-written `llm-dsv` row.
- `scripts/dsh-credentials.py` is the only installer helper allowed to mutate
  `$DSH_HOME/.credentials.yaml`. It accepts a value only through stdin, does not print it,
  replaces the file atomically, and applies mode `0600`.

The interactive installer reads choices and hidden key input from `/dev/tty`, rather than the
`curl` pipe. `--no-configure` must not read, create, or change credentials. Interactive `Y`
keeps an existing DSV key; explicit `--configure` may rotate it. `--verify` must not alter the
profile, and `--uninstall` must preserve credentials.

Never place DSV public keys, visual-provider keys, or machine-specific paths in source files,
logs, test fixtures intended for release, or published assets. Use synthetic values in tests.

## DSH Installer Checks

Run these after changing the installer, profile helper, credentials helper, or DSH docs:

```bash
pytest -q tests/test_dsh_credentials.py tests/test_dsh_installer.py \
  tests/test_dsh_installer_script.py tests/test_release_assets.py \
  tests/test_docs_install_command.py
bash -n scripts/install-dsh-dsv.sh
python3 -m py_compile scripts/dsh-credentials.py scripts/dsh-profile.py
```

For a release-facing smoke test, use a temporary `DSH_HOME` and the public raw installer. Test
`--no-configure`, `--configure`, `--verify`, and `--uninstall`; confirm `--configure` does not
emit its synthetic key and that uninstall leaves `.credentials.yaml` unchanged.

## Documentation

Keep [`docs/DSH-DSV-INSTALL.zh.md`](docs/DSH-DSV-INSTALL.zh.md) and
[`docs/DSH-DSV-INSTALL.md`](docs/DSH-DSV-INSTALL.md) aligned whenever command behavior
changes. The Chinese guide is the detailed user workflow; the English guide is its concise
counterpart. Update `tests/test_docs_install_command.py` when moving DSH user-facing commands
between README and contributor documentation.
