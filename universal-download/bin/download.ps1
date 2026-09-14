param([Parameter(ValueFromRemainingArguments=$true)][string[]]$args)
Start-Process -FilePath "C:\Python314\pythonw.exe" -ArgumentList @("C:\Just-Projects\universal-download\src\main.py", $args)
