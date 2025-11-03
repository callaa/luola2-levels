#/bin/sh

set -e

mkdir -p luola2
for i in src/*.toml; do
	./ora2level.py $i
done
