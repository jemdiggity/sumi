#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
target=${1:-$(rustc -vV | sed -n 's/^host: //p')}
cargo build --locked --release --manifest-path "$root/native/Cargo.toml" --target "$target"
mkdir -p "$root/dist/$target"
cp "$root/native/target/$target/release/sumi" "$root/dist/$target/sumi"
printf '%s\n' "$root/dist/$target/sumi"
