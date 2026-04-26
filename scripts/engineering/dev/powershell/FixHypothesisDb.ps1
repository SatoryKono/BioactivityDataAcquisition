$repoPath = 'E:\g-drive\05_AI\github\BioactivityDataAcquisition2'
  $targetScript = Join-Path $repoPath 'scripts\engineering\dev\run_pytest_sharded.sh'
  $tempPython = Join-Path $env:TEMP 'hypothesis_fix.py'

  $pythonCode = @"
  from pathlib import Path

  path = Path(r'$targetScript')
  text = path.read_text()

  if 'default_tmp_hypothesis_database_dir' not in text:
      insert_pos = text.index('normalize_coverage_dir_for_environment()')
      new_block = \"default_tmp_hypothesis_database_dir() {\\n    local repo_name\\n    repo_name=\\\"$(basename \\\"$REPO_ROOT\\\")\\\"\\n    printf '/tmp/%s-hypothesis-db-%s-%s\\\\n' \\\\\\n        \\\"$repo_name\\\" \\\\
  \\n        \\\"$(date +%Y%m%d-%H%M%S)\\\" \\\\\\n        \\\"$$\\\"\\n}\\n\\n\"
      text = text[:insert_pos] + new_block + text[insert_pos:]

  if 'prepare_hypothesis_database_for_environment' not in text:
      insert_pos = text.index('start_log_tailer() {')
      new_block = \"prepare_hypothesis_database_for_environment() {\\n    if [[ -n \\\"${HYPOTHESIS_DATABASE:-}\\\" ]]; then\\n        return 0\\n    fi\\n\\n    if ! is_wsl_mounted_checkout; then\\n        return 0\\n
  fi\\n\\n    HYPOTHESIS_DATABASE=\\\"$(default_tmp_hypothesis_database_dir)\\\"\\n    mkdir -p \\\"$HYPOTHESIS_DATABASE\\\"\\n    export HYPOTHESIS_DATABASE\\n    echo \\\"[run_pytest_sharded][info] Using temp Hypothesis
  database $HYPOTHESIS_DATABASE for mounted WSL checkout $REPO_ROOT\\\" >&2\\n}\\n\\n\"
      text = text[:insert_pos] + new_block + text[insert_pos:]

  needle = 'normalize_coverage_dir_for_environment()\\n'
  replacement = 'normalize_coverage_dir_for_environment()\\n    prepare_hypothesis_database_for_environment\\n'
  if replacement not in text:
      text = text.replace(needle, replacement, 1)

  path.write_text(text)
  print('Hypothesis patch applied')
  "@

  Set-Content -Path $tempPython -Value $pythonCode -Encoding UTF8
  python $tempPython
  Remove-Item $tempPython
