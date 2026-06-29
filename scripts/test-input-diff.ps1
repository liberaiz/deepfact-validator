# 入力差テスト (PowerShell版・bash 不要)
# Usage: pwsh -NoProfile -File scripts/test-input-diff.ps1

$Url = $env:DEEPFACT_URL
if (-not $Url) { $Url = "https://deepfact-validator-kjciocymea-an.a.run.app/api/analyze" }
$OutputDir = "$PSScriptRoot/../test-results"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Invoke-Test {
    param([string]$Name, [string]$Type, [string]$Payload)
    Write-Host "=================================================="
    Write-Host "=== $Name ==="
    Write-Host "type: $Type"
    Write-Host "payload: $($Payload.Substring(0, [Math]::Min(80, $Payload.Length)))..."
    Write-Host "=================================================="
    $body = @{ input_type = $Type; payload = $Payload } | ConvertTo-Json -Compress
    try {
        $res = Invoke-RestMethod -Method Post -Uri $Url -Body $body -ContentType "application/json" -TimeoutSec 60
        $res | ConvertTo-Json -Depth 6 | Out-File "$OutputDir/$Name.json" -Encoding utf8
        $c = $res.credibility
        Write-Host "-- 結果サマリ --"
        Write-Host ("overall: {0} ({1}%)" -f $c.overall_label, [int]($c.overall_score * 100))
        Write-Host ("source : {0:N2}" -f $c.source_credibility)
        Write-Host ("neutral: {0:N2}" -f $c.position_bias)
        Write-Host ("fact   : {0:N2}" -f $c.fact_consistency)
        Write-Host ("obs    : {0}" -f $res.structural_observations.Count)
        Write-Host ("contrar: {0}" -f $res.contrarian_views.Count)
        Write-Host ("primary: {0}" -f $res.primary_sources.Count)
        Write-Host ""
    } catch {
        Write-Host "[ERROR] $_" -ForegroundColor Red
    }
}

Invoke-Test "01-fake-claim" "text" "ウクライナ東部でウクライナ政府軍によるロシア系住民のジェノサイド（集団殺害）が起きていると主張。証拠は示されていないが事実だ。"
Invoke-Test "02-mhlw-primary" "url" "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryouhoken/iryouhoken01/index.html"
Invoke-Test "03-neutral-news" "text" "政府は2026年6月、医療制度改革に関する新たな指針を発表した。指針には診療報酬体系の見直しが含まれており、関係団体からは賛否両論の声が上がっている。厚生労働省によると2027年度から段階的に施行される。"
Invoke-Test "04-hype-ad" "text" "たった3日でガンが消えた！医師も驚愕の奇跡のサプリ、今だけ50%OFF！購入はこちら。副作用なし、すべての癌に効きます。"

Write-Host "=================================================="
Write-Host "全パターン完了。比較表:"
Write-Host "=================================================="
Get-ChildItem "$OutputDir/*.json" | ForEach-Object {
    $name = $_.BaseName
    $obj = Get-Content $_.FullName | ConvertFrom-Json
    $c = $obj.credibility
    "{0,-20} {1,-4} {2,6}%  src={3:N2}  neu={4:N2}  fact={5:N2}" -f $name, $c.overall_label, [int]($c.overall_score * 100), $c.source_credibility, $c.position_bias, $c.fact_consistency
}
