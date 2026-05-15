from dblp_kgqa.modules.entity_linker.factory import EntityLinkerFactory
from dblp_kgqa.modules.info_extractor.factory import InfoExtractorFactory
from dblp_kgqa.modules.query_executor.factory import QueryExecutorFactory
from dblp_kgqa.modules.query_generator.factory import QueryGeneratorFactory
from dblp_kgqa.modules.relation_linker.factory import RelationLinkerFactory
from dblp_kgqa.pipeline.pipeline import KGQAPipeline, PipelineConfig
from dblp_kgqa.services.registry import ServiceRegistry


class PipelineFactory:
    @staticmethod
    def create(
        config: PipelineConfig, service_registry: ServiceRegistry
    ) -> KGQAPipeline:
        return KGQAPipeline(
            info_extractor=InfoExtractorFactory.create(
                config.info_extractor_config, service_registry
            ),
            entity_linker=EntityLinkerFactory.create(
                config.entity_linker_config, service_registry
            ),
            relation_linker=RelationLinkerFactory.create(
                config.relation_linker_config, service_registry
            ),
            query_generator=QueryGeneratorFactory.create(
                config.query_generator_config, service_registry
            ),
            query_executor=QueryExecutorFactory.create(
                config.query_executor_config, service_registry
            ),
        )
