with open("src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py", "r") as f:
    content = f.read()

fetch_filtered_old = """
        for chunk_idx in range(0, len(dois), self.batch_size * concurrency_limit):
            chunk_dois = dois[chunk_idx : chunk_idx + self.batch_size * concurrency_limit]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            tasks = [self._fetch_batch_with_nulls(batch) for batch in batches]
            results = await asyncio.gather(*tasks)

            for batch_results in results:
                for record in batch_results:
                    if record is not None:
                        record["_lookup_method"] = "doi"
                        yield record
                        fetched += 1
                        if limit and fetched >= limit:
                            return"""

fetch_filtered_new = """
        for chunk_idx in range(0, len(dois), self.batch_size * concurrency_limit):
            chunk_dois = dois[chunk_idx : chunk_idx + self.batch_size * concurrency_limit]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            results = await asyncio.gather(*(self._fetch_batch_with_nulls(b) for b in batches))

            for batch_results in results:
                for record in batch_results:
                    if record is None:
                        continue
                    record["_lookup_method"] = "doi"
                    yield record
                    fetched += 1
                    if limit and fetched >= limit:
                        return"""

content = content.replace(fetch_filtered_old, fetch_filtered_new)

batch_doi_phase_old = """
        for chunk_idx in range(0, len(valid_dois), self.batch_size * concurrency_limit):
            if limit and count >= limit:
                return

            chunk_dois = valid_dois[chunk_idx : chunk_idx + self.batch_size * concurrency_limit]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            tasks = [self._fetch_batch_with_nulls(batch) for batch in batches]
            results = await asyncio.gather(*tasks)

            for batch, batch_results in zip(batches, results, strict=True):
                for doi, record in zip(batch, batch_results, strict=True):
                    if record is None:
                        continue
                    resolved_dois.add(doi.lower())
                    record["_lookup_method"] = "doi"
                    record["_resolved_doi"] = doi
                    count += 1
                    yield record
                    if limit and count >= limit:
                        return"""

batch_doi_phase_new = """
        for chunk_idx in range(0, len(valid_dois), self.batch_size * concurrency_limit):
            if limit and count >= limit:
                return

            chunk_dois = valid_dois[chunk_idx : chunk_idx + self.batch_size * concurrency_limit]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            results = await asyncio.gather(*(self._fetch_batch_with_nulls(b) for b in batches))

            for batch, batch_results in zip(batches, results, strict=True):
                for doi, record in zip(batch, batch_results, strict=True):
                    if record is None:
                        continue
                    resolved_dois.add(doi.lower())
                    record["_lookup_method"] = "doi"
                    record["_resolved_doi"] = doi
                    count += 1
                    yield record
                    if limit and count >= limit:
                        return"""

content = content.replace(batch_doi_phase_old, batch_doi_phase_new)

with open("src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py", "w") as f:
    f.write(content)
