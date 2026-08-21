#!/usr/bin/env bash
# Drop exited MCP containers matching IMAGE_MATCH. Never touch bioetl-*.
# Default is dry-run. Set MCP_DOCKER_PRUNE_APPLY=1 or pass apply=1 as $2.
remove_mcp_exited_containers() {
  local image_match="${1:?image match required}"
  local apply="${2:-${MCP_DOCKER_PRUNE_APPLY:-0}}"
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
            echo "mcp-docker-prune: id=${id} name=${name} image=${image} apply=${apply}"
            if [[ "${apply}" == "1" ]]; then
              docker rm -f "${id}"
            else
              echo "mcp-docker-prune: dry-run (set MCP_DOCKER_PRUNE_APPLY=1 to remove)"
            fi
            ;;
          *) ;;
        esac
        ;;
    esac
  done < <(docker ps -aq --filter 'status=exited' 2>/dev/null || true)
  return 0
}
