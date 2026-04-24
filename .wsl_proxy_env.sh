#!/usr/bin/env bash
# WSL2 proxy environment — sourced from ~/.bashrc
# Routes WSL2 traffic through Windows host proxy (port 3128)

_WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}')
if [[ -n "$_WIN_HOST_IP" ]]; then
  export http_proxy="http://${_WIN_HOST_IP}:3128"
  export https_proxy="http://${_WIN_HOST_IP}:3128"
  export HTTP_PROXY="$http_proxy"
  export HTTPS_PROXY="$https_proxy"
  export no_proxy="localhost,127.0.0.1,.local"
  export NO_PROXY="$no_proxy"
fi

alias proxy-on='_W=$(/sbin/ip route show default | awk '\''{print $3}'\'') && export http_proxy=http://$_W:3128 https_proxy=http://$_W:3128 HTTP_PROXY=http://$_W:3128 HTTPS_PROXY=http://$_W:3128 && echo "proxy ON via $_W:3128"'
alias proxy-off='unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && echo "proxy OFF"'

# WSL Browser configuration (for antigravity and other tools)
if [[ -f "/mnt/c/Windows/System32/cmd.exe" ]]; then
  export BROWSER='/mnt/c/Windows/System32/cmd.exe /c start'
fi

# Antigravity alias
alias antigravity='python3 -m antigravity'
