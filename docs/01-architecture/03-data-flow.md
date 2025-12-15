# Data Flow
*Aligned with RULES.md v5.0*

## Обзор

Пайплайны реализуются как направленные ациклические графы (**DAG**) с прохождением данных через Medallion Architecture (§2.1).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐ │
│  │  Lock   │───►│  Extract  │───►│Transform │───►│ Validate │───►│ Load  │ │
│  │ Acquire │    │  (Bronze) │    │          │    │          │    │Silver/│ │
│  └─────────┘    └───────────┘    └──────────┘    └────┬─────┘    │ Gold  │ │
│       │              │                │               │          └───────┘ │
│       │              │                │               │               │     │
│       ▼              ▼                ▼               ▼               ▼     │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│  │Heartbeat│    │ Lineage │    │  Hash    │    │Quarantine│    │Checkpoint│
│  │  (20s)  │    │   Log   │    │ Service  │    │  (DQ)    │    │  Save   │ │
│  └─────────┘    └─────────┘    └──────────┘    └──────────┘    └─────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Medallion Architecture (§2.1)

### Bronze Layer

**Формат**: JSONL + zstd  
**Path**: `bronze/{format_version}/{provider}/{entity}/{date}/`  
**Retention**: 90 дней hot → Archive (S3 Lifecycle)  
**Идемпотентность**: Append-only

```
s3://bioetl/bronze/v1/chembl/activity/2025-12-15/
├── batch_001.jsonl.zst
├── batch_002.jsonl.zst
└── _manifest.json
```

### Silver Layer

**Формат**: Delta Lake (delta-rs)  
**Path**: `silver/{provider}/{entity}/year={YYYY}/month={MM}/`  
**Retention**: Постоянно  
**Идемпотентность**: Merge/Upsert по `primary_key`

**Constraints**:
- Raw Parquet MUST NOT использоваться (§2.1)
- Обязателен ACID
- Time Travel — для Ops, не для DR

### Gold Layer

**Формат**: Delta Lake / Parquet  
**Path**: `gold/{provider}/{entity}_aggregated/`  
**Retention**: Постоянно  
**Идемпотентность**: SCD Type 2 или partition overwrite

---

## Стадии Пайплайна

### 1. Lock Acquisition (§3.3)

```python
async def prepare_run(self):
    # 1. Acquire distributed lock
    lock_key = f"lock:{self.provider}_{self.entity}"
    if self.run_type in ("backfill", "rebuild"):
        lock_key += ":exclusive"  # §2.4.1
    
    await self.lock.acquire(
        blocking=True,
        timeout=300  # --wait-for-lock
    )
    
    # 2. Start heartbeat thread (every 20s)
    self._start_heartbeat()
    
    # 3. Load checkpoint if --resume
    if self.resume:
        self.state = await self.checkpoint.load(self.pipeline_name)
```

### 2. Extract (Bronze)

**Ответственность**: Получение сырых данных, запись в Bronze

```python
async def extract(self) -> None:
    # 1. Fetch from upstream (with Circuit Breaker)
    async for batch in self.client.fetch_batches(self.query):
        # 2. Write to Bronze (JSONL + zstd)
        bronze_path = await self.bronze_writer.write(
            batch,
            path=f"bronze/v1/{self.provider}/{self.entity}/{today}/"
        )
        
        # 3. Record lineage (§2.3)
        await self.lineage_log.record(
            batch_id=batch.id,
            bronze_paths=[bronze_path],
            transform_version=self.transform_version,
            run_params=self.run_params
        )
        
        # 4. Update checkpoint
        await self.checkpoint.save(self.pipeline_name, {
            "last_processed_id": batch.last_id,
            "bronze_path": bronze_path
        })
```

**Circuit Breaker Integration (§3.1.4)**:
```python
if self.circuit_breaker.state == "OPEN":
    raise CircuitOpenError("Provider unhealthy, pipeline paused")

try:
    response = await self.client.fetch(query)
    self.circuit_breaker.record_success()
except RecoverableError:
    self.circuit_breaker.record_failure()
    if self.circuit_breaker.should_trip():
        self.circuit_breaker.open()
```

### 3. Transform

**Ответственность**: Нормализация, расчёт хэшей

```python
async def transform(self, raw_batch: list[dict]) -> list[dict]:
    transformed = []
    
    for record in raw_batch:
        # 1. Normalize values (§2.8.1)
        normalized = self.normalizer.normalize(record)
        
        # 2. Add metadata (§2.4)
        normalized["_run_id"] = self.run_id
        normalized["_run_type"] = self.run_type
        normalized["_source_batch_id"] = self.current_batch_id
        normalized["_ingestion_ts"] = datetime.now(timezone.utc)
        
        # 3. Calculate content hash (§2.8.1)
        hashable_data = {
            k: v for k, v in normalized.items()
            if not k.startswith("_")
        }
        normalized["_content_hash"] = self.hash_service.compute(
            provider=self.provider,
            data=hashable_data
        )
        
        transformed.append(normalized)
    
    return transformed
```

**Normalization Rules (§2.8.1)**:
| Type | Rule |
|------|------|
| NaN/Inf | → `null` |
| Float | `round(val, 10)` |
| Date | ISO format `YYYY-MM-DD` |
| String | `strip()` |

### 4. Validate

**Ответственность**: Pandera-валидация, DQ metrics

```python
async def validate(self, batch: list[dict]) -> ValidationResult:
    df = pl.DataFrame(batch)
    
    # 1. Apply Pandera schema
    try:
        validated_df = self.schema.validate(df, lazy=True)
        errors = []
    except pa.errors.SchemaErrors as e:
        errors = e.failure_cases
    
    # 2. Calculate error rates (§3.1.2)
    record_error_rate = len(errors) / len(df)
    
    # 3. Check thresholds
    if record_error_rate > self.hard_threshold:  # 20%
        raise BatchFailError(f"DQ error rate {record_error_rate:.1%} > 20%")
    
    if record_error_rate > self.soft_threshold:  # 5%
        self.logger.warning(f"DQ warning: {record_error_rate:.1%} errors")
    
    # 4. Route failures to Quarantine (§2.6)
    for error in errors:
        await self.quarantine.write(
            pipeline=self.pipeline_name,
            error_code=error.check,
            payload=json.dumps(error.record)[:65536],
            bronze_batch_id=self.current_batch_id,
            bronze_file_uri=self.current_bronze_path
        )
    
    # 5. Export DQ metrics (§3.4)
    self.metrics.record_validation(
        pipeline=self.pipeline_name,
        total=len(df),
        passed=len(df) - len(errors),
        failed=len(errors)
    )
    
    return ValidationResult(
        valid_records=validated_df.to_dicts(),
        error_count=len(errors)
    )
```

### 5. Load (Silver/Gold)

**Ответственность**: Delta Lake write с Safety Guard

```python
async def load(self, validated: list[dict]) -> None:
    # 1. Safety Guard: validate lock before write (§3.3)
    if not self.lock.validate_ownership():
        raise LockLostError("Lock lost, aborting to prevent split-brain")
    
    # 2. Write to Silver (merge/upsert)
    await self.delta_writer.write(
        data=validated,
        path=self.silver_path,
        mode="merge",
        primary_key=self.primary_key,
        partition_by=self.partition_by
    )
    
    # 3. Optionally write to Gold
    if self.gold_enabled:
        aggregated = self.aggregate(validated)
        await self.delta_writer.write(
            data=aggregated,
            path=self.gold_path,
            mode="overwrite"
        )
    
    # 4. Re-validate lock after write
    if not self.lock.validate_ownership():
        self.logger.error("Lock lost DURING write, data may be inconsistent")
```

### 6. Finalize

```python
async def finalize_run(self) -> RunResult:
    # 1. Delete checkpoint (success)
    await self.checkpoint.delete(self.pipeline_name)
    
    # 2. Release lock
    await self.lock.release()
    
    # 3. Publish final metrics
    self.metrics.publish_run_complete(
        pipeline=self.pipeline_name,
        run_id=self.run_id,
        duration=self.duration,
        records_processed=self.total_records
    )
    
    return RunResult(
        status="SUCCESS",
        records_processed=self.total_records,
        errors=self.total_errors
    )
```

---

## Data Lineage (§2.3)

Оптимизированная схема:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            sys.lineage_log                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ batch_id (PK) │ pipeline │ bronze_paths │ transform_version │ run_params   │
├───────────────┼──────────┼──────────────┼───────────────────┼──────────────┤
│ uuid-001      │ chembl.. │ [s3://...]   │ 1.2.0             │ {incremental}│
└───────────────┴──────────┴──────────────┴───────────────────┴──────────────┘
                     │
                     │ FK: _source_batch_id
                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Silver Record                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ activity_id │ _source_batch_id │ _run_id │ _content_hash │ ...             │
└─────────────┴──────────────────┴─────────┴───────────────┴─────────────────┘
```

**Constraint**: Полные пути к файлам в каждой строке запрещены (избыточность).

---

## Error Handling Flow

### Recoverable Errors (§3.1.3)

```
┌──────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Request  │────►│ Error?  │─No─►│ Success │────►│  Next   │
└──────────┘     └────┬────┘     └─────────┘     └─────────┘
                      │Yes
                      ▼
                 ┌─────────┐
                 │Retry?   │─Yes─► Wait (1s × 2^n + jitter) ──┐
                 │ n < 3   │                                   │
                 └────┬────┘◄──────────────────────────────────┘
                      │No
                      ▼
                 ┌─────────┐
                 │Circuit  │
                 │Breaker  │
                 │ +1 fail │
                 └─────────┘
```

### Data Quality Errors (§2.6)

```
┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│   Record     │────►│  Validate   │─OK─►│   Silver    │
└──────────────┘     └──────┬──────┘     └─────────────┘
                            │Fail
                            ▼
                     ┌──────────────┐
                     │ Error Rate?  │
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         ┌────────┐   ┌──────────┐   ┌─────────┐
         │ < 5%   │   │ 5% - 20% │   │  > 20%  │
         │  OK    │   │ Warning  │   │  FAIL   │
         └───┬────┘   └────┬─────┘   └────┬────┘
             │             │              │
             └─────────────┼──────────────┘
                           ▼
                    ┌─────────────┐
                    │ Quarantine  │
                    │ (per record)│
                    └─────────────┘
```

---

## Checkpoint & Recovery (§5.3.1)

### Checkpoint Save

```python
# Atomicity via S3 ETag (If-Match)
await s3.put_object(
    Bucket="bioetl-checkpoints",
    Key=f"checkpoints/{pipeline_name}.json",
    Body=json.dumps({
        "last_processed_id": last_id,
        "bronze_batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }),
    IfNoneMatch="*"  # Prevent Lost Updates
)
```

### Recovery on Restart

```
┌──────────────┐     ┌─────────────────┐
│ Pipeline     │────►│ Checkpoint      │
│ Start        │     │ exists?         │
└──────────────┘     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │ Yes           │ Yes           │ No
              │ --resume      │ no flag       │
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │ Resume     │  │ Warning    │  │ Fresh      │
       │ from ID+1  │  │ Use flag   │  │ Start      │
       └────────────┘  └────────────┘  └────────────┘
```

---

## Graceful Shutdown (§5.3)

При получении SIGTERM/SIGINT:

```python
async def handle_shutdown(self, signal):
    self.logger.info(f"Received {signal}, initiating graceful shutdown")
    
    # 1. Stop fetching new records
    self._stop_extract = True
    
    # 2. Wait for current batch to complete
    await self._current_batch_task
    
    # 3. Save checkpoint with ETag
    await self.checkpoint.save(self.pipeline_name, self.state)
    
    # 4. Release lock
    await self.lock.release()
    
    # 5. Exit 0
    sys.exit(0)
```

**Guarantees**: At-Least-Once + Дедупликация в Silver (через Content Hash).

---

## End-to-end Сценарий (ChEMBL Activity)

```
1. CLI: bioetl run --pipeline chembl_activity --resume
                    │
2. Lock Acquire ────┼──► Redis SETNX lock:chembl_activity
                    │
3. Checkpoint Load ─┼──► S3 GET checkpoints/chembl_activity.json
                    │    Resume from last_processed_id
                    │
4. Extract ─────────┼──► ChemblClient.fetch_activities()
                    │    └── Circuit Breaker check
                    │    └── Write Bronze (JSONL + zstd)
                    │    └── Lineage Log entry
                    │
5. Transform ───────┼──► NormalizerMixin.normalize()
                    │    └── HashService.compute_content_hash()
                    │    └── Add _run_id, _run_type, _source_batch_id
                    │
6. Validate ────────┼──► ActivityTableSchema.validate()
                    │    └── DQ Metrics export
                    │    └── Quarantine failed records
                    │
7. Load ────────────┼──► Safety Guard: lock.validate_ownership()
                    │    └── Delta Lake merge (Silver)
                    │
8. Finalize ────────┼──► Checkpoint delete
                    │    └── Lock release
                    │    └── RunResult publish
```

---

## Хуки и Режимы

### Pipeline Hooks

| Hook | Timing | Purpose |
|------|--------|---------|
| `prepare_run` | Before extract | Lock, Checkpoint load |
| `finalize_run` | After load | Lock release, Metrics |
| `on_error` | On exception | Cleanup, Alert |

### Execution Modes

| Mode | Behavior |
|------|----------|
| `--dry-run` | Extract/Transform/Validate без записи |
| `--resume` | Продолжить с checkpoint |
| `--ignore-checkpoint` | Игнорировать stale checkpoint |
| `--full-rebuild` | Silver rebuild с нуля |

---

## Связи с другими документами

- **Domain Objects**: [01-domain-objects.md](01-domain-objects.md)
- **ETL Layers**: [02-etl-layers.md](02-etl-layers.md)
- **Physical Layout**: [05-physical-layout.md](05-physical-layout.md)
