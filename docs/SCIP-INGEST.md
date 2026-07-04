# SCIP ingest (v0.2)

Stubborn reads standard SCIP indexes produced by industry indexers.

## Supported formats

| Extension | Producer examples | Notes |
|-----------|-------------------|-------|
| `.scip` | scip-java, scip-clang, rust-analyzer | Streaming protobuf (default) |
| `.scip.ndjson` | scip-java (`TYPED_NDJSON`) | One partial `Index` JSON object per line |
| `.json` | Stubborn fixtures | Test / bootstrap only |

## scip-java workflow

```bash
# At the root of a Maven/Gradle Java project
scip-java index
# → writes index.scip

stubborn index --scip index.scip --out metadata/symbols.db
stubborn context metadata/symbols.db \
  --target "semanticdb maven com/example/MyService#" \
  --out my-service.stub.java

# Compact graph format (v0.7+)
stubborn context metadata/symbols.db \
  --target "semanticdb maven com/example/MyService#" \
  --format stubborn-dsl \
  --out my-service.stubborn-dsl
```

## What gets extracted

- **Symbols** — `SymbolInformation` from each document + `external_symbols`
- **Edges** — `Relationship` fields (`type`, `reference`, `implementation`, `definition`)
- **Occurrence refs** — non-definition occurrences linked to the nearest non-`local` enclosing symbol (lambda-safe)
- **Signature refs** — return/parameter types parsed from signatures, stored as `signature-ref` edges (used in `smart` prune mode; skipped in `strict` / `fast`)
- **Constructor promotion** — `Foo#<init>()` references also emit `Foo#` type references

## Protobuf bindings

Schema: [`proto/scip.proto`](../proto/scip.proto) (from [sourcegraph/scip](https://github.com/sourcegraph/scip))

Regenerate Python bindings:

```bash
./scripts/regenerate_scip_proto.sh
```

Output: `src/stubborn/ingest/scip_proto/scip_pb2.py`
