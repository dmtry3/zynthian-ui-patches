#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="${SCRIPT_DIR}/patches"
DEFAULT_PATCHES=(
    "midi-cc-autofocus.patch"
    "launcher-hold-move-clip.patch"
)
SELECTED_PATCHES=()
ZYNTHIAN_UI_DIR="/zynthian/zynthian-ui"
REVERT=0
STATUS=0
RESTART=1

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Apply, check, or revert Zynthian UI patches for zynthian-ui (vangelis).

Options:
  --zynthian-ui-dir PATH   Path to zynthian-ui directory (default: /zynthian/zynthian-ui)
  --patch NAME             Operate only on a specific patch filename (repeatable)
  --revert                 Revert patch(es)
  --status                 Check whether patch(es) are applied
  --no-restart             Do not restart zynthian systemd service
  -h, --help               Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zynthian-ui-dir)
            ZYNTHIAN_UI_DIR="$2"
            shift 2
            ;;
        --patch)
            SELECTED_PATCHES+=("$2")
            shift 2
            ;;
        --revert)
            REVERT=1
            shift
            ;;
        --status)
            STATUS=1
            shift
            ;;
        --no-restart)
            RESTART=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ "${#SELECTED_PATCHES[@]}" -eq 0 ]]; then
    PATCH_LIST=("${DEFAULT_PATCHES[@]}")
else
    PATCH_LIST=("${SELECTED_PATCHES[@]}")
fi

PATCH_FILES=()
for patch_name in "${PATCH_LIST[@]}"; do
    if [[ -f "${patch_name}" ]]; then
        PATCH_FILES+=("${patch_name}")
    elif [[ -f "${PATCHES_DIR}/${patch_name}" ]]; then
        PATCH_FILES+=("${PATCHES_DIR}/${patch_name}")
    elif [[ -f "${PATCHES_DIR}/${patch_name}.patch" ]]; then
        PATCH_FILES+=("${PATCHES_DIR}/${patch_name}.patch")
    else
        echo "Patch file not found: ${patch_name}" >&2
        exit 1
    fi
done

if [[ ! -d "${ZYNTHIAN_UI_DIR}" ]]; then
    echo "zynthian-ui directory not found: ${ZYNTHIAN_UI_DIR}" >&2
    exit 1
fi

cd "${ZYNTHIAN_UI_DIR}"

CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
if [[ -z "${CURRENT_BRANCH}" ]]; then
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
fi
CURRENT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "Target: ${ZYNTHIAN_UI_DIR} (branch: ${CURRENT_BRANCH}, commit: ${CURRENT_COMMIT})"

if [[ "${CURRENT_BRANCH}" != vangelis* && "${CURRENT_BRANCH}" != "unknown" ]]; then
    echo "Warning: expected a 'vangelis' branch of zynthian-ui, found '${CURRENT_BRANCH}'." >&2
fi

if [[ "${STATUS}" -eq 1 ]]; then
    has_conflict=0
    for patch_file in "${PATCH_FILES[@]}"; do
        patch_base="$(basename "${patch_file}")"
        if git apply --reverse --check "${patch_file}" >/dev/null 2>&1; then
            echo "Status: APPLIED (${patch_base})"
        elif git apply --check "${patch_file}" >/dev/null 2>&1; then
            echo "Status: NOT APPLIED (${patch_base} applies cleanly)"
        else
            echo "Status: CONFLICT (${patch_base} does not apply cleanly to current tree)" >&2
            has_conflict=1
        fi
    done
    exit $(( has_conflict ? 2 : 0 ))
fi

CHANGED=0
CHANGED_PATCHES=()

if [[ "${REVERT}" -eq 1 ]]; then
    for (( idx=${#PATCH_FILES[@]}-1; idx>=0; idx-- )); do
        patch_file="${PATCH_FILES[$idx]}"
        patch_base="$(basename "${patch_file}")"
        if git apply --check "${patch_file}" >/dev/null 2>&1; then
            echo "Patch is not currently applied (${patch_base})."
        else
            echo "Checking if ${patch_base} can be cleanly reverted..."
            git apply --reverse --check "${patch_file}"
            git apply --reverse "${patch_file}"
            CHANGED=1
            CHANGED_PATCHES+=("${patch_file}")
            echo "Reverted ${patch_base} successfully."
        fi
    done
else
    for patch_file in "${PATCH_FILES[@]}"; do
        patch_base="$(basename "${patch_file}")"
        if git apply --reverse --check "${patch_file}" >/dev/null 2>&1; then
            echo "Patch is already applied (${patch_base})."
        else
            echo "Checking if ${patch_base} applies cleanly..."
            git apply --check "${patch_file}"
            git apply "${patch_file}"
            CHANGED=1
            CHANGED_PATCHES+=("${patch_file}")
            echo "Applied ${patch_base} successfully."
        fi
    done
fi

if [[ "${CHANGED}" -eq 1 ]] && command -v python3 >/dev/null 2>&1; then
    PY_FILES=()
    while IFS= read -r py_file; do
        if [[ -n "${py_file}" && -f "${py_file}" ]]; then
            PY_FILES+=("${py_file}")
        fi
    done < <(
        for patch_file in "${CHANGED_PATCHES[@]}"; do
            sed -n 's|^+++ b/\(.*\.py\)$|\1|p' "${patch_file}"
        done | sort -u
    )
    if [[ "${#PY_FILES[@]}" -gt 0 ]]; then
        echo "Validating Python syntax of patched files..."
        python3 -m py_compile "${PY_FILES[@]}"
        echo "Python syntax check passed."
    fi
fi

if [[ "${RESTART}" -eq 1 && "${CHANGED}" -eq 1 ]]; then
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files zynthian.service >/dev/null 2>&1; then
        echo "Restarting zynthian service..."
        if [[ "${EUID}" -eq 0 ]]; then
            systemctl restart zynthian
        else
            sudo systemctl restart zynthian
        fi
        echo "zynthian service restarted."
    else
        echo "Note: systemd zynthian.service not found — please restart Zynthian UI manually."
    fi
elif [[ "${RESTART}" -eq 1 && "${CHANGED}" -eq 0 ]]; then
    echo "No changes made; skipping zynthian service restart."
fi
