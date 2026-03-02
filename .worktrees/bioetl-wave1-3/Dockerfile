FROM debian:bookworm-slim

LABEL maintainer="Your Organization" \
      description="Cloudflare WARP service container" \
      version="1.0"

# Install dependencies and Cloudflare WARP in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dbus \
    gnupg \
    lsb-release && \
    # Setup Cloudflare GPG key
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | \
    gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg && \
    # Add Cloudflare repository
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/cloudflare-client.list && \
    # Install WARP
    apt-get update && \
    apt-get install -y --no-install-recommends cloudflare-warp && \
    # Clean up apt cache to reduce image size
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    # Create WARP state directory
    mkdir -p /var/lib/cloudflare-warp && \
    chmod 755 /var/lib/cloudflare-warp

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Declare volume mount point
VOLUME ["/var/lib/cloudflare-warp"]

# Improve signal handling for graceful shutdown
STOPSIGNAL SIGTERM

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
