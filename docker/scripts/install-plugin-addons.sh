#!/usr/bin/env sh
# Install selected acmed issuer plugin packages and addon tooling.
# Usage: install-plugin-addons.sh <sources-root> <plugin-dirs-csv>
# Author: Ruslan Ovsyannikov <rovsyannikov@gmail.com>
# License: MIT

set -eu

SOURCES_ROOT="${1:?sources root is required}"
PLUGIN_DIRS_RAW="${2:-}"
APT_PACKAGE_LIST="/tmp/acmed-plugin-apt-packages.txt"

if [ -z "${PLUGIN_DIRS_RAW}" ]; then
  exit 0
fi

: >"${APT_PACKAGE_LIST}"

split_and_iterate_plugins() {
  old_ifs="$IFS"
  IFS=','
  set -f
  for raw in $PLUGIN_DIRS_RAW; do
    plugin_dir="$(printf '%s' "$raw" | tr -d '[:space:]')"
    if [ -z "$plugin_dir" ]; then
      continue
    fi
    "$@" "$plugin_dir"
  done
  set +f
  IFS="$old_ifs"
}

collect_plugin_metadata() {
  plugin_dir="$1"
  plugin_path="${SOURCES_ROOT}/${plugin_dir}"

  if [ ! -d "$plugin_path" ]; then
    echo "acmed-install-plugin-addons: plugin source not found: ${plugin_path}" >&2
    exit 2
  fi

  if [ ! -f "${plugin_path}/pyproject.toml" ]; then
    echo "acmed-install-plugin-addons: missing pyproject.toml in ${plugin_path}" >&2
    exit 2
  fi

  pip install --no-cache-dir "$plugin_path"

  if [ -f "${plugin_path}/addon/pip-requirements.txt" ]; then
    pip install --no-cache-dir -r "${plugin_path}/addon/pip-requirements.txt"
  fi

  if [ -f "${plugin_path}/addon/apt-packages.txt" ]; then
    awk 'NF && $1 !~ /^#/' "${plugin_path}/addon/apt-packages.txt" >>"${APT_PACKAGE_LIST}"
  fi
}

run_plugin_addon_install() {
  plugin_dir="$1"
  plugin_path="${SOURCES_ROOT}/${plugin_dir}"
  addon_install="${plugin_path}/addon/install.sh"

  if [ -x "$addon_install" ]; then
    ACMED_PLUGIN_PATH="$plugin_path" sh "$addon_install"
  fi
}

split_and_iterate_plugins collect_plugin_metadata

if [ -s "$APT_PACKAGE_LIST" ]; then
  sort -u "$APT_PACKAGE_LIST" -o "$APT_PACKAGE_LIST"
  apt-get update
  xargs apt-get install --yes --no-install-recommends <"$APT_PACKAGE_LIST"
  rm -rf /var/lib/apt/lists/*
fi

split_and_iterate_plugins run_plugin_addon_install

rm -f "$APT_PACKAGE_LIST"
