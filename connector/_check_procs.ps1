$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
    Write-Output ("PID={0} | CMD={1}" -f $_.ProcessId, $_.CommandLine)
}