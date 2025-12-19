<#
.SYNOPSIS
    BioETL Pipeline Runner
.DESCRIPTION
    Запуск пайплайнов BioETL с правильной настройкой окружения.
    Переопределяет PYTHONPATH для изоляции от других проектов.
.EXAMPLE
    .\run.ps1 run --pipeline chembl_activity --limit 10
    .\run.ps1 --help
#>

param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Переопределяем PYTHONPATH на текущий проект
$env:PYTHONPATH = "$PSScriptRoot\src"

# Запускаем bioetl CLI
& "$PSScriptRoot\.venv\Scripts\bioetl.exe" @Arguments
