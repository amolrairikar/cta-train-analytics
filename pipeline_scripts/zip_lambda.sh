#!/bin/bash

# Usage: ./create_lambda.sh <function_name> <handler_filename> <source_path>

# Set script to fail on error
set -e

# Extract arguments
FUNCTION_NAME=$1
HANDLER_FILENAME=$2
SOURCE_PATH=$(realpath "$3")

# Define directory paths
BUILD_DIR="$SOURCE_PATH/build"
echo "Build dir: $BUILD_DIR"
ZIP_PATH="$SOURCE_PATH/${FUNCTION_NAME}.zip"
echo "Zip path: $ZIP_PATH"
REQUIREMENTS_PATH="$SOURCE_PATH/requirements.txt"
echo "Requirements path: $REQUIREMENTS_PATH"
HANDLER_PATH="$SOURCE_PATH/$HANDLER_FILENAME"
echo "Handler path: $HANDLER_PATH"
SITE_PACKAGES_DIR="$BUILD_DIR/python"
echo "Site packages path: $SITE_PACKAGES_DIR"

# Clean build directory
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$SITE_PACKAGES_DIR"

# Install dependencies
pip install -r "$REQUIREMENTS_PATH" -t "$SITE_PACKAGES_DIR"

# Copy handler file
cp "$HANDLER_PATH" "$BUILD_DIR/"

# Create zip file
cd "$SITE_PACKAGES_DIR"
zip -r "$ZIP_PATH" . > /dev/null
cd "$BUILD_DIR"
zip -g "$ZIP_PATH" "$HANDLER_FILENAME" > /dev/null

echo "Lambda package created at: $ZIP_PATH"