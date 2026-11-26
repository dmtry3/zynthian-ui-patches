#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ZYNTHIAN_PATCHES_REPO:-https://github.com/dmtry3/zynthian-ui-patches.git}"
REPO_BRANCH="${ZYNTHIAN_PATCHES_BRANCH:-main}"
INSTALL_DIR="${ZYNTHIAN_PATCHES_DIR:-/root/zynthian-ui-patches}"
ZYNTHIAN_UI_DIR="${ZYNTHIAN_UI_DIR:-/zynthian/zynthian-ui}"

SYSTEMD_DROPIN_DIR="/etc/systemd/system/zynthian.service.d"
SYSTEMD_DROPIN_FILE="${SYSTEMD_DROPIN_DIR}/zynthian-ui-patches.conf"

ACTION="apply"
RESTART=1
MANAGE_HOOK=1

usage() {
    cat <<EOF
Usage: $(basename "${0:-install.sh}") [OPTIONS]

Install, check, or revert Zynthian UI patches directly on Zynthian.
Works both from a cloned repository and via curl | bash.
By default, installs a systemd ExecStartPre drop-in so patches are
automatically re-applied after Zynthian updates.

Options:
  --revert, --uninstall    Remove auto-reapply hook and revert all patches
  --status                 Show current patch and auto-reapply hook status
  --no-restart             Do not restart zynthian systemd service
  --no-hook                Do not install or remove systemd auto-reapply hook
  --zynthian-ui-dir PATH   Path to zynthian-ui (default: /zynthian/zynthian-ui)
  --dir PATH               Install/clone directory when run remotely (default: /root/zynthian-ui-patches)
  --branch BRANCH          Git branch to clone/update (default: main)
  -h, --help               Show this help

One-line remote install:
  curl -fsSL https://raw.githubusercontent.com/dmtry3/zynthian-ui-patches/main/install.sh | bash
EOF
}

run_root() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

has_zynthian_service() {
    command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files zynthian.service >/dev/null 2>&1
}

install_systemd_hook() {
    local work_dir="$1"
    if ! has_zynthian_service; then
        echo "Note: systemd zynthian.service not found — skipping auto-reapply hook."
        return 0
    fi

    local expected_content
    expected_content=$(cat <<EOF
# Auto-reapply Zynthian UI patches before zynthian.service starts
# (survives update_zynthian.sh / git checkout . resets)
[Service]
ExecStartPre=-${work_dir}/install.sh --no-restart --no-hook --zynthian-ui-dir ${ZYNTHIAN_UI_DIR}
EOF
)

    if [[ -f "${SYSTEMD_DROPIN_FILE}" ]] && [[ "$(cat "${SYSTEMD_DROPIN_FILE}")" == "${expected_content}" ]]; then
        echo "Auto-reapply systemd hook is already installed (${SYSTEMD_DROPIN_FILE})."
        return 0
    fi

    echo "Installing systemd auto-reapply hook: ${SYSTEMD_DROPIN_FILE}"
    run_root mkdir -p "${SYSTEMD_DROPIN_DIR}"
    printf '%s\n' "${expected_content}" | run_root tee "${SYSTEMD_DROPIN_FILE}" >/dev/null
    run_root systemctl daemon-reload
    echo "Systemd auto-reapply hook enabled."
}

remove_systemd_hook() {
    if [[ ! -f "${SYSTEMD_DROPIN_FILE}" ]]; then
        echo "Auto-reapply systemd hook is not installed."
        return 0
    fi

    echo "Removing systemd auto-reapply hook: ${SYSTEMD_DROPIN_FILE}"
    run_root rm -f "${SYSTEMD_DROPIN_FILE}"
    run_root rmdir "${SYSTEMD_DROPIN_DIR}" 2>/dev/null || true
    if has_zynthian_service; then
        run_root systemctl daemon-reload
    fi
    echo "Systemd auto-reapply hook removed."
}

print_hook_status() {
    if [[ -f "${SYSTEMD_DROPIN_FILE}" ]]; then
        echo "Auto-reapply hook: ENABLED (${SYSTEMD_DROPIN_FILE})"
    else
        echo "Auto-reapply hook: DISABLED"
    fi
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
        --no-hook)
            MANAGE_HOOK=0
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
    status)
        ARGS+=(--status)
        rc=0
        bash "${WORK_DIR}/apply-patch.sh" "${ARGS[@]}" || rc=$?
        print_hook_status
        exit "${rc}"
        ;;
    revert)
        if [[ "${MANAGE_HOOK}" -eq 1 ]]; then
            remove_systemd_hook
        fi
        ARGS+=(--revert)
        if [[ "${RESTART}" -eq 0 ]]; then
            ARGS+=(--no-restart)
        fi
        exec bash "${WORK_DIR}/apply-patch.sh" "${ARGS[@]}"
        ;;
    apply)
        if [[ "${MANAGE_HOOK}" -eq 1 ]]; then
            install_systemd_hook "${WORK_DIR}"
        fi
        if [[ "${RESTART}" -eq 0 ]]; then
            ARGS+=(--no-restart)
        fi
        exec bash "${WORK_DIR}/apply-patch.sh" "${ARGS[@]}"
        ;;
esac
