#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ZYNTHIAN_PATCHES_REPO:-https://github.com/dmtry3/zynthian-ui-patches.git}"
REPO_BRANCH="${ZYNTHIAN_PATCHES_BRANCH:-main}"
INSTALL_DIR="${ZYNTHIAN_PATCHES_DIR:-/root/zynthian-ui-patches}"
ZYNTHIAN_UI_DIR="${ZYNTHIAN_UI_DIR:-/zynthian/zynthian-ui}"

ACTION="apply"
RESTART=1

usage() {
    cat <<EOF
Usage: $(basename "${0:-install.sh}") [OPTIONS]

Install, check, or revert Zynthian UI patches directly on Zynthian.
Works both from a cloned repository and via curl | bash.

Options:
  --revert, --uninstall    Revert all installed patches
  --status                 Show current patch installation status
  --no-restart             Do not restart zynthian systemd service
  --zynthian-ui-dir PATH   Path to zynthian-ui (default: /zynthian/zynthian-ui)
  --dir PATH               Install/clone directory when run remotely (default: /root/zynthian-ui-patches)
  --branch BRANCH          Git branch to clone/update (default: main)
  -h, --help               Show this help

One-line remote install:
  curl -fsSL https://raw.githubusercontent.com/dmtry3/zynthian-ui-patches/main/install.sh | bash
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --revert|--uninstall)
            ACTION="revert"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --no-restart)
            RESTART=0
            shift
            ;;
        --zynthian-ui-dir)
            ZYNTHIAN_UI_DIR="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --branch)
            REPO_BRANCH="$2"
            shift 2
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

SCRIPT_PATH="${BASH_SOURCE[0]:-}"
WORK_DIR=""
if [[ -n "${SCRIPT_PATH}" && -f "${SCRIPT_PATH}" ]]; then
    CANDIDATE_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
    if [[ -f "${CANDIDATE_DIR}/apply-patch.sh" && -d "${CANDIDATE_DIR}/patches" ]]; then
        WORK_DIR="${CANDIDATE_DIR}"
    fi
fi

if [[ -z "${WORK_DIR}" ]]; then
    if ! command -v git >/dev/null 2>&1; then
        echo "Error: git is required to clone ${REPO_URL}" >&2
        exit 1
    fi

    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        echo "Updating existing repository in ${INSTALL_DIR}..."
        git -C "${INSTALL_DIR}" fetch origin "${REPO_BRANCH}"
        git -C "${INSTALL_DIR}" checkout "${REPO_BRANCH}"
        git -C "${INSTALL_DIR}" pull --ff-only origin "${REPO_BRANCH}"
    else
        echo "Cloning ${REPO_URL} (${REPO_BRANCH}) into ${INSTALL_DIR}..."
        mkdir -p "$(dirname "${INSTALL_DIR}")"
        git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
    fi
    WORK_DIR="${INSTALL_DIR}"
fi

ARGS=(--zynthian-ui-dir "${ZYNTHIAN_UI_DIR}")
case "${ACTION}" in
    revert)
        ARGS+=(--revert)
        ;;
    status)
        ARGS+=(--status)
        ;;
esac

if [[ "${RESTART}" -eq 0 ]]; then
    ARGS+=(--no-restart)
fi

exec bash "${WORK_DIR}/apply-patch.sh" "${ARGS[@]}"
