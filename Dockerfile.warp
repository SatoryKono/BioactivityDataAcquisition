# Cloudflare Warp client container
FROM debian:12-slim

WORKDIR /app

# Install Warp and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    iputils-ping \
    iproute2 \
    && curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-client.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    cloudflare-warp \
    && groupadd -r warp \
    && useradd -r -g warp warp \
    && mkdir -p /var/lib/cloudflare-warp \
    && chown -R warp:warp /var/lib/cloudflare-warp \
    && rm -rf /var/lib/apt/lists/*

# Set logging
ENV RUST_LOG=warn

# Run as the non-root service user by default.
USER warp

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["warp-cli connect && exec sleep infinity"]
