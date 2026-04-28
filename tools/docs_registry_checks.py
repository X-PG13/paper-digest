from __future__ import annotations

from pathlib import Path

from tools.docs_contracts import MAINTAINER_DOC_REGISTRY_CONTRACT
from tools.docs_findings import DocsCheckFinding
from tools.docs_links import (
    extract_markdown_link_targets_from_lines,
    extract_repository_reference_targets_from_lines,
)
from tools.docs_parser import (
    get_markdown_section_lines,
    iter_visible_lines,
)
from tools.docs_sources import collect_text_source_origins, resolve_repository_path


def check_maintainer_doc_registry(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []

    readme_source = MAINTAINER_DOC_REGISTRY_CONTRACT.readme_source
    registry_source = MAINTAINER_DOC_REGISTRY_CONTRACT.registry_source
    guide_source = MAINTAINER_DOC_REGISTRY_CONTRACT.guide_source
    subject_origins = collect_text_source_origins(
        root,
        (readme_source, registry_source, guide_source),
    )

    readme = resolve_repository_path(root, readme_source.path)
    readme_docs_map = get_markdown_section_lines(readme, readme_source.heading)
    if readme_docs_map is None:
        errors.append(
            DocsCheckFinding(
                message=f"missing section '{readme_source.heading}'",
                path=readme_source.path,
                line=subject_origins[readme_source.label].line,
                end_line=subject_origins[readme_source.label].end_line,
            )
        )
        return errors

    hub = resolve_repository_path(root, registry_source.path)
    hub_source_of_truth = get_markdown_section_lines(hub, registry_source.heading)
    if hub_source_of_truth is None:
        errors.append(
            DocsCheckFinding(
                message=f"missing section '{registry_source.heading}'",
                path=registry_source.path,
                line=subject_origins[registry_source.label].line,
                end_line=subject_origins[registry_source.label].end_line,
            )
        )
        return errors

    guide = resolve_repository_path(root, guide_source.path)
    guide_governance = get_markdown_section_lines(guide, guide_source.heading)
    if guide_governance is None:
        errors.append(
            DocsCheckFinding(
                message=f"missing section '{guide_source.heading}'",
                path=guide_source.path,
                line=subject_origins[guide_source.label].line,
                end_line=subject_origins[guide_source.label].end_line,
            )
        )
        return errors

    readme_targets = extract_markdown_link_targets_from_lines(
        root,
        readme,
        readme_docs_map,
    )
    hub_targets = extract_repository_reference_targets_from_lines(hub_source_of_truth)
    guide_targets = extract_repository_reference_targets_from_lines(
        [line for _, line in iter_visible_lines(guide)]
    )

    missing_from_readme = sorted(hub_targets - readme_targets)
    if missing_from_readme:
        errors.append(
            DocsCheckFinding(
                message=(
                    f"{registry_source.label} references docs that are missing from "
                    f"{readme_source.label}: " + ", ".join(missing_from_readme)
                ),
                path=readme_source.path,
                line=subject_origins[readme_source.label].line,
                end_line=subject_origins[readme_source.label].end_line,
            )
        )

    missing_from_guide = sorted(hub_targets - guide_targets)
    if missing_from_guide:
        errors.append(
            DocsCheckFinding(
                message=(
                    f"{guide_source.path} is missing source-of-truth docs "
                    f"referenced by {registry_source.label}: "
                    + ", ".join(missing_from_guide)
                ),
                path=guide_source.path,
                line=subject_origins[guide_source.label].line,
                end_line=subject_origins[guide_source.label].end_line,
            )
        )

    required_readme_targets = set(
        MAINTAINER_DOC_REGISTRY_CONTRACT.required_readme_targets
    )
    missing_entry_points = sorted(required_readme_targets - readme_targets)
    if missing_entry_points:
        errors.append(
            DocsCheckFinding(
                message=(
                    f"{readme_source.label} is missing maintainer entry-point docs: "
                    + ", ".join(missing_entry_points)
                ),
                path=readme_source.path,
                line=subject_origins[readme_source.label].line,
                end_line=subject_origins[readme_source.label].end_line,
            )
        )

    return errors
