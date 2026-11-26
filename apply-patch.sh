#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="${SCRIPT_DIR}/patches/midi-cc-autofocus.patch"
ZYNTHIAN_UI_DIR="/zynthian/zynthian-ui"
REVERT=0
STATUS=0
RESTART=1

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Apply, check, or revert the MIDI CC Auto-Focus patch for zynthian-ui (vangelis).

Options:
  --zynthian-ui-dir PATH   Path to zynthian-ui directory (default: /zynthian/zynthian-ui)
  --revert                 Revert the patch
  --status                 Check whether the patch is applied
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

if [[ ! -f "${PATCH_FILE}" ]]; then
    echo "Patch file not found: ${PATCH_FILE}" >&2
    exit 1
fi

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
    if git apply --reverse --check "${PATCH_FILE}" >/dev/null 2>&1; then
        echo "Status: APPLIED (midi-cc-autofocus.patch)"
        exit 0
    elif git apply --check "${PATCH_FILE}" >/dev/null 2>&1; then
        echo "Status: NOT APPLIED (patch applies cleanly)"
        exit 0
    else
        echo "Status: CONFLICT (patch does not apply cleanly to current tree)" >&2
        exit 2
    fi
fi

CHANGED=0

if [[ "${REVERT}" -eq 1 ]]; then
    if git apply --check "${PATCH_FILE}" >/dev/null 2>&1; then
        echo "Patch is not currently applied in ${ZYNTHIAN_UI_DIR}."
    else
        echo "Checking if patch can be cleanly reverted in ${ZYNTHIAN_UI_DIR}..."
        git apply --reverse --check "${PATCH_FILE}"
        git apply --reverse "${PATCH_FILE}"
        CHANGED=1
        echo "Patch reverted successfully."
    fi
else
    if git apply --reverse --check "${PATCH_FILE}" >/dev/null 2>&1; then
        echo "Patch is already applied in ${ZYNTHIAN_UI_DIR}."
    else
        echo "Checking if patch applies cleanly in ${ZYNTHIAN_UI_DIR}..."
        git apply --check "${PATCH_FILE}"
        git apply "${PATCH_FILE}"
        CHANGED=1
        echo "Patch applied successfully."
    fi
fi

if [[ "${CHANGED}" -eq 1 ]] && command -v python3 >/dev/null 2>&1; then
    echo "Validating Python syntax of patched files..."
    python3 -m py_compile \
        zyngine/zynthian_chain_manager.py \
        zyngui/zynthian_gui_chain_options.py \
        zyngui/zynthian_gui_config.py \
        zyngui/zynthian_gui_control.py
    echo "Python syntax check passed."
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
