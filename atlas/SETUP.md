# Atlas Vector Search — Setup Guide

This guide creates the `versions_vector_index` that `memory_search` needs for
`$vectorSearch` queries. The index name must match exactly.

---

## 1. Navigate to Vector Search

1. Open [cloud.mongodb.com](https://cloud.mongodb.com) and select your project.
2. In the left sidebar, click **Atlas Search** (under Services).
3. Make sure you are on the **Vector Search** tab (not the "Search" / full-text tab).

---

## 2. Create the index

1. Click **Create Vector Search Index**.
2. Choose **JSON Editor** (not the Visual Editor — the filter fields require JSON).
3. Fill in the fields:

   | Field | Value |
   |---|---|
   | Database | `siningai` |
   | Collection | `versions` |
   | Index Name | `versions_vector_index` |

   > The index name must be **exactly** `versions_vector_index` — the Jenkinsfile
   > and the `memory_search` agent instruction both reference this string.

4. Paste the following JSON into the editor:

   ```json
   {
     "fields": [
       { "type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine" },
       { "type": "filter", "path": "artwork_id" },
       { "type": "filter", "path": "stage" }
     ]
   }
   ```

   The same JSON is also in `atlas/vector_search_index.json` in this repo.

5. Click **Next**, review the summary, then click **Create Search Index**.

---

## 3. Wait for Active status

Building takes 30 seconds to a few minutes depending on collection size.
Refresh the **Atlas Search** page and wait until the index status shows **Active**.

> **Do not run `$vectorSearch` queries while the index is Building** — they will return
> empty results without an error, which is confusing to debug.

---

## 4. Verify the index

Run this in **Atlas → Browse Collections → aggregation pipeline** on `siningai.versions`,
or via `mongosh`:

```js
db.versions.aggregate([
  {
    $vectorSearch: {
      index: "versions_vector_index",
      path: "embedding",
      // A 1024-element array of zeros — just enough to test the index exists
      queryVector: Array(1024).fill(0),
      numCandidates: 10,
      limit: 3
    }
  },
  { $project: { auto_description: 1, stage: 1, score: { $meta: "vectorSearchScore" } } }
])
```

A successful response (even with zero results) confirms the index is wired up. An error
like `"index not found"` means the name is wrong or the index hasn't finished building.

---

## Troubleshooting

**Index stays in "Building" for more than 10 minutes**
- Large collections take longer. If it has been over 30 minutes, delete and recreate it.
- Check that the collection is not being written to extremely rapidly at the same time.

**`$vectorSearch` returns 0 results despite documents existing**
- Check that version documents have an `embedding` field. If you added the feature after
  existing versions were saved, run the backfill script:
  ```bash
  python scripts/backfill_embeddings.py
  ```
- Confirm `embedding` is an array of exactly 1024 floats, not a nested object or null.

**Error: "Index not found: versions_vector_index"**
- The `memory_search` agent's aggregation pipeline hard-codes this name. Check the index
  name in the Atlas UI — it is case-sensitive.

**Error: "dimension mismatch"**
- The `embedding` values in the documents were generated with a different model or
  dimension. The index expects 1024 dimensions (voyage-multimodal-3 / voyage-3 output).
  Re-run the backfill script to regenerate embeddings.

**`$vectorSearch` returns results but scores are all 0.0**
- This can happen with zero vectors (e.g., a failed embed that stored zeros). Check the
  document's embedding field with `db.versions.findOne({}, {embedding: {$slice: 3}})`.

**Atlas Search tab is missing**
- Vector Search requires M10 or higher cluster tier. Free (M0) clusters do not support it.