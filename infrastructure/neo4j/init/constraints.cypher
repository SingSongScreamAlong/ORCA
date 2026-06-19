// ORCA Neo4j constraints and indexes — the relationship graph projection.
//
// Neo4j stores entities as nodes and relationships as edges, mirroring the
// authoritative relational record in PostgreSQL. These constraints keep the
// projection clean. Apply with:
//
//   cypher-shell -u neo4j -p <password> -f constraints.cypher

// Each entity node is unique by its id (the PostgreSQL entity id).
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Index entity value for lookups ("what else shares this phone number?").
CREATE INDEX entity_value_index IF NOT EXISTS
FOR (e:Entity) ON (e.value);

CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.entity_type);

// Relationship edges carry the relational relationship id so the projection stays
// reconcilable with PostgreSQL.
CREATE INDEX related_id_index IF NOT EXISTS
FOR ()-[r:RELATED]-() ON (r.id);
