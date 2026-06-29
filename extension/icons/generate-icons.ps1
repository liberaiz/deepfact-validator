# DeepFact Validator Extension Icons Generator
# Liberaiz brand: navy (#1B2A4E) + gold (#C9A55C) + paper (#F8F6F1)

Add-Type -AssemblyName System.Drawing

$sizes = @(16, 48, 128)
$dir = $PSScriptRoot

foreach ($size in $sizes) {
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

    $g.Clear([System.Drawing.Color]::Transparent)

    # Navy filled circle
    $navy = [System.Drawing.Color]::FromArgb(255, 27, 42, 78)
    $brushNavy = New-Object System.Drawing.SolidBrush $navy
    $g.FillEllipse($brushNavy, 0, 0, $size, $size)

    # Gold inner ring
    $pad = [int]($size / 8)
    $gold = [System.Drawing.Color]::FromArgb(255, 201, 165, 92)
    $penWidth = [Math]::Max(1, [int]($size / 32))
    $pen = New-Object System.Drawing.Pen $gold, $penWidth
    $g.DrawEllipse($pen, $pad, $pad, $size - 2*$pad, $size - 2*$pad)

    # Center letter D
    $fontSize = [float]($size * 0.55)
    $font = New-Object System.Drawing.Font ("Arial", $fontSize, [System.Drawing.FontStyle]::Bold)
    $paper = [System.Drawing.Color]::FromArgb(255, 248, 246, 241)
    $textBrush = New-Object System.Drawing.SolidBrush $paper
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $rect = New-Object System.Drawing.RectangleF 0, 0, $size, $size
    $g.DrawString("D", $font, $textBrush, $rect, $format)

    $path = Join-Path $dir "icon$size.png"
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)

    $g.Dispose()
    $bmp.Dispose()
    $font.Dispose()
    $brushNavy.Dispose()
    $textBrush.Dispose()
    $pen.Dispose()

    Write-Output "Created: $path"
}
