#!/usr/bin/env bash
# Drop exited MCP containers matching IMAGE_MATCH. Never touch bioetl-*.
# Set BIOETL_MCP_PRUNE_DRY_RUN=1 to print matching ids without docker rm.
remove_mcp_exited_containers() {
  local image_match="${1:?image match required}"
  local dry_run="${BIOETL_MCP_PRUNE_DRY_RUN:-0}"
  local id name image
  while IFS= read -r id; do
    [[ -z "${id}" ]] && continue
    name="$(docker inspect --format '{{.Name}}' "${id}" 2>/dev/null | sed 's#^/##')"
    image="$(docker inspect --format '{{.Config.Image}}' "${id}" 2>/dev/null || true)"
    case "${name}" in
      bioetl|bioetl-neo4j|bioetl-*) continue ;;
      *)
        case "${image}" in
          *"${image_match}"*)
            if [[ "${dry_run}" == "1" ]]; then
              printf 'dry-run: would docker rm -f %s name=%s image=%s\n' "${id}" "${name}" "${image}" >&2
            else
              docker rm -f "${id}" >/dev/null 2>&1 || true
            fi
            ;;
          *) ;;
        esac
        ;;
    esac
  done < <(docker ps -aq --filter 'status=exited' 2>/dev/null || true)
  return 0
}
