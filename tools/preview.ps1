# usage: powershell -NoProfile -File tools/preview.ps1 out\a.pptx [out\b.pptx ...]
# Renders every slide with real PowerPoint: out\a.png (1 slide) or out\a_01.png, out\a_02.png ... (several)
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Files)
# one render at a time machine-wide: PowerPoint is a single shared instance
$mx = New-Object System.Threading.Mutex($false, "Global\slidegen_preview"); [void]$mx.WaitOne(300000)
try {
  $app = New-Object -ComObject PowerPoint.Application
  foreach ($f in ($Files | Where-Object { $_ -like "*.pptx" })) {   # ignore stray args
    $full = (Resolve-Path $f).Path
    $pres = $app.Presentations.Open($full, $true, $false, $false)   # read-only, untitled, no window
    $n = $pres.Slides.Count
    for ($i = 1; $i -le $n; $i++) {
      $png = if ($n -eq 1) { [IO.Path]::ChangeExtension($full, '.png') } else { $full -replace '\.pptx$', ('_{0:D2}.png' -f $i) }
      $pres.Slides($i).Export($png, 'PNG', 1600, 900); Write-Output $png
    }
    $pres.Close()
  }
  if ($app.Presentations.Count -eq 0) { $app.Quit() }   # never close the user's open decks
} finally { $mx.ReleaseMutex() }
