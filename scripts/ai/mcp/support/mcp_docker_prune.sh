#!/usr/bin/env bash
# Drop exited MCP containers matching IMAGE_MATCH. Never touch bioetl-*.
remove_mcp_exited_containers() {
  local image_match="${1:?image match required}"
  local id name image
  while IFS= read -r id; do
    [[ -z "${id}" ]] && continue
    name="$(docker inspect --format '{{.Name}}' "${id}" 2>/dev/null | sed 's#^/##')"
    image="$(docker inspect --format '{{.Config.Image}}' "${id}" 2>/dev/null || true)"
    case "${name}" in
      bioetl|bioetl-neo4j|bioetl-*) continue ;;
    esac
    case "${image}" in
      *"${image_match}"*) docker rm -f "${id}" >/dev/null 2>&1 || true ;;
    esac
  done < <(docker ps -aq --filter 'status=exited' 2>/dev/null || true)
}
