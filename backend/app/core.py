"""Legacy compatibility facade.

The backend now uses focused application modules. This module remains only to
preserve the old import surface for legacy callers.
"""

from .application.attachments import insert_attachment, read_attachment
from .application.imports import (
    add_features_from_dataframe,
    add_organisms_from_dataframe,
    get_importable_plasmids,
    import_plasmids,
)
from .application.legacy_mutations import (
    add_gmo,
    destroy_gmo,
    duplicate_plasmid,
    update_aliases,
    update_cassettes,
)
from .application.lookups import get_feature_annotations, get_organism_short_names
from .application.normalization import sanitize_annotation
from .application.reports import (
    export_all_features,
    export_all_organisms,
    generate_formblatt,
    generate_plasmid_list,
    get_used_features_df,
    get_used_organisms_df,
)
from .application.validation import check_features, check_organisms, check_plasmids

__all__ = [
    "add_features_from_dataframe",
    "add_gmo",
    "add_organisms_from_dataframe",
    "check_features",
    "check_organisms",
    "check_plasmids",
    "destroy_gmo",
    "duplicate_plasmid",
    "export_all_features",
    "export_all_organisms",
    "generate_formblatt",
    "generate_plasmid_list",
    "get_feature_annotations",
    "get_importable_plasmids",
    "get_organism_short_names",
    "get_used_features_df",
    "get_used_organisms_df",
    "import_plasmids",
    "insert_attachment",
    "read_attachment",
    "sanitize_annotation",
    "update_aliases",
    "update_cassettes",
]
