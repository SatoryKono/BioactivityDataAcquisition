# /ci-matrix

**Goal:** Сгенерировать матрицу прогонов CI (smoke/full, with-golden, параллельные шаги).


**Inputs**

- `--pipelines LIST` (required)
- `--modes LIST` (optional): например smoke,full


**Steps**

1) Собрать список задач с зависимостями
2) Сериализовать в формат выбранной CI-системы
3) Проверить баланс по времени/ресурсам


**Constraints**

- Не превышать квоты CI


**Outputs**

- `.ci/matrix.generated.yaml`
- `reports/ci/matrix.md`


**Exit criteria**

- Матрица корректно импортируется и даёт ускорение сборки

