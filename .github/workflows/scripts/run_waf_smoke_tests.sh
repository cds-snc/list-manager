#!/bin/bash
input=".github/workflows/scripts/inputs/valid_paths.txt"
blocks=0
while IFS= read -r path
do
  response=$(curl --write-out '%{http_code}' --silent --output /dev/null "$path")
  if [[ $response -eq 204 ]]; then
    echo "$path blocked by the AWS WAF"
    ((blocks++)) # Error 204 indicates that the request was blocked by the AWS WAF
  fi
done < "$input"

if [[ $blocks -gt 0 ]]; then
  exit 1
fi