# PNG Diagram Artifacts

Эта директория содержит PNG-рендеры для Mermaid-диаграмм из `../mermaid/`.

Минимальные требования:

- для каждой актуальной `.mermaid` диаграммы должен существовать одноимённый `.png` файл;
- имена файлов должны совпадать (`01-high-level.mermaid` → `01-high-level.png`).

Для генерации PNG:

```bash
cd docs/02-architecture/diagrams
./render-diagrams.sh
```
