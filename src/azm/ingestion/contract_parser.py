import re
import yaml
import pathlib
from typing import Dict, Any, List, Optional
from src.azm.ingestion.universal_ingester import (
    AzmIngestionConfig,
    AzmConceptDef,
    AzmRelationshipDef,
    AzmSchematicViewDef,
    AzmSchematicFieldDef,
    AzmExternalMappingDef
)

def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]) or {}, parts[2]
    return {}, content

def parse_markdown_contracts(semantic_path: str, schematic_path: str) -> AzmIngestionConfig:
    with open(semantic_path, "r", encoding="utf-8") as f:
        semantic_raw = f.read()
    with open(schematic_path, "r", encoding="utf-8") as f:
        schematic_raw = f.read()

    sem_meta, sem_body = parse_frontmatter(semantic_raw)
    sch_meta, sch_body = parse_frontmatter(schematic_raw)

    required = ["source_bs", "namespace_name", "namespace_classification", "contract_version"]
    for req in required:
        if req not in sem_meta:
            raise ValueError(f"Missing '{req}' in semantic contract frontmatter")

    concepts = []
    relationships = []
    external_mappings = []

    concept_blocks = re.findall(r'### Concept: (.*?)\n((?:- \*\*.*?\n)*)', sem_body)
    for c_name, c_body in concept_blocks:
        key_m = re.search(r'- \*\*Semantic Key:\*\* (.*)', c_body)
        type_m = re.search(r'- \*\*Concept Type:\*\* (.*)', c_body)
        def_m = re.search(r'- \*\*Definition:\*\* (.*)', c_body)
        alias_m = re.search(r'- \*\*Aliases:\*\* (.*)', c_body)
        
        if not (key_m and type_m and def_m):
            raise ValueError(f"Concept {c_name} missing required fields in {semantic_path}")
            
        aliases = [a.strip() for a in alias_m.group(1).split(',')] if alias_m and alias_m.group(1).strip() else []
        
        concepts.append(AzmConceptDef(
            semantic_key=key_m.group(1).strip(),
            concept_name=c_name.strip(),
            concept_type=type_m.group(1).strip(),
            definition=def_m.group(1).strip(),
            source_element=f"### Concept: {c_name.strip()}",
            aliases=aliases
        ))

    rel_section = re.search(r'### Relationships\n\n\|.*?\|\n\|[-| ]+\|\n((?:\|.*?\|(?:\n|$))+)', sem_body)
    if rel_section:
        for line in rel_section.group(1).strip().split('\n'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 5:
                relationships.append(AzmRelationshipDef(
                    source_key=parts[0],
                    target_key=parts[1],
                    relationship_type=parts[2],
                    derivation_rule=parts[3],
                    source_element=parts[4]
                ))

    map_section = re.search(r'### External Mappings\n\n\|.*?\|\n\|[-| ]+\|\n((?:\|.*?\|(?:\n|$))+)', sem_body)
    if map_section:
        for line in map_section.group(1).strip().split('\n'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 4:
                external_mappings.append(AzmExternalMappingDef(
                    native_concept_key=parts[0],
                    external_system=parts[1],
                    external_key=parts[2],
                    display_name=parts[3]
                ))

    views = []
    view_blocks = re.findall(r'### View: (.*?)\n- \*\*Description:\*\* (.*?)\n\n\|.*?\|\n\|[-| ]+\|\n((?:\|.*?\|(?:\n|$))+)', sch_body)
    for v_name, v_desc, v_table in view_blocks:
        fields = []
        for line in v_table.strip().split('\n'):
            if not line.strip(): continue
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 6:
                fields.append(AzmSchematicFieldDef(
                    field_name=parts[0],
                    field_type=parts[1],
                    is_derived=parts[2].lower() == 'true',
                    is_channel_field=parts[3].lower() == 'true',
                    mapped_concept_key=parts[4] if parts[4] and parts[4] != 'None' else None,
                    description=parts[5]
                ))
        views.append(AzmSchematicViewDef(
            view_name=v_name.strip(),
            description=v_desc.strip(),
            surface_type="SQL_VIEW",
            fields=fields
        ))

    return AzmIngestionConfig(
        source_bs=sem_meta["source_bs"],
        namespace_name=sem_meta["namespace_name"],
        namespace_classification=sem_meta["namespace_classification"],
        namespace_description=sem_meta.get("namespace_description", ""),
        contract_version=str(sem_meta["contract_version"]),
        semantic_contract_content=semantic_raw,
        schematic_contract_content=schematic_raw,
        semantic_source_element=pathlib.Path(semantic_path).name,
        schematic_source_element=pathlib.Path(schematic_path).name,
        concepts=concepts,
        relationships=relationships,
        views=views,
        external_mappings=external_mappings
    )

def ingest_contracts(semantic_path: str, schematic_path: str, db_url: Optional[str] = None):
    config = parse_markdown_contracts(semantic_path, schematic_path)
    from src.azm.ingestion.universal_ingester import UniversalAzmIngester
    ingester = UniversalAzmIngester(db_url)
    return ingester.ingest(config)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        print(ingest_contracts(sys.argv[1], sys.argv[2]))
