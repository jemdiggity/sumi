# Sumi native scheduling preview

Rust implements the `schedule` command family. The normal `bin/sumi` remains the
Python prototype; native Sumi never calls Python as a fallback. Other command
families (mux layouts, managed agent runs, pane TUIs, skill installation) are not
yet ported and produce an unsupported-command error.

Build with Rust 1.93.1 (the CI toolchain):

```sh
native/build.sh
# macOS arm64 example:
dist/aarch64-apple-darwin/sumi --root /path/to/project schedule add hello --every 10s -- /bin/echo hello
dist/aarch64-apple-darwin/sumi --root /path/to/project schedule serve
```

`native/build.sh <rust-target>` writes `dist/<target>/sumi`. Install that binary
where you want to try it, for example `~/.local/bin/sumi-native`; do not replace
your regular `sumi` until you want the scheduling-only preview. A downloaded CI
artifact may need `chmod +x sumi`. No source checkout, Python interpreter, Rust
compiler, package manager, or network is needed to run it. OS libraries are used;
this is not a fully static binary. Executables that you schedule remain external.
Without `--root`, Git discovers the project root when available; otherwise the
current directory is used. Use `--root` when running without Git.

The preview targets macOS arm64 and Linux x86_64 (Ubuntu 24.04 CI baseline, GNU
libc). It does not claim compatibility with older Linux libc versions or Windows.
The workflow builds and executes the contract suite on each target; cross builds
alone do not count as validation. Artifacts are attached to workflow runs.

Python and native Sumi share definitions, history and locks; see [STATE.md](STATE.md).
Usage and recovery semantics follow the root README's scheduling section.

```sh
SUMI_NATIVE_BIN="$PWD/dist/aarch64-apple-darwin/sumi" python3 -m unittest discover -s tests -v
cargo clippy --locked --manifest-path native/Cargo.toml -- -D warnings
python3 native/benchmark.py dist/aarch64-apple-darwin/sumi
```

Python is only a developer dependency for the shared acceptance suite and benchmark.
The standalone check copies the executable out of the checkout and runs it with
an empty tool search path. Tests use real child processes, shared state and locks,
not mirrored Rust/Python unit suites. Performance results are documented in
`.sumi/docs/impl/LF-40/`; they do not imply faster model responses.
