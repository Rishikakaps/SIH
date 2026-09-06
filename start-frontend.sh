#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"
RUNTIME_SRC="/private/tmp/rx-lens-frontend-src"

cd "$FRONTEND"
if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Copying frontend source to fast local runtime path..."
mkdir -p "$RUNTIME_SRC"
rm -rf "$RUNTIME_SRC/app" "$RUNTIME_SRC/.next"
cp "$FRONTEND/package.json" "$RUNTIME_SRC/package.json"
cp "$FRONTEND/package-lock.json" "$RUNTIME_SRC/package-lock.json"
cp "$FRONTEND/tsconfig.json" "$RUNTIME_SRC/tsconfig.json"
cp "$FRONTEND/next.config.js" "$RUNTIME_SRC/next.config.js"
cp "$FRONTEND/next-env.d.ts" "$RUNTIME_SRC/next-env.d.ts"
cp -R "$FRONTEND/app" "$RUNTIME_SRC/app"

cd "$RUNTIME_SRC"
if [ -L node_modules ]; then
  rm node_modules
fi
if [ ! -d node_modules ]; then
  echo "Installing frontend runtime dependencies. This is only needed once..."
  npm install
fi

echo "Starting Rx Lens frontend at http://127.0.0.1:3000"
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
