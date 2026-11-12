#!/bin/bash
# usage: tools/preview.sh out/file.pptx -> out/file.pdf + out/file.png (LibreOffice headless, 110 dpi)
# Uses soffice.bin directly (soffice.exe is a launcher that hangs under auto-update) and a throwaway profile.
f="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; d=$(dirname "$f"); b=$(basename "$f" .pptx)
P="C:\Program Files\LibreOffice\program"
cd "$P" && timeout 150 ./soffice.bin "-env:UserInstallation=file:///C:/Temp/lo_prev" --headless --convert-to pdf --outdir "$(cygpath -w "$d")" "$(cygpath -w "$f")" 2>&1 | tail -2
py -3 -I -c "import fitz,sys;fitz.open(sys.argv[1]).load_page(0).get_pixmap(dpi=110).save(sys.argv[2])" "$d/$b.pdf" "$d/$b.png" && ls "$d/$b.png"
