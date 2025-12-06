# /render-diagrams

**Goal:** Перегенерировать все mermaid-диаграммы (`.mmd`) в `docs/architecture/diagrams` в PNG.

**Inputs**

- `--scale FLOAT` (optional): масштаб PNG, по умолчанию `10`.
- `--backgroundColor COLOR` (optional): фон, по умолчанию `white`.

**Steps**

1) Выполнить из корня репозитория (PowerShell):
   ```
   Get-ChildItem "docs/architecture/diagrams" -Filter *.mmd -Recurse | ForEach-Object {
     $out = $_.FullName -replace '\.mmd$','.png'
     npx.cmd @mermaid-js/mermaid-cli@10.9.1 --input "$($_.FullName)" --output "$out" --backgroundColor white --scale 10
   }
   ```
   При необходимости подставить свои `--scale/--backgroundColor`.
2) Убедиться, что все команды завершились с кодом 0 и PNG обновлены.

**Constraints**

- Не изменять исходные `.mmd` в рамках команды.
- Использовать `@mermaid-js/mermaid-cli@10.9.1` (совместимо с `classDiagram-v2` и init-директивами).
- Запускать в среде без интерактивного ввода (команда должна завершаться автоматически).

**Outputs**

- Обновленные `.png` файлы, соответствующие каждому `.mmd`.

**Exit criteria**

- Код возврата 0; все `.mmd` имеют свежие `.png` без ошибок парсера mermaid.

