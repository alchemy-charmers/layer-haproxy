git describe --tags > ./src/VERSION
LAYER_PATH=./layers INTERFACE_PATH=./interfaces charm build ./src --force
