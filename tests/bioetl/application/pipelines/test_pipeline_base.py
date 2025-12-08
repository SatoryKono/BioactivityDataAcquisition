"""
Tests for the PipelineBase class.
"""

# pylint: disable=redefined-outer-name, protected-access
from pathlib import Path
from typing import Callable, Iterable
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.contracts import ExtractorABC, LoaderABC
from bioetl.application.pipelines.hooks_impl import (
    ContinueOnErrorPolicyImpl,
    FailFastErrorPolicyImpl,
)
from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext
from bioetl.domain.pipelines.contracts import PipelineHookABC
from bioetl.domain.transform.factories import default_post_transformer
from bioetl.domain.transform.transformers import (
    DatabaseVersionTransformerImpl,
    FulldateTransformerImpl,
    HashColumnsTransformerImpl,
    IndexColumnTransformerImpl,
    TransformerABC,
    TransformerChainImpl,
)
from bioetl.infrastructure.transform.factories import default_hash_service


class CallableExtractor(ExtractorABC):
    """Extractor stub that delegates to a callable."""

    def __init__(self, action: Callable[..., Iterable[pd.DataFrame] | pd.DataFrame]):
        self._action = action
        self.call_count = 0

    def extract(self, **kwargs):
        self.call_count += 1
        return self._action(**kwargs)


class RecordingLoader(LoaderABC):
    """Loader stub that records calls and returns a WriteResult."""

    def __init__(self):
        self.calls: list[tuple[pd.DataFrame, Path, RunContext, list[str] | None]] = []

    def load(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        self.calls.append((df.copy(), output_path, context, column_order))
        return WriteResult(path=output_path, row_count=len(df), duration_sec=0.0)


class SimpleTransformer(TransformerABC):
    """Transformer stub that annotates processed rows."""

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        return df.assign(transformed=True)


class ConcretePipeline(PipelineBase):
    """A concrete implementation of PipelineBase for testing."""

    def __init__(
        self,
        *args,
        extractor: ExtractorABC | None = None,
        transformer: TransformerABC | None = None,
        loader: LoaderABC | None = None,
        **kwargs,
    ):
        super().__init__(
            *args,
            extractor=extractor,
            transformer=transformer,
            loader=loader,
            **kwargs,
        )

    def extract(self, **kwargs):
        """Mock extraction returning sample data."""
        if self._extractor is not None:
            return self._extractor.extract(**kwargs)
        return pd.DataFrame({"id": [1, 2], "val": ["x", "y"]})

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mock transformation adding a column."""
        if self._transformer is not None:
            return self._transformer.apply(df)
        df["transformed"] = True
        return df

    def write(self, df: pd.DataFrame, output_path: Path, context: RunContext):
        return super().write(df, output_path, context)


class DatasetPipeline(PipelineBase):
    """Pipeline that operates on a provided in-memory dataset."""

    def __init__(
        self,
        *args,
        dataset: pd.DataFrame,
        extractor: ExtractorABC | None = None,
        transformer: TransformerABC | None = None,
        loader: LoaderABC | None = None,
        **kwargs,
    ):
        self._dataset = dataset
        extractor_impl = extractor or CallableExtractor(lambda **_: [dataset.copy()])
        transformer_impl = transformer or SimpleTransformer()
        super().__init__(
            *args,
            extractor=extractor_impl,
            transformer=transformer_impl,
            loader=loader,
            **kwargs,
        )

    def extract(self, **kwargs):
        _ = kwargs
        return self._extractor.extract(**kwargs)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._transformer.apply(df)

    def write(self, df: pd.DataFrame, output_path: Path, context: RunContext):
        return super().write(df, output_path, context)


@pytest.fixture
def hash_service():
    return default_hash_service()


@pytest.fixture
def default_extractor():
    return CallableExtractor(
        lambda **_: [pd.DataFrame({"id": [1, 2], "val": ["x", "y"]})]
    )


@pytest.fixture
def default_transformer():
    return SimpleTransformer()


@pytest.fixture
def mock_loader():
    return RecordingLoader()


@pytest.mark.unit
def test_pipeline_run_success(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    tmp_path,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Test a successful pipeline run."""
    # Arrange
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )

    output_path = tmp_path / "output.parquet"

    # Act
    result = pipeline.run(output_path=output_path)

    # Assert
    assert result.success
    assert result.row_count == 2
    assert len(result.stages) == 4  # extract, transform, validate, write

    # Verify logger calls
    mock_logger.info.assert_any_call("Pipeline started", run_id=result.run_id)

    # Verify write called
    assert len(mock_loader.calls) == 1


@pytest.mark.unit
def test_pipeline_dry_run(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    tmp_path,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Test a dry run of the pipeline."""
    # Arrange
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )

    # Act
    result = pipeline.run(output_path=tmp_path, dry_run=True)

    # Assert
    assert result.success

    stage_names = [s.stage_name for s in result.stages]
    assert "extract" in stage_names
    assert "transform" in stage_names
    assert "validate" in stage_names
    assert "write" not in stage_names

    assert mock_loader.calls == []


@pytest.mark.unit
def test_pipeline_hooks(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Test that hooks are called correctly."""
    # Arrange
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )
    mock_hook = MagicMock(spec=PipelineHookABC)
    pipeline.register_hook(mock_hook)

    # Act
    pipeline.run(Path("dummy"), dry_run=True)

    # Assert lifecycle hooks (extract, transform, validate)
    assert mock_hook.on_stage_start.call_count >= 3
    assert mock_hook.on_stage_end.call_count >= 3

    # Check arguments for one call
    args, _ = mock_hook.on_stage_start.call_args_list[0]
    assert args[0] == "extract"


@pytest.mark.unit
def test_pipeline_error_hooks(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Test that error hooks are called on failure."""
    # Arrange
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )
    mock_hook = MagicMock(spec=PipelineHookABC)
    pipeline.register_hook(mock_hook)

    # Mock extract to fail
    pipeline._extractor = CallableExtractor(
        lambda **_: (_ for _ in ()).throw(ValueError("Extraction failed"))
    )

    # Act & Assert
    with pytest.raises(PipelineStageError) as exc_info:
        pipeline.run(Path("dummy"))

    assert isinstance(exc_info.value.cause, ValueError)
    assert str(exc_info.value.cause) == "Extraction failed"
    assert exc_info.value.stage == "extract"

    # Verify hook called
    assert mock_hook.on_error.call_count >= 1
    args, _ = mock_hook.on_error.call_args
    assert args[0] == "extract"  # stage name
    assert isinstance(args[1], PipelineStageError)
    assert args[1].stage == "extract"


@pytest.mark.unit
def test_error_policy_skip_stage(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    tmp_path,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Пайплайн продолжает работу при политике SKIP."""

    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        error_policy=ContinueOnErrorPolicyImpl(),
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )
    pipeline._extractor = CallableExtractor(
        lambda **_: (_ for _ in ()).throw(ValueError("boom"))
    )

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.row_count == 0


@pytest.mark.unit
def test_error_policy_retry(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    tmp_path,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Пайплайн повторяет стадию при политике RETRY."""

    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        error_policy=ContinueOnErrorPolicyImpl(max_retries=1),
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )

    outcomes = iter([ValueError("temporary"), pd.DataFrame({"id": [1]})])

    def flaky_extract(**_):
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    pipeline._extractor = CallableExtractor(flaky_extract)

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.row_count == 1
    assert pipeline._extractor.call_count == 2


@pytest.mark.unit
def test_error_policy_retry_callback_and_skip(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Политика RETRY вызывает on_retry и пропускает стадию после лимита."""
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        error_policy=ContinueOnErrorPolicyImpl(max_retries=1),
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )

    attempts = {"count": 0}

    def failing_action():
        attempts["count"] += 1
        raise ValueError("unstable")

    on_retry = MagicMock()
    context = RunContext(
        entity_name=mock_config.entity_name,
        provider=pipeline._provider_id.value,  # noqa: SLF001
    )

    result_df = pipeline._runtime_manager.execute_stage(  # noqa: SLF001
        "extract",
        context,
        failing_action,
        on_retry=on_retry,
    )

    assert isinstance(result_df, pd.DataFrame)
    assert result_df.empty
    assert attempts["count"] == 2
    on_retry.assert_called_once()
    last_error = pipeline._runtime_manager.last_error  # noqa: SLF001
    assert last_error is not None
    assert last_error.attempt == 2


@pytest.mark.unit
def test_error_policy_failfast_raises(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    tmp_path,
    hash_service,
    default_extractor,
    default_transformer,
):
    """FailFast останавливает пайплайн при первой ошибке."""
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        error_policy=FailFastErrorPolicyImpl(),
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )
    pipeline._extractor = CallableExtractor(
        lambda **_: (_ for _ in ()).throw(ValueError("boom"))
    )

    with pytest.raises(PipelineStageError):
        pipeline.run(output_path=tmp_path, dry_run=True)
    assert pipeline._extractor.call_count == 1


@pytest.mark.unit
def test_hashing_logic(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    hash_service,
):
    """Test different scenarios for business key hashing."""
    _ = (
        mock_config,
        mock_logger,
        mock_validation_service,
        mock_loader,
    )
    transformer = HashColumnsTransformerImpl(hash_service, ["id"])
    df = pd.DataFrame({"id": [1], "val": ["x"]})
    res = transformer.apply(df)
    assert "hash_row" in res.columns
    assert "hash_business_key" in res.columns
    assert res["hash_business_key"].iloc[0] is not None

    transformer_missing = HashColumnsTransformerImpl(
        hash_service,
        ["missing_col"],
    )
    res_missing = transformer_missing.apply(df)
    assert res_missing["hash_business_key"].iloc[0] is None

    transformer_empty = HashColumnsTransformerImpl(
        hash_service,
        [],
    )
    res_empty = transformer_empty.apply(df)
    assert res_empty["hash_business_key"].iloc[0] is None


@pytest.mark.unit
def test_pipeline_dry_run_metadata_and_stages(
    pipeline_test_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    small_pipeline_df,
    tmp_path,
    hash_service,
):
    """Dry-run returns accurate stage info and metadata."""
    pipeline = DatasetPipeline(
        config=pipeline_test_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        dataset=small_pipeline_df,
    )

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.output_path is None
    assert not result.errors
    _assert_stages(
        result,
        expected_names=["extract", "transform", "validate"],
        expected_count=len(small_pipeline_df),
    )
    _assert_dry_run_meta(
        result, pipeline_test_config, expected_count=len(small_pipeline_df)
    )


@pytest.mark.unit
def test_post_transformer_factory_alignment(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_loader,
    mock_metadata_builder,
    hash_service,
    default_extractor,
    default_transformer,
):
    """Container и PipelineBase собирают идентичную цепочку
    пост-трансформеров."""

    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        loader=mock_loader,
        hash_service=hash_service,
        metadata_builder=mock_metadata_builder,
        extractor=default_extractor,
        transformer=default_transformer,
    )

    factory_transformer = default_post_transformer(
        hash_service=hash_service,
        business_key_fields=mock_config.hashing.business_key_fields,
        version_provider=pipeline.get_version,
    )

    pipeline_signature = _extract_chain_signature(pipeline._post_transformer)
    container_signature = _extract_chain_signature(factory_transformer)

    assert pipeline_signature == container_signature


def _assert_stages(
    result,
    *,
    expected_names: list[str],
    expected_count: int,
) -> None:
    assert [stage.stage_name for stage in result.stages] == expected_names
    assert [stage.records_processed for stage in result.stages] == [
        expected_count for _ in expected_names
    ]
    assert all(stage.errors == [] for stage in result.stages)
    assert all(stage.duration_sec >= 0 for stage in result.stages)


def _assert_dry_run_meta(
    result,
    config,
    *,
    expected_count: int,
) -> None:
    meta = result.meta
    assert meta["dry_run"] is True
    assert meta["row_count"] == expected_count
    assert meta["provider"] == config.provider
    assert meta["entity"] == config.entity_name


def _extract_chain_signature(transformer: TransformerABC) -> list[tuple]:
    assert isinstance(transformer, TransformerChainImpl)

    signature: list[tuple] = []
    components = transformer._transformers  # type: ignore[attr-defined]
    for component in components:
        if isinstance(component, HashColumnsTransformerImpl):
            hash_service = component._hash_service  # type: ignore[attr-defined]
            business_key_fields = (
                component._business_key_fields  # type: ignore[attr-defined]
            )
            signature.append(
                (
                    component.__class__.__name__,
                    hash_service,
                    business_key_fields,
                )
            )
            continue

        if isinstance(component, IndexColumnTransformerImpl):
            hash_service = component._hash_service  # type: ignore[attr-defined]
            signature.append((component.__class__.__name__, hash_service))
            continue

        if isinstance(component, DatabaseVersionTransformerImpl):
            hash_service = component._hash_service  # type: ignore[attr-defined]
            version = component._database_version_provider()  # type: ignore[attr-defined]
            signature.append((component.__class__.__name__, hash_service, version))
            continue

        if isinstance(component, FulldateTransformerImpl):
            hash_service = component._hash_service  # type: ignore[attr-defined]
            signature.append((component.__class__.__name__, hash_service))
            continue

    return signature
