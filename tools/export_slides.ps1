# usage: powershell -NoProfile -File tools/export_slides.ps1 jobs.json
# jobs.json (utf8): [{"deck":"<abs path>","slides":[{"n":3,"png":"<abs path>"}]}]. Exports 1600x900 PNGs via PowerPoint, read-only, no window.
param([string]$JobFile)
$jobs = Get-Content -Raw -Encoding UTF8 $JobFile | ConvertFrom-Json
$app = New-Object -ComObject PowerPoint.Application
foreach ($j in $jobs) {
  try {
    $pres = $app.Presentations.Open($j.deck, $true, $false, $false)
    foreach ($s in $j.slides) {
      try { $pres.Slides($s.n).Export($s.png, 'PNG', 1600, 900) } catch { Write-Output ("FAIL`t" + $j.deck + "`t" + $s.n + "`t" + $_.Exception.Message) }
    }
    $pres.Close()
  } catch { Write-Output ("FAIL`t" + $j.deck + "`t*`t" + $_.Exception.Message) }
}
$app.Quit()
