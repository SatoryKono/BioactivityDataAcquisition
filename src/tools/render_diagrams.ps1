param(
    [string]$Root = "docs",
    [string]$Background = "white",
    [double]$Scale = 10.0,
    [string]$Theme = "default",
    [string]$Config = ""
)

python "$PSScriptRoot\render_diagrams.py" --root $Root --background $Background --scale $Scale --theme $Theme --config $Config

