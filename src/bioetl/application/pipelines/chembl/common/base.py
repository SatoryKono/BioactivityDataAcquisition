from bioetl.application.pipelines.chembl.base import ChemblPipelineBase

class ChemblCommonPipeline(ChemblPipelineBase):
    """
    Base class for common ChEMBL pipelines.
    Currently just an alias for ChemblPipelineBase but allows for future extension
    common to simple entities (like target, assay, etc).
    """
    pass

