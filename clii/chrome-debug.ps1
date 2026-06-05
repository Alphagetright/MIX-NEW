# Chrome DevTools MCP 启动脚本
# 关掉所有 Chrome -> 用默认 profile + 调试端口重新启动

taskkill /F /IM chrome.exe 2>$null
Start-Sleep -Seconds 2

$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$userData = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=$userData"
)

Start-Sleep -Seconds 4

# 验证
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -UseBasicParsing
    Write-Output "OK - Chrome $($r.Browser) DevTools ready on port 9222"
} catch {
    Write-Output "FAILED - port 9222 not responding"
}
