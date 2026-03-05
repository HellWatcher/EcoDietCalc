#!/usr/bin/env bash
# Build EcoDietMod in Release config and upload the DLL to a GitHub release.
# Usage: ./scripts/release-upload.sh [TAG]
#   TAG defaults to the latest git tag.
set -euo pipefail

TAG="${1:-$(git describe --tags --abbrev=0)}"
DLL="mod/EcoDietMod/bin/Release/net8.0/EcoDietMod.dll"

echo "Building Release..."
dotnet build -c Release mod/EcoDietMod/EcoDietMod.csproj -v quiet

echo "Uploading $DLL to release $TAG..."
gh release upload "$TAG" "$DLL" --clobber

echo "Done."
