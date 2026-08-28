Write-Output "starting sync"
Start-Process -FilePath "E:\github\BioactivityDataAcquisition\.venv-win\Scripts\python.exe" -ArgumentList "-m","scripts.engineering.repo","sync-inventory" -RedirectStandardOutput "E:\github\BioactivityDataAcquisition\sync.log" -RedirectStandardError "E:\github\BioactivityDataAcquisition\sync.err" -NoNewWindow -PassThru | Out-Null
Write-Output "started"
