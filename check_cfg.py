import asyncio

from bioetl.application.services.pipeline_config import PipelineConfigService


async def main():
    try:
        service = PipelineConfigService()
        config = await service.load_config("chembl", "publication")
        print(
            "Silver filters required fields:",
            config.filters.silver_filters.required_fields,
        )
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
