#!/bin/bash
for file in marquees/*.png; do echo "${file}" && mogrify  -resize 400x400\> "${file}"; done
for file in screenshots/*.png; do echo "${file}" && mogrify  -resize 800x800\> "${file}"; done
for file in covers/*.png; do echo "${file}" && mogrify  -resize 500x700\> "${file}"; done
