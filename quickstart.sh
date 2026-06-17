#!/bin/bash
# Quick start script for BioETL Docker setup

set -e

echo "========================================="
echo "BioETL Docker Quick Start"
echo "========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo "Detected Windows environment (PowerShell recommended)"
    echo ""
    echo "To set up Docker, run:"
    echo ""
    echo "  # Check Docker installation"
    echo "  .\\docker-setup.ps1 check"
    echo ""
    echo "  # Build the image"
    echo "  .\\docker-setup.ps1 build"
    echo ""
    echo "  # Start all services"
    echo "  .\\docker-setup.ps1 start-full"
    echo ""
    echo "Alternative: Use Makefile commands"
    echo "  make docker-check"
    echo "  make docker-build"
    echo "  make docker-start-full"
    exit 0
fi

echo "Detected Unix-like environment"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker is installed"
docker --version
echo ""

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo "✓ Docker Compose is installed"
docker compose version
echo ""

# Make setup script executable
if [ -f "docker-setup.sh" ]; then
    chmod +x docker-setup.sh
    echo "✓ Setup script is executable"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Build the BioETL image:"
    echo "     ./docker-setup.sh build"
    echo ""
    echo "  2. Start main services:"
    echo "     ./docker-setup.sh start"
    echo ""
    echo "  3. Or start full stack (with all dependencies):"
    echo "     ./docker-setup.sh start-full"
    echo ""
    echo "Available commands:"
    echo "  ./docker-setup.sh check         - Check Docker installation"
    echo "  ./docker-setup.sh build         - Build BioETL image"
    echo "  ./docker-setup.sh start         - Start main services"
    echo "  ./docker-setup.sh start-full    - Start all services"
    echo "  ./docker-setup.sh stop          - Stop main services"
    echo "  ./docker-setup.sh stop-full     - Stop all services"
    echo "  ./docker-setup.sh logs [service]- View logs"
    echo "  ./docker-setup.sh health        - Check health status"
    echo "  ./docker-setup.sh clean         - Remove all resources"
    echo ""
    echo "Or use Makefile commands:"
    echo "  make docker-build"
    echo "  make docker-start-full"
    echo "  make docker-logs"
    echo "  make docker-health"
else
    echo "⚠ docker-setup.sh not found"
fi
