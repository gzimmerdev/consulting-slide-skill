#!/bin/bash
# usage: render.sh out_dir file1.pptx file2.pptx ...  (LibreOffice headless -> PDF)
out="$1"; shift
for f in "$@"; do timeout 400 "/c/Program Files/LibreOffice/program/soffice.exe" -env:UserInstallation=file:///C:/Temp/lo_profile --headless --convert-to pdf --outdir "$out" "$f" >/dev/null 2>&1; echo "done: $f"; done
