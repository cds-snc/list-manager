#!/bin/bash
input=".github/workflows/scripts/inputs/valid_paths.txt"
while IFS= read -r path
do
  response=$(curl --write-out '%{http_code}' --silent --output /dev/null "$path")
  if [[ $response -eq 204 ]]; then
    exit 1 # Error 204 indicates that the request was blocked by the AWS WAF
  fi
done < "$input"