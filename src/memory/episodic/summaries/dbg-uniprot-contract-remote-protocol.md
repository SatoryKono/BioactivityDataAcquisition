---
id: dbg-uniprot-contract-remote-protocol
title: Debug UniProt contract RemoteProtocolError
task_id: dbg-uniprot-contract-remote-protocol
created_at: '2026-06-02T08:18:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_uniprot_contract.py
summary: Broadened UniProt contract transient outage handling from a few connect/read
  exceptions to httpx.TransportError so RemoteProtocolError from live proteomes requests
  skips as network/provider flakiness instead of failing the contract test.
---

# Episodic summary

## Task

- Title: Debug UniProt contract RemoteProtocolError

## Outcome

- Broadened UniProt contract transient outage handling from a few connect/read exceptions to httpx.TransportError so RemoteProtocolError from live proteomes requests skips as network/provider flakiness instead of failing the contract test.

## Lessons learned

- Replace with durable follow-up if needed
