fpath = "tests/intelligence_domains/ndr/test_ndr_orchestration.py"
with open(fpath, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("        mock_id_resolver =") or \
       line.startswith("        mock_id_resolver.resolve") or \
       line.startswith("        mock_cem_resolver =") or \
       line.startswith("        rabta =") or \
       line.startswith("            id_resolver") or \
       line.startswith("            cem_resolver") or \
       line.startswith("            classifier") or \
       line.startswith("            memory_provider") or \
       line.startswith("        )") or \
       line.startswith("        query =") or \
       line.startswith("        response =") or \
       line.startswith("            query=") or \
       line.startswith("            id_urn=") or \
       line.startswith("            cem_urn=") or \
       line.startswith("            auth_context=") or \
       line.startswith("            session_id=") or \
       line.startswith("        assert response"):
        new_lines.append(line[4:])
    else:
        new_lines.append(line)

with open(fpath, "w") as f:
    f.writelines(new_lines)
