# Project Structure

Generated: E:\g-drive\05_AI\github\BioactivityDataAcquisition2

```
BioactivityDataAcquisition2/
    ├── .ai/
    │   └── mcp/
    │       └── mcp.json
    ├── .aiassistant/
    │   └── rules/
    │       ├── 00-core-principles.md
    │       ├── 01-naming-conventions.md
    │       ├── 02-python-style.md
    │       ├── 03-logging.md
    │       ├── 04-data-schemas.md
    │       ├── 05-deterministic-io.md
    │       ├── 06-testing.md
    │       ├── 07-cli-contracts.md
    │       ├── 08-api-clients.md
    │       ├── 09-etl-architecture.md
    │       ├── 10-secrets-and-config.md
    │       ├── 11-abc-default-impl-policy.md
    │       ├── 12-entity-naming-policy.md
    │       └── 13-documentation-standards.md
    ├── .benchmarks/
    ├── .claude/
    │   ├── agents/
    │   │   ├── subagents/
    │   │   │   ├── pyAuditBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   ├── pyCodeBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   ├── pyConfigBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   ├── pyDebugBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   ├── pyDocBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   ├── pyPlanBot/
    │   │   │   │   └── SUBAGENT.md
    │   │   │   └── pyTestBot/
    │   │   │       └── SUBAGENT.md
    │   │   ├── ORCHESTRATION.md
    │   │   ├── py-audit-bot.md
    │   │   ├── py-code-bot.md
    │   │   ├── py-config-bot.md
    │   │   ├── py-debug-bot.md
    │   │   ├── py-doc-bot.md
    │   │   ├── py-plan-bot.md
    │   │   └── py-test-bot.md
    │   ├── prompts/
    │   │   ├── 00-Audit/
    │   │   │   ├── 02-architecture-audit.md
    │   │   │   └── 02-file-structure-audit-standardization.md
    │   │   ├── 00-Documentation/
    │   │   │   ├── 00-documentation-audit-update-task.md
    │   │   │   ├── 01-docstrings-completion.md
    │   │   │   └── 04-naming-compliance-audit-prompt.md
    │   │   ├── 01-documentation-update-prompt.md
    │   │   └── 03-repository-cleanup-assistant.md
    │   ├── rules/
    │   │   └── ai-selfreview-rules.md
    │   ├── skills/
    │   │   ├── new-pipeline.md
    │   │   ├── vcr-record.md
    │   │   └── verify-architecture.md
    │   ├── PROJECT_CONTEXT.md
    │   ├── settings.json
    │   └── settings.local.json
    ├── .codex/
    │   ├── skills/
    │   │   ├── documentation-audit/
    │   │   │   ├── agents/
    │   │   │   │   └── openai.yaml
    │   │   │   ├── references/
    │   │   │   │   ├── audit-checklist.md
    │   │   │   │   └── report-template.md
    │   │   │   └── SKILL.md
    │   │   └── public/
    │   │       └── architecture-guardian/
    │   │           ├── agents/
    │   │           │   └── openai.yaml
    │   │           └── SKILL.md
    │   ├── config.toml
    │   └── settings.json
    ├── .gemini/
    │   └── settings.json
    ├── .github/
    │   ├── workflows/
    │   │   ├── architecture.yml
    │   │   ├── commit-lint.yml
    │   │   ├── compiled-artifacts-block.yml
    │   │   ├── contract-tests.yml
    │   │   ├── docs.yml
    │   │   ├── duplication-complexity.yml
    │   │   ├── import-linter.yml
    │   │   ├── mutation-testing.yml
    │   │   ├── port-contracts.yml
    │   │   ├── project-automation.yml
    │   │   ├── release.yml
    │   │   ├── security.yml
    │   │   ├── tests.yml
    │   │   ├── type-checking.yml
    │   │   ├── vacuum.yml
    │   │   └── validate-mermaid.yml
    │   ├── CODE_OF_CONDUCT.md
    │   ├── CONTRIBUTING.md
    │   └── SECURITY.md
    ├── .hypothesis/
    │   ├── constants/
    │   │   ├── 009c4c693fb78114
    │   │   ├── 00b6e67f83ee1249
    │   │   ├── 01ebdcaee1c7257f
    │   │   ├── 0255024d88d52609
    │   │   ├── 02e2a3698e766226
    │   │   ├── 02e8770b18770657
    │   │   ├── 03b7ff76d0ee87f5
    │   │   ├── 03d6244e38ecf911
    │   │   ├── 049da5d33861130f
    │   │   ├── 04a86cf2efa02e47
    │   │   ├── 0520b3a74b4c15bd
    │   │   ├── 05cd1017975eefca
    │   │   ├── 05dc98beec81d193
    │   │   ├── 063ab2508852cb76
    │   │   ├── 064ce2e4995a0b55
    │   │   ├── 06819d6ccbf676b5
    │   │   ├── 069c99fe7190022f
    │   │   ├── 06c631230e01680d
    │   │   ├── 06cd5ac319db1bc8
    │   │   ├── 071ca21e504c7364
    │   │   ├── 07535ac5a4ff5b88
    │   │   ├── 076e43433c76339f
    │   │   ├── 077239329d0a609a
    │   │   ├── 0788b9d9dd7e9634
    │   │   ├── 0832884c95415fd6
    │   │   ├── 083a379a2e56fba9
    │   │   ├── 084cc8b66255f9f9
    │   │   ├── 08c772ba4116926b
    │   │   ├── 09560aa662fb5000
    │   │   ├── 096b8ca3ee7a1973
    │   │   ├── 096e802ead190427
    │   │   ├── 09a8aba9b139c5c3
    │   │   ├── 0a06318fc8f22802
    │   │   ├── 0a5ccc8e180bdf20
    │   │   ├── 0a79afa2065a01b4
    │   │   ├── 0a8826fdef103843
    │   │   ├── 0a88a94f94861361
    │   │   ├── 0aa9932940b86484
    │   │   ├── 0aaf8b215c93dae6
    │   │   ├── 0b04aaea51d3c299
    │   │   ├── 0b0e1b22ee150205
    │   │   ├── 0b13554b32973240
    │   │   ├── 0b2ea31d468fa451
    │   │   ├── 0b36849c59420767
    │   │   ├── 0c1e9f0fa3a0c67b
    │   │   ├── 0c507e967f7d3125
    │   │   ├── 0c7781844c0300ee
    │   │   ├── 0cc1a59ce7410c50
    │   │   ├── 0d0c1b558c94575f
    │   │   ├── 0dd4b0b9defbf128
    │   │   ├── 0dd6cbed1602442b
    │   │   ├── 0e0ed8cd6a36280e
    │   │   ├── 0e24da378d9bd773
    │   │   ├── 0e32f66c5b8fa3c8
    │   │   ├── 0e52688de878912f
    │   │   ├── 0eb7f7ce38090aeb
    │   │   ├── 0ed99aaf09e6f279
    │   │   ├── 0f0f36e1987da495
    │   │   ├── 0f30251c00e3148a
    │   │   ├── 0f8928d3afa35ec9
    │   │   ├── 1082b00d71733f92
    │   │   ├── 10ad2f0768df757f
    │   │   ├── 113d22cb84ede695
    │   │   ├── 116e780a4f36aa4a
    │   │   ├── 11bc2f285c5c840b
    │   │   ├── 11ca980ce1e84372
    │   │   ├── 1204ac393193be36
    │   │   ├── 1206e765acd59db9
    │   │   ├── 1231851d998acca4
    │   │   ├── 12dbd9892bda48dc
    │   │   ├── 1305dd2df178bbda
    │   │   ├── 131876e7e326de2d
    │   │   ├── 13468fc04894ea4f
    │   │   ├── 136642b989967b01
    │   │   ├── 13868a05452a0a73
    │   │   ├── 13c8e4ebe1571ded
    │   │   ├── 13c99a7b5e588a67
    │   │   ├── 14565d89cd48d148
    │   │   ├── 153cc05a97f39505
    │   │   ├── 15524d12ec596d8a
    │   │   ├── 15d2b181bd55060b
    │   │   ├── 169e23a123cf1f82
    │   │   ├── 1711a3f9dd8371e0
    │   │   ├── 172d7d0a62cea958
    │   │   ├── 173220ebf1b09443
    │   │   ├── 1741edc7bbef4294
    │   │   ├── 175adb690c44f7fd
    │   │   ├── 17a6754bf8858cd9
    │   │   ├── 181e9facefec517a
    │   │   ├── 183f9a75f81378e5
    │   │   ├── 185369cab692918a
    │   │   ├── 18671e32236189d9
    │   │   ├── 186d8d238459fa3b
    │   │   ├── 18712592aeb96a6b
    │   │   ├── 192721418f13beb3
    │   │   ├── 194aa71a3baebe9d
    │   │   ├── 1955b38147f3acbf
    │   │   ├── 1964bc6c5caf63a3
    │   │   ├── 19945edc87716e85
    │   │   ├── 1aca8fd80aadb827
    │   │   ├── 1b63de5799f071d5
    │   │   ├── 1b8b5d907d59719a
    │   │   ├── 1c46299b6707e73d
    │   │   ├── 1cb67778210116fb
    │   │   ├── 1d0bc8345c5d34d4
    │   │   ├── 1d0e6185ac11649f
    │   │   ├── 1d6b664f186d5235
    │   │   ├── 1dd74263407afa7b
    │   │   ├── 1dd9dd460b8f9c3b
    │   │   ├── 1e5034a869c16bac
    │   │   ├── 1e6ca76ac1c91909
    │   │   ├── 1e6ccb30049b9ca3
    │   │   ├── 1e9d90404b97a9a6
    │   │   ├── 1f4d5c2150c79040
    │   │   ├── 1f78916d7ba15f03
    │   │   ├── 201736e4a4b12d07
    │   │   ├── 201aa37ec12bc1d8
    │   │   ├── 20272946973653f2
    │   │   ├── 2030988c4617ddc8
    │   │   ├── 20a202699ff73cb0
    │   │   ├── 20b75b064d61b502
    │   │   ├── 21fb97b6d798b799
    │   │   ├── 21ffa8167cd55ae7
    │   │   ├── 2326ea560e98964c
    │   │   ├── 23c1d55f481e96e5
    │   │   ├── 23f1d3a67b654e76
    │   │   ├── 240041d7b57ec46b
    │   │   ├── 24c03f4659618e56
    │   │   ├── 24c8bcf3212713bf
    │   │   ├── 24d25f7a8251427b
    │   │   ├── 24dca32398470847
    │   │   ├── 24e92cd43c497642
    │   │   ├── 250326151a63b9b7
    │   │   ├── 251a40c5eaeae8c0
    │   │   ├── 25800c550d897377
    │   │   ├── 25917451909e5254
    │   │   ├── 264ca79b3b905f2e
    │   │   ├── 266d1644ad80cf62
    │   │   ├── 26d8198df8b4353e
    │   │   ├── 26e3fd0137d4b708
    │   │   ├── 271d89bc236c466e
    │   │   ├── 27f278437b109411
    │   │   ├── 288fa9da6fa89ef7
    │   │   ├── 289b80106a8f62fa
    │   │   ├── 28b9fb74573446e6
    │   │   ├── 28c70021bb622e8a
    │   │   ├── 28cd04f63ea2c045
    │   │   ├── 291aca9853777156
    │   │   ├── 293966075aeeba2b
    │   │   ├── 294e13965437b784
    │   │   ├── 29f1c9bc22821da2
    │   │   ├── 2a5ca256c8f39662
    │   │   ├── 2aa530284555750c
    │   │   ├── 2ac28c40cfea812a
    │   │   ├── 2b21d892bffdc8ba
    │   │   ├── 2b5f0ee160866db1
    │   │   ├── 2bed416665fbadff
    │   │   ├── 2c4c7eb2994679f9
    │   │   ├── 2cca63790c0bbf20
    │   │   ├── 2d494915fe2ff3be
    │   │   ├── 2d4dcac767fd6cfe
    │   │   ├── 2d893470ebca06dd
    │   │   ├── 2da79997e5a17388
    │   │   ├── 2de1998afd291c6d
    │   │   ├── 2e097243797b7e9c
    │   │   ├── 2e63e853f6276b47
    │   │   ├── 2e6844ce223bc091
    │   │   ├── 2eecb5f293ba6ff4
    │   │   ├── 2f5c42bb8309997f
    │   │   ├── 2f710d3490908aff
    │   │   ├── 2f8136f588d414d0
    │   │   ├── 2fd831480a153432
    │   │   ├── 302316ffd338133a
    │   │   ├── 30388efc1a5d21f8
    │   │   ├── 30456912036f4fc1
    │   │   ├── 30660b6cb43c013b
    │   │   ├── 3166ad08a7a82fc4
    │   │   ├── 317239d6001e4cac
    │   │   ├── 31b16ce8f63019fe
    │   │   ├── 31c5a09da09399a0
    │   │   ├── 322b670b3581aa50
    │   │   ├── 327a40dfb0f89d85
    │   │   ├── 32b8b1603f1d7a17
    │   │   ├── 32d8b17fafa3adce
    │   │   ├── 32dc7f053e616959
    │   │   ├── 3354bf6b72433dd8
    │   │   ├── 3360058964ecfe10
    │   │   ├── 33697263f9a36ae5
    │   │   ├── 33731b0c83cd4820
    │   │   ├── 33cbc6ed2a0d7eb5
    │   │   ├── 33fb51e3a7db624f
    │   │   ├── 344b71bb69289b06
    │   │   ├── 3459226d23eb196e
    │   │   ├── 3474fe35755e4ddf
    │   │   ├── 349d30b263fa7b0b
    │   │   ├── 350413f1daf2121b
    │   │   ├── 354757987d006785
    │   │   ├── 35589c4c397d5beb
    │   │   ├── 35618869ce83732e
    │   │   ├── 357ad438a58004ca
    │   │   ├── 36437dbe9df7d0c2
    │   │   ├── 36870587afd536c0
    │   │   ├── 36e39d1bc4c63f91
    │   │   ├── 379995172aac131b
    │   │   ├── 38079ade4fa2d0f7
    │   │   ├── 383257c7ca20f53e
    │   │   ├── 38e48afce4c1f81a
    │   │   ├── 397bace8d0ca7ce9
    │   │   ├── 3a0e8d623347f880
    │   │   ├── 3ab3ae6ed3675a78
    │   │   ├── 3ae231f4e05e6217
    │   │   ├── 3b0403d016b66943
    │   │   ├── 3b34d75848344b97
    │   │   ├── 3b8fa06d57b1ece4
    │   │   ├── 3b95bdde7cf0247f
    │   │   ├── 3ba41297f1743495
    │   │   ├── 3bf6c1a261b5ec14
    │   │   ├── 3cd346f634f7222a
    │   │   ├── 3cd93bfa34139a2a
    │   │   ├── 3cf8efb2532222ca
    │   │   ├── 3d015c0cc3dfd0d2
    │   │   ├── 3d3c6a6237a1eefc
    │   │   ├── 3d45e9e446d50be1
    │   │   ├── 3d4ad205e1ec65e0
    │   │   ├── 3d5468732b82e3b3
    │   │   ├── 3d62c890961a50d7
    │   │   ├── 3e30ad1a4689d1b1
    │   │   ├── 3e95d4ec7bf606ff
    │   │   ├── 3eb7ccc38db2f1bd
    │   │   ├── 3ec3c83f152e1c5f
    │   │   ├── 3f06ccc5e73b3a94
    │   │   ├── 3f35551857f882b3
    │   │   ├── 3f50fd12ad93c611
    │   │   ├── 3f6c46636622dab1
    │   │   ├── 3f9ae50678cb9208
    │   │   ├── 3fbfbcbb99ab9f14
    │   │   ├── 414aa0b47ae77492
    │   │   ├── 416f3963b5037ae4
    │   │   ├── 41b551cd2bb750ce
    │   │   ├── 41bfc24f66d9d301
    │   │   ├── 423755265ab215f8
    │   │   ├── 425007432024b5d8
    │   │   ├── 426777eceb1e9477
    │   │   ├── 42c0fbcdb08f8116
    │   │   ├── 42d8a67a7b97765c
    │   │   ├── 43e54da66503ea74
    │   │   ├── 44151109c767790d
    │   │   ├── 44e4c9d38c10dddb
    │   │   ├── 45a069456c2feb48
    │   │   ├── 45cca08b25114bcd
    │   │   ├── 4609178ff8ffe39b
    │   │   ├── 4652d39b73a183bf
    │   │   ├── 46dfacaf83dbf1ee
    │   │   ├── 470be9f8f2ab1f50
    │   │   ├── 473a033f6d3d4283
    │   │   ├── 476d75e80915169e
    │   │   ├── 47fdcbf518d8deaf
    │   │   ├── 4878c896442b2113
    │   │   ├── 4880c508441ae614
    │   │   ├── 48adb991ed6ec792
    │   │   ├── 49209951302a53f1
    │   │   ├── 4954c3b2a2980eab
    │   │   ├── 498836cf66952349
    │   │   ├── 498b42c1a13a2346
    │   │   ├── 49a04bcfa23754a4
    │   │   ├── 4a2ed26cb0b8f525
    │   │   ├── 4a7ce5aa3339618f
    │   │   ├── 4aa233515390b3f1
    │   │   ├── 4abaaec9807087a4
    │   │   ├── 4b0120efc7273eae
    │   │   ├── 4b1dcc6b37e32771
    │   │   ├── 4b3e7f7f941a2c04
    │   │   ├── 4b48d224a0444b30
    │   │   ├── 4ba9f176f41ec269
    │   │   ├── 4c76febf535ca9ab
    │   │   ├── 4cca9ba830cfff48
    │   │   ├── 4cd58c4f1abc6bab
    │   │   ├── 4d00c01158ed45db
    │   │   ├── 4d143dca8572361f
    │   │   ├── 4d32b7cb3ffcf330
    │   │   ├── 4d5029dd4c916b4f
    │   │   ├── 4d524e91397187e4
    │   │   ├── 4da36df3da06a15a
    │   │   ├── 4dcbe6c59d328dcb
    │   │   ├── 4e22d3f34e440e07
    │   │   ├── 4e5a58ad851747e4
    │   │   ├── 4e70e1f2024d9780
    │   │   ├── 4e9eb3fdb3ff506c
    │   │   ├── 4eb1c3be9fe0ed68
    │   │   ├── 4effd043dfe92814
    │   │   ├── 4f019e3e3a02fbf9
    │   │   ├── 4f0d6c15d3d3b247
    │   │   ├── 4f38412943871c5c
    │   │   ├── 4f8e81b62dbeb8cc
    │   │   ├── 4fb2ae70b3deb0c4
    │   │   ├── 4ffe4a05802b45e8
    │   │   ├── 506ebd1999d0ef6b
    │   │   ├── 51a60623589a0b5a
    │   │   ├── 51e865b88adb5646
    │   │   ├── 5221b8699605e4b0
    │   │   ├── 5244a3fa5856ef35
    │   │   ├── 53072f7d604eff93
    │   │   ├── 533afdb43211adad
    │   │   ├── 536209c0f855f5c0
    │   │   ├── 53c06fdf383d8823
    │   │   ├── 53ceedd82248d596
    │   │   ├── 5415c6e8ed0e8596
    │   │   ├── 54497b7a8afa54cb
    │   │   ├── 5460203b76a8dace
    │   │   ├── 547fa6a100297800
    │   │   ├── 548336e78a3998e1
    │   │   ├── 5538e1c02d445671
    │   │   ├── 5580c99ef6481f11
    │   │   ├── 55f28878ee884c0d
    │   │   ├── 56366fe14074f0c4
    │   │   ├── 56abc623fc3a5298
    │   │   ├── 581c7f69715d23b3
    │   │   ├── 582b97630d810493
    │   │   ├── 583bc7f3c741c6e0
    │   │   ├── 5879fd7d2db64280
    │   │   ├── 58a60b021e31c9fc
    │   │   ├── 58a9cb89d80145cc
    │   │   ├── 58ab9665c2f838f7
    │   │   ├── 58f6c34da2ec43d9
    │   │   ├── 59722ce03a82653b
    │   │   ├── 5979b06e7ebc6080
    │   │   ├── 59c8f8f6ea161473
    │   │   ├── 5a0aeaf50fcab452
    │   │   ├── 5a6c09875ab7c78e
    │   │   ├── 5abc104ef43a223c
    │   │   ├── 5b4be9a17ccbb955
    │   │   ├── 5b5456ecaec22c14
    │   │   ├── 5bee28a0d555719b
    │   │   ├── 5bfb73e60773802c
    │   │   ├── 5c3e4164cf4db7f9
    │   │   ├── 5c95a8bab55ee922
    │   │   ├── 5cbd1562c8ac29b8
    │   │   ├── 5cf4662dc9cdf208
    │   │   ├── 5de46f7d90d2a75d
    │   │   ├── 5e91e38998f977e7
    │   │   ├── 5eb12d44be150201
    │   │   ├── 5f2dd7621c7f73bb
    │   │   ├── 5f2def453202aea3
    │   │   ├── 5f4e02b2f313550e
    │   │   ├── 5f932bcb0277e269
    │   │   ├── 5fa6e8feb9fd062b
    │   │   ├── 5fb4184fb78bc749
    │   │   ├── 5fc01e08e41fda0f
    │   │   ├── 5fd38948000c0484
    │   │   ├── 6022cb90ccb8b6da
    │   │   ├── 60582ca82efff6a0
    │   │   ├── 60a534d74428d445
    │   │   ├── 60cd735239fa28ba
    │   │   ├── 60e9ba7b9eb5ed6b
    │   │   ├── 60f493f6be1ac4e5
    │   │   ├── 610956c72bf82f1c
    │   │   ├── 6110d77a7d4c1e59
    │   │   ├── 61460c98bd647a70
    │   │   ├── 616d00e9d7940c74
    │   │   ├── 618db7635df30549
    │   │   ├── 6215506d31828320
    │   │   ├── 62b2583f755984eb
    │   │   ├── 62c94bc0d7aa3770
    │   │   ├── 62dea96bfccb9f8d
    │   │   ├── 62f896a2709f70d2
    │   │   ├── 632b0c83df9db524
    │   │   ├── 634b6b2345279fbc
    │   │   ├── 63c4191a4a719057
    │   │   ├── 63f0fe1b2b22111c
    │   │   ├── 63f11f3f5215f31d
    │   │   ├── 64729d9417be2688
    │   │   ├── 6539e02b390c8c5e
    │   │   ├── 657130f8386f3866
    │   │   ├── 65947b49b17d3e60
    │   │   ├── 65d196c6dc0f6c93
    │   │   ├── 65ea978a99cf85fd
    │   │   ├── 6651191964800af4
    │   │   ├── 6659e61cbb2870ff
    │   │   ├── 669547cbd6e707de
    │   │   ├── 67552ca89ed0b3ee
    │   │   ├── 67612e92d73eced6
    │   │   ├── 67888cc0d1d55d76
    │   │   ├── 68289c71e1073218
    │   │   ├── 6828a11cdff9399d
    │   │   ├── 68ae5b4a4538918f
    │   │   ├── 68c20491c4081c8a
    │   │   ├── 6915197373e26f5f
    │   │   ├── 694f41b52c4a3342
    │   │   ├── 699366ee741d35ba
    │   │   ├── 69b1b27fcf8d12a6
    │   │   ├── 69b6221ed4c1831a
    │   │   ├── 6a36b001911864ba
    │   │   ├── 6a7c24c3382ebbc6
    │   │   ├── 6addfe4dc663cff9
    │   │   ├── 6b16bdcef08745ee
    │   │   ├── 6b4304590d9018c4
    │   │   ├── 6bc5296b7d20cc08
    │   │   ├── 6c56c8241852633a
    │   │   ├── 6cc258e642dac66e
    │   │   ├── 6cc305cafe99ab59
    │   │   ├── 6d644ed942c7adbc
    │   │   ├── 6df5419b4af25b8b
    │   │   ├── 6e0b4aa92db4790f
    │   │   ├── 6e4ed7fef5ce10df
    │   │   ├── 6e5c0cdfe5a6b006
    │   │   ├── 6ea0b3157b68bbb0
    │   │   ├── 6eb3660f8e9bdaf0
    │   │   ├── 6eb820984d543d43
    │   │   ├── 6eb9b239985cb861
    │   │   ├── 6ec84b833568f2f8
    │   │   ├── 6edb18bdfd295672
    │   │   ├── 6f3a2f7d8c9672a9
    │   │   ├── 6f729c8760153457
    │   │   ├── 6fb6a708c16bdec0
    │   │   ├── 70973efd7f2eb1c5
    │   │   ├── 70b0b71bfb34d5d8
    │   │   ├── 70f90acdee725f0f
    │   │   ├── 70fa2aac5323c6a8
    │   │   ├── 710b3048412f57e1
    │   │   ├── 71281177ae268e08
    │   │   ├── 71d0aea7c24876f2
    │   │   ├── 720d1c425134039b
    │   │   ├── 7244739d65e5ab5c
    │   │   ├── 72fdb75f9319d301
    │   │   ├── 7316e8e794775794
    │   │   ├── 73a01060849dc749
    │   │   ├── 749d4d4a70818054
    │   │   ├── 749e2e0aceb20266
    │   │   ├── 74cf026eb44e7574
    │   │   ├── 74fd1683e8caace1
    │   │   ├── 751006837ee992f1
    │   │   ├── 75184061aad8462e
    │   │   ├── 7530e99d50fa7df7
    │   │   ├── 754c03f78ff97175
    │   │   ├── 7555cd1813e6df46
    │   │   ├── 7572939b37c4fd82
    │   │   ├── 75a74dcaf66629e4
    │   │   ├── 75aa04d4d21025c8
    │   │   ├── 75de966d730b5ca4
    │   │   ├── 7632ccd152888c87
    │   │   ├── 76431a37812e34f6
    │   │   ├── 7664e40b58c99dfd
    │   │   ├── 7683df041914cde8
    │   │   ├── 769af700337b3eb2
    │   │   ├── 76b07c840f79809f
    │   │   ├── 76d944da1226cfe7
    │   │   ├── 7720ed9c1254aa3f
    │   │   ├── 776fffac01a87a3c
    │   │   ├── 778c743baf26383c
    │   │   ├── 77b969b3871d0955
    │   │   ├── 78070c9792ed364d
    │   │   ├── 787d8a2a6461b676
    │   │   ├── 78a0cd23b80a8b68
    │   │   ├── 78b2ae07bd13c4b7
    │   │   ├── 78ec4382f297f09a
    │   │   ├── 78f09f861e5d3255
    │   │   ├── 7944848c3d1ccd1c
    │   │   ├── 796023a98be5def8
    │   │   ├── 79654f0aafb58272
    │   │   ├── 7975ace5db2cf1a5
    │   │   ├── 7980c6fad8a1a666
    │   │   ├── 79f043adbac1b3da
    │   │   ├── 7accedadfc8fd929
    │   │   ├── 7b237e5af83865a6
    │   │   ├── 7b292c50beb8c68f
    │   │   ├── 7b643c5044eb86ed
    │   │   ├── 7bbccb3ec9133102
    │   │   ├── 7bd6731d3ff42f52
    │   │   ├── 7be0ee6094d0f58f
    │   │   ├── 7c98bc542660e962
    │   │   ├── 7c9ce454174962b0
    │   │   ├── 7caff21279b241bc
    │   │   ├── 7cb054385d8f625b
    │   │   ├── 7ce8c3e8c1456813
    │   │   ├── 7d3b66a3d1a7263b
    │   │   ├── 7de9b894e1c04196
    │   │   ├── 7e23a5ca39626b70
    │   │   ├── 7e44e487931c591c
    │   │   ├── 7f619a93e89056c8
    │   │   ├── 7f742d0006e93b24
    │   │   ├── 7fbe7edf59fe6ce0
    │   │   ├── 7fd076b51e62fde9
    │   │   ├── 7fd737dea8958dde
    │   │   ├── 800360cfdd9e54cb
    │   │   ├── 8033b424398da87d
    │   │   ├── 80d35ca6652eaab5
    │   │   ├── 80dafe9491fcdb4c
    │   │   ├── 810717502bfa83d0
    │   │   ├── 81194b7d56750330
    │   │   ├── 81a84c07d58ec5ac
    │   │   ├── 81c3c4efe45d6975
    │   │   ├── 81fdf02c2cee43f1
    │   │   ├── 821e7fca3033f7bc
    │   │   ├── 82290de70700479f
    │   │   ├── 826179c1461c5969
    │   │   ├── 826b0668e91c6e6a
    │   │   ├── 82740db088c6032c
    │   │   ├── 8277e3cd30ce6249
    │   │   ├── 83cfef7ea589affa
    │   │   ├── 83e4cdab94e279b6
    │   │   ├── 844b8dfb473b6833
    │   │   ├── 845c7a00862b1240
    │   │   ├── 8468d289e2a46968
    │   │   ├── 84698904d80763db
    │   │   ├── 8490f8d40367d2b5
    │   │   ├── 8512bd65c00938e1
    │   │   ├── 8520a500541c15b5
    │   │   ├── 85367fdfbb59e30c
    │   │   ├── 853932c08d0c833e
    │   │   ├── 86ee5998aeb39009
    │   │   ├── 870082e05f6fbecd
    │   │   ├── 87135ca783b3a320
    │   │   ├── 873781fc9e560285
    │   │   ├── 8747977e3ca244ec
    │   │   ├── 87b0ac7d08e7f887
    │   │   ├── 8834d52db065b061
    │   │   ├── 88e7dc2bcbfc181c
    │   │   ├── 88f6c65709bec958
    │   │   ├── 8905db9887f61d13
    │   │   ├── 89cb1ee9c6d601db
    │   │   ├── 89db8584fafe7083
    │   │   ├── 89e33d3cd63c61ab
    │   │   ├── 8a16ae6e72baf48d
    │   │   ├── 8a800b484929466b
    │   │   ├── 8a92c14625f902cc
    │   │   ├── 8ac630f3bd0845c8
    │   │   ├── 8b06d44ec383188a
    │   │   ├── 8b07477676ac08c1
    │   │   ├── 8b511d3487a97c5c
    │   │   ├── 8ba30fdd3dae50df
    │   │   ├── 8c3ab828442df1a0
    │   │   ├── 8c8d1b866dec4aa7
    │   │   ├── 8c97699c71ab9753
    │   │   ├── 8cb06ae3433f848b
    │   │   ├── 8cdf52b64b204069
    │   │   ├── 8ce4a2710a8985bf
    │   │   ├── 8d34014b3a852bbe
    │   │   ├── 8d8ffb51fa78078d
    │   │   ├── 8da47dcc335165ae
    │   │   ├── 8dbe93175d226062
    │   │   ├── 8df72e0dbf66db87
    │   │   ├── 8e6188f237f72cc5
    │   │   ├── 8e70e1e0b148db74
    │   │   ├── 8f4c836086955fed
    │   │   ├── 8f57dcf5387dc7bb
    │   │   ├── 903e42cf94abe057
    │   │   ├── 90a8f2103c6bcf70
    │   │   ├── 90b176c873088fa6
    │   │   ├── 90df260e7190920a
    │   │   ├── 90e5dca0f39a4821
    │   │   ├── 911a89c10332734f
    │   │   ├── 91bff1ae72164dba
    │   │   ├── 91d191f88a2a8c9b
    │   │   ├── 91d696d35c9abb2f
    │   │   ├── 92bcb49cfe9409cc
    │   │   ├── 92bdd5c1e3862496
    │   │   ├── 938e99169c2c4afa
    │   │   ├── 94755467ddee3502
    │   │   ├── 95359b8a6878bd39
    │   │   ├── 95839d0b03bb32b3
    │   │   ├── 95d44d459c77bfe8
    │   │   ├── 95ea9ebcbb01c870
    │   │   ├── 96aa986adc3e781d
    │   │   ├── 96bc8158b93ff9c3
    │   │   ├── 9739a69f3292d7d3
    │   │   ├── 9757a12ae80988ec
    │   │   ├── 978246cd49ac4ae7
    │   │   ├── 979c75ae4f18caa5
    │   │   ├── 97b6a4b2ddb67996
    │   │   ├── 97f5c5cc5b26b04d
    │   │   ├── 98113a7762a9bc02
    │   │   ├── 985b11173d209a1a
    │   │   ├── 98c184dbddb07ee3
    │   │   ├── 98c1a3fce354207c
    │   │   ├── 9970acbea4824f59
    │   │   ├── 997275c6835fa632
    │   │   ├── 99be0bcd34908169
    │   │   ├── 99cead82bbb494a1
    │   │   ├── 9a2af25c1951f588
    │   │   ├── 9a78a5ed48efd492
    │   │   ├── 9a9cce5256bed380
    │   │   ├── 9b703a18928311d5
    │   │   ├── 9bac771bbddc2a87
    │   │   ├── 9bd7d8cecb3e67fd
    │   │   ├── 9c0ffa6fc479bc63
    │   │   ├── 9c2fe3e071c18106
    │   │   ├── 9c3afdde70775151
    │   │   ├── 9c57f325a724d53f
    │   │   ├── 9c605de5cfce1952
    │   │   ├── 9c705af66b52b2ff
    │   │   ├── 9c92e0cf11111a50
    │   │   ├── 9cc5766ac2757a05
    │   │   ├── 9cf620129ba6e2d0
    │   │   ├── 9cfffdbd56bc70fa
    │   │   ├── 9d0522b0c8c0fa70
    │   │   ├── 9d4d0e3314b62fef
    │   │   ├── 9d510d7e21510560
    │   │   ├── 9d6e4929d94ef99c
    │   │   ├── 9d7596734a55ce50
    │   │   ├── 9d8e016be596a399
    │   │   ├── 9db01ee14cbd43f5
    │   │   ├── 9dca034cdac1a27d
    │   │   ├── 9e0cb95354cf479b
    │   │   ├── 9e6af81dffabbef5
    │   │   ├── 9e7673c92b074a10
    │   │   ├── 9e9e9373d4fa5b45
    │   │   ├── 9ea22e98e136bf99
    │   │   ├── 9eb334adac0e1036
    │   │   ├── 9ebcfacedcc70044
    │   │   ├── 9f0e09b155ab4c42
    │   │   ├── 9f547e05187fa333
    │   │   ├── 9f65d9a4e7fcb451
    │   │   ├── a0bca092753b62a2
    │   │   ├── a0d206b589a9316a
    │   │   ├── a0f262b4ad68c062
    │   │   ├── a121ed9a5cfb14d0
    │   │   ├── a144abc61de57a73
    │   │   ├── a19dcda4ddf927dd
    │   │   ├── a208848ab496f343
    │   │   ├── a29aa8f18ca69399
    │   │   ├── a38ba78afa9a3d43
    │   │   ├── a40f0b123dad9972
    │   │   ├── a4485234bcad6f90
    │   │   ├── a4bb69d9f364d1ae
    │   │   ├── a4e223fe8c3557dc
    │   │   ├── a51a95fac7965bee
    │   │   ├── a5eeeba0f33a884f
    │   │   ├── a631e460c64d3b4d
    │   │   ├── a664bf36969e2af6
    │   │   ├── a670b9ceb47ee54b
    │   │   ├── a6d8ae2cc0c0f389
    │   │   ├── a6e989d4f99229e6
    │   │   ├── a6ea38ca2b5d91d4
    │   │   ├── a77a3de71f06b19c
    │   │   ├── a7885cec3dc5b8ea
    │   │   ├── a808595105b225b2
    │   │   ├── a834bb59ebbe742b
    │   │   ├── a8d1194e01283339
    │   │   ├── a90dfa91d8e10820
    │   │   ├── a91df2332ffe4f85
    │   │   ├── a92904ee3876d073
    │   │   ├── a9c480350a6e32d5
    │   │   ├── a9ce841437918e69
    │   │   ├── a9fe8fc490cc669b
    │   │   ├── aa0dda97c72fa4b3
    │   │   ├── aad2ccaafe5f6c2d
    │   │   ├── aad74357f6c29a03
    │   │   ├── aad802f88a5c3686
    │   │   ├── ab01a6867b961ecf
    │   │   ├── ab512a73f3d04bb2
    │   │   ├── ab704748a638733f
    │   │   ├── ab79f7f1ac143283
    │   │   ├── ac31ffd6ba08cb08
    │   │   ├── ac7aa5a082390d73
    │   │   ├── acbff73a70f1c768
    │   │   ├── ad58ab67b1eb5d18
    │   │   ├── adc0ecebbec2dddf
    │   │   ├── adf53905cbfe349f
    │   │   ├── ae0dc2fac530f634
    │   │   ├── ae0e1e674253f34e
    │   │   ├── ae151bfcd13494d9
    │   │   ├── ae272dcefb957001
    │   │   ├── ae2c80451e2f9533
    │   │   ├── ae2ced03cb7d55ae
    │   │   ├── aea3099c8b3cfa0e
    │   │   ├── aeb231b44ff1b87d
    │   │   ├── aef6e6d1ff4c7281
    │   │   ├── af0b9c9710c2d770
    │   │   ├── afa50226088555fb
    │   │   ├── afc3c6c7cddec45d
    │   │   ├── afee07255407ddb2
    │   │   ├── affa5537e9a3753f
    │   │   ├── b00c429b1ec47023
    │   │   ├── b083f584e5dd62f2
    │   │   ├── b0d141037c2b7e73
    │   │   ├── b108d8ffb34b7b37
    │   │   ├── b150b760abea7ee7
    │   │   ├── b17ef3930a72eb85
    │   │   ├── b1bbd96fbd3e8763
    │   │   ├── b1c7fea48bd9cf5b
    │   │   ├── b1c94be6727c2dc3
    │   │   ├── b1cabd8ad2113c78
    │   │   ├── b1d697c97d1d51a5
    │   │   ├── b23532faa98ccc97
    │   │   ├── b247cf49b0a8f1f3
    │   │   ├── b37248b534671378
    │   │   ├── b38fe0bd06288f3a
    │   │   ├── b4d724e1a6728a75
    │   │   ├── b59e694f0a0a5358
    │   │   ├── b5ca108f4fb74393
    │   │   ├── b5f804962672de12
    │   │   ├── b62a5c66a8318711
    │   │   ├── b659111e24e0d197
    │   │   ├── b75f028964f62c4b
    │   │   ├── b79211821b6d9357
    │   │   ├── b7ed6cac7f568110
    │   │   ├── b81a3ce6a8cdfb23
    │   │   ├── b851c15421fca503
    │   │   ├── b8ec2ae5f7db6c6b
    │   │   ├── b97f16d565a3027d
    │   │   ├── b987e5dc89383722
    │   │   ├── b9a438a25dba08f4
    │   │   ├── bad8ca5420701df1
    │   │   ├── bae6fa6b3c868f1b
    │   │   ├── bb549ba8b29031ae
    │   │   ├── bbd663f1d19c8080
    │   │   ├── bbfae8fcf1ea0ad8
    │   │   ├── bc4000df922f8a64
    │   │   ├── bc45b7113403d107
    │   │   ├── bc4c988270276f7b
    │   │   ├── bc79766f1d715103
    │   │   ├── bd9026819e2dcb1d
    │   │   ├── bda825e0f661b7c3
    │   │   ├── bdb23b16829df55a
    │   │   ├── be426885134a09b0
    │   │   ├── bec173b2dd720f94
    │   │   ├── bedf38afedfef915
    │   │   ├── bf532d80a9ac5227
    │   │   ├── bff1435589b23c3f
    │   │   ├── bffa072cbf0329c6
    │   │   ├── c030be840560bdb6
    │   │   ├── c05f7c8dd2cc0f72
    │   │   ├── c10488cba99f1ea2
    │   │   ├── c11f15c519594224
    │   │   ├── c1248fc79075973a
    │   │   ├── c16162114a2c6bd5
    │   │   ├── c182368b534167f3
    │   │   ├── c1aef3489213629e
    │   │   ├── c1b087eaa31690ee
    │   │   ├── c1e3d4505b5c1274
    │   │   ├── c20033a9d14de75e
    │   │   ├── c26d5b579277374a
    │   │   ├── c2bd4f268ea650ba
    │   │   ├── c4537ec090de4c5c
    │   │   ├── c4ce82d8f68d291c
    │   │   ├── c52974e1320e77b1
    │   │   ├── c55905a032c22876
    │   │   ├── c55da1ecdedf9670
    │   │   ├── c56860ab56aa48ce
    │   │   ├── c5aac036f1e141c3
    │   │   ├── c6c48a394206279c
    │   │   ├── c709312a0a05d7bc
    │   │   ├── c71b0bb66f42f4a5
    │   │   ├── c7644a5519a8d98e
    │   │   ├── c7ac311da2bd855e
    │   │   ├── c7c42c47d19f99cb
    │   │   ├── c800f8ef01f55a7b
    │   │   ├── c82b29682e937b7b
    │   │   ├── c8591b63673d66b1
    │   │   ├── c89f6459c02bfb71
    │   │   ├── c930f287c3e89129
    │   │   ├── c9a665cbc52f4afd
    │   │   ├── c9b52eb3e02ceb73
    │   │   ├── c9f7cb466f0bcfee
    │   │   ├── ca4cf196a8f24204
    │   │   ├── cab099c680143df5
    │   │   ├── cac2f627788e70e2
    │   │   ├── cb01a8ae40887ba5
    │   │   ├── cb9eb4e4aa42c816
    │   │   ├── cc31acc7b295d3d9
    │   │   ├── cc326f96da5ce00e
    │   │   ├── cc391a72d77792cd
    │   │   ├── cc4b5175cb84a745
    │   │   ├── cc6f166e2163d02a
    │   │   ├── ccc5ff2ad1841593
    │   │   ├── cd15ec2e84072762
    │   │   ├── cd1adc7c09bd403c
    │   │   ├── cd595086ff8c3910
    │   │   ├── cd6bf4d42a86db27
    │   │   ├── ce66e0379693707b
    │   │   ├── ce951807a5dfe91a
    │   │   ├── cece4c7351ad595d
    │   │   ├── cefc921df1ff9d39
    │   │   ├── cf540f910aad5674
    │   │   ├── cfa71708e254bbfb
    │   │   ├── cfad690190ebb528
    │   │   ├── cfc133427c84139a
    │   │   ├── d012f3b46b3f159e
    │   │   ├── d06743505232bb24
    │   │   ├── d0ab0df247c0ef3f
    │   │   ├── d151a1ce7c610324
    │   │   ├── d157a7a5d363036e
    │   │   ├── d15efe14b8b82aeb
    │   │   ├── d17252da711979bb
    │   │   ├── d189c16633edf929
    │   │   ├── d19e3fecd34e0ff2
    │   │   ├── d25fe81cd34d5012
    │   │   ├── d2660d8abec95268
    │   │   ├── d2d6b11e67526f91
    │   │   ├── d2f0f5408aae54d3
    │   │   ├── d2fc55bcd6a72b0a
    │   │   ├── d3f25523d963c90f
    │   │   ├── d4011e6fd3ef00d6
    │   │   ├── d4208e4fe6008606
    │   │   ├── d440ae043fae9ddc
    │   │   ├── d48fdf5ac98f96ae
    │   │   ├── d4fb3bebe4c8e598
    │   │   ├── d5085db5723ba8b5
    │   │   ├── d520ed548019f242
    │   │   ├── d5c0f9477898705b
    │   │   ├── d64e27b19ee696de
    │   │   ├── d65daabc63eee8b8
    │   │   ├── d72620da91ef36dd
    │   │   ├── d72b9cb5dc8976bb
    │   │   ├── d75267225e4e4e63
    │   │   ├── d774f3c88d41e5ce
    │   │   ├── d79f95a35ac81574
    │   │   ├── d7a5bd93cafe50ae
    │   │   ├── d7e71a44ab281688
    │   │   ├── d7f6f61da3436603
    │   │   ├── d835d91e0d6529a7
    │   │   ├── d83c1dfa08bb86e1
    │   │   ├── d86a46092d786dc6
    │   │   ├── d872275471087cf7
    │   │   ├── d8ee054381e21453
    │   │   ├── d9016fc2c0f33ff5
    │   │   ├── d99b19e60edf3bb9
    │   │   ├── d9a91cf2e6ecce23
    │   │   ├── d9af442e56c04520
    │   │   ├── d9fa3486aea8179e
    │   │   ├── da178c52e155e1b4
    │   │   ├── da7bf43364a579f5
    │   │   ├── dad47da15fe32f96
    │   │   ├── daee3e26985cc119
    │   │   ├── daf14d9eeddc030d
    │   │   ├── daff62273c215a16
    │   │   ├── db26caef3cd62450
    │   │   ├── db579ebb5a04b3ea
    │   │   ├── db57dded60326ce3
    │   │   ├── dbb8766283940707
    │   │   ├── dbd2b5971ff3ae13
    │   │   ├── dbdb96a8d4f48fb4
    │   │   ├── dbe89045204c7c8f
    │   │   ├── dc3c0c10407a5365
    │   │   ├── dc447c7b83071a7e
    │   │   ├── dce94acb96a11ce9
    │   │   ├── dd216d7461b4d693
    │   │   ├── ddbc8281dd1f63c8
    │   │   ├── ddfb98f74b35a689
    │   │   ├── de411ab9e45bd9c1
    │   │   ├── de525809c5949e70
    │   │   ├── de6d7e51357f2236
    │   │   ├── de734020e9c8f0b0
    │   │   ├── de84300ed4d874a0
    │   │   ├── de9e0b9fd68595fa
    │   │   ├── df05a283a7caa48f
    │   │   ├── df44fa9da38251ee
    │   │   ├── df48cf29e47e947b
    │   │   ├── df7072bb5ca1778c
    │   │   ├── dfab66368b279007
    │   │   ├── dfaed2a2d592aa3e
    │   │   ├── dfd04cfb1bbe9942
    │   │   ├── dffced06d1fde3e1
    │   │   ├── e01071867ad8847a
    │   │   ├── e08acebc43c2390b
    │   │   ├── e0dadc79a40998f0
    │   │   ├── e0ef9ac9f93e1a04
    │   │   ├── e160086d420d4b5a
    │   │   ├── e17274eda5592e23
    │   │   ├── e198420d34e2d0c7
    │   │   ├── e1a581363a7405c0
    │   │   ├── e1eb787dc7130dbf
    │   │   ├── e205a5acdd7b2dfb
    │   │   ├── e23a0431db0bec2e
    │   │   ├── e288ba8c28c853c6
    │   │   ├── e2bdae5ec5bd7ff7
    │   │   ├── e2d1a03bb72f77f5
    │   │   ├── e322613879d67c07
    │   │   ├── e382a32186af05a7
    │   │   ├── e40b4640b824e9eb
    │   │   ├── e40d9a3ff72dcb0f
    │   │   ├── e42cfb3d6c1284bc
    │   │   ├── e4ef26b5f1eff328
    │   │   ├── e4f301859afe3e3d
    │   │   ├── e4ffef2f5f51ecfd
    │   │   ├── e58bb45976c4fa86
    │   │   ├── e598781e796424c9
    │   │   ├── e5ab415e96647054
    │   │   ├── e5d92822842d26a5
    │   │   ├── e5f9ede31fa5508e
    │   │   ├── e5fe9afa7b005992
    │   │   ├── e6048cafba57b932
    │   │   ├── e6ab9ffdf7d6f335
    │   │   ├── e6ae3082a03e1e99
    │   │   ├── e6b2d1e1aab37297
    │   │   ├── e6c5ca33183a02de
    │   │   ├── e73c16b17d33d440
    │   │   ├── e764320760c61a43
    │   │   ├── e81e792267eae8a1
    │   │   ├── e82d47bf4b3b3c02
    │   │   ├── e900af4d0302c8dd
    │   │   ├── e91370462d0089d2
    │   │   ├── e94af4e6da587953
    │   │   ├── e9967157885e5f13
    │   │   ├── e9f19f24809281c2
    │   │   ├── e9f4def271d6d2f3
    │   │   ├── ea087f7fdd2d277c
    │   │   ├── ea0c05c6ff678ad2
    │   │   ├── ea0c51d213a9da3d
    │   │   ├── ea228b76acaeb0a6
    │   │   ├── ea4e49fae40b0415
    │   │   ├── ea8b82d291d7e362
    │   │   ├── eabfa207a6a53a1e
    │   │   ├── ead479b077c6fcd0
    │   │   ├── eb4dc5b9550f829e
    │   │   ├── eba4525602889f9c
    │   │   ├── ebb6e97f043d5673
    │   │   ├── ebc7e0d7e94de937
    │   │   ├── ebce60af1f6af204
    │   │   ├── ebd446e113e58cb7
    │   │   ├── ec4a5a957d56356d
    │   │   ├── ec619341d2e7049f
    │   │   ├── ed30d447a544b0bb
    │   │   ├── ed9abc44e0fcff95
    │   │   ├── edd3dde9025d3d64
    │   │   ├── edf5aacd6187662c
    │   │   ├── edfe24e7760c3ce4
    │   │   ├── ee52396b2cc57142
    │   │   ├── eee928b742dbfa0e
    │   │   ├── ef01fd3fdf94ef35
    │   │   ├── ef45554c298ca3c0
    │   │   ├── ef7da73e1eca5d62
    │   │   ├── efe34c6d2b637143
    │   │   ├── efe9625b89f32b8b
    │   │   ├── eff32708b25ab0b2
    │   │   ├── eff87d822782aa31
    │   │   ├── f0b22aa208203d4d
    │   │   ├── f0bb1dbec33a7ac5
    │   │   ├── f1aaa453d12b97a4
    │   │   ├── f232195b584f3ea7
    │   │   ├── f26f7958ba833015
    │   │   ├── f30490d255651cb6
    │   │   ├── f3137b19c321ef7b
    │   │   ├── f3d572a1e559ed34
    │   │   ├── f3da64c0ae5e4dfb
    │   │   ├── f3fa03266b3e226b
    │   │   ├── f4078d311da78e4a
    │   │   ├── f446f957101df4d1
    │   │   ├── f50350489e0b30d8
    │   │   ├── f53d9ddc361c2cc9
    │   │   ├── f549bd7d1db6a472
    │   │   ├── f585b06196a564ff
    │   │   ├── f5af7634c562ea02
    │   │   ├── f5d0165bea555079
    │   │   ├── f60ab13d3261ae5a
    │   │   ├── f642467501ec3553
    │   │   ├── f654154deb1fae36
    │   │   ├── f69b513f289cf622
    │   │   ├── f6bdd4bfd1ce9e55
    │   │   ├── f6cfb6f52e2be3e0
    │   │   ├── f6d49afb0d3397e1
    │   │   ├── f76720ab44bd0a01
    │   │   ├── f787dec9c7962669
    │   │   ├── f7afbd5db14c9102
    │   │   ├── f7c0e648a75f865a
    │   │   ├── f7ca12f2fac8d910
    │   │   ├── f804d037ba2ef5d5
    │   │   ├── f8f900da21695f4a
    │   │   ├── f910b3b9599e6af2
    │   │   ├── f9394f6c1bc39a61
    │   │   ├── f965b95ba9f41fef
    │   │   ├── f9e35d2c7a88601b
    │   │   ├── fa152c226efdab59
    │   │   ├── fa2e088897d20e66
    │   │   ├── fa35dc626897085f
    │   │   ├── fa905456266ce0a5
    │   │   ├── fab7230ffdafa5e2
    │   │   ├── fb14b314964a12ae
    │   │   ├── fb31ea37bda42d61
    │   │   ├── fb861829adc09aed
    │   │   ├── fbfc5fe651aeb3af
    │   │   ├── fcd3a54577b06275
    │   │   ├── fcf1612df6ce4b9a
    │   │   ├── fd34f8cb463b451f
    │   │   ├── fd4e2032dbac2b48
    │   │   ├── fe23fe7118140c59
    │   │   ├── fe2a092e89ba0cfd
    │   │   ├── ffaa7c064a54a967
    │   │   └── ffb7618eba2a9efc
    │   ├── tmp/
    │   │   ├── tmp022l6q1o
    │   │   ├── tmp04iqn21n
    │   │   ├── tmp05tjv27w
    │   │   ├── tmp0admjxcn
    │   │   ├── tmp0ayp2fdd
    │   │   ├── tmp0g40na8t
    │   │   ├── tmp0lvgdv4v
    │   │   ├── tmp0nuaq5oa
    │   │   ├── tmp0rnknl4v
    │   │   ├── tmp0zypkjjs
    │   │   ├── tmp18wx_klp
    │   │   ├── tmp1kgco1s5
    │   │   ├── tmp1pkh1a03
    │   │   ├── tmp1q6yw4rr
    │   │   ├── tmp1sac3yqj
    │   │   ├── tmp2k8pirjf
    │   │   ├── tmp2ldyqqj5
    │   │   ├── tmp2qgqvxlg
    │   │   ├── tmp2rvt3p8x
    │   │   ├── tmp2vlpzsmk
    │   │   ├── tmp2vyjhwfw
    │   │   ├── tmp30_gfhqv
    │   │   ├── tmp35lapczm
    │   │   ├── tmp36yrwkg2
    │   │   ├── tmp38mfaipt
    │   │   ├── tmp3bz8nvim
    │   │   ├── tmp3h3z6k2b
    │   │   ├── tmp3hekdoky
    │   │   ├── tmp3trl9c5q
    │   │   ├── tmp3w0_gv9t
    │   │   ├── tmp3wlozpa0
    │   │   ├── tmp40zdk18y
    │   │   ├── tmp48k1a7xa
    │   │   ├── tmp49_zu3s_
    │   │   ├── tmp4atn3cn6
    │   │   ├── tmp4cofyj3t
    │   │   ├── tmp4dp_ss9k
    │   │   ├── tmp4et95rhs
    │   │   ├── tmp4gsie85u
    │   │   ├── tmp4ogqwo0k
    │   │   ├── tmp4t9j3qo0
    │   │   ├── tmp4vl3g1jk
    │   │   ├── tmp599f7vj7
    │   │   ├── tmp5litfm_4
    │   │   ├── tmp5mdwpf4l
    │   │   ├── tmp5tfo7yi9
    │   │   ├── tmp5ultttsu
    │   │   ├── tmp5yl5jctk
    │   │   ├── tmp64wfuvkf
    │   │   ├── tmp65c4wwqx
    │   │   ├── tmp67qca0va
    │   │   ├── tmp6_cvur9b
    │   │   ├── tmp6_xiygz0
    │   │   ├── tmp6b6ay7g8
    │   │   ├── tmp6fgfnkn0
    │   │   ├── tmp6kvtishq
    │   │   ├── tmp6p1pqn3u
    │   │   ├── tmp6thup75u
    │   │   ├── tmp6w20bgzg
    │   │   ├── tmp6wovmh39
    │   │   ├── tmp6x5inrah
    │   │   ├── tmp70jv4dyp
    │   │   ├── tmp72issb51
    │   │   ├── tmp74mimy6s
    │   │   ├── tmp74z7ay0z
    │   │   ├── tmp7f56fs5n
    │   │   ├── tmp7gqgpxpb
    │   │   ├── tmp7j6v5zbs
    │   │   ├── tmp7mt9oziu
    │   │   ├── tmp7obhul4a
    │   │   ├── tmp7rru1p48
    │   │   ├── tmp7ub1752s
    │   │   ├── tmp7x_5oxnb
    │   │   ├── tmp7yqzoxzc
    │   │   ├── tmp81kmiogc
    │   │   ├── tmp832xux0r
    │   │   ├── tmp848395e5
    │   │   ├── tmp84ygu9lp
    │   │   ├── tmp872ui707
    │   │   ├── tmp89cevlke
    │   │   ├── tmp8c64kt9b
    │   │   ├── tmp8ik_iaml
    │   │   ├── tmp8szkjy7w
    │   │   ├── tmp8tdp2lze
    │   │   ├── tmp8ts4b0t0
    │   │   ├── tmp8vbveq0q
    │   │   ├── tmp8xugc9w0
    │   │   ├── tmp90oky5d3
    │   │   ├── tmp91l1dqpr
    │   │   ├── tmp92l1q3bk
    │   │   ├── tmp99qto5pg
    │   │   ├── tmp9_0_762e
    │   │   ├── tmp9aq31fff
    │   │   ├── tmp9h6irems
    │   │   ├── tmp9olv9mia
    │   │   ├── tmp_194n6jh
    │   │   ├── tmp_du_7p02
    │   │   ├── tmp_h2_2fb1
    │   │   ├── tmp_lyd0udd
    │   │   ├── tmp_rf95buf
    │   │   ├── tmp_t60k90c
    │   │   ├── tmpa2h808nh
    │   │   ├── tmpagnm86kp
    │   │   ├── tmpagukft_r
    │   │   ├── tmpal9_a2tf
    │   │   ├── tmpamp5vwup
    │   │   ├── tmpatcrhej4
    │   │   ├── tmpb2nysu4m
    │   │   ├── tmpb35pathv
    │   │   ├── tmpb3_xcgbi
    │   │   ├── tmpbb3brjtp
    │   │   ├── tmpbcmmo23j
    │   │   ├── tmpbgbt1y2x
    │   │   ├── tmpblsvrutb
    │   │   ├── tmpbo_3m23l
    │   │   ├── tmpbp5_gp9i
    │   │   ├── tmpbpaf0b3m
    │   │   ├── tmpbpro6oj0
    │   │   ├── tmpbq86wsbs
    │   │   ├── tmpbqqj_ve8
    │   │   ├── tmpbvkdg56u
    │   │   ├── tmpbwalcyhb
    │   │   ├── tmpbwk0tufy
    │   │   ├── tmpbzamizyi
    │   │   ├── tmpc30xpuse
    │   │   ├── tmpcd3r9pka
    │   │   ├── tmpcfrs0fsr
    │   │   ├── tmpcis6gilx
    │   │   ├── tmpcos738rn
    │   │   ├── tmpcuqh3ekb
    │   │   ├── tmpcyfm2c6j
    │   │   ├── tmpd06z0q6j
    │   │   ├── tmpd2j8p93e
    │   │   ├── tmpd83mea9i
    │   │   ├── tmpdbznzdno
    │   │   ├── tmpdesyibc1
    │   │   ├── tmpdi3vcpas
    │   │   ├── tmpdk5gfbnz
    │   │   ├── tmpdoydcyqj
    │   │   ├── tmpdqrw54pt
    │   │   ├── tmpdr08rz1t
    │   │   ├── tmpdyb0n52j
    │   │   ├── tmpe677eqpz
    │   │   ├── tmpes_w92j_
    │   │   ├── tmpexcbwdvi
    │   │   ├── tmpey5ldpm2
    │   │   ├── tmpey8bx0ve
    │   │   ├── tmpf3uyxm1d
    │   │   ├── tmpfcfpurlv
    │   │   ├── tmpfjafq2x7
    │   │   ├── tmpflmeczu8
    │   │   ├── tmpfn1tt4yi
    │   │   ├── tmpfn2mb2o4
    │   │   ├── tmpfnfxrzuv
    │   │   ├── tmpg1g4uex9
    │   │   ├── tmpg4unbb3g
    │   │   ├── tmpg_c8gyw5
    │   │   ├── tmpgbxsmj_g
    │   │   ├── tmpgko1al7m
    │   │   ├── tmpgkz2my19
    │   │   ├── tmpgpzaaiug
    │   │   ├── tmpgqv28f8m
    │   │   ├── tmpgrgqsq0r
    │   │   ├── tmph07a4o91
    │   │   ├── tmph07g2xhl
    │   │   ├── tmph9_hbfra
    │   │   ├── tmphb4oktko
    │   │   ├── tmphbmud2bi
    │   │   ├── tmphi0e3tj0
    │   │   ├── tmphij_cjji
    │   │   ├── tmphn_3stl8
    │   │   ├── tmphplf65xf
    │   │   ├── tmphrat0690
    │   │   ├── tmphw7p6iaf
    │   │   ├── tmphx5xc9mg
    │   │   ├── tmphxbw8d5z
    │   │   ├── tmphzt17cuy
    │   │   ├── tmpi04qd7sp
    │   │   ├── tmpi2jbn3k7
    │   │   ├── tmpi4wcpd8f
    │   │   ├── tmpifb2fmlf
    │   │   ├── tmpiqcjl28c
    │   │   ├── tmpiqrays03
    │   │   ├── tmpisk2y_ob
    │   │   ├── tmpix3wr77z
    │   │   ├── tmpj38jx1ne
    │   │   ├── tmpj5o252zd
    │   │   ├── tmpj69h19j5
    │   │   ├── tmpj732zg9t
    │   │   ├── tmpjce7im7s
    │   │   ├── tmpjckkoeuj
    │   │   ├── tmpjhmb0ujm
    │   │   ├── tmpju4dlkyk
    │   │   ├── tmpju_2nvc2
    │   │   ├── tmpk3vm0c1p
    │   │   ├── tmpk8m3oh89
    │   │   ├── tmpkafrmg6z
    │   │   ├── tmpkcadn8q1
    │   │   ├── tmpkdg8hgmv
    │   │   ├── tmpkfm1usjg
    │   │   ├── tmpkj_xirb4
    │   │   ├── tmpkq8due9s
    │   │   ├── tmpkquhckjf
    │   │   ├── tmpkrgfbhau
    │   │   ├── tmpkwa1_pxo
    │   │   ├── tmpkxn0jy2l
    │   │   ├── tmpl13evlbb
    │   │   ├── tmpl4y4qei2
    │   │   ├── tmple_o5g43
    │   │   ├── tmplgbekxu1
    │   │   ├── tmpli8__ge3
    │   │   ├── tmplowv85n7
    │   │   ├── tmplss1muf4
    │   │   ├── tmplul6vic1
    │   │   ├── tmplyl7ng5p
    │   │   ├── tmpm3fwyzik
    │   │   ├── tmpmaencqc2
    │   │   ├── tmpmetrrcui
    │   │   ├── tmpmgq8si3_
    │   │   ├── tmpmldbnwck
    │   │   ├── tmpmwhqjqmp
    │   │   ├── tmpmzlnfww6
    │   │   ├── tmpn5mx6ioo
    │   │   ├── tmpn7rx1n9c
    │   │   ├── tmpn9dfp5a5
    │   │   ├── tmpndbo3dqu
    │   │   ├── tmpnh9d4tkf
    │   │   ├── tmpnke9zeyx
    │   │   ├── tmpnlyv55lo
    │   │   ├── tmpnp4j7bqu
    │   │   ├── tmpo6qc9lcq
    │   │   ├── tmpo6xfxmvl
    │   │   ├── tmpob3c44fg
    │   │   ├── tmpogwf4r3z
    │   │   ├── tmpoh9tl6ci
    │   │   ├── tmpokvgorhe
    │   │   ├── tmpolq6dujv
    │   │   ├── tmpom__ahuh
    │   │   ├── tmpopsbibgj
    │   │   ├── tmpoqg4y83r
    │   │   ├── tmpoy2lnn4t
    │   │   ├── tmpp0kc_grp
    │   │   ├── tmpp7_js049
    │   │   ├── tmppf0rgcxn
    │   │   ├── tmppkbu82k1
    │   │   ├── tmppqv6jxhb
    │   │   ├── tmppvmws5_v
    │   │   ├── tmppzuo201n
    │   │   ├── tmpq09epiev
    │   │   ├── tmpq_8u_xsl
    │   │   ├── tmpqcds2mf2
    │   │   ├── tmpqhaqra6z
    │   │   ├── tmpqiapek4b
    │   │   ├── tmpqlgze6ze
    │   │   ├── tmpquwkjwhy
    │   │   ├── tmpqx_638zl
    │   │   ├── tmpr424t_t1
    │   │   ├── tmpr4n8hyac
    │   │   ├── tmprasi6vqk
    │   │   ├── tmprcnzvokd
    │   │   ├── tmpre0_4mjk
    │   │   ├── tmprf2h2pha
    │   │   ├── tmprm_s07aa
    │   │   ├── tmprr0zagw3
    │   │   ├── tmprwploznp
    │   │   ├── tmprxgcg34z
    │   │   ├── tmps3cztcz8
    │   │   ├── tmps_do0e03
    │   │   ├── tmpsatn9whk
    │   │   ├── tmpsimcb71q
    │   │   ├── tmpsnp0eb2p
    │   │   ├── tmpspax5vj4
    │   │   ├── tmpt8a_ounw
    │   │   ├── tmptb4wj3o6
    │   │   ├── tmptg8ai5bg
    │   │   ├── tmptorduhzt
    │   │   ├── tmptv8j3_0t
    │   │   ├── tmpu1bpkjj5
    │   │   ├── tmpu1ts1b1f
    │   │   ├── tmpu4obikc0
    │   │   ├── tmpu6gte1pn
    │   │   ├── tmpu9y6_gbq
    │   │   ├── tmpub9929pl
    │   │   ├── tmpudappe5u
    │   │   ├── tmpul9ad_tc
    │   │   ├── tmpurxu6_5w
    │   │   ├── tmpv45mnzkv
    │   │   ├── tmpv81nxno0
    │   │   ├── tmpv9k3fnec
    │   │   ├── tmpv9r5kg40
    │   │   ├── tmpvfxlc8dz
    │   │   ├── tmpvjwoqacw
    │   │   ├── tmpvnz0hn9o
    │   │   ├── tmpvpwn3daa
    │   │   ├── tmpvqhzmfoc
    │   │   ├── tmpwd99gu_x
    │   │   ├── tmpwgk2h_tt
    │   │   ├── tmpwv68cf3s
    │   │   ├── tmpx1q9f3d5
    │   │   ├── tmpx2uvuajx
    │   │   ├── tmpxcmydmy2
    │   │   ├── tmpxhshxlnq
    │   │   ├── tmpxlsa2o6f
    │   │   ├── tmpxt2041br
    │   │   ├── tmpxtd7gju1
    │   │   ├── tmpy0ghtp1v
    │   │   ├── tmpy0qrvph7
    │   │   ├── tmpy5y85aie
    │   │   ├── tmpym_mnch3
    │   │   ├── tmpyvj1rz_h
    │   │   ├── tmpyvmwwcf2
    │   │   ├── tmpyxcs8vjw
    │   │   ├── tmpyxyfb5qh
    │   │   ├── tmpyz1tds34
    │   │   ├── tmpz0u77923
    │   │   ├── tmpz3hdvdhv
    │   │   ├── tmpz4hzng9a
    │   │   ├── tmpz5edqqh5
    │   │   ├── tmpzdupor62
    │   │   ├── tmpzmop7qfd
    │   │   ├── tmpzt3r68cl
    │   │   ├── tmpzwingkjq
    │   │   └── tmpzz6nq6ct
    │   └── unicode_data/
    │       └── 15.1.0/
    │           ├── charmap.json.gz
    │           └── codec-utf-8.json.gz
    ├── .idea/
    │   ├── dictionaries/
    │   │   └── project.xml
    │   ├── inspectionProfiles/
    │   │   └── profiles_settings.xml
    │   ├── stylesheetLinters/
    │   │   └── stylelint.xml
    │   ├── .gitignore
    │   ├── BioactivityDataAcquisition2.iml
    │   ├── codex.xml
    │   ├── copilot.data.migration.agent.xml
    │   ├── copilot.data.migration.ask.xml
    │   ├── copilot.data.migration.ask2agent.xml
    │   ├── copilot.data.migration.edit.xml
    │   ├── csv-editor.xml
    │   ├── misc.xml
    │   ├── modules.xml
    │   ├── vcs.xml
    │   ├── webResources.xml
    │   └── workspace.xml
    ├── .import_linter_cache/
    │   ├── .gitignore
    │   ├── 020bf9a579f422a2334140ee2267ca0d0306daa1.data.json
    │   ├── CACHEDIR.TAG
    │   ├── bioetl.meta.json
    │   └── ffd35c0055ccf94f516de1a6a1eb6149bab5d4ab.data.json
    ├── .jules/
    │   └── bolt.md
    ├── .mypy_cache/
    │   ├── 3.11/
    │   │   ├── _pytest/
    │   │   │   ├── _code/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── code.data.json
    │   │   │   │   ├── code.meta.json
    │   │   │   │   ├── source.data.json
    │   │   │   │   └── source.meta.json
    │   │   │   ├── _io/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── pprint.data.json
    │   │   │   │   ├── pprint.meta.json
    │   │   │   │   ├── saferepr.data.json
    │   │   │   │   ├── saferepr.meta.json
    │   │   │   │   ├── terminalwriter.data.json
    │   │   │   │   ├── terminalwriter.meta.json
    │   │   │   │   ├── wcwidth.data.json
    │   │   │   │   └── wcwidth.meta.json
    │   │   │   ├── assertion/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── rewrite.data.json
    │   │   │   │   ├── rewrite.meta.json
    │   │   │   │   ├── truncate.data.json
    │   │   │   │   ├── truncate.meta.json
    │   │   │   │   ├── util.data.json
    │   │   │   │   └── util.meta.json
    │   │   │   ├── config/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── argparsing.data.json
    │   │   │   │   ├── argparsing.meta.json
    │   │   │   │   ├── compat.data.json
    │   │   │   │   ├── compat.meta.json
    │   │   │   │   ├── exceptions.data.json
    │   │   │   │   ├── exceptions.meta.json
    │   │   │   │   ├── findpaths.data.json
    │   │   │   │   └── findpaths.meta.json
    │   │   │   ├── mark/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── expression.data.json
    │   │   │   │   ├── expression.meta.json
    │   │   │   │   ├── structures.data.json
    │   │   │   │   └── structures.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _argcomplete.data.json
    │   │   │   ├── _argcomplete.meta.json
    │   │   │   ├── _version.data.json
    │   │   │   ├── _version.meta.json
    │   │   │   ├── cacheprovider.data.json
    │   │   │   ├── cacheprovider.meta.json
    │   │   │   ├── capture.data.json
    │   │   │   ├── capture.meta.json
    │   │   │   ├── compat.data.json
    │   │   │   ├── compat.meta.json
    │   │   │   ├── debugging.data.json
    │   │   │   ├── debugging.meta.json
    │   │   │   ├── deprecated.data.json
    │   │   │   ├── deprecated.meta.json
    │   │   │   ├── doctest.data.json
    │   │   │   ├── doctest.meta.json
    │   │   │   ├── fixtures.data.json
    │   │   │   ├── fixtures.meta.json
    │   │   │   ├── freeze_support.data.json
    │   │   │   ├── freeze_support.meta.json
    │   │   │   ├── helpconfig.data.json
    │   │   │   ├── helpconfig.meta.json
    │   │   │   ├── hookspec.data.json
    │   │   │   ├── hookspec.meta.json
    │   │   │   ├── legacypath.data.json
    │   │   │   ├── legacypath.meta.json
    │   │   │   ├── logging.data.json
    │   │   │   ├── logging.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── monkeypatch.data.json
    │   │   │   ├── monkeypatch.meta.json
    │   │   │   ├── nodes.data.json
    │   │   │   ├── nodes.meta.json
    │   │   │   ├── outcomes.data.json
    │   │   │   ├── outcomes.meta.json
    │   │   │   ├── pathlib.data.json
    │   │   │   ├── pathlib.meta.json
    │   │   │   ├── pytester.data.json
    │   │   │   ├── pytester.meta.json
    │   │   │   ├── pytester_assertions.data.json
    │   │   │   ├── pytester_assertions.meta.json
    │   │   │   ├── python.data.json
    │   │   │   ├── python.meta.json
    │   │   │   ├── python_api.data.json
    │   │   │   ├── python_api.meta.json
    │   │   │   ├── raises.data.json
    │   │   │   ├── raises.meta.json
    │   │   │   ├── recwarn.data.json
    │   │   │   ├── recwarn.meta.json
    │   │   │   ├── reports.data.json
    │   │   │   ├── reports.meta.json
    │   │   │   ├── runner.data.json
    │   │   │   ├── runner.meta.json
    │   │   │   ├── scope.data.json
    │   │   │   ├── scope.meta.json
    │   │   │   ├── stash.data.json
    │   │   │   ├── stash.meta.json
    │   │   │   ├── subtests.data.json
    │   │   │   ├── subtests.meta.json
    │   │   │   ├── terminal.data.json
    │   │   │   ├── terminal.meta.json
    │   │   │   ├── timing.data.json
    │   │   │   ├── timing.meta.json
    │   │   │   ├── tmpdir.data.json
    │   │   │   ├── tmpdir.meta.json
    │   │   │   ├── tracemalloc.data.json
    │   │   │   ├── tracemalloc.meta.json
    │   │   │   ├── unraisableexception.data.json
    │   │   │   ├── unraisableexception.meta.json
    │   │   │   ├── warning_types.data.json
    │   │   │   ├── warning_types.meta.json
    │   │   │   ├── warnings.data.json
    │   │   │   └── warnings.meta.json
    │   │   ├── _typeshed/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── importlib.data.json
    │   │   │   ├── importlib.meta.json
    │   │   │   ├── wsgi.data.json
    │   │   │   └── wsgi.meta.json
    │   │   ├── annotated_types/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── anyio/
    │   │   │   ├── _core/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _contextmanagers.data.json
    │   │   │   │   ├── _contextmanagers.meta.json
    │   │   │   │   ├── _eventloop.data.json
    │   │   │   │   ├── _eventloop.meta.json
    │   │   │   │   ├── _exceptions.data.json
    │   │   │   │   ├── _exceptions.meta.json
    │   │   │   │   ├── _fileio.data.json
    │   │   │   │   ├── _fileio.meta.json
    │   │   │   │   ├── _resources.data.json
    │   │   │   │   ├── _resources.meta.json
    │   │   │   │   ├── _signals.data.json
    │   │   │   │   ├── _signals.meta.json
    │   │   │   │   ├── _sockets.data.json
    │   │   │   │   ├── _sockets.meta.json
    │   │   │   │   ├── _streams.data.json
    │   │   │   │   ├── _streams.meta.json
    │   │   │   │   ├── _subprocesses.data.json
    │   │   │   │   ├── _subprocesses.meta.json
    │   │   │   │   ├── _synchronization.data.json
    │   │   │   │   ├── _synchronization.meta.json
    │   │   │   │   ├── _tasks.data.json
    │   │   │   │   ├── _tasks.meta.json
    │   │   │   │   ├── _tempfile.data.json
    │   │   │   │   ├── _tempfile.meta.json
    │   │   │   │   ├── _testing.data.json
    │   │   │   │   ├── _testing.meta.json
    │   │   │   │   ├── _typedattr.data.json
    │   │   │   │   └── _typedattr.meta.json
    │   │   │   ├── abc/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _eventloop.data.json
    │   │   │   │   ├── _eventloop.meta.json
    │   │   │   │   ├── _resources.data.json
    │   │   │   │   ├── _resources.meta.json
    │   │   │   │   ├── _sockets.data.json
    │   │   │   │   ├── _sockets.meta.json
    │   │   │   │   ├── _streams.data.json
    │   │   │   │   ├── _streams.meta.json
    │   │   │   │   ├── _subprocesses.data.json
    │   │   │   │   ├── _subprocesses.meta.json
    │   │   │   │   ├── _tasks.data.json
    │   │   │   │   ├── _tasks.meta.json
    │   │   │   │   ├── _testing.data.json
    │   │   │   │   └── _testing.meta.json
    │   │   │   ├── streams/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── memory.data.json
    │   │   │   │   ├── memory.meta.json
    │   │   │   │   ├── stapled.data.json
    │   │   │   │   ├── stapled.meta.json
    │   │   │   │   ├── tls.data.json
    │   │   │   │   └── tls.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── from_thread.data.json
    │   │   │   ├── from_thread.meta.json
    │   │   │   ├── lowlevel.data.json
    │   │   │   ├── lowlevel.meta.json
    │   │   │   ├── to_thread.data.json
    │   │   │   └── to_thread.meta.json
    │   │   ├── arro3/
    │   │   │   └── core/
    │   │   │       ├── __init__.data.json
    │   │   │       ├── __init__.meta.json
    │   │   │       ├── _array.data.json
    │   │   │       ├── _array.meta.json
    │   │   │       ├── _array_reader.data.json
    │   │   │       ├── _array_reader.meta.json
    │   │   │       ├── _buffer.data.json
    │   │   │       ├── _buffer.meta.json
    │   │   │       ├── _chunked_array.data.json
    │   │   │       ├── _chunked_array.meta.json
    │   │   │       ├── _core.data.json
    │   │   │       ├── _core.meta.json
    │   │   │       ├── _data_type.data.json
    │   │   │       ├── _data_type.meta.json
    │   │   │       ├── _field.data.json
    │   │   │       ├── _field.meta.json
    │   │   │       ├── _record_batch.data.json
    │   │   │       ├── _record_batch.meta.json
    │   │   │       ├── _record_batch_reader.data.json
    │   │   │       ├── _record_batch_reader.meta.json
    │   │   │       ├── _scalar.data.json
    │   │   │       ├── _scalar.meta.json
    │   │   │       ├── _schema.data.json
    │   │   │       ├── _schema.meta.json
    │   │   │       ├── _table.data.json
    │   │   │       ├── _table.meta.json
    │   │   │       ├── types.data.json
    │   │   │       └── types.meta.json
    │   │   ├── asyncio/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── base_events.data.json
    │   │   │   ├── base_events.meta.json
    │   │   │   ├── base_futures.data.json
    │   │   │   ├── base_futures.meta.json
    │   │   │   ├── constants.data.json
    │   │   │   ├── constants.meta.json
    │   │   │   ├── coroutines.data.json
    │   │   │   ├── coroutines.meta.json
    │   │   │   ├── events.data.json
    │   │   │   ├── events.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── futures.data.json
    │   │   │   ├── futures.meta.json
    │   │   │   ├── locks.data.json
    │   │   │   ├── locks.meta.json
    │   │   │   ├── mixins.data.json
    │   │   │   ├── mixins.meta.json
    │   │   │   ├── proactor_events.data.json
    │   │   │   ├── proactor_events.meta.json
    │   │   │   ├── protocols.data.json
    │   │   │   ├── protocols.meta.json
    │   │   │   ├── queues.data.json
    │   │   │   ├── queues.meta.json
    │   │   │   ├── runners.data.json
    │   │   │   ├── runners.meta.json
    │   │   │   ├── selector_events.data.json
    │   │   │   ├── selector_events.meta.json
    │   │   │   ├── streams.data.json
    │   │   │   ├── streams.meta.json
    │   │   │   ├── subprocess.data.json
    │   │   │   ├── subprocess.meta.json
    │   │   │   ├── taskgroups.data.json
    │   │   │   ├── taskgroups.meta.json
    │   │   │   ├── tasks.data.json
    │   │   │   ├── tasks.meta.json
    │   │   │   ├── threads.data.json
    │   │   │   ├── threads.meta.json
    │   │   │   ├── timeouts.data.json
    │   │   │   ├── timeouts.meta.json
    │   │   │   ├── transports.data.json
    │   │   │   ├── transports.meta.json
    │   │   │   ├── unix_events.data.json
    │   │   │   ├── unix_events.meta.json
    │   │   │   ├── windows_events.data.json
    │   │   │   ├── windows_events.meta.json
    │   │   │   ├── windows_utils.data.json
    │   │   │   └── windows_utils.meta.json
    │   │   ├── attr/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _cmp.data.json
    │   │   │   ├── _cmp.meta.json
    │   │   │   ├── _typing_compat.data.json
    │   │   │   ├── _typing_compat.meta.json
    │   │   │   ├── _version_info.data.json
    │   │   │   ├── _version_info.meta.json
    │   │   │   ├── converters.data.json
    │   │   │   ├── converters.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── filters.data.json
    │   │   │   ├── filters.meta.json
    │   │   │   ├── setters.data.json
    │   │   │   ├── setters.meta.json
    │   │   │   ├── validators.data.json
    │   │   │   └── validators.meta.json
    │   │   ├── attrs/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── bioetl/
    │   │   │   ├── application/
    │   │   │   │   ├── composite/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── aggregator.data.json
    │   │   │   │   │   ├── aggregator.meta.json
    │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   ├── column_orderer.data.json
    │   │   │   │   │   ├── column_orderer.meta.json
    │   │   │   │   │   ├── column_renamer.data.json
    │   │   │   │   │   ├── column_renamer.meta.json
    │   │   │   │   │   ├── coordinator.data.json
    │   │   │   │   │   ├── coordinator.meta.json
    │   │   │   │   │   ├── deduplication.data.json
    │   │   │   │   │   ├── deduplication.meta.json
    │   │   │   │   │   ├── dependency_coordinator.data.json
    │   │   │   │   │   ├── dependency_coordinator.meta.json
    │   │   │   │   │   ├── fsm_helper.data.json
    │   │   │   │   │   ├── fsm_helper.meta.json
    │   │   │   │   │   ├── key_extractor.data.json
    │   │   │   │   │   ├── key_extractor.meta.json
    │   │   │   │   │   ├── merger.data.json
    │   │   │   │   │   ├── merger.meta.json
    │   │   │   │   │   ├── preflight_validator.data.json
    │   │   │   │   │   ├── preflight_validator.meta.json
    │   │   │   │   │   ├── runner.data.json
    │   │   │   │   │   ├── runner.meta.json
    │   │   │   │   │   ├── runner_helpers.data.json
    │   │   │   │   │   └── runner_helpers.meta.json
    │   │   │   │   ├── core/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── base_transformer.data.json
    │   │   │   │   │   ├── base_transformer.meta.json
    │   │   │   │   │   ├── batch_executor.data.json
    │   │   │   │   │   ├── batch_executor.meta.json
    │   │   │   │   │   ├── batch_metrics.data.json
    │   │   │   │   │   ├── batch_metrics.meta.json
    │   │   │   │   │   ├── batch_tracing.data.json
    │   │   │   │   │   ├── batch_tracing.meta.json
    │   │   │   │   │   ├── batch_transformer.data.json
    │   │   │   │   │   ├── batch_transformer.meta.json
    │   │   │   │   │   ├── batch_writer.data.json
    │   │   │   │   │   ├── batch_writer.meta.json
    │   │   │   │   │   ├── checkpoint_manager.data.json
    │   │   │   │   │   ├── checkpoint_manager.meta.json
    │   │   │   │   │   ├── cleanup_service.data.json
    │   │   │   │   │   ├── cleanup_service.meta.json
    │   │   │   │   │   ├── config.data.json
    │   │   │   │   │   ├── config.meta.json
    │   │   │   │   │   ├── field_specs.data.json
    │   │   │   │   │   ├── field_specs.meta.json
    │   │   │   │   │   ├── filtered_data_source.data.json
    │   │   │   │   │   ├── filtered_data_source.meta.json
    │   │   │   │   │   ├── heartbeat.data.json
    │   │   │   │   │   ├── heartbeat.meta.json
    │   │   │   │   │   ├── idmapping_data_source.data.json
    │   │   │   │   │   ├── idmapping_data_source.meta.json
    │   │   │   │   │   ├── lock_manager.data.json
    │   │   │   │   │   ├── lock_manager.meta.json
    │   │   │   │   │   ├── pipeline_services.data.json
    │   │   │   │   │   ├── pipeline_services.meta.json
    │   │   │   │   │   ├── postrun_service.data.json
    │   │   │   │   │   ├── postrun_service.meta.json
    │   │   │   │   │   ├── preflight_service.data.json
    │   │   │   │   │   ├── preflight_service.meta.json
    │   │   │   │   │   ├── protocols.data.json
    │   │   │   │   │   ├── protocols.meta.json
    │   │   │   │   │   ├── publication_term_data_source.data.json
    │   │   │   │   │   ├── publication_term_data_source.meta.json
    │   │   │   │   │   ├── quarantine_manager.data.json
    │   │   │   │   │   ├── quarantine_manager.meta.json
    │   │   │   │   │   ├── record_processor.data.json
    │   │   │   │   │   ├── record_processor.meta.json
    │   │   │   │   │   ├── runner.data.json
    │   │   │   │   │   ├── runner.meta.json
    │   │   │   │   │   ├── shutdown.data.json
    │   │   │   │   │   ├── shutdown.meta.json
    │   │   │   │   │   ├── subcellular_fraction_data_source.data.json
    │   │   │   │   │   ├── subcellular_fraction_data_source.meta.json
    │   │   │   │   │   ├── transform_utils.data.json
    │   │   │   │   │   └── transform_utils.meta.json
    │   │   │   │   ├── observability/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── observer.data.json
    │   │   │   │   │   ├── observer.meta.json
    │   │   │   │   │   ├── span_helpers.data.json
    │   │   │   │   │   └── span_helpers.meta.json
    │   │   │   │   ├── pipelines/
    │   │   │   │   │   ├── chembl/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── activity.data.json
    │   │   │   │   │   │   ├── activity.meta.json
    │   │   │   │   │   │   ├── activity_transformer.data.json
    │   │   │   │   │   │   ├── activity_transformer.meta.json
    │   │   │   │   │   │   ├── assay.data.json
    │   │   │   │   │   │   ├── assay.meta.json
    │   │   │   │   │   │   ├── assay_parameters.data.json
    │   │   │   │   │   │   ├── assay_parameters.meta.json
    │   │   │   │   │   │   ├── assay_parameters_transformer.data.json
    │   │   │   │   │   │   ├── assay_parameters_transformer.meta.json
    │   │   │   │   │   │   ├── assay_transformer.data.json
    │   │   │   │   │   │   ├── assay_transformer.meta.json
    │   │   │   │   │   │   ├── base_chembl_transformer.data.json
    │   │   │   │   │   │   ├── base_chembl_transformer.meta.json
    │   │   │   │   │   │   ├── cell_line.data.json
    │   │   │   │   │   │   ├── cell_line.meta.json
    │   │   │   │   │   │   ├── cell_line_transformer.data.json
    │   │   │   │   │   │   ├── cell_line_transformer.meta.json
    │   │   │   │   │   │   ├── compound_record.data.json
    │   │   │   │   │   │   ├── compound_record.meta.json
    │   │   │   │   │   │   ├── compound_record_transformer.data.json
    │   │   │   │   │   │   ├── compound_record_transformer.meta.json
    │   │   │   │   │   │   ├── molecule.data.json
    │   │   │   │   │   │   ├── molecule.meta.json
    │   │   │   │   │   │   ├── molecule_transformer.data.json
    │   │   │   │   │   │   ├── molecule_transformer.meta.json
    │   │   │   │   │   │   ├── protein_class.data.json
    │   │   │   │   │   │   ├── protein_class.meta.json
    │   │   │   │   │   │   ├── protein_class_transformer.data.json
    │   │   │   │   │   │   ├── protein_class_transformer.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   ├── publication.meta.json
    │   │   │   │   │   │   ├── publication_similarity.data.json
    │   │   │   │   │   │   ├── publication_similarity.meta.json
    │   │   │   │   │   │   ├── publication_similarity_transformer.data.json
    │   │   │   │   │   │   ├── publication_similarity_transformer.meta.json
    │   │   │   │   │   │   ├── publication_term.data.json
    │   │   │   │   │   │   ├── publication_term.meta.json
    │   │   │   │   │   │   ├── publication_term_transformer.data.json
    │   │   │   │   │   │   ├── publication_term_transformer.meta.json
    │   │   │   │   │   │   ├── publication_transformer.data.json
    │   │   │   │   │   │   ├── publication_transformer.meta.json
    │   │   │   │   │   │   ├── subcellular_fraction.data.json
    │   │   │   │   │   │   ├── subcellular_fraction.meta.json
    │   │   │   │   │   │   ├── subcellular_fraction_transformer.data.json
    │   │   │   │   │   │   ├── subcellular_fraction_transformer.meta.json
    │   │   │   │   │   │   ├── target.data.json
    │   │   │   │   │   │   ├── target.meta.json
    │   │   │   │   │   │   ├── target_component.data.json
    │   │   │   │   │   │   ├── target_component.meta.json
    │   │   │   │   │   │   ├── target_component_transformer.data.json
    │   │   │   │   │   │   ├── target_component_transformer.meta.json
    │   │   │   │   │   │   ├── target_transformer.data.json
    │   │   │   │   │   │   ├── target_transformer.meta.json
    │   │   │   │   │   │   ├── tissue.data.json
    │   │   │   │   │   │   ├── tissue.meta.json
    │   │   │   │   │   │   ├── tissue_transformer.data.json
    │   │   │   │   │   │   └── tissue_transformer.meta.json
    │   │   │   │   │   ├── common/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── base_publication_transformer.data.json
    │   │   │   │   │   │   ├── base_publication_transformer.meta.json
    │   │   │   │   │   │   ├── extractors.data.json
    │   │   │   │   │   │   └── extractors.meta.json
    │   │   │   │   │   ├── crossref/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── author_extractors.data.json
    │   │   │   │   │   │   ├── author_extractors.meta.json
    │   │   │   │   │   │   ├── extractors.data.json
    │   │   │   │   │   │   ├── extractors.meta.json
    │   │   │   │   │   │   ├── reference_extractors.data.json
    │   │   │   │   │   │   ├── reference_extractors.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   └── transformer.meta.json
    │   │   │   │   │   ├── openalex/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── extractors.data.json
    │   │   │   │   │   │   ├── extractors.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   └── transformer.meta.json
    │   │   │   │   │   ├── pubchem/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── compound.data.json
    │   │   │   │   │   │   ├── compound.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   └── transformer.meta.json
    │   │   │   │   │   ├── pubmed/
    │   │   │   │   │   │   ├── extractors/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── abstract.data.json
    │   │   │   │   │   │   │   ├── abstract.meta.json
    │   │   │   │   │   │   │   ├── author.data.json
    │   │   │   │   │   │   │   ├── author.meta.json
    │   │   │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   │   │   ├── classification.data.json
    │   │   │   │   │   │   │   ├── classification.meta.json
    │   │   │   │   │   │   │   ├── date.data.json
    │   │   │   │   │   │   │   ├── date.meta.json
    │   │   │   │   │   │   │   ├── identifier.data.json
    │   │   │   │   │   │   │   └── identifier.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   ├── publication.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   ├── transformer.meta.json
    │   │   │   │   │   │   ├── xml_utils.data.json
    │   │   │   │   │   │   └── xml_utils.meta.json
    │   │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── extractors.data.json
    │   │   │   │   │   │   ├── extractors.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   └── transformer.meta.json
    │   │   │   │   │   ├── uniprot/
    │   │   │   │   │   │   ├── extractors/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── comments.data.json
    │   │   │   │   │   │   │   ├── comments.meta.json
    │   │   │   │   │   │   │   ├── crossrefs.data.json
    │   │   │   │   │   │   │   ├── crossrefs.meta.json
    │   │   │   │   │   │   │   ├── features.data.json
    │   │   │   │   │   │   │   ├── features.meta.json
    │   │   │   │   │   │   │   ├── genes.data.json
    │   │   │   │   │   │   │   ├── genes.meta.json
    │   │   │   │   │   │   │   ├── taxonomy.data.json
    │   │   │   │   │   │   │   ├── taxonomy.meta.json
    │   │   │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   │   │   └── utils.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── idmapping_transformer.data.json
    │   │   │   │   │   │   ├── idmapping_transformer.meta.json
    │   │   │   │   │   │   ├── protein.data.json
    │   │   │   │   │   │   ├── protein.meta.json
    │   │   │   │   │   │   ├── transformer.data.json
    │   │   │   │   │   │   └── transformer.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── generic.data.json
    │   │   │   │   │   └── generic.meta.json
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── dq/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── bronze_analyzer.data.json
    │   │   │   │   │   │   ├── bronze_analyzer.meta.json
    │   │   │   │   │   │   ├── gold_analyzer.data.json
    │   │   │   │   │   │   ├── gold_analyzer.meta.json
    │   │   │   │   │   │   ├── silver_analyzer.data.json
    │   │   │   │   │   │   ├── silver_analyzer.meta.json
    │   │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   │   └── utils.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── bronze_cleanup_service.data.json
    │   │   │   │   │   ├── bronze_cleanup_service.meta.json
    │   │   │   │   │   ├── checkpoint_service.data.json
    │   │   │   │   │   ├── checkpoint_service.meta.json
    │   │   │   │   │   ├── config_service.data.json
    │   │   │   │   │   ├── config_service.meta.json
    │   │   │   │   │   ├── data_quality_service.data.json
    │   │   │   │   │   ├── data_quality_service.meta.json
    │   │   │   │   │   ├── dq_metrics_calculator.data.json
    │   │   │   │   │   ├── dq_metrics_calculator.meta.json
    │   │   │   │   │   ├── dq_report_service.data.json
    │   │   │   │   │   ├── dq_report_service.meta.json
    │   │   │   │   │   ├── export_service.data.json
    │   │   │   │   │   ├── export_service.meta.json
    │   │   │   │   │   ├── health_service.data.json
    │   │   │   │   │   ├── health_service.meta.json
    │   │   │   │   │   ├── lock_service.data.json
    │   │   │   │   │   ├── lock_service.meta.json
    │   │   │   │   │   ├── medallion_lifecycle.data.json
    │   │   │   │   │   ├── medallion_lifecycle.meta.json
    │   │   │   │   │   ├── medallion_types.data.json
    │   │   │   │   │   ├── medallion_types.meta.json
    │   │   │   │   │   ├── metrics_service.data.json
    │   │   │   │   │   ├── metrics_service.meta.json
    │   │   │   │   │   ├── pipeline_runner_service.data.json
    │   │   │   │   │   ├── pipeline_runner_service.meta.json
    │   │   │   │   │   ├── quarantine_service.data.json
    │   │   │   │   │   ├── quarantine_service.meta.json
    │   │   │   │   │   ├── shutdown_service.data.json
    │   │   │   │   │   ├── shutdown_service.meta.json
    │   │   │   │   │   ├── vacuum_service.data.json
    │   │   │   │   │   └── vacuum_service.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── composition/
    │   │   │   │   ├── bootstrap/
    │   │   │   │   │   ├── assembly/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   │   ├── storage.data.json
    │   │   │   │   │   │   └── storage.meta.json
    │   │   │   │   │   ├── cli/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   │   ├── config.data.json
    │   │   │   │   │   │   ├── config.meta.json
    │   │   │   │   │   │   ├── health.data.json
    │   │   │   │   │   │   ├── health.meta.json
    │   │   │   │   │   │   ├── lock.data.json
    │   │   │   │   │   │   ├── lock.meta.json
    │   │   │   │   │   │   ├── metrics.data.json
    │   │   │   │   │   │   ├── metrics.meta.json
    │   │   │   │   │   │   ├── noop.data.json
    │   │   │   │   │   │   ├── noop.meta.json
    │   │   │   │   │   │   ├── storage.data.json
    │   │   │   │   │   │   └── storage.meta.json
    │   │   │   │   │   ├── runtime/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── assembly.data.json
    │   │   │   │   │   │   ├── assembly.meta.json
    │   │   │   │   │   │   ├── composite.data.json
    │   │   │   │   │   │   ├── composite.meta.json
    │   │   │   │   │   │   ├── observability.data.json
    │   │   │   │   │   │   ├── observability.meta.json
    │   │   │   │   │   │   ├── pipeline.data.json
    │   │   │   │   │   │   ├── pipeline.meta.json
    │   │   │   │   │   │   ├── runner.data.json
    │   │   │   │   │   │   └── runner.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── factories/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── data_source_factory.data.json
    │   │   │   │   │   ├── data_source_factory.meta.json
    │   │   │   │   │   ├── dq_factory.data.json
    │   │   │   │   │   ├── dq_factory.meta.json
    │   │   │   │   │   ├── http_client_factory.data.json
    │   │   │   │   │   ├── http_client_factory.meta.json
    │   │   │   │   │   ├── pipeline_factories.data.json
    │   │   │   │   │   ├── pipeline_factories.meta.json
    │   │   │   │   │   ├── pipeline_factory.data.json
    │   │   │   │   │   ├── pipeline_factory.meta.json
    │   │   │   │   │   ├── runner_factory.data.json
    │   │   │   │   │   ├── runner_factory.meta.json
    │   │   │   │   │   ├── services_factory.data.json
    │   │   │   │   │   ├── services_factory.meta.json
    │   │   │   │   │   ├── storage.data.json
    │   │   │   │   │   ├── storage.meta.json
    │   │   │   │   │   ├── storage_adapter.data.json
    │   │   │   │   │   ├── storage_adapter.meta.json
    │   │   │   │   │   ├── storage_factory.data.json
    │   │   │   │   │   ├── storage_factory.meta.json
    │   │   │   │   │   ├── transformer_factory.data.json
    │   │   │   │   │   └── transformer_factory.meta.json
    │   │   │   │   ├── providers/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── decorators.data.json
    │   │   │   │   │   ├── decorators.meta.json
    │   │   │   │   │   ├── loader.data.json
    │   │   │   │   │   ├── loader.meta.json
    │   │   │   │   │   ├── provider_registry.data.json
    │   │   │   │   │   ├── provider_registry.meta.json
    │   │   │   │   │   ├── registration.data.json
    │   │   │   │   │   └── registration.meta.json
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── metadata_coordinator.data.json
    │   │   │   │   │   ├── metadata_coordinator.meta.json
    │   │   │   │   │   ├── versioning.data.json
    │   │   │   │   │   └── versioning.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── bootstrap_contexts.data.json
    │   │   │   │   ├── bootstrap_contexts.meta.json
    │   │   │   │   ├── bootstrap_logger.data.json
    │   │   │   │   ├── bootstrap_logger.meta.json
    │   │   │   │   ├── builders.data.json
    │   │   │   │   ├── builders.meta.json
    │   │   │   │   ├── entrypoints.data.json
    │   │   │   │   ├── entrypoints.meta.json
    │   │   │   │   ├── observability.data.json
    │   │   │   │   ├── observability.meta.json
    │   │   │   │   ├── registry.data.json
    │   │   │   │   ├── registry.meta.json
    │   │   │   │   ├── types.data.json
    │   │   │   │   └── types.meta.json
    │   │   │   ├── domain/
    │   │   │   │   ├── aggregates/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── batch.data.json
    │   │   │   │   │   ├── batch.meta.json
    │   │   │   │   │   ├── events.data.json
    │   │   │   │   │   ├── events.meta.json
    │   │   │   │   │   ├── pipeline_run.data.json
    │   │   │   │   │   ├── pipeline_run.meta.json
    │   │   │   │   │   ├── quarantine_entry.data.json
    │   │   │   │   │   └── quarantine_entry.meta.json
    │   │   │   │   ├── composite/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── aggregation.data.json
    │   │   │   │   │   ├── aggregation.meta.json
    │   │   │   │   │   ├── config.data.json
    │   │   │   │   │   ├── config.meta.json
    │   │   │   │   │   ├── field_groups.data.json
    │   │   │   │   │   ├── field_groups.meta.json
    │   │   │   │   │   ├── lineage.data.json
    │   │   │   │   │   ├── lineage.meta.json
    │   │   │   │   │   ├── result.data.json
    │   │   │   │   │   ├── result.meta.json
    │   │   │   │   │   ├── state.data.json
    │   │   │   │   │   ├── state.meta.json
    │   │   │   │   │   ├── strategy.data.json
    │   │   │   │   │   └── strategy.meta.json
    │   │   │   │   ├── configs/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   └── base.meta.json
    │   │   │   │   ├── contracts/
    │   │   │   │   │   └── gold/
    │   │   │   │   │       ├── _base.data.json
    │   │   │   │   │       ├── _base.meta.json
    │   │   │   │   │       ├── composite.data.json
    │   │   │   │   │       ├── composite.meta.json
    │   │   │   │   │       ├── pubchem.data.json
    │   │   │   │   │       └── pubchem.meta.json
    │   │   │   │   ├── entities/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── bioactivity.data.json
    │   │   │   │   │   ├── bioactivity.meta.json
    │   │   │   │   │   ├── chembl.data.json
    │   │   │   │   │   ├── chembl.meta.json
    │   │   │   │   │   ├── chembl_activity.data.json
    │   │   │   │   │   ├── chembl_activity.meta.json
    │   │   │   │   │   ├── chembl_assay_parameters.data.json
    │   │   │   │   │   ├── chembl_assay_parameters.meta.json
    │   │   │   │   │   ├── chembl_compound_record.data.json
    │   │   │   │   │   ├── chembl_compound_record.meta.json
    │   │   │   │   │   ├── chembl_structures.data.json
    │   │   │   │   │   ├── chembl_structures.meta.json
    │   │   │   │   │   ├── chembl_subcellular_fraction.data.json
    │   │   │   │   │   ├── chembl_subcellular_fraction.meta.json
    │   │   │   │   │   ├── chembl_tissue.data.json
    │   │   │   │   │   ├── chembl_tissue.meta.json
    │   │   │   │   │   ├── crossref.data.json
    │   │   │   │   │   ├── crossref.meta.json
    │   │   │   │   │   ├── openalex.data.json
    │   │   │   │   │   ├── openalex.meta.json
    │   │   │   │   │   ├── pubchem.data.json
    │   │   │   │   │   ├── pubchem.meta.json
    │   │   │   │   │   ├── publication_base.data.json
    │   │   │   │   │   ├── publication_base.meta.json
    │   │   │   │   │   ├── pubmed.data.json
    │   │   │   │   │   ├── pubmed.meta.json
    │   │   │   │   │   ├── semanticscholar.data.json
    │   │   │   │   │   ├── semanticscholar.meta.json
    │   │   │   │   │   ├── uniprot.data.json
    │   │   │   │   │   └── uniprot.meta.json
    │   │   │   │   ├── exceptions/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── data_quality.data.json
    │   │   │   │   │   ├── data_quality.meta.json
    │   │   │   │   │   ├── infrastructure.data.json
    │   │   │   │   │   ├── infrastructure.meta.json
    │   │   │   │   │   ├── internal.data.json
    │   │   │   │   │   ├── internal.meta.json
    │   │   │   │   │   ├── network.data.json
    │   │   │   │   │   ├── network.meta.json
    │   │   │   │   │   ├── validation.data.json
    │   │   │   │   │   └── validation.meta.json
    │   │   │   │   ├── filtering/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── column_filter.data.json
    │   │   │   │   │   ├── column_filter.meta.json
    │   │   │   │   │   ├── gold_config.data.json
    │   │   │   │   │   ├── gold_config.meta.json
    │   │   │   │   │   ├── input_config.data.json
    │   │   │   │   │   ├── input_config.meta.json
    │   │   │   │   │   ├── list_filters.data.json
    │   │   │   │   │   ├── list_filters.meta.json
    │   │   │   │   │   ├── load_result.data.json
    │   │   │   │   │   ├── load_result.meta.json
    │   │   │   │   │   ├── range_filter.data.json
    │   │   │   │   │   └── range_filter.meta.json
    │   │   │   │   ├── mapping/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── publication_fields.data.json
    │   │   │   │   │   └── publication_fields.meta.json
    │   │   │   │   ├── models/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── metadata.data.json
    │   │   │   │   │   └── metadata.meta.json
    │   │   │   │   ├── ports/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── audit.data.json
    │   │   │   │   │   ├── audit.meta.json
    │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   ├── data_normalization.data.json
    │   │   │   │   │   ├── data_normalization.meta.json
    │   │   │   │   │   ├── data_source.data.json
    │   │   │   │   │   ├── data_source.meta.json
    │   │   │   │   │   ├── delta_reader.data.json
    │   │   │   │   │   ├── delta_reader.meta.json
    │   │   │   │   │   ├── dq_config.data.json
    │   │   │   │   │   ├── dq_config.meta.json
    │   │   │   │   │   ├── dq_report.data.json
    │   │   │   │   │   ├── dq_report.meta.json
    │   │   │   │   │   ├── filtering.data.json
    │   │   │   │   │   ├── filtering.meta.json
    │   │   │   │   │   ├── health_check.data.json
    │   │   │   │   │   ├── health_check.meta.json
    │   │   │   │   │   ├── idmapping.data.json
    │   │   │   │   │   ├── idmapping.meta.json
    │   │   │   │   │   ├── locking.data.json
    │   │   │   │   │   ├── locking.meta.json
    │   │   │   │   │   ├── memory.data.json
    │   │   │   │   │   ├── memory.meta.json
    │   │   │   │   │   ├── metadata.data.json
    │   │   │   │   │   ├── metadata.meta.json
    │   │   │   │   │   ├── metadata_coordinator.data.json
    │   │   │   │   │   ├── metadata_coordinator.meta.json
    │   │   │   │   │   ├── noop.data.json
    │   │   │   │   │   ├── noop.meta.json
    │   │   │   │   │   ├── normalization.data.json
    │   │   │   │   │   ├── normalization.meta.json
    │   │   │   │   │   ├── observability.data.json
    │   │   │   │   │   ├── observability.meta.json
    │   │   │   │   │   ├── pii.data.json
    │   │   │   │   │   ├── pii.meta.json
    │   │   │   │   │   ├── quarantine.data.json
    │   │   │   │   │   ├── quarantine.meta.json
    │   │   │   │   │   ├── resilience.data.json
    │   │   │   │   │   ├── resilience.meta.json
    │   │   │   │   │   ├── runner.data.json
    │   │   │   │   │   ├── runner.meta.json
    │   │   │   │   │   ├── serialization.data.json
    │   │   │   │   │   ├── serialization.meta.json
    │   │   │   │   │   ├── shutdown.data.json
    │   │   │   │   │   ├── shutdown.meta.json
    │   │   │   │   │   ├── storage.data.json
    │   │   │   │   │   ├── storage.meta.json
    │   │   │   │   │   ├── validation.data.json
    │   │   │   │   │   ├── validation.meta.json
    │   │   │   │   │   ├── watermark.data.json
    │   │   │   │   │   └── watermark.meta.json
    │   │   │   │   ├── registry/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   └── publication.meta.json
    │   │   │   │   ├── schemas/
    │   │   │   │   │   ├── chembl/
    │   │   │   │   │   │   ├── activity.data.json
    │   │   │   │   │   │   ├── activity.meta.json
    │   │   │   │   │   │   ├── assay.data.json
    │   │   │   │   │   │   ├── assay.meta.json
    │   │   │   │   │   │   ├── assay_parameters.data.json
    │   │   │   │   │   │   ├── assay_parameters.meta.json
    │   │   │   │   │   │   ├── cell_line.data.json
    │   │   │   │   │   │   ├── cell_line.meta.json
    │   │   │   │   │   │   ├── compound_record.data.json
    │   │   │   │   │   │   ├── compound_record.meta.json
    │   │   │   │   │   │   ├── molecule.data.json
    │   │   │   │   │   │   ├── molecule.meta.json
    │   │   │   │   │   │   ├── molecule_form.data.json
    │   │   │   │   │   │   ├── molecule_form.meta.json
    │   │   │   │   │   │   ├── protein_classification.data.json
    │   │   │   │   │   │   ├── protein_classification.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   ├── publication.meta.json
    │   │   │   │   │   │   ├── publication_similarity.data.json
    │   │   │   │   │   │   ├── publication_similarity.meta.json
    │   │   │   │   │   │   ├── publication_term.data.json
    │   │   │   │   │   │   ├── publication_term.meta.json
    │   │   │   │   │   │   ├── target.data.json
    │   │   │   │   │   │   ├── target.meta.json
    │   │   │   │   │   │   ├── target_component.data.json
    │   │   │   │   │   │   ├── target_component.meta.json
    │   │   │   │   │   │   ├── target_relation.data.json
    │   │   │   │   │   │   └── target_relation.meta.json
    │   │   │   │   │   ├── common/
    │   │   │   │   │   ├── crossref/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── author.data.json
    │   │   │   │   │   │   ├── author.meta.json
    │   │   │   │   │   │   ├── funder.data.json
    │   │   │   │   │   │   ├── funder.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   ├── publication.meta.json
    │   │   │   │   │   │   ├── reference.data.json
    │   │   │   │   │   │   ├── reference.meta.json
    │   │   │   │   │   │   ├── work.data.json
    │   │   │   │   │   │   └── work.meta.json
    │   │   │   │   │   ├── openalex/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   └── publication.meta.json
    │   │   │   │   │   ├── pubchem/
    │   │   │   │   │   │   ├── compound.data.json
    │   │   │   │   │   │   └── compound.meta.json
    │   │   │   │   │   ├── pubmed/
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   └── publication.meta.json
    │   │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── publication.data.json
    │   │   │   │   │   │   └── publication.meta.json
    │   │   │   │   │   ├── uniprot/
    │   │   │   │   │   │   ├── idmapping.data.json
    │   │   │   │   │   │   ├── idmapping.meta.json
    │   │   │   │   │   │   ├── isoform.data.json
    │   │   │   │   │   │   ├── isoform.meta.json
    │   │   │   │   │   │   ├── protein.data.json
    │   │   │   │   │   │   └── protein.meta.json
    │   │   │   │   │   ├── _field_orders.data.json
    │   │   │   │   │   ├── _field_orders.meta.json
    │   │   │   │   │   ├── chembl.data.json
    │   │   │   │   │   ├── chembl.meta.json
    │   │   │   │   │   ├── column_order.data.json
    │   │   │   │   │   ├── column_order.meta.json
    │   │   │   │   │   ├── constants.data.json
    │   │   │   │   │   ├── constants.meta.json
    │   │   │   │   │   ├── pubchem.data.json
    │   │   │   │   │   ├── pubchem.meta.json
    │   │   │   │   │   ├── pubmed.data.json
    │   │   │   │   │   ├── pubmed.meta.json
    │   │   │   │   │   ├── uniprot.data.json
    │   │   │   │   │   └── uniprot.meta.json
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── activity_aggregator.data.json
    │   │   │   │   │   ├── activity_aggregator.meta.json
    │   │   │   │   │   ├── data_normalization_config.data.json
    │   │   │   │   │   ├── data_normalization_config.meta.json
    │   │   │   │   │   ├── data_normalization_service.data.json
    │   │   │   │   │   ├── data_normalization_service.meta.json
    │   │   │   │   │   ├── dq_metrics_calculator.data.json
    │   │   │   │   │   ├── dq_metrics_calculator.meta.json
    │   │   │   │   │   ├── dq_serializer.data.json
    │   │   │   │   │   ├── dq_serializer.meta.json
    │   │   │   │   │   ├── identity_service.data.json
    │   │   │   │   │   ├── identity_service.meta.json
    │   │   │   │   │   ├── normalization_config.data.json
    │   │   │   │   │   ├── normalization_config.meta.json
    │   │   │   │   │   ├── normalization_service.data.json
    │   │   │   │   │   ├── normalization_service.meta.json
    │   │   │   │   │   ├── unit_converter.data.json
    │   │   │   │   │   ├── unit_converter.meta.json
    │   │   │   │   │   ├── value_validator.data.json
    │   │   │   │   │   └── value_validator.meta.json
    │   │   │   │   ├── value_objects/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── academic_ids.data.json
    │   │   │   │   │   ├── academic_ids.meta.json
    │   │   │   │   │   ├── activity.data.json
    │   │   │   │   │   ├── activity.meta.json
    │   │   │   │   │   ├── activity_values.data.json
    │   │   │   │   │   ├── activity_values.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── bronze_result.data.json
    │   │   │   │   │   ├── bronze_result.meta.json
    │   │   │   │   │   ├── chemical.data.json
    │   │   │   │   │   ├── chemical.meta.json
    │   │   │   │   │   ├── column_order.data.json
    │   │   │   │   │   ├── column_order.meta.json
    │   │   │   │   │   ├── column_qualifier.data.json
    │   │   │   │   │   ├── column_qualifier.meta.json
    │   │   │   │   │   ├── compound_ids.data.json
    │   │   │   │   │   ├── compound_ids.meta.json
    │   │   │   │   │   ├── dq_metrics.data.json
    │   │   │   │   │   ├── dq_metrics.meta.json
    │   │   │   │   │   ├── dq_report.data.json
    │   │   │   │   │   ├── dq_report.meta.json
    │   │   │   │   │   ├── dq_result.data.json
    │   │   │   │   │   ├── dq_result.meta.json
    │   │   │   │   │   ├── identifiers.data.json
    │   │   │   │   │   ├── identifiers.meta.json
    │   │   │   │   │   ├── publication_field_groups.data.json
    │   │   │   │   │   ├── publication_field_groups.meta.json
    │   │   │   │   │   ├── publications.data.json
    │   │   │   │   │   ├── publications.meta.json
    │   │   │   │   │   ├── run_context.data.json
    │   │   │   │   │   ├── run_context.meta.json
    │   │   │   │   │   ├── silver_result.data.json
    │   │   │   │   │   ├── silver_result.meta.json
    │   │   │   │   │   ├── taxonomy_id.data.json
    │   │   │   │   │   └── taxonomy_id.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   ├── config.meta.json
    │   │   │   │   ├── config_types.data.json
    │   │   │   │   ├── config_types.meta.json
    │   │   │   │   ├── constants.data.json
    │   │   │   │   ├── constants.meta.json
    │   │   │   │   ├── context.data.json
    │   │   │   │   ├── context.meta.json
    │   │   │   │   ├── error_classifier.data.json
    │   │   │   │   ├── error_classifier.meta.json
    │   │   │   │   ├── events.data.json
    │   │   │   │   ├── events.meta.json
    │   │   │   │   ├── locking.data.json
    │   │   │   │   ├── locking.meta.json
    │   │   │   │   ├── medallion.data.json
    │   │   │   │   ├── medallion.meta.json
    │   │   │   │   ├── normalization.data.json
    │   │   │   │   ├── normalization.meta.json
    │   │   │   │   ├── resilience.data.json
    │   │   │   │   ├── resilience.meta.json
    │   │   │   │   ├── serialization.data.json
    │   │   │   │   ├── serialization.meta.json
    │   │   │   │   ├── transformations.data.json
    │   │   │   │   ├── transformations.meta.json
    │   │   │   │   ├── types.data.json
    │   │   │   │   ├── types.meta.json
    │   │   │   │   ├── validation.data.json
    │   │   │   │   └── validation.meta.json
    │   │   │   ├── infrastructure/
    │   │   │   │   ├── adapters/
    │   │   │   │   │   ├── chembl/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── entity_mapper.data.json
    │   │   │   │   │   │   ├── entity_mapper.meta.json
    │   │   │   │   │   │   ├── exceptions.data.json
    │   │   │   │   │   │   ├── exceptions.meta.json
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   └── models.meta.json
    │   │   │   │   │   ├── common/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── api_request_collector.data.json
    │   │   │   │   │   │   ├── api_request_collector.meta.json
    │   │   │   │   │   │   ├── base_title_fallback.data.json
    │   │   │   │   │   │   ├── base_title_fallback.meta.json
    │   │   │   │   │   │   ├── title_matching.data.json
    │   │   │   │   │   │   └── title_matching.meta.json
    │   │   │   │   │   ├── crossref/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── batch.data.json
    │   │   │   │   │   │   ├── batch.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── exceptions.data.json
    │   │   │   │   │   │   ├── exceptions.meta.json
    │   │   │   │   │   │   ├── fallback.data.json
    │   │   │   │   │   │   ├── fallback.meta.json
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   └── models.meta.json
    │   │   │   │   │   ├── decorators/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── circuit_breaker.data.json
    │   │   │   │   │   │   ├── circuit_breaker.meta.json
    │   │   │   │   │   │   ├── retry.data.json
    │   │   │   │   │   │   └── retry.meta.json
    │   │   │   │   │   ├── http/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── circuit_breaker.data.json
    │   │   │   │   │   │   ├── circuit_breaker.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── health.data.json
    │   │   │   │   │   │   ├── health.meta.json
    │   │   │   │   │   │   ├── health_monitor.data.json
    │   │   │   │   │   │   ├── health_monitor.meta.json
    │   │   │   │   │   │   ├── pagination.data.json
    │   │   │   │   │   │   ├── pagination.meta.json
    │   │   │   │   │   │   ├── rate_limiter.data.json
    │   │   │   │   │   │   └── rate_limiter.meta.json
    │   │   │   │   │   ├── input/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── csv_filter_reader.data.json
    │   │   │   │   │   │   └── csv_filter_reader.meta.json
    │   │   │   │   │   ├── openalex/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── fallback.data.json
    │   │   │   │   │   │   └── fallback.meta.json
    │   │   │   │   │   ├── pubchem/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── entity_mapper.data.json
    │   │   │   │   │   │   ├── entity_mapper.meta.json
    │   │   │   │   │   │   ├── fetch_strategies.data.json
    │   │   │   │   │   │   ├── fetch_strategies.meta.json
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   └── models.meta.json
    │   │   │   │   │   ├── pubmed/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── fallback.data.json
    │   │   │   │   │   │   ├── fallback.meta.json
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   ├── models.meta.json
    │   │   │   │   │   │   ├── pubmed_client.data.json
    │   │   │   │   │   │   ├── pubmed_client.meta.json
    │   │   │   │   │   │   ├── xml_processor.data.json
    │   │   │   │   │   │   └── xml_processor.meta.json
    │   │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── adapter.data.json
    │   │   │   │   │   │   ├── adapter.meta.json
    │   │   │   │   │   │   ├── fallback.data.json
    │   │   │   │   │   │   └── fallback.meta.json
    │   │   │   │   │   ├── uniprot/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   │   ├── fasta_parser.data.json
    │   │   │   │   │   │   ├── fasta_parser.meta.json
    │   │   │   │   │   │   ├── idmapping_client.data.json
    │   │   │   │   │   │   ├── idmapping_client.meta.json
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   └── models.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── base_metrics.data.json
    │   │   │   │   │   ├── base_metrics.meta.json
    │   │   │   │   │   ├── error_handling.data.json
    │   │   │   │   │   ├── error_handling.meta.json
    │   │   │   │   │   ├── filterable_mixin.data.json
    │   │   │   │   │   ├── filterable_mixin.meta.json
    │   │   │   │   │   ├── health_check_mixin.data.json
    │   │   │   │   │   ├── health_check_mixin.meta.json
    │   │   │   │   │   ├── logging_utils.data.json
    │   │   │   │   │   ├── logging_utils.meta.json
    │   │   │   │   │   ├── sync_base.data.json
    │   │   │   │   │   ├── sync_base.meta.json
    │   │   │   │   │   ├── validation.data.json
    │   │   │   │   │   └── validation.meta.json
    │   │   │   │   ├── audit/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── file_audit.data.json
    │   │   │   │   │   └── file_audit.meta.json
    │   │   │   │   ├── checkpoint/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── local_checkpoint.data.json
    │   │   │   │   │   └── local_checkpoint.meta.json
    │   │   │   │   ├── config/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _base.data.json
    │   │   │   │   │   ├── _base.meta.json
    │   │   │   │   │   ├── base_config_loader.data.json
    │   │   │   │   │   ├── base_config_loader.meta.json
    │   │   │   │   │   ├── dq_config_loader.data.json
    │   │   │   │   │   ├── dq_config_loader.meta.json
    │   │   │   │   │   ├── field_group_loader.data.json
    │   │   │   │   │   ├── field_group_loader.meta.json
    │   │   │   │   │   ├── filter_config_loader.data.json
    │   │   │   │   │   ├── filter_config_loader.meta.json
    │   │   │   │   │   ├── pipeline_config_loader.data.json
    │   │   │   │   │   └── pipeline_config_loader.meta.json
    │   │   │   │   ├── export/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── csv_exporter.data.json
    │   │   │   │   │   ├── csv_exporter.meta.json
    │   │   │   │   │   ├── dq_report_writer.data.json
    │   │   │   │   │   └── dq_report_writer.meta.json
    │   │   │   │   ├── locking/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── memory_lock.data.json
    │   │   │   │   │   └── memory_lock.meta.json
    │   │   │   │   ├── observability/
    │   │   │   │   │   ├── anomaly/
    │   │   │   │   │   │   ├── detectors/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   │   │   ├── zscore.data.json
    │   │   │   │   │   │   │   └── zscore.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── detector.data.json
    │   │   │   │   │   │   ├── detector.meta.json
    │   │   │   │   │   │   ├── monitor.data.json
    │   │   │   │   │   │   ├── monitor.meta.json
    │   │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   │   └── types.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── logging.data.json
    │   │   │   │   │   ├── logging.meta.json
    │   │   │   │   │   ├── logging_config.data.json
    │   │   │   │   │   ├── logging_config.meta.json
    │   │   │   │   │   ├── metrics.data.json
    │   │   │   │   │   ├── metrics.meta.json
    │   │   │   │   │   ├── metrics_server_adapter.data.json
    │   │   │   │   │   ├── metrics_server_adapter.meta.json
    │   │   │   │   │   ├── noop_logger.data.json
    │   │   │   │   │   ├── noop_logger.meta.json
    │   │   │   │   │   ├── noop_metrics.data.json
    │   │   │   │   │   ├── noop_metrics.meta.json
    │   │   │   │   │   ├── noop_tracing.data.json
    │   │   │   │   │   ├── noop_tracing.meta.json
    │   │   │   │   │   ├── prometheus_metrics.data.json
    │   │   │   │   │   ├── prometheus_metrics.meta.json
    │   │   │   │   │   ├── server.data.json
    │   │   │   │   │   ├── server.meta.json
    │   │   │   │   │   ├── tracing.data.json
    │   │   │   │   │   ├── tracing.meta.json
    │   │   │   │   │   ├── unified_logger.data.json
    │   │   │   │   │   └── unified_logger.meta.json
    │   │   │   │   ├── quarantine/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── helpers.data.json
    │   │   │   │   │   ├── helpers.meta.json
    │   │   │   │   │   ├── operations.data.json
    │   │   │   │   │   ├── operations.meta.json
    │   │   │   │   │   ├── unified.data.json
    │   │   │   │   │   └── unified.meta.json
    │   │   │   │   ├── schemas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base_schemas.data.json
    │   │   │   │   │   ├── base_schemas.meta.json
    │   │   │   │   │   ├── composite_config.data.json
    │   │   │   │   │   ├── composite_config.meta.json
    │   │   │   │   │   ├── dq_config.data.json
    │   │   │   │   │   ├── dq_config.meta.json
    │   │   │   │   │   ├── dq_report_config.data.json
    │   │   │   │   │   ├── dq_report_config.meta.json
    │   │   │   │   │   ├── filter_config.data.json
    │   │   │   │   │   ├── filter_config.meta.json
    │   │   │   │   │   ├── pipeline_config.data.json
    │   │   │   │   │   ├── pipeline_config.meta.json
    │   │   │   │   │   ├── silver.data.json
    │   │   │   │   │   ├── silver.meta.json
    │   │   │   │   │   ├── source_config.data.json
    │   │   │   │   │   └── source_config.meta.json
    │   │   │   │   ├── security/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── pii_hasher.data.json
    │   │   │   │   │   └── pii_hasher.meta.json
    │   │   │   │   ├── serialization/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── encoders.data.json
    │   │   │   │   │   └── encoders.meta.json
    │   │   │   │   ├── storage/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _atomic.data.json
    │   │   │   │   │   ├── _atomic.meta.json
    │   │   │   │   │   ├── arrow_converter.data.json
    │   │   │   │   │   ├── arrow_converter.meta.json
    │   │   │   │   │   ├── base_delta_writer.data.json
    │   │   │   │   │   ├── base_delta_writer.meta.json
    │   │   │   │   │   ├── bronze_writer.data.json
    │   │   │   │   │   ├── bronze_writer.meta.json
    │   │   │   │   │   ├── delta_reader.data.json
    │   │   │   │   │   ├── delta_reader.meta.json
    │   │   │   │   │   ├── gold_writer.data.json
    │   │   │   │   │   ├── gold_writer.meta.json
    │   │   │   │   │   ├── metadata_builder.data.json
    │   │   │   │   │   ├── metadata_builder.meta.json
    │   │   │   │   │   ├── metadata_writer.data.json
    │   │   │   │   │   ├── metadata_writer.meta.json
    │   │   │   │   │   ├── retention_manager.data.json
    │   │   │   │   │   ├── retention_manager.meta.json
    │   │   │   │   │   ├── silver_writer.data.json
    │   │   │   │   │   └── silver_writer.meta.json
    │   │   │   │   ├── system/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── memory_monitor.data.json
    │   │   │   │   │   └── memory_monitor.meta.json
    │   │   │   │   ├── validation/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── pandera_validator.data.json
    │   │   │   │   │   └── pandera_validator.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── config_loader.data.json
    │   │   │   │   └── config_loader.meta.json
    │   │   │   ├── interfaces/
    │   │   │   │   ├── cli/
    │   │   │   │   │   ├── commands/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── archive.data.json
    │   │   │   │   │   │   ├── archive.meta.json
    │   │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   │   ├── cleanup.data.json
    │   │   │   │   │   │   ├── cleanup.meta.json
    │   │   │   │   │   │   ├── config.data.json
    │   │   │   │   │   │   ├── config.meta.json
    │   │   │   │   │   │   ├── export.data.json
    │   │   │   │   │   │   ├── export.meta.json
    │   │   │   │   │   │   ├── health.data.json
    │   │   │   │   │   │   ├── health.meta.json
    │   │   │   │   │   │   ├── health_server_integration.data.json
    │   │   │   │   │   │   ├── health_server_integration.meta.json
    │   │   │   │   │   │   ├── lock.data.json
    │   │   │   │   │   │   ├── lock.meta.json
    │   │   │   │   │   │   ├── maintenance.data.json
    │   │   │   │   │   │   ├── maintenance.meta.json
    │   │   │   │   │   │   ├── metrics_server_integration.data.json
    │   │   │   │   │   │   ├── metrics_server_integration.meta.json
    │   │   │   │   │   │   ├── quarantine.data.json
    │   │   │   │   │   │   ├── quarantine.meta.json
    │   │   │   │   │   │   ├── run.data.json
    │   │   │   │   │   │   ├── run.meta.json
    │   │   │   │   │   │   ├── run_all.data.json
    │   │   │   │   │   │   ├── run_all.meta.json
    │   │   │   │   │   │   ├── run_composite.data.json
    │   │   │   │   │   │   ├── run_composite.meta.json
    │   │   │   │   │   │   ├── run_helpers.data.json
    │   │   │   │   │   │   ├── run_helpers.meta.json
    │   │   │   │   │   │   ├── vacuum.data.json
    │   │   │   │   │   │   └── vacuum.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── __main__.data.json
    │   │   │   │   │   ├── __main__.meta.json
    │   │   │   │   │   ├── exit_codes.data.json
    │   │   │   │   │   ├── exit_codes.meta.json
    │   │   │   │   │   ├── formatters.data.json
    │   │   │   │   │   ├── formatters.meta.json
    │   │   │   │   │   ├── main.data.json
    │   │   │   │   │   └── main.meta.json
    │   │   │   │   ├── http/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── health_server.data.json
    │   │   │   │   │   ├── health_server.meta.json
    │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   └── types.meta.json
    │   │   │   │   ├── orchestration/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── observability.data.json
    │   │   │   │   └── observability.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── __main__.data.json
    │   │   │   └── __main__.meta.json
    │   │   ├── black/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _width_table.data.json
    │   │   │   ├── _width_table.meta.json
    │   │   │   ├── brackets.data.json
    │   │   │   ├── brackets.meta.json
    │   │   │   ├── cache.data.json
    │   │   │   ├── cache.meta.json
    │   │   │   ├── comments.data.json
    │   │   │   ├── comments.meta.json
    │   │   │   ├── const.data.json
    │   │   │   ├── const.meta.json
    │   │   │   ├── files.data.json
    │   │   │   ├── files.meta.json
    │   │   │   ├── handle_ipynb_magics.data.json
    │   │   │   ├── handle_ipynb_magics.meta.json
    │   │   │   ├── linegen.data.json
    │   │   │   ├── linegen.meta.json
    │   │   │   ├── lines.data.json
    │   │   │   ├── lines.meta.json
    │   │   │   ├── mode.data.json
    │   │   │   ├── mode.meta.json
    │   │   │   ├── nodes.data.json
    │   │   │   ├── nodes.meta.json
    │   │   │   ├── numerics.data.json
    │   │   │   ├── numerics.meta.json
    │   │   │   ├── output.data.json
    │   │   │   ├── output.meta.json
    │   │   │   ├── parsing.data.json
    │   │   │   ├── parsing.meta.json
    │   │   │   ├── ranges.data.json
    │   │   │   ├── ranges.meta.json
    │   │   │   ├── report.data.json
    │   │   │   ├── report.meta.json
    │   │   │   ├── rusty.data.json
    │   │   │   ├── rusty.meta.json
    │   │   │   ├── strings.data.json
    │   │   │   ├── strings.meta.json
    │   │   │   ├── trans.data.json
    │   │   │   └── trans.meta.json
    │   │   ├── certifi/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── core.data.json
    │   │   │   └── core.meta.json
    │   │   ├── click/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _compat.data.json
    │   │   │   ├── _compat.meta.json
    │   │   │   ├── _termui_impl.data.json
    │   │   │   ├── _termui_impl.meta.json
    │   │   │   ├── _utils.data.json
    │   │   │   ├── _utils.meta.json
    │   │   │   ├── _winconsole.data.json
    │   │   │   ├── _winconsole.meta.json
    │   │   │   ├── core.data.json
    │   │   │   ├── core.meta.json
    │   │   │   ├── decorators.data.json
    │   │   │   ├── decorators.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── formatting.data.json
    │   │   │   ├── formatting.meta.json
    │   │   │   ├── globals.data.json
    │   │   │   ├── globals.meta.json
    │   │   │   ├── parser.data.json
    │   │   │   ├── parser.meta.json
    │   │   │   ├── shell_completion.data.json
    │   │   │   ├── shell_completion.meta.json
    │   │   │   ├── termui.data.json
    │   │   │   ├── termui.meta.json
    │   │   │   ├── types.data.json
    │   │   │   ├── types.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   └── utils.meta.json
    │   │   ├── collections/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── abc.data.json
    │   │   │   └── abc.meta.json
    │   │   ├── concurrent/
    │   │   │   ├── futures/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _base.data.json
    │   │   │   │   ├── _base.meta.json
    │   │   │   │   ├── process.data.json
    │   │   │   │   ├── process.meta.json
    │   │   │   │   ├── thread.data.json
    │   │   │   │   └── thread.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── ctypes/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _endian.data.json
    │   │   │   ├── _endian.meta.json
    │   │   │   ├── wintypes.data.json
    │   │   │   └── wintypes.meta.json
    │   │   ├── dateutil/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _common.data.json
    │   │   │   ├── _common.meta.json
    │   │   │   ├── relativedelta.data.json
    │   │   │   └── relativedelta.meta.json
    │   │   ├── deltalake/
    │   │   │   ├── fs/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _base_handler.data.json
    │   │   │   │   ├── _base_handler.meta.json
    │   │   │   │   ├── fs_handler.data.json
    │   │   │   │   └── fs_handler.meta.json
    │   │   │   ├── writer/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _conversion.data.json
    │   │   │   │   ├── _conversion.meta.json
    │   │   │   │   ├── _utils.data.json
    │   │   │   │   ├── _utils.meta.json
    │   │   │   │   ├── convert_to.data.json
    │   │   │   │   ├── convert_to.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── writer.data.json
    │   │   │   │   └── writer.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _internal.data.json
    │   │   │   ├── _internal.meta.json
    │   │   │   ├── _util.data.json
    │   │   │   ├── _util.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── query.data.json
    │   │   │   ├── query.meta.json
    │   │   │   ├── schema.data.json
    │   │   │   ├── schema.meta.json
    │   │   │   ├── table.data.json
    │   │   │   ├── table.meta.json
    │   │   │   ├── transaction.data.json
    │   │   │   └── transaction.meta.json
    │   │   ├── dotenv/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── parser.data.json
    │   │   │   ├── parser.meta.json
    │   │   │   ├── variables.data.json
    │   │   │   └── variables.meta.json
    │   │   ├── email/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _policybase.data.json
    │   │   │   ├── _policybase.meta.json
    │   │   │   ├── charset.data.json
    │   │   │   ├── charset.meta.json
    │   │   │   ├── contentmanager.data.json
    │   │   │   ├── contentmanager.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── header.data.json
    │   │   │   ├── header.meta.json
    │   │   │   ├── message.data.json
    │   │   │   ├── message.meta.json
    │   │   │   ├── policy.data.json
    │   │   │   └── policy.meta.json
    │   │   ├── exceptiongroup/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _catch.data.json
    │   │   │   ├── _catch.meta.json
    │   │   │   ├── _suppress.data.json
    │   │   │   ├── _suppress.meta.json
    │   │   │   ├── _version.data.json
    │   │   │   └── _version.meta.json
    │   │   ├── h11/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _abnf.data.json
    │   │   │   ├── _abnf.meta.json
    │   │   │   ├── _connection.data.json
    │   │   │   ├── _connection.meta.json
    │   │   │   ├── _events.data.json
    │   │   │   ├── _events.meta.json
    │   │   │   ├── _headers.data.json
    │   │   │   ├── _headers.meta.json
    │   │   │   ├── _readers.data.json
    │   │   │   ├── _readers.meta.json
    │   │   │   ├── _receivebuffer.data.json
    │   │   │   ├── _receivebuffer.meta.json
    │   │   │   ├── _state.data.json
    │   │   │   ├── _state.meta.json
    │   │   │   ├── _util.data.json
    │   │   │   ├── _util.meta.json
    │   │   │   ├── _version.data.json
    │   │   │   ├── _version.meta.json
    │   │   │   ├── _writers.data.json
    │   │   │   └── _writers.meta.json
    │   │   ├── html/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── entities.data.json
    │   │   │   └── entities.meta.json
    │   │   ├── http/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── client.data.json
    │   │   │   ├── client.meta.json
    │   │   │   ├── cookiejar.data.json
    │   │   │   ├── cookiejar.meta.json
    │   │   │   ├── server.data.json
    │   │   │   └── server.meta.json
    │   │   ├── httpcore/
    │   │   │   ├── _async/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── connection.data.json
    │   │   │   │   ├── connection.meta.json
    │   │   │   │   ├── connection_pool.data.json
    │   │   │   │   ├── connection_pool.meta.json
    │   │   │   │   ├── http11.data.json
    │   │   │   │   ├── http11.meta.json
    │   │   │   │   ├── http2.data.json
    │   │   │   │   ├── http2.meta.json
    │   │   │   │   ├── http_proxy.data.json
    │   │   │   │   ├── http_proxy.meta.json
    │   │   │   │   ├── interfaces.data.json
    │   │   │   │   ├── interfaces.meta.json
    │   │   │   │   ├── socks_proxy.data.json
    │   │   │   │   └── socks_proxy.meta.json
    │   │   │   ├── _backends/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── anyio.data.json
    │   │   │   │   ├── anyio.meta.json
    │   │   │   │   ├── auto.data.json
    │   │   │   │   ├── auto.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── mock.data.json
    │   │   │   │   ├── mock.meta.json
    │   │   │   │   ├── sync.data.json
    │   │   │   │   ├── sync.meta.json
    │   │   │   │   ├── trio.data.json
    │   │   │   │   └── trio.meta.json
    │   │   │   ├── _sync/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── connection.data.json
    │   │   │   │   ├── connection.meta.json
    │   │   │   │   ├── connection_pool.data.json
    │   │   │   │   ├── connection_pool.meta.json
    │   │   │   │   ├── http11.data.json
    │   │   │   │   ├── http11.meta.json
    │   │   │   │   ├── http2.data.json
    │   │   │   │   ├── http2.meta.json
    │   │   │   │   ├── http_proxy.data.json
    │   │   │   │   ├── http_proxy.meta.json
    │   │   │   │   ├── interfaces.data.json
    │   │   │   │   ├── interfaces.meta.json
    │   │   │   │   ├── socks_proxy.data.json
    │   │   │   │   └── socks_proxy.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _api.data.json
    │   │   │   ├── _api.meta.json
    │   │   │   ├── _exceptions.data.json
    │   │   │   ├── _exceptions.meta.json
    │   │   │   ├── _models.data.json
    │   │   │   ├── _models.meta.json
    │   │   │   ├── _ssl.data.json
    │   │   │   ├── _ssl.meta.json
    │   │   │   ├── _synchronization.data.json
    │   │   │   ├── _synchronization.meta.json
    │   │   │   ├── _trace.data.json
    │   │   │   ├── _trace.meta.json
    │   │   │   ├── _utils.data.json
    │   │   │   └── _utils.meta.json
    │   │   ├── httpx/
    │   │   │   ├── _transports/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── asgi.data.json
    │   │   │   │   ├── asgi.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── default.data.json
    │   │   │   │   ├── default.meta.json
    │   │   │   │   ├── mock.data.json
    │   │   │   │   ├── mock.meta.json
    │   │   │   │   ├── wsgi.data.json
    │   │   │   │   └── wsgi.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── __version__.data.json
    │   │   │   ├── __version__.meta.json
    │   │   │   ├── _api.data.json
    │   │   │   ├── _api.meta.json
    │   │   │   ├── _auth.data.json
    │   │   │   ├── _auth.meta.json
    │   │   │   ├── _client.data.json
    │   │   │   ├── _client.meta.json
    │   │   │   ├── _config.data.json
    │   │   │   ├── _config.meta.json
    │   │   │   ├── _content.data.json
    │   │   │   ├── _content.meta.json
    │   │   │   ├── _decoders.data.json
    │   │   │   ├── _decoders.meta.json
    │   │   │   ├── _exceptions.data.json
    │   │   │   ├── _exceptions.meta.json
    │   │   │   ├── _main.data.json
    │   │   │   ├── _main.meta.json
    │   │   │   ├── _models.data.json
    │   │   │   ├── _models.meta.json
    │   │   │   ├── _multipart.data.json
    │   │   │   ├── _multipart.meta.json
    │   │   │   ├── _status_codes.data.json
    │   │   │   ├── _status_codes.meta.json
    │   │   │   ├── _types.data.json
    │   │   │   ├── _types.meta.json
    │   │   │   ├── _urlparse.data.json
    │   │   │   ├── _urlparse.meta.json
    │   │   │   ├── _urls.data.json
    │   │   │   ├── _urls.meta.json
    │   │   │   ├── _utils.data.json
    │   │   │   └── _utils.meta.json
    │   │   ├── hypothesis/
    │   │   │   ├── extra/
    │   │   │   │   ├── pandas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── impl.data.json
    │   │   │   │   │   └── impl.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _array_helpers.data.json
    │   │   │   │   ├── _array_helpers.meta.json
    │   │   │   │   ├── numpy.data.json
    │   │   │   │   └── numpy.meta.json
    │   │   │   ├── internal/
    │   │   │   │   ├── conjecture/
    │   │   │   │   │   ├── shrinking/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── bytes.data.json
    │   │   │   │   │   │   ├── bytes.meta.json
    │   │   │   │   │   │   ├── choicetree.data.json
    │   │   │   │   │   │   ├── choicetree.meta.json
    │   │   │   │   │   │   ├── collection.data.json
    │   │   │   │   │   │   ├── collection.meta.json
    │   │   │   │   │   │   ├── common.data.json
    │   │   │   │   │   │   ├── common.meta.json
    │   │   │   │   │   │   ├── floats.data.json
    │   │   │   │   │   │   ├── floats.meta.json
    │   │   │   │   │   │   ├── integer.data.json
    │   │   │   │   │   │   ├── integer.meta.json
    │   │   │   │   │   │   ├── ordering.data.json
    │   │   │   │   │   │   ├── ordering.meta.json
    │   │   │   │   │   │   ├── string.data.json
    │   │   │   │   │   │   └── string.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── choice.data.json
    │   │   │   │   │   ├── choice.meta.json
    │   │   │   │   │   ├── choicetree.data.json
    │   │   │   │   │   ├── choicetree.meta.json
    │   │   │   │   │   ├── data.data.json
    │   │   │   │   │   ├── data.meta.json
    │   │   │   │   │   ├── datatree.data.json
    │   │   │   │   │   ├── datatree.meta.json
    │   │   │   │   │   ├── engine.data.json
    │   │   │   │   │   ├── engine.meta.json
    │   │   │   │   │   ├── floats.data.json
    │   │   │   │   │   ├── floats.meta.json
    │   │   │   │   │   ├── junkdrawer.data.json
    │   │   │   │   │   ├── junkdrawer.meta.json
    │   │   │   │   │   ├── optimiser.data.json
    │   │   │   │   │   ├── optimiser.meta.json
    │   │   │   │   │   ├── pareto.data.json
    │   │   │   │   │   ├── pareto.meta.json
    │   │   │   │   │   ├── providers.data.json
    │   │   │   │   │   ├── providers.meta.json
    │   │   │   │   │   ├── shrinker.data.json
    │   │   │   │   │   ├── shrinker.meta.json
    │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   └── utils.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── cache.data.json
    │   │   │   │   ├── cache.meta.json
    │   │   │   │   ├── cathetus.data.json
    │   │   │   │   ├── cathetus.meta.json
    │   │   │   │   ├── charmap.data.json
    │   │   │   │   ├── charmap.meta.json
    │   │   │   │   ├── compat.data.json
    │   │   │   │   ├── compat.meta.json
    │   │   │   │   ├── constants_ast.data.json
    │   │   │   │   ├── constants_ast.meta.json
    │   │   │   │   ├── coverage.data.json
    │   │   │   │   ├── coverage.meta.json
    │   │   │   │   ├── detection.data.json
    │   │   │   │   ├── detection.meta.json
    │   │   │   │   ├── entropy.data.json
    │   │   │   │   ├── entropy.meta.json
    │   │   │   │   ├── escalation.data.json
    │   │   │   │   ├── escalation.meta.json
    │   │   │   │   ├── filtering.data.json
    │   │   │   │   ├── filtering.meta.json
    │   │   │   │   ├── floats.data.json
    │   │   │   │   ├── floats.meta.json
    │   │   │   │   ├── healthcheck.data.json
    │   │   │   │   ├── healthcheck.meta.json
    │   │   │   │   ├── intervalsets.data.json
    │   │   │   │   ├── intervalsets.meta.json
    │   │   │   │   ├── lambda_sources.data.json
    │   │   │   │   ├── lambda_sources.meta.json
    │   │   │   │   ├── observability.data.json
    │   │   │   │   ├── observability.meta.json
    │   │   │   │   ├── reflection.data.json
    │   │   │   │   ├── reflection.meta.json
    │   │   │   │   ├── scrutineer.data.json
    │   │   │   │   ├── scrutineer.meta.json
    │   │   │   │   ├── validation.data.json
    │   │   │   │   └── validation.meta.json
    │   │   │   ├── strategies/
    │   │   │   │   ├── _internal/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── collections.data.json
    │   │   │   │   │   ├── collections.meta.json
    │   │   │   │   │   ├── core.data.json
    │   │   │   │   │   ├── core.meta.json
    │   │   │   │   │   ├── datetime.data.json
    │   │   │   │   │   ├── datetime.meta.json
    │   │   │   │   │   ├── deferred.data.json
    │   │   │   │   │   ├── deferred.meta.json
    │   │   │   │   │   ├── featureflags.data.json
    │   │   │   │   │   ├── featureflags.meta.json
    │   │   │   │   │   ├── flatmapped.data.json
    │   │   │   │   │   ├── flatmapped.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   ├── functions.meta.json
    │   │   │   │   │   ├── ipaddress.data.json
    │   │   │   │   │   ├── ipaddress.meta.json
    │   │   │   │   │   ├── lazy.data.json
    │   │   │   │   │   ├── lazy.meta.json
    │   │   │   │   │   ├── misc.data.json
    │   │   │   │   │   ├── misc.meta.json
    │   │   │   │   │   ├── numbers.data.json
    │   │   │   │   │   ├── numbers.meta.json
    │   │   │   │   │   ├── random.data.json
    │   │   │   │   │   ├── random.meta.json
    │   │   │   │   │   ├── recursive.data.json
    │   │   │   │   │   ├── recursive.meta.json
    │   │   │   │   │   ├── shared.data.json
    │   │   │   │   │   ├── shared.meta.json
    │   │   │   │   │   ├── strategies.data.json
    │   │   │   │   │   ├── strategies.meta.json
    │   │   │   │   │   ├── strings.data.json
    │   │   │   │   │   ├── strings.meta.json
    │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   ├── types.meta.json
    │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   └── utils.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── utils/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── conventions.data.json
    │   │   │   │   ├── conventions.meta.json
    │   │   │   │   ├── dynamicvariables.data.json
    │   │   │   │   ├── dynamicvariables.meta.json
    │   │   │   │   ├── threading.data.json
    │   │   │   │   └── threading.meta.json
    │   │   │   ├── vendor/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── pretty.data.json
    │   │   │   │   └── pretty.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _settings.data.json
    │   │   │   ├── _settings.meta.json
    │   │   │   ├── configuration.data.json
    │   │   │   ├── configuration.meta.json
    │   │   │   ├── control.data.json
    │   │   │   ├── control.meta.json
    │   │   │   ├── core.data.json
    │   │   │   ├── core.meta.json
    │   │   │   ├── database.data.json
    │   │   │   ├── database.meta.json
    │   │   │   ├── entry_points.data.json
    │   │   │   ├── entry_points.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── reporting.data.json
    │   │   │   ├── reporting.meta.json
    │   │   │   ├── stateful.data.json
    │   │   │   ├── stateful.meta.json
    │   │   │   ├── statistics.data.json
    │   │   │   ├── statistics.meta.json
    │   │   │   ├── version.data.json
    │   │   │   └── version.meta.json
    │   │   ├── idna/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── core.data.json
    │   │   │   ├── core.meta.json
    │   │   │   ├── idnadata.data.json
    │   │   │   ├── idnadata.meta.json
    │   │   │   ├── intranges.data.json
    │   │   │   ├── intranges.meta.json
    │   │   │   ├── package_data.data.json
    │   │   │   └── package_data.meta.json
    │   │   ├── importlib/
    │   │   │   ├── metadata/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _meta.data.json
    │   │   │   │   └── _meta.meta.json
    │   │   │   ├── resources/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _common.data.json
    │   │   │   │   ├── _common.meta.json
    │   │   │   │   ├── abc.data.json
    │   │   │   │   ├── abc.meta.json
    │   │   │   │   ├── readers.data.json
    │   │   │   │   └── readers.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _abc.data.json
    │   │   │   ├── _abc.meta.json
    │   │   │   ├── _bootstrap.data.json
    │   │   │   ├── _bootstrap.meta.json
    │   │   │   ├── _bootstrap_external.data.json
    │   │   │   ├── _bootstrap_external.meta.json
    │   │   │   ├── abc.data.json
    │   │   │   ├── abc.meta.json
    │   │   │   ├── machinery.data.json
    │   │   │   ├── machinery.meta.json
    │   │   │   ├── readers.data.json
    │   │   │   ├── readers.meta.json
    │   │   │   ├── util.data.json
    │   │   │   └── util.meta.json
    │   │   ├── importlib_metadata/
    │   │   │   ├── compat/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── py311.data.json
    │   │   │   │   ├── py311.meta.json
    │   │   │   │   ├── py39.data.json
    │   │   │   │   └── py39.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _adapters.data.json
    │   │   │   ├── _adapters.meta.json
    │   │   │   ├── _collections.data.json
    │   │   │   ├── _collections.meta.json
    │   │   │   ├── _compat.data.json
    │   │   │   ├── _compat.meta.json
    │   │   │   ├── _functools.data.json
    │   │   │   ├── _functools.meta.json
    │   │   │   ├── _itertools.data.json
    │   │   │   ├── _itertools.meta.json
    │   │   │   ├── _meta.data.json
    │   │   │   ├── _meta.meta.json
    │   │   │   ├── _text.data.json
    │   │   │   ├── _text.meta.json
    │   │   │   ├── _typing.data.json
    │   │   │   └── _typing.meta.json
    │   │   ├── iniconfig/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _parse.data.json
    │   │   │   ├── _parse.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   └── exceptions.meta.json
    │   │   ├── jinja2/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _identifier.data.json
    │   │   │   ├── _identifier.meta.json
    │   │   │   ├── async_utils.data.json
    │   │   │   ├── async_utils.meta.json
    │   │   │   ├── bccache.data.json
    │   │   │   ├── bccache.meta.json
    │   │   │   ├── compiler.data.json
    │   │   │   ├── compiler.meta.json
    │   │   │   ├── debug.data.json
    │   │   │   ├── debug.meta.json
    │   │   │   ├── defaults.data.json
    │   │   │   ├── defaults.meta.json
    │   │   │   ├── environment.data.json
    │   │   │   ├── environment.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── ext.data.json
    │   │   │   ├── ext.meta.json
    │   │   │   ├── filters.data.json
    │   │   │   ├── filters.meta.json
    │   │   │   ├── idtracking.data.json
    │   │   │   ├── idtracking.meta.json
    │   │   │   ├── lexer.data.json
    │   │   │   ├── lexer.meta.json
    │   │   │   ├── loaders.data.json
    │   │   │   ├── loaders.meta.json
    │   │   │   ├── nodes.data.json
    │   │   │   ├── nodes.meta.json
    │   │   │   ├── optimizer.data.json
    │   │   │   ├── optimizer.meta.json
    │   │   │   ├── parser.data.json
    │   │   │   ├── parser.meta.json
    │   │   │   ├── runtime.data.json
    │   │   │   ├── runtime.meta.json
    │   │   │   ├── sandbox.data.json
    │   │   │   ├── sandbox.meta.json
    │   │   │   ├── tests.data.json
    │   │   │   ├── tests.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   ├── utils.meta.json
    │   │   │   ├── visitor.data.json
    │   │   │   └── visitor.meta.json
    │   │   ├── json/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── decoder.data.json
    │   │   │   ├── decoder.meta.json
    │   │   │   ├── encoder.data.json
    │   │   │   └── encoder.meta.json
    │   │   ├── logging/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── markdown_it/
    │   │   │   ├── common/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── entities.data.json
    │   │   │   │   ├── entities.meta.json
    │   │   │   │   ├── html_blocks.data.json
    │   │   │   │   ├── html_blocks.meta.json
    │   │   │   │   ├── html_re.data.json
    │   │   │   │   ├── html_re.meta.json
    │   │   │   │   ├── normalize_url.data.json
    │   │   │   │   ├── normalize_url.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── helpers/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── parse_link_destination.data.json
    │   │   │   │   ├── parse_link_destination.meta.json
    │   │   │   │   ├── parse_link_label.data.json
    │   │   │   │   ├── parse_link_label.meta.json
    │   │   │   │   ├── parse_link_title.data.json
    │   │   │   │   └── parse_link_title.meta.json
    │   │   │   ├── presets/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── commonmark.data.json
    │   │   │   │   ├── commonmark.meta.json
    │   │   │   │   ├── default.data.json
    │   │   │   │   ├── default.meta.json
    │   │   │   │   ├── zero.data.json
    │   │   │   │   └── zero.meta.json
    │   │   │   ├── rules_block/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── blockquote.data.json
    │   │   │   │   ├── blockquote.meta.json
    │   │   │   │   ├── code.data.json
    │   │   │   │   ├── code.meta.json
    │   │   │   │   ├── fence.data.json
    │   │   │   │   ├── fence.meta.json
    │   │   │   │   ├── heading.data.json
    │   │   │   │   ├── heading.meta.json
    │   │   │   │   ├── hr.data.json
    │   │   │   │   ├── hr.meta.json
    │   │   │   │   ├── html_block.data.json
    │   │   │   │   ├── html_block.meta.json
    │   │   │   │   ├── lheading.data.json
    │   │   │   │   ├── lheading.meta.json
    │   │   │   │   ├── list.data.json
    │   │   │   │   ├── list.meta.json
    │   │   │   │   ├── paragraph.data.json
    │   │   │   │   ├── paragraph.meta.json
    │   │   │   │   ├── reference.data.json
    │   │   │   │   ├── reference.meta.json
    │   │   │   │   ├── state_block.data.json
    │   │   │   │   ├── state_block.meta.json
    │   │   │   │   ├── table.data.json
    │   │   │   │   └── table.meta.json
    │   │   │   ├── rules_core/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── block.data.json
    │   │   │   │   ├── block.meta.json
    │   │   │   │   ├── inline.data.json
    │   │   │   │   ├── inline.meta.json
    │   │   │   │   ├── linkify.data.json
    │   │   │   │   ├── linkify.meta.json
    │   │   │   │   ├── normalize.data.json
    │   │   │   │   ├── normalize.meta.json
    │   │   │   │   ├── replacements.data.json
    │   │   │   │   ├── replacements.meta.json
    │   │   │   │   ├── smartquotes.data.json
    │   │   │   │   ├── smartquotes.meta.json
    │   │   │   │   ├── state_core.data.json
    │   │   │   │   ├── state_core.meta.json
    │   │   │   │   ├── text_join.data.json
    │   │   │   │   └── text_join.meta.json
    │   │   │   ├── rules_inline/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── autolink.data.json
    │   │   │   │   ├── autolink.meta.json
    │   │   │   │   ├── backticks.data.json
    │   │   │   │   ├── backticks.meta.json
    │   │   │   │   ├── balance_pairs.data.json
    │   │   │   │   ├── balance_pairs.meta.json
    │   │   │   │   ├── emphasis.data.json
    │   │   │   │   ├── emphasis.meta.json
    │   │   │   │   ├── entity.data.json
    │   │   │   │   ├── entity.meta.json
    │   │   │   │   ├── escape.data.json
    │   │   │   │   ├── escape.meta.json
    │   │   │   │   ├── fragments_join.data.json
    │   │   │   │   ├── fragments_join.meta.json
    │   │   │   │   ├── html_inline.data.json
    │   │   │   │   ├── html_inline.meta.json
    │   │   │   │   ├── image.data.json
    │   │   │   │   ├── image.meta.json
    │   │   │   │   ├── link.data.json
    │   │   │   │   ├── link.meta.json
    │   │   │   │   ├── linkify.data.json
    │   │   │   │   ├── linkify.meta.json
    │   │   │   │   ├── newline.data.json
    │   │   │   │   ├── newline.meta.json
    │   │   │   │   ├── state_inline.data.json
    │   │   │   │   ├── state_inline.meta.json
    │   │   │   │   ├── strikethrough.data.json
    │   │   │   │   ├── strikethrough.meta.json
    │   │   │   │   ├── text.data.json
    │   │   │   │   └── text.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _punycode.data.json
    │   │   │   ├── _punycode.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── parser_block.data.json
    │   │   │   ├── parser_block.meta.json
    │   │   │   ├── parser_core.data.json
    │   │   │   ├── parser_core.meta.json
    │   │   │   ├── parser_inline.data.json
    │   │   │   ├── parser_inline.meta.json
    │   │   │   ├── renderer.data.json
    │   │   │   ├── renderer.meta.json
    │   │   │   ├── ruler.data.json
    │   │   │   ├── ruler.meta.json
    │   │   │   ├── token.data.json
    │   │   │   ├── token.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   └── utils.meta.json
    │   │   ├── markupsafe/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _native.data.json
    │   │   │   ├── _native.meta.json
    │   │   │   ├── _speedups.data.json
    │   │   │   └── _speedups.meta.json
    │   │   ├── mdurl/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _decode.data.json
    │   │   │   ├── _decode.meta.json
    │   │   │   ├── _encode.data.json
    │   │   │   ├── _encode.meta.json
    │   │   │   ├── _format.data.json
    │   │   │   ├── _format.meta.json
    │   │   │   ├── _parse.data.json
    │   │   │   ├── _parse.meta.json
    │   │   │   ├── _url.data.json
    │   │   │   └── _url.meta.json
    │   │   ├── multiprocessing/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── connection.data.json
    │   │   │   ├── connection.meta.json
    │   │   │   ├── context.data.json
    │   │   │   ├── context.meta.json
    │   │   │   ├── managers.data.json
    │   │   │   ├── managers.meta.json
    │   │   │   ├── pool.data.json
    │   │   │   ├── pool.meta.json
    │   │   │   ├── popen_fork.data.json
    │   │   │   ├── popen_fork.meta.json
    │   │   │   ├── popen_forkserver.data.json
    │   │   │   ├── popen_forkserver.meta.json
    │   │   │   ├── popen_spawn_posix.data.json
    │   │   │   ├── popen_spawn_posix.meta.json
    │   │   │   ├── popen_spawn_win32.data.json
    │   │   │   ├── popen_spawn_win32.meta.json
    │   │   │   ├── process.data.json
    │   │   │   ├── process.meta.json
    │   │   │   ├── queues.data.json
    │   │   │   ├── queues.meta.json
    │   │   │   ├── reduction.data.json
    │   │   │   ├── reduction.meta.json
    │   │   │   ├── shared_memory.data.json
    │   │   │   ├── shared_memory.meta.json
    │   │   │   ├── sharedctypes.data.json
    │   │   │   ├── sharedctypes.meta.json
    │   │   │   ├── spawn.data.json
    │   │   │   ├── spawn.meta.json
    │   │   │   ├── synchronize.data.json
    │   │   │   ├── synchronize.meta.json
    │   │   │   ├── util.data.json
    │   │   │   └── util.meta.json
    │   │   ├── numpy/
    │   │   │   ├── _core/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _asarray.data.json
    │   │   │   │   ├── _asarray.meta.json
    │   │   │   │   ├── _internal.data.json
    │   │   │   │   ├── _internal.meta.json
    │   │   │   │   ├── _type_aliases.data.json
    │   │   │   │   ├── _type_aliases.meta.json
    │   │   │   │   ├── _ufunc_config.data.json
    │   │   │   │   ├── _ufunc_config.meta.json
    │   │   │   │   ├── arrayprint.data.json
    │   │   │   │   ├── arrayprint.meta.json
    │   │   │   │   ├── defchararray.data.json
    │   │   │   │   ├── defchararray.meta.json
    │   │   │   │   ├── einsumfunc.data.json
    │   │   │   │   ├── einsumfunc.meta.json
    │   │   │   │   ├── fromnumeric.data.json
    │   │   │   │   ├── fromnumeric.meta.json
    │   │   │   │   ├── function_base.data.json
    │   │   │   │   ├── function_base.meta.json
    │   │   │   │   ├── multiarray.data.json
    │   │   │   │   ├── multiarray.meta.json
    │   │   │   │   ├── numeric.data.json
    │   │   │   │   ├── numeric.meta.json
    │   │   │   │   ├── numerictypes.data.json
    │   │   │   │   ├── numerictypes.meta.json
    │   │   │   │   ├── records.data.json
    │   │   │   │   ├── records.meta.json
    │   │   │   │   ├── shape_base.data.json
    │   │   │   │   ├── shape_base.meta.json
    │   │   │   │   ├── strings.data.json
    │   │   │   │   └── strings.meta.json
    │   │   │   ├── _typing/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _add_docstring.data.json
    │   │   │   │   ├── _add_docstring.meta.json
    │   │   │   │   ├── _array_like.data.json
    │   │   │   │   ├── _array_like.meta.json
    │   │   │   │   ├── _char_codes.data.json
    │   │   │   │   ├── _char_codes.meta.json
    │   │   │   │   ├── _dtype_like.data.json
    │   │   │   │   ├── _dtype_like.meta.json
    │   │   │   │   ├── _extended_precision.data.json
    │   │   │   │   ├── _extended_precision.meta.json
    │   │   │   │   ├── _nbit.data.json
    │   │   │   │   ├── _nbit.meta.json
    │   │   │   │   ├── _nbit_base.data.json
    │   │   │   │   ├── _nbit_base.meta.json
    │   │   │   │   ├── _nested_sequence.data.json
    │   │   │   │   ├── _nested_sequence.meta.json
    │   │   │   │   ├── _scalars.data.json
    │   │   │   │   ├── _scalars.meta.json
    │   │   │   │   ├── _shape.data.json
    │   │   │   │   ├── _shape.meta.json
    │   │   │   │   ├── _ufunc.data.json
    │   │   │   │   └── _ufunc.meta.json
    │   │   │   ├── char/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── core/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── ctypeslib/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _ctypeslib.data.json
    │   │   │   │   └── _ctypeslib.meta.json
    │   │   │   ├── f2py/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── __version__.data.json
    │   │   │   │   ├── __version__.meta.json
    │   │   │   │   ├── auxfuncs.data.json
    │   │   │   │   ├── auxfuncs.meta.json
    │   │   │   │   ├── cfuncs.data.json
    │   │   │   │   ├── cfuncs.meta.json
    │   │   │   │   ├── f2py2e.data.json
    │   │   │   │   └── f2py2e.meta.json
    │   │   │   ├── fft/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _helper.data.json
    │   │   │   │   ├── _helper.meta.json
    │   │   │   │   ├── _pocketfft.data.json
    │   │   │   │   └── _pocketfft.meta.json
    │   │   │   ├── lib/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _array_utils_impl.data.json
    │   │   │   │   ├── _array_utils_impl.meta.json
    │   │   │   │   ├── _arraypad_impl.data.json
    │   │   │   │   ├── _arraypad_impl.meta.json
    │   │   │   │   ├── _arraysetops_impl.data.json
    │   │   │   │   ├── _arraysetops_impl.meta.json
    │   │   │   │   ├── _arrayterator_impl.data.json
    │   │   │   │   ├── _arrayterator_impl.meta.json
    │   │   │   │   ├── _datasource.data.json
    │   │   │   │   ├── _datasource.meta.json
    │   │   │   │   ├── _format_impl.data.json
    │   │   │   │   ├── _format_impl.meta.json
    │   │   │   │   ├── _function_base_impl.data.json
    │   │   │   │   ├── _function_base_impl.meta.json
    │   │   │   │   ├── _histograms_impl.data.json
    │   │   │   │   ├── _histograms_impl.meta.json
    │   │   │   │   ├── _index_tricks_impl.data.json
    │   │   │   │   ├── _index_tricks_impl.meta.json
    │   │   │   │   ├── _iotools.data.json
    │   │   │   │   ├── _iotools.meta.json
    │   │   │   │   ├── _nanfunctions_impl.data.json
    │   │   │   │   ├── _nanfunctions_impl.meta.json
    │   │   │   │   ├── _npyio_impl.data.json
    │   │   │   │   ├── _npyio_impl.meta.json
    │   │   │   │   ├── _polynomial_impl.data.json
    │   │   │   │   ├── _polynomial_impl.meta.json
    │   │   │   │   ├── _scimath_impl.data.json
    │   │   │   │   ├── _scimath_impl.meta.json
    │   │   │   │   ├── _shape_base_impl.data.json
    │   │   │   │   ├── _shape_base_impl.meta.json
    │   │   │   │   ├── _stride_tricks_impl.data.json
    │   │   │   │   ├── _stride_tricks_impl.meta.json
    │   │   │   │   ├── _twodim_base_impl.data.json
    │   │   │   │   ├── _twodim_base_impl.meta.json
    │   │   │   │   ├── _type_check_impl.data.json
    │   │   │   │   ├── _type_check_impl.meta.json
    │   │   │   │   ├── _ufunclike_impl.data.json
    │   │   │   │   ├── _ufunclike_impl.meta.json
    │   │   │   │   ├── _utils_impl.data.json
    │   │   │   │   ├── _utils_impl.meta.json
    │   │   │   │   ├── _version.data.json
    │   │   │   │   ├── _version.meta.json
    │   │   │   │   ├── array_utils.data.json
    │   │   │   │   ├── array_utils.meta.json
    │   │   │   │   ├── format.data.json
    │   │   │   │   ├── format.meta.json
    │   │   │   │   ├── introspect.data.json
    │   │   │   │   ├── introspect.meta.json
    │   │   │   │   ├── mixins.data.json
    │   │   │   │   ├── mixins.meta.json
    │   │   │   │   ├── npyio.data.json
    │   │   │   │   ├── npyio.meta.json
    │   │   │   │   ├── scimath.data.json
    │   │   │   │   ├── scimath.meta.json
    │   │   │   │   ├── stride_tricks.data.json
    │   │   │   │   └── stride_tricks.meta.json
    │   │   │   ├── linalg/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _linalg.data.json
    │   │   │   │   ├── _linalg.meta.json
    │   │   │   │   ├── _umath_linalg.data.json
    │   │   │   │   ├── _umath_linalg.meta.json
    │   │   │   │   ├── linalg.data.json
    │   │   │   │   └── linalg.meta.json
    │   │   │   ├── ma/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── core.data.json
    │   │   │   │   ├── core.meta.json
    │   │   │   │   ├── extras.data.json
    │   │   │   │   ├── extras.meta.json
    │   │   │   │   ├── mrecords.data.json
    │   │   │   │   └── mrecords.meta.json
    │   │   │   ├── matrixlib/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── defmatrix.data.json
    │   │   │   │   └── defmatrix.meta.json
    │   │   │   ├── polynomial/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _polybase.data.json
    │   │   │   │   ├── _polybase.meta.json
    │   │   │   │   ├── _polytypes.data.json
    │   │   │   │   ├── _polytypes.meta.json
    │   │   │   │   ├── chebyshev.data.json
    │   │   │   │   ├── chebyshev.meta.json
    │   │   │   │   ├── hermite.data.json
    │   │   │   │   ├── hermite.meta.json
    │   │   │   │   ├── hermite_e.data.json
    │   │   │   │   ├── hermite_e.meta.json
    │   │   │   │   ├── laguerre.data.json
    │   │   │   │   ├── laguerre.meta.json
    │   │   │   │   ├── legendre.data.json
    │   │   │   │   ├── legendre.meta.json
    │   │   │   │   ├── polynomial.data.json
    │   │   │   │   ├── polynomial.meta.json
    │   │   │   │   ├── polyutils.data.json
    │   │   │   │   └── polyutils.meta.json
    │   │   │   ├── random/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _generator.data.json
    │   │   │   │   ├── _generator.meta.json
    │   │   │   │   ├── _mt19937.data.json
    │   │   │   │   ├── _mt19937.meta.json
    │   │   │   │   ├── _pcg64.data.json
    │   │   │   │   ├── _pcg64.meta.json
    │   │   │   │   ├── _philox.data.json
    │   │   │   │   ├── _philox.meta.json
    │   │   │   │   ├── _sfc64.data.json
    │   │   │   │   ├── _sfc64.meta.json
    │   │   │   │   ├── bit_generator.data.json
    │   │   │   │   ├── bit_generator.meta.json
    │   │   │   │   ├── mtrand.data.json
    │   │   │   │   └── mtrand.meta.json
    │   │   │   ├── rec/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── strings/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── testing/
    │   │   │   │   ├── _private/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   └── utils.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── overrides.data.json
    │   │   │   │   └── overrides.meta.json
    │   │   │   ├── typing/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── __config__.data.json
    │   │   │   ├── __config__.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _array_api_info.data.json
    │   │   │   ├── _array_api_info.meta.json
    │   │   │   ├── _expired_attrs_2_0.data.json
    │   │   │   ├── _expired_attrs_2_0.meta.json
    │   │   │   ├── _globals.data.json
    │   │   │   ├── _globals.meta.json
    │   │   │   ├── _pytesttester.data.json
    │   │   │   ├── _pytesttester.meta.json
    │   │   │   ├── dtypes.data.json
    │   │   │   ├── dtypes.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── matlib.data.json
    │   │   │   ├── matlib.meta.json
    │   │   │   ├── version.data.json
    │   │   │   └── version.meta.json
    │   │   ├── openpyxl/
    │   │   │   ├── cell/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── cell.data.json
    │   │   │   │   ├── cell.meta.json
    │   │   │   │   ├── read_only.data.json
    │   │   │   │   ├── read_only.meta.json
    │   │   │   │   ├── rich_text.data.json
    │   │   │   │   ├── rich_text.meta.json
    │   │   │   │   ├── text.data.json
    │   │   │   │   └── text.meta.json
    │   │   │   ├── chart/
    │   │   │   │   ├── _3d.data.json
    │   │   │   │   ├── _3d.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _chart.data.json
    │   │   │   │   ├── _chart.meta.json
    │   │   │   │   ├── area_chart.data.json
    │   │   │   │   ├── area_chart.meta.json
    │   │   │   │   ├── axis.data.json
    │   │   │   │   ├── axis.meta.json
    │   │   │   │   ├── bar_chart.data.json
    │   │   │   │   ├── bar_chart.meta.json
    │   │   │   │   ├── bubble_chart.data.json
    │   │   │   │   ├── bubble_chart.meta.json
    │   │   │   │   ├── data_source.data.json
    │   │   │   │   ├── data_source.meta.json
    │   │   │   │   ├── label.data.json
    │   │   │   │   ├── label.meta.json
    │   │   │   │   ├── layout.data.json
    │   │   │   │   ├── layout.meta.json
    │   │   │   │   ├── legend.data.json
    │   │   │   │   ├── legend.meta.json
    │   │   │   │   ├── line_chart.data.json
    │   │   │   │   ├── line_chart.meta.json
    │   │   │   │   ├── picture.data.json
    │   │   │   │   ├── picture.meta.json
    │   │   │   │   ├── pie_chart.data.json
    │   │   │   │   ├── pie_chart.meta.json
    │   │   │   │   ├── radar_chart.data.json
    │   │   │   │   ├── radar_chart.meta.json
    │   │   │   │   ├── reference.data.json
    │   │   │   │   ├── reference.meta.json
    │   │   │   │   ├── scatter_chart.data.json
    │   │   │   │   ├── scatter_chart.meta.json
    │   │   │   │   ├── shapes.data.json
    │   │   │   │   ├── shapes.meta.json
    │   │   │   │   ├── stock_chart.data.json
    │   │   │   │   ├── stock_chart.meta.json
    │   │   │   │   ├── surface_chart.data.json
    │   │   │   │   ├── surface_chart.meta.json
    │   │   │   │   ├── text.data.json
    │   │   │   │   ├── text.meta.json
    │   │   │   │   ├── title.data.json
    │   │   │   │   ├── title.meta.json
    │   │   │   │   ├── updown_bars.data.json
    │   │   │   │   └── updown_bars.meta.json
    │   │   │   ├── chartsheet/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── chartsheet.data.json
    │   │   │   │   ├── chartsheet.meta.json
    │   │   │   │   ├── custom.data.json
    │   │   │   │   ├── custom.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── protection.data.json
    │   │   │   │   ├── protection.meta.json
    │   │   │   │   ├── publish.data.json
    │   │   │   │   ├── publish.meta.json
    │   │   │   │   ├── relation.data.json
    │   │   │   │   ├── relation.meta.json
    │   │   │   │   ├── views.data.json
    │   │   │   │   └── views.meta.json
    │   │   │   ├── comments/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── comments.data.json
    │   │   │   │   └── comments.meta.json
    │   │   │   ├── compat/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── numbers.data.json
    │   │   │   │   ├── numbers.meta.json
    │   │   │   │   ├── strings.data.json
    │   │   │   │   └── strings.meta.json
    │   │   │   ├── descriptors/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── excel.data.json
    │   │   │   │   ├── excel.meta.json
    │   │   │   │   ├── nested.data.json
    │   │   │   │   ├── nested.meta.json
    │   │   │   │   ├── sequence.data.json
    │   │   │   │   ├── sequence.meta.json
    │   │   │   │   ├── serialisable.data.json
    │   │   │   │   └── serialisable.meta.json
    │   │   │   ├── drawing/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── colors.data.json
    │   │   │   │   ├── colors.meta.json
    │   │   │   │   ├── connector.data.json
    │   │   │   │   ├── connector.meta.json
    │   │   │   │   ├── drawing.data.json
    │   │   │   │   ├── drawing.meta.json
    │   │   │   │   ├── effect.data.json
    │   │   │   │   ├── effect.meta.json
    │   │   │   │   ├── fill.data.json
    │   │   │   │   ├── fill.meta.json
    │   │   │   │   ├── geometry.data.json
    │   │   │   │   ├── geometry.meta.json
    │   │   │   │   ├── graphic.data.json
    │   │   │   │   ├── graphic.meta.json
    │   │   │   │   ├── image.data.json
    │   │   │   │   ├── image.meta.json
    │   │   │   │   ├── line.data.json
    │   │   │   │   ├── line.meta.json
    │   │   │   │   ├── picture.data.json
    │   │   │   │   ├── picture.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── relation.data.json
    │   │   │   │   ├── relation.meta.json
    │   │   │   │   ├── spreadsheet_drawing.data.json
    │   │   │   │   ├── spreadsheet_drawing.meta.json
    │   │   │   │   ├── text.data.json
    │   │   │   │   ├── text.meta.json
    │   │   │   │   ├── xdr.data.json
    │   │   │   │   └── xdr.meta.json
    │   │   │   ├── formatting/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── formatting.data.json
    │   │   │   │   ├── formatting.meta.json
    │   │   │   │   ├── rule.data.json
    │   │   │   │   └── rule.meta.json
    │   │   │   ├── formula/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── tokenizer.data.json
    │   │   │   │   └── tokenizer.meta.json
    │   │   │   ├── packaging/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── manifest.data.json
    │   │   │   │   ├── manifest.meta.json
    │   │   │   │   ├── relationship.data.json
    │   │   │   │   ├── relationship.meta.json
    │   │   │   │   ├── workbook.data.json
    │   │   │   │   └── workbook.meta.json
    │   │   │   ├── pivot/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── cache.data.json
    │   │   │   │   ├── cache.meta.json
    │   │   │   │   ├── fields.data.json
    │   │   │   │   ├── fields.meta.json
    │   │   │   │   ├── record.data.json
    │   │   │   │   ├── record.meta.json
    │   │   │   │   ├── table.data.json
    │   │   │   │   └── table.meta.json
    │   │   │   ├── reader/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── excel.data.json
    │   │   │   │   ├── excel.meta.json
    │   │   │   │   ├── workbook.data.json
    │   │   │   │   └── workbook.meta.json
    │   │   │   ├── styles/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── alignment.data.json
    │   │   │   │   ├── alignment.meta.json
    │   │   │   │   ├── borders.data.json
    │   │   │   │   ├── borders.meta.json
    │   │   │   │   ├── cell_style.data.json
    │   │   │   │   ├── cell_style.meta.json
    │   │   │   │   ├── colors.data.json
    │   │   │   │   ├── colors.meta.json
    │   │   │   │   ├── differential.data.json
    │   │   │   │   ├── differential.meta.json
    │   │   │   │   ├── fills.data.json
    │   │   │   │   ├── fills.meta.json
    │   │   │   │   ├── fonts.data.json
    │   │   │   │   ├── fonts.meta.json
    │   │   │   │   ├── named_styles.data.json
    │   │   │   │   ├── named_styles.meta.json
    │   │   │   │   ├── numbers.data.json
    │   │   │   │   ├── numbers.meta.json
    │   │   │   │   ├── protection.data.json
    │   │   │   │   ├── protection.meta.json
    │   │   │   │   ├── proxy.data.json
    │   │   │   │   ├── proxy.meta.json
    │   │   │   │   ├── styleable.data.json
    │   │   │   │   └── styleable.meta.json
    │   │   │   ├── utils/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── bound_dictionary.data.json
    │   │   │   │   ├── bound_dictionary.meta.json
    │   │   │   │   ├── cell.data.json
    │   │   │   │   ├── cell.meta.json
    │   │   │   │   ├── formulas.data.json
    │   │   │   │   ├── formulas.meta.json
    │   │   │   │   ├── indexed_list.data.json
    │   │   │   │   └── indexed_list.meta.json
    │   │   │   ├── workbook/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── child.data.json
    │   │   │   │   ├── child.meta.json
    │   │   │   │   ├── defined_name.data.json
    │   │   │   │   ├── defined_name.meta.json
    │   │   │   │   ├── function_group.data.json
    │   │   │   │   ├── function_group.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── protection.data.json
    │   │   │   │   ├── protection.meta.json
    │   │   │   │   ├── smart_tags.data.json
    │   │   │   │   ├── smart_tags.meta.json
    │   │   │   │   ├── web.data.json
    │   │   │   │   ├── web.meta.json
    │   │   │   │   ├── workbook.data.json
    │   │   │   │   └── workbook.meta.json
    │   │   │   ├── worksheet/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _read_only.data.json
    │   │   │   │   ├── _read_only.meta.json
    │   │   │   │   ├── _write_only.data.json
    │   │   │   │   ├── _write_only.meta.json
    │   │   │   │   ├── cell_range.data.json
    │   │   │   │   ├── cell_range.meta.json
    │   │   │   │   ├── datavalidation.data.json
    │   │   │   │   ├── datavalidation.meta.json
    │   │   │   │   ├── dimensions.data.json
    │   │   │   │   ├── dimensions.meta.json
    │   │   │   │   ├── drawing.data.json
    │   │   │   │   ├── drawing.meta.json
    │   │   │   │   ├── filters.data.json
    │   │   │   │   ├── filters.meta.json
    │   │   │   │   ├── formula.data.json
    │   │   │   │   ├── formula.meta.json
    │   │   │   │   ├── header_footer.data.json
    │   │   │   │   ├── header_footer.meta.json
    │   │   │   │   ├── hyperlink.data.json
    │   │   │   │   ├── hyperlink.meta.json
    │   │   │   │   ├── page.data.json
    │   │   │   │   ├── page.meta.json
    │   │   │   │   ├── pagebreak.data.json
    │   │   │   │   ├── pagebreak.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── protection.data.json
    │   │   │   │   ├── protection.meta.json
    │   │   │   │   ├── scenario.data.json
    │   │   │   │   ├── scenario.meta.json
    │   │   │   │   ├── table.data.json
    │   │   │   │   ├── table.meta.json
    │   │   │   │   ├── views.data.json
    │   │   │   │   ├── views.meta.json
    │   │   │   │   ├── worksheet.data.json
    │   │   │   │   └── worksheet.meta.json
    │   │   │   ├── xml/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _functions_overloads.data.json
    │   │   │   │   ├── _functions_overloads.meta.json
    │   │   │   │   ├── functions.data.json
    │   │   │   │   └── functions.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _constants.data.json
    │   │   │   └── _constants.meta.json
    │   │   ├── opentelemetry/
    │   │   │   ├── _logs/
    │   │   │   │   ├── _internal/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── severity/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── attributes/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── context/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── context.data.json
    │   │   │   │   └── context.meta.json
    │   │   │   ├── environment_variables/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── exporter/
    │   │   │   │   ├── otlp/
    │   │   │   │   │   ├── proto/
    │   │   │   │   │   │   ├── common/
    │   │   │   │   │   │   │   ├── _internal/
    │   │   │   │   │   │   │   │   ├── trace_encoder/
    │   │   │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   │   │   ├── version/
    │   │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── trace_encoder.data.json
    │   │   │   │   │   │   │   └── trace_encoder.meta.json
    │   │   │   │   │   │   └── grpc/
    │   │   │   │   │   │       ├── trace_exporter/
    │   │   │   │   │   │       │   ├── __init__.data.json
    │   │   │   │   │   │       │   └── __init__.meta.json
    │   │   │   │   │   │       ├── version/
    │   │   │   │   │   │       │   ├── __init__.data.json
    │   │   │   │   │   │       │   └── __init__.meta.json
    │   │   │   │   │   │       ├── __init__.data.json
    │   │   │   │   │   │       ├── __init__.meta.json
    │   │   │   │   │   │       ├── exporter.data.json
    │   │   │   │   │   │       └── exporter.meta.json
    │   │   │   │   │   ├── proto.data.json
    │   │   │   │   │   └── proto.meta.json
    │   │   │   │   ├── otlp.data.json
    │   │   │   │   └── otlp.meta.json
    │   │   │   ├── metrics/
    │   │   │   │   ├── _internal/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── instrument.data.json
    │   │   │   │   │   ├── instrument.meta.json
    │   │   │   │   │   ├── observation.data.json
    │   │   │   │   │   └── observation.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── proto/
    │   │   │   │   ├── collector/
    │   │   │   │   │   ├── logs/
    │   │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   │   ├── logs_service_pb2.data.json
    │   │   │   │   │   │   │   ├── logs_service_pb2.meta.json
    │   │   │   │   │   │   │   ├── logs_service_pb2_grpc.data.json
    │   │   │   │   │   │   │   └── logs_service_pb2_grpc.meta.json
    │   │   │   │   │   │   ├── v1.data.json
    │   │   │   │   │   │   └── v1.meta.json
    │   │   │   │   │   ├── metrics/
    │   │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── metrics_service_pb2.data.json
    │   │   │   │   │   │   │   ├── metrics_service_pb2.meta.json
    │   │   │   │   │   │   │   ├── metrics_service_pb2_grpc.data.json
    │   │   │   │   │   │   │   └── metrics_service_pb2_grpc.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── trace/
    │   │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── trace_service_pb2.data.json
    │   │   │   │   │   │   │   ├── trace_service_pb2.meta.json
    │   │   │   │   │   │   │   ├── trace_service_pb2_grpc.data.json
    │   │   │   │   │   │   │   └── trace_service_pb2_grpc.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── logs.data.json
    │   │   │   │   │   └── logs.meta.json
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── common_pb2.data.json
    │   │   │   │   │   │   └── common_pb2.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── logs/
    │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   ├── logs_pb2.data.json
    │   │   │   │   │   │   └── logs_pb2.meta.json
    │   │   │   │   │   ├── v1.data.json
    │   │   │   │   │   └── v1.meta.json
    │   │   │   │   ├── metrics/
    │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── metrics_pb2.data.json
    │   │   │   │   │   │   └── metrics_pb2.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── resource/
    │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── resource_pb2.data.json
    │   │   │   │   │   │   └── resource_pb2.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── trace/
    │   │   │   │   │   ├── v1/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── trace_pb2.data.json
    │   │   │   │   │   │   └── trace_pb2.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── logs.data.json
    │   │   │   │   └── logs.meta.json
    │   │   │   ├── sdk/
    │   │   │   │   ├── _logs/
    │   │   │   │   │   ├── _internal/
    │   │   │   │   │   │   ├── export/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── in_memory_log_exporter.data.json
    │   │   │   │   │   │   │   └── in_memory_log_exporter.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── export/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── _shared_internal/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── environment_variables/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── metrics/
    │   │   │   │   │   ├── _internal/
    │   │   │   │   │   │   ├── exemplar/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── exemplar.data.json
    │   │   │   │   │   │   │   ├── exemplar.meta.json
    │   │   │   │   │   │   │   ├── exemplar_filter.data.json
    │   │   │   │   │   │   │   ├── exemplar_filter.meta.json
    │   │   │   │   │   │   │   ├── exemplar_reservoir.data.json
    │   │   │   │   │   │   │   └── exemplar_reservoir.meta.json
    │   │   │   │   │   │   ├── exponential_histogram/
    │   │   │   │   │   │   │   ├── mapping/
    │   │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   │   ├── errors.data.json
    │   │   │   │   │   │   │   │   ├── errors.meta.json
    │   │   │   │   │   │   │   │   ├── exponent_mapping.data.json
    │   │   │   │   │   │   │   │   ├── exponent_mapping.meta.json
    │   │   │   │   │   │   │   │   ├── ieee_754.data.json
    │   │   │   │   │   │   │   │   ├── ieee_754.meta.json
    │   │   │   │   │   │   │   │   ├── logarithm_mapping.data.json
    │   │   │   │   │   │   │   │   └── logarithm_mapping.meta.json
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   │   ├── buckets.data.json
    │   │   │   │   │   │   │   └── buckets.meta.json
    │   │   │   │   │   │   ├── export/
    │   │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── _view_instrument_match.data.json
    │   │   │   │   │   │   ├── _view_instrument_match.meta.json
    │   │   │   │   │   │   ├── aggregation.data.json
    │   │   │   │   │   │   ├── aggregation.meta.json
    │   │   │   │   │   │   ├── exceptions.data.json
    │   │   │   │   │   │   ├── exceptions.meta.json
    │   │   │   │   │   │   ├── instrument.data.json
    │   │   │   │   │   │   ├── instrument.meta.json
    │   │   │   │   │   │   ├── measurement.data.json
    │   │   │   │   │   │   ├── measurement.meta.json
    │   │   │   │   │   │   ├── measurement_consumer.data.json
    │   │   │   │   │   │   ├── measurement_consumer.meta.json
    │   │   │   │   │   │   ├── metric_reader_storage.data.json
    │   │   │   │   │   │   ├── metric_reader_storage.meta.json
    │   │   │   │   │   │   ├── point.data.json
    │   │   │   │   │   │   ├── point.meta.json
    │   │   │   │   │   │   ├── sdk_configuration.data.json
    │   │   │   │   │   │   ├── sdk_configuration.meta.json
    │   │   │   │   │   │   ├── view.data.json
    │   │   │   │   │   │   └── view.meta.json
    │   │   │   │   │   ├── export/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── resources/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── trace/
    │   │   │   │   │   ├── export/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── id_generator.data.json
    │   │   │   │   │   ├── id_generator.meta.json
    │   │   │   │   │   ├── sampling.data.json
    │   │   │   │   │   └── sampling.meta.json
    │   │   │   │   ├── util/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── instrumentation.data.json
    │   │   │   │   │   └── instrumentation.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── semconv/
    │   │   │   │   ├── _incubating/
    │   │   │   │   │   ├── attributes/
    │   │   │   │   │   │   ├── code_attributes.data.json
    │   │   │   │   │   │   └── code_attributes.meta.json
    │   │   │   │   │   ├── attributes.data.json
    │   │   │   │   │   └── attributes.meta.json
    │   │   │   │   ├── attributes/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── exception_attributes.data.json
    │   │   │   │   │   └── exception_attributes.meta.json
    │   │   │   │   ├── resource/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _incubating.data.json
    │   │   │   │   └── _incubating.meta.json
    │   │   │   ├── trace/
    │   │   │   │   ├── propagation/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── span.data.json
    │   │   │   │   ├── span.meta.json
    │   │   │   │   ├── status.data.json
    │   │   │   │   └── status.meta.json
    │   │   │   ├── util/
    │   │   │   │   ├── _decorator.data.json
    │   │   │   │   ├── _decorator.meta.json
    │   │   │   │   ├── _importlib_metadata.data.json
    │   │   │   │   ├── _importlib_metadata.meta.json
    │   │   │   │   ├── _once.data.json
    │   │   │   │   ├── _once.meta.json
    │   │   │   │   ├── _providers.data.json
    │   │   │   │   ├── _providers.meta.json
    │   │   │   │   ├── re.data.json
    │   │   │   │   ├── re.meta.json
    │   │   │   │   ├── types.data.json
    │   │   │   │   └── types.meta.json
    │   │   │   ├── exporter.data.json
    │   │   │   ├── exporter.meta.json
    │   │   │   ├── util.data.json
    │   │   │   └── util.meta.json
    │   │   ├── orjson/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── os/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── path.data.json
    │   │   │   └── path.meta.json
    │   │   ├── packaging/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _elffile.data.json
    │   │   │   ├── _elffile.meta.json
    │   │   │   ├── _manylinux.data.json
    │   │   │   ├── _manylinux.meta.json
    │   │   │   ├── _musllinux.data.json
    │   │   │   ├── _musllinux.meta.json
    │   │   │   ├── _parser.data.json
    │   │   │   ├── _parser.meta.json
    │   │   │   ├── _structures.data.json
    │   │   │   ├── _structures.meta.json
    │   │   │   ├── _tokenizer.data.json
    │   │   │   ├── _tokenizer.meta.json
    │   │   │   ├── markers.data.json
    │   │   │   ├── markers.meta.json
    │   │   │   ├── requirements.data.json
    │   │   │   ├── requirements.meta.json
    │   │   │   ├── specifiers.data.json
    │   │   │   ├── specifiers.meta.json
    │   │   │   ├── tags.data.json
    │   │   │   ├── tags.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   ├── utils.meta.json
    │   │   │   ├── version.data.json
    │   │   │   └── version.meta.json
    │   │   ├── pandas/
    │   │   │   ├── _config/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   └── config.meta.json
    │   │   │   ├── _libs/
    │   │   │   │   ├── tslibs/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── nattype.data.json
    │   │   │   │   │   ├── nattype.meta.json
    │   │   │   │   │   ├── np_datetime.data.json
    │   │   │   │   │   ├── np_datetime.meta.json
    │   │   │   │   │   ├── offsets.data.json
    │   │   │   │   │   ├── offsets.meta.json
    │   │   │   │   │   ├── period.data.json
    │   │   │   │   │   ├── period.meta.json
    │   │   │   │   │   ├── timedeltas.data.json
    │   │   │   │   │   ├── timedeltas.meta.json
    │   │   │   │   │   ├── timestamps.data.json
    │   │   │   │   │   └── timestamps.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── indexing.data.json
    │   │   │   │   ├── indexing.meta.json
    │   │   │   │   ├── interval.data.json
    │   │   │   │   ├── interval.meta.json
    │   │   │   │   ├── lib.data.json
    │   │   │   │   ├── lib.meta.json
    │   │   │   │   ├── missing.data.json
    │   │   │   │   ├── missing.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   └── properties.meta.json
    │   │   │   ├── _testing/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── api/
    │   │   │   │   ├── extensions/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── indexers/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── interchange/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── types/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── typing/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── arrays/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── core/
    │   │   │   │   ├── arrays/
    │   │   │   │   │   ├── arrow/
    │   │   │   │   │   │   ├── dtype.data.json
    │   │   │   │   │   │   └── dtype.meta.json
    │   │   │   │   │   ├── sparse/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── accessor.data.json
    │   │   │   │   │   │   ├── accessor.meta.json
    │   │   │   │   │   │   ├── array.data.json
    │   │   │   │   │   │   ├── array.meta.json
    │   │   │   │   │   │   ├── dtype.data.json
    │   │   │   │   │   │   └── dtype.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── arrow.data.json
    │   │   │   │   │   ├── arrow.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── boolean.data.json
    │   │   │   │   │   ├── boolean.meta.json
    │   │   │   │   │   ├── categorical.data.json
    │   │   │   │   │   ├── categorical.meta.json
    │   │   │   │   │   ├── datetimelike.data.json
    │   │   │   │   │   ├── datetimelike.meta.json
    │   │   │   │   │   ├── datetimes.data.json
    │   │   │   │   │   ├── datetimes.meta.json
    │   │   │   │   │   ├── floating.data.json
    │   │   │   │   │   ├── floating.meta.json
    │   │   │   │   │   ├── integer.data.json
    │   │   │   │   │   ├── integer.meta.json
    │   │   │   │   │   ├── interval.data.json
    │   │   │   │   │   ├── interval.meta.json
    │   │   │   │   │   ├── masked.data.json
    │   │   │   │   │   ├── masked.meta.json
    │   │   │   │   │   ├── numeric.data.json
    │   │   │   │   │   ├── numeric.meta.json
    │   │   │   │   │   ├── numpy_.data.json
    │   │   │   │   │   ├── numpy_.meta.json
    │   │   │   │   │   ├── period.data.json
    │   │   │   │   │   ├── period.meta.json
    │   │   │   │   │   ├── string_.data.json
    │   │   │   │   │   ├── string_.meta.json
    │   │   │   │   │   ├── timedeltas.data.json
    │   │   │   │   │   └── timedeltas.meta.json
    │   │   │   │   ├── computation/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── api.data.json
    │   │   │   │   │   ├── api.meta.json
    │   │   │   │   │   ├── eval.data.json
    │   │   │   │   │   ├── eval.meta.json
    │   │   │   │   │   ├── expr.data.json
    │   │   │   │   │   ├── expr.meta.json
    │   │   │   │   │   ├── ops.data.json
    │   │   │   │   │   ├── ops.meta.json
    │   │   │   │   │   ├── pytables.data.json
    │   │   │   │   │   ├── pytables.meta.json
    │   │   │   │   │   ├── scope.data.json
    │   │   │   │   │   └── scope.meta.json
    │   │   │   │   ├── dtypes/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── api.data.json
    │   │   │   │   │   ├── api.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── common.data.json
    │   │   │   │   │   ├── common.meta.json
    │   │   │   │   │   ├── concat.data.json
    │   │   │   │   │   ├── concat.meta.json
    │   │   │   │   │   ├── dtypes.data.json
    │   │   │   │   │   ├── dtypes.meta.json
    │   │   │   │   │   ├── inference.data.json
    │   │   │   │   │   ├── inference.meta.json
    │   │   │   │   │   ├── missing.data.json
    │   │   │   │   │   └── missing.meta.json
    │   │   │   │   ├── groupby/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── generic.data.json
    │   │   │   │   │   ├── generic.meta.json
    │   │   │   │   │   ├── groupby.data.json
    │   │   │   │   │   ├── groupby.meta.json
    │   │   │   │   │   ├── grouper.data.json
    │   │   │   │   │   ├── grouper.meta.json
    │   │   │   │   │   ├── indexing.data.json
    │   │   │   │   │   └── indexing.meta.json
    │   │   │   │   ├── indexes/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── accessors.data.json
    │   │   │   │   │   ├── accessors.meta.json
    │   │   │   │   │   ├── api.data.json
    │   │   │   │   │   ├── api.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── category.data.json
    │   │   │   │   │   ├── category.meta.json
    │   │   │   │   │   ├── datetimelike.data.json
    │   │   │   │   │   ├── datetimelike.meta.json
    │   │   │   │   │   ├── datetimes.data.json
    │   │   │   │   │   ├── datetimes.meta.json
    │   │   │   │   │   ├── extension.data.json
    │   │   │   │   │   ├── extension.meta.json
    │   │   │   │   │   ├── frozen.data.json
    │   │   │   │   │   ├── frozen.meta.json
    │   │   │   │   │   ├── interval.data.json
    │   │   │   │   │   ├── interval.meta.json
    │   │   │   │   │   ├── multi.data.json
    │   │   │   │   │   ├── multi.meta.json
    │   │   │   │   │   ├── period.data.json
    │   │   │   │   │   ├── period.meta.json
    │   │   │   │   │   ├── range.data.json
    │   │   │   │   │   ├── range.meta.json
    │   │   │   │   │   ├── timedeltas.data.json
    │   │   │   │   │   └── timedeltas.meta.json
    │   │   │   │   ├── interchange/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── dataframe_protocol.data.json
    │   │   │   │   │   ├── dataframe_protocol.meta.json
    │   │   │   │   │   ├── from_dataframe.data.json
    │   │   │   │   │   └── from_dataframe.meta.json
    │   │   │   │   ├── reshape/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── api.data.json
    │   │   │   │   │   ├── api.meta.json
    │   │   │   │   │   ├── concat.data.json
    │   │   │   │   │   ├── concat.meta.json
    │   │   │   │   │   ├── encoding.data.json
    │   │   │   │   │   ├── encoding.meta.json
    │   │   │   │   │   ├── melt.data.json
    │   │   │   │   │   ├── melt.meta.json
    │   │   │   │   │   ├── merge.data.json
    │   │   │   │   │   ├── merge.meta.json
    │   │   │   │   │   ├── pivot.data.json
    │   │   │   │   │   ├── pivot.meta.json
    │   │   │   │   │   ├── tile.data.json
    │   │   │   │   │   └── tile.meta.json
    │   │   │   │   ├── strings/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── accessor.data.json
    │   │   │   │   │   └── accessor.meta.json
    │   │   │   │   ├── tools/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── datetimes.data.json
    │   │   │   │   │   ├── datetimes.meta.json
    │   │   │   │   │   ├── numeric.data.json
    │   │   │   │   │   ├── numeric.meta.json
    │   │   │   │   │   ├── timedeltas.data.json
    │   │   │   │   │   └── timedeltas.meta.json
    │   │   │   │   ├── util/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── hashing.data.json
    │   │   │   │   │   └── hashing.meta.json
    │   │   │   │   ├── window/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── ewm.data.json
    │   │   │   │   │   ├── ewm.meta.json
    │   │   │   │   │   ├── expanding.data.json
    │   │   │   │   │   ├── expanding.meta.json
    │   │   │   │   │   ├── rolling.data.json
    │   │   │   │   │   └── rolling.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── accessor.data.json
    │   │   │   │   ├── accessor.meta.json
    │   │   │   │   ├── algorithms.data.json
    │   │   │   │   ├── algorithms.meta.json
    │   │   │   │   ├── api.data.json
    │   │   │   │   ├── api.meta.json
    │   │   │   │   ├── arraylike.data.json
    │   │   │   │   ├── arraylike.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── construction.data.json
    │   │   │   │   ├── construction.meta.json
    │   │   │   │   ├── frame.data.json
    │   │   │   │   ├── frame.meta.json
    │   │   │   │   ├── generic.data.json
    │   │   │   │   ├── generic.meta.json
    │   │   │   │   ├── indexers.data.json
    │   │   │   │   ├── indexers.meta.json
    │   │   │   │   ├── indexing.data.json
    │   │   │   │   ├── indexing.meta.json
    │   │   │   │   ├── resample.data.json
    │   │   │   │   ├── resample.meta.json
    │   │   │   │   ├── series.data.json
    │   │   │   │   └── series.meta.json
    │   │   │   ├── errors/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── io/
    │   │   │   │   ├── excel/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _base.data.json
    │   │   │   │   │   └── _base.meta.json
    │   │   │   │   ├── formats/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── format.data.json
    │   │   │   │   │   ├── format.meta.json
    │   │   │   │   │   ├── style.data.json
    │   │   │   │   │   ├── style.meta.json
    │   │   │   │   │   ├── style_render.data.json
    │   │   │   │   │   └── style_render.meta.json
    │   │   │   │   ├── json/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _json.data.json
    │   │   │   │   │   ├── _json.meta.json
    │   │   │   │   │   ├── _normalize.data.json
    │   │   │   │   │   ├── _normalize.meta.json
    │   │   │   │   │   ├── _table_schema.data.json
    │   │   │   │   │   └── _table_schema.meta.json
    │   │   │   │   ├── parsers/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── readers.data.json
    │   │   │   │   │   └── readers.meta.json
    │   │   │   │   ├── sas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── sas7bdat.data.json
    │   │   │   │   │   ├── sas7bdat.meta.json
    │   │   │   │   │   ├── sas_xport.data.json
    │   │   │   │   │   ├── sas_xport.meta.json
    │   │   │   │   │   ├── sasreader.data.json
    │   │   │   │   │   └── sasreader.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── api.data.json
    │   │   │   │   ├── api.meta.json
    │   │   │   │   ├── clipboards.data.json
    │   │   │   │   ├── clipboards.meta.json
    │   │   │   │   ├── feather_format.data.json
    │   │   │   │   ├── feather_format.meta.json
    │   │   │   │   ├── html.data.json
    │   │   │   │   ├── html.meta.json
    │   │   │   │   ├── orc.data.json
    │   │   │   │   ├── orc.meta.json
    │   │   │   │   ├── parquet.data.json
    │   │   │   │   ├── parquet.meta.json
    │   │   │   │   ├── pickle.data.json
    │   │   │   │   ├── pickle.meta.json
    │   │   │   │   ├── pytables.data.json
    │   │   │   │   ├── pytables.meta.json
    │   │   │   │   ├── spss.data.json
    │   │   │   │   ├── spss.meta.json
    │   │   │   │   ├── sql.data.json
    │   │   │   │   ├── sql.meta.json
    │   │   │   │   ├── stata.data.json
    │   │   │   │   ├── stata.meta.json
    │   │   │   │   ├── xml.data.json
    │   │   │   │   └── xml.meta.json
    │   │   │   ├── plotting/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _core.data.json
    │   │   │   │   ├── _core.meta.json
    │   │   │   │   ├── _misc.data.json
    │   │   │   │   └── _misc.meta.json
    │   │   │   ├── tseries/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── api.data.json
    │   │   │   │   ├── api.meta.json
    │   │   │   │   ├── frequencies.data.json
    │   │   │   │   ├── frequencies.meta.json
    │   │   │   │   ├── holiday.data.json
    │   │   │   │   ├── holiday.meta.json
    │   │   │   │   ├── offsets.data.json
    │   │   │   │   └── offsets.meta.json
    │   │   │   ├── util/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _decorators.data.json
    │   │   │   │   ├── _decorators.meta.json
    │   │   │   │   ├── _print_versions.data.json
    │   │   │   │   └── _print_versions.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _typing.data.json
    │   │   │   ├── _typing.meta.json
    │   │   │   ├── testing.data.json
    │   │   │   └── testing.meta.json
    │   │   ├── pandera/
    │   │   │   ├── accessors/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── dask_accessor.data.json
    │   │   │   │   ├── dask_accessor.meta.json
    │   │   │   │   ├── pandas_accessor.data.json
    │   │   │   │   └── pandas_accessor.meta.json
    │   │   │   ├── api/
    │   │   │   │   ├── base/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── checks.data.json
    │   │   │   │   │   ├── checks.meta.json
    │   │   │   │   │   ├── error_handler.data.json
    │   │   │   │   │   ├── error_handler.meta.json
    │   │   │   │   │   ├── model.data.json
    │   │   │   │   │   ├── model.meta.json
    │   │   │   │   │   ├── model_components.data.json
    │   │   │   │   │   ├── model_components.meta.json
    │   │   │   │   │   ├── model_config.data.json
    │   │   │   │   │   ├── model_config.meta.json
    │   │   │   │   │   ├── parsers.data.json
    │   │   │   │   │   ├── parsers.meta.json
    │   │   │   │   │   ├── schema.data.json
    │   │   │   │   │   ├── schema.meta.json
    │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   └── types.meta.json
    │   │   │   │   ├── dataframe/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── components.data.json
    │   │   │   │   │   ├── components.meta.json
    │   │   │   │   │   ├── container.data.json
    │   │   │   │   │   ├── container.meta.json
    │   │   │   │   │   ├── model.data.json
    │   │   │   │   │   ├── model.meta.json
    │   │   │   │   │   ├── model_components.data.json
    │   │   │   │   │   ├── model_components.meta.json
    │   │   │   │   │   ├── model_config.data.json
    │   │   │   │   │   └── model_config.meta.json
    │   │   │   │   ├── pandas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── array.data.json
    │   │   │   │   │   ├── array.meta.json
    │   │   │   │   │   ├── components.data.json
    │   │   │   │   │   ├── components.meta.json
    │   │   │   │   │   ├── container.data.json
    │   │   │   │   │   ├── container.meta.json
    │   │   │   │   │   ├── model.data.json
    │   │   │   │   │   ├── model.meta.json
    │   │   │   │   │   ├── model_config.data.json
    │   │   │   │   │   ├── model_config.meta.json
    │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   └── types.meta.json
    │   │   │   │   ├── polars/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── components.data.json
    │   │   │   │   │   ├── components.meta.json
    │   │   │   │   │   ├── container.data.json
    │   │   │   │   │   ├── container.meta.json
    │   │   │   │   │   ├── model.data.json
    │   │   │   │   │   ├── model.meta.json
    │   │   │   │   │   ├── model_config.data.json
    │   │   │   │   │   ├── model_config.meta.json
    │   │   │   │   │   ├── types.data.json
    │   │   │   │   │   ├── types.meta.json
    │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   └── utils.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── checks.data.json
    │   │   │   │   ├── checks.meta.json
    │   │   │   │   ├── extensions.data.json
    │   │   │   │   ├── extensions.meta.json
    │   │   │   │   ├── function_dispatch.data.json
    │   │   │   │   ├── function_dispatch.meta.json
    │   │   │   │   ├── hypotheses.data.json
    │   │   │   │   ├── hypotheses.meta.json
    │   │   │   │   ├── parsers.data.json
    │   │   │   │   └── parsers.meta.json
    │   │   │   ├── backends/
    │   │   │   │   ├── base/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── builtin_checks.data.json
    │   │   │   │   │   ├── builtin_checks.meta.json
    │   │   │   │   │   ├── builtin_hypotheses.data.json
    │   │   │   │   │   └── builtin_hypotheses.meta.json
    │   │   │   │   ├── pandas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── array.data.json
    │   │   │   │   │   ├── array.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── checks.data.json
    │   │   │   │   │   ├── checks.meta.json
    │   │   │   │   │   ├── components.data.json
    │   │   │   │   │   ├── components.meta.json
    │   │   │   │   │   ├── container.data.json
    │   │   │   │   │   ├── container.meta.json
    │   │   │   │   │   ├── error_formatters.data.json
    │   │   │   │   │   ├── error_formatters.meta.json
    │   │   │   │   │   ├── hypotheses.data.json
    │   │   │   │   │   ├── hypotheses.meta.json
    │   │   │   │   │   ├── parsers.data.json
    │   │   │   │   │   ├── parsers.meta.json
    │   │   │   │   │   ├── register.data.json
    │   │   │   │   │   └── register.meta.json
    │   │   │   │   ├── polars/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── register.data.json
    │   │   │   │   │   └── register.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── engines/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── engine.data.json
    │   │   │   │   ├── engine.meta.json
    │   │   │   │   ├── geopandas_engine.data.json
    │   │   │   │   ├── geopandas_engine.meta.json
    │   │   │   │   ├── numpy_engine.data.json
    │   │   │   │   ├── numpy_engine.meta.json
    │   │   │   │   ├── pandas_engine.data.json
    │   │   │   │   ├── pandas_engine.meta.json
    │   │   │   │   ├── polars_engine.data.json
    │   │   │   │   ├── polars_engine.meta.json
    │   │   │   │   ├── pyarrow_engine.data.json
    │   │   │   │   ├── pyarrow_engine.meta.json
    │   │   │   │   ├── type_aliases.data.json
    │   │   │   │   ├── type_aliases.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── io/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── pandas_io.data.json
    │   │   │   │   └── pandas_io.meta.json
    │   │   │   ├── schema_inference/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── pandas.data.json
    │   │   │   │   └── pandas.meta.json
    │   │   │   ├── schema_statistics/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── pandas.data.json
    │   │   │   │   └── pandas.meta.json
    │   │   │   ├── strategies/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── base_strategies.data.json
    │   │   │   │   ├── base_strategies.meta.json
    │   │   │   │   ├── pandas_strategies.data.json
    │   │   │   │   └── pandas_strategies.meta.json
    │   │   │   ├── typing/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── common.data.json
    │   │   │   │   ├── common.meta.json
    │   │   │   │   ├── formats.data.json
    │   │   │   │   ├── formats.meta.json
    │   │   │   │   ├── pandas.data.json
    │   │   │   │   ├── pandas.meta.json
    │   │   │   │   ├── polars.data.json
    │   │   │   │   └── polars.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _pandas_deprecated.data.json
    │   │   │   ├── _pandas_deprecated.meta.json
    │   │   │   ├── _patch_numpy2.data.json
    │   │   │   ├── _patch_numpy2.meta.json
    │   │   │   ├── _version.data.json
    │   │   │   ├── _version.meta.json
    │   │   │   ├── config.data.json
    │   │   │   ├── config.meta.json
    │   │   │   ├── constants.data.json
    │   │   │   ├── constants.meta.json
    │   │   │   ├── decorators.data.json
    │   │   │   ├── decorators.meta.json
    │   │   │   ├── dtypes.data.json
    │   │   │   ├── dtypes.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── extensions.data.json
    │   │   │   ├── extensions.meta.json
    │   │   │   ├── external_config.data.json
    │   │   │   ├── external_config.meta.json
    │   │   │   ├── import_utils.data.json
    │   │   │   ├── import_utils.meta.json
    │   │   │   ├── inspection_utils.data.json
    │   │   │   ├── inspection_utils.meta.json
    │   │   │   ├── pandas.data.json
    │   │   │   ├── pandas.meta.json
    │   │   │   ├── polars.data.json
    │   │   │   ├── polars.meta.json
    │   │   │   ├── system.data.json
    │   │   │   ├── system.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   ├── utils.meta.json
    │   │   │   ├── validation_depth.data.json
    │   │   │   └── validation_depth.meta.json
    │   │   ├── pathlib/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── pathspec/
    │   │   │   ├── patterns/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── gitwildmatch.data.json
    │   │   │   │   └── gitwildmatch.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _meta.data.json
    │   │   │   ├── _meta.meta.json
    │   │   │   ├── gitignore.data.json
    │   │   │   ├── gitignore.meta.json
    │   │   │   ├── pathspec.data.json
    │   │   │   ├── pathspec.meta.json
    │   │   │   ├── pattern.data.json
    │   │   │   ├── pattern.meta.json
    │   │   │   ├── util.data.json
    │   │   │   └── util.meta.json
    │   │   ├── platformdirs/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── api.data.json
    │   │   │   ├── api.meta.json
    │   │   │   ├── version.data.json
    │   │   │   ├── version.meta.json
    │   │   │   ├── windows.data.json
    │   │   │   └── windows.meta.json
    │   │   ├── pluggy/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _callers.data.json
    │   │   │   ├── _callers.meta.json
    │   │   │   ├── _hooks.data.json
    │   │   │   ├── _hooks.meta.json
    │   │   │   ├── _manager.data.json
    │   │   │   ├── _manager.meta.json
    │   │   │   ├── _result.data.json
    │   │   │   ├── _result.meta.json
    │   │   │   ├── _tracing.data.json
    │   │   │   ├── _tracing.meta.json
    │   │   │   ├── _version.data.json
    │   │   │   ├── _version.meta.json
    │   │   │   ├── _warnings.data.json
    │   │   │   └── _warnings.meta.json
    │   │   ├── polars/
    │   │   │   ├── _utils/
    │   │   │   │   ├── construction/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── dataframe.data.json
    │   │   │   │   │   ├── dataframe.meta.json
    │   │   │   │   │   ├── other.data.json
    │   │   │   │   │   ├── other.meta.json
    │   │   │   │   │   ├── series.data.json
    │   │   │   │   │   ├── series.meta.json
    │   │   │   │   │   ├── utils.data.json
    │   │   │   │   │   └── utils.meta.json
    │   │   │   │   ├── parse/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── expr.data.json
    │   │   │   │   │   └── expr.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── async_.data.json
    │   │   │   │   ├── async_.meta.json
    │   │   │   │   ├── cache.data.json
    │   │   │   │   ├── cache.meta.json
    │   │   │   │   ├── constants.data.json
    │   │   │   │   ├── constants.meta.json
    │   │   │   │   ├── convert.data.json
    │   │   │   │   ├── convert.meta.json
    │   │   │   │   ├── deprecation.data.json
    │   │   │   │   ├── deprecation.meta.json
    │   │   │   │   ├── getitem.data.json
    │   │   │   │   ├── getitem.meta.json
    │   │   │   │   ├── logging.data.json
    │   │   │   │   ├── logging.meta.json
    │   │   │   │   ├── parquet.data.json
    │   │   │   │   ├── parquet.meta.json
    │   │   │   │   ├── polars_version.data.json
    │   │   │   │   ├── polars_version.meta.json
    │   │   │   │   ├── pycapsule.data.json
    │   │   │   │   ├── pycapsule.meta.json
    │   │   │   │   ├── scan.data.json
    │   │   │   │   ├── scan.meta.json
    │   │   │   │   ├── serde.data.json
    │   │   │   │   ├── serde.meta.json
    │   │   │   │   ├── slice.data.json
    │   │   │   │   ├── slice.meta.json
    │   │   │   │   ├── udfs.data.json
    │   │   │   │   ├── udfs.meta.json
    │   │   │   │   ├── unstable.data.json
    │   │   │   │   ├── unstable.meta.json
    │   │   │   │   ├── various.data.json
    │   │   │   │   ├── various.meta.json
    │   │   │   │   ├── wrap.data.json
    │   │   │   │   └── wrap.meta.json
    │   │   │   ├── catalog/
    │   │   │   │   ├── unity/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   ├── client.meta.json
    │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   └── models.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── convert/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── general.data.json
    │   │   │   │   ├── general.meta.json
    │   │   │   │   ├── normalize.data.json
    │   │   │   │   └── normalize.meta.json
    │   │   │   ├── dataframe/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _html.data.json
    │   │   │   │   ├── _html.meta.json
    │   │   │   │   ├── frame.data.json
    │   │   │   │   ├── frame.meta.json
    │   │   │   │   ├── group_by.data.json
    │   │   │   │   ├── group_by.meta.json
    │   │   │   │   ├── plotting.data.json
    │   │   │   │   └── plotting.meta.json
    │   │   │   ├── datatype_expr/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── array.data.json
    │   │   │   │   ├── array.meta.json
    │   │   │   │   ├── datatype_expr.data.json
    │   │   │   │   ├── datatype_expr.meta.json
    │   │   │   │   ├── list.data.json
    │   │   │   │   ├── list.meta.json
    │   │   │   │   ├── struct.data.json
    │   │   │   │   └── struct.meta.json
    │   │   │   ├── datatypes/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _parse.data.json
    │   │   │   │   ├── _parse.meta.json
    │   │   │   │   ├── _utils.data.json
    │   │   │   │   ├── _utils.meta.json
    │   │   │   │   ├── classes.data.json
    │   │   │   │   ├── classes.meta.json
    │   │   │   │   ├── constants.data.json
    │   │   │   │   ├── constants.meta.json
    │   │   │   │   ├── constructor.data.json
    │   │   │   │   ├── constructor.meta.json
    │   │   │   │   ├── convert.data.json
    │   │   │   │   ├── convert.meta.json
    │   │   │   │   ├── extension.data.json
    │   │   │   │   ├── extension.meta.json
    │   │   │   │   ├── group.data.json
    │   │   │   │   └── group.meta.json
    │   │   │   ├── expr/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── array.data.json
    │   │   │   │   ├── array.meta.json
    │   │   │   │   ├── binary.data.json
    │   │   │   │   ├── binary.meta.json
    │   │   │   │   ├── categorical.data.json
    │   │   │   │   ├── categorical.meta.json
    │   │   │   │   ├── datetime.data.json
    │   │   │   │   ├── datetime.meta.json
    │   │   │   │   ├── expr.data.json
    │   │   │   │   ├── expr.meta.json
    │   │   │   │   ├── ext.data.json
    │   │   │   │   ├── ext.meta.json
    │   │   │   │   ├── list.data.json
    │   │   │   │   ├── list.meta.json
    │   │   │   │   ├── meta.data.json
    │   │   │   │   ├── meta.meta.json
    │   │   │   │   ├── name.data.json
    │   │   │   │   ├── name.meta.json
    │   │   │   │   ├── string.data.json
    │   │   │   │   ├── string.meta.json
    │   │   │   │   ├── struct.data.json
    │   │   │   │   ├── struct.meta.json
    │   │   │   │   ├── whenthen.data.json
    │   │   │   │   └── whenthen.meta.json
    │   │   │   ├── functions/
    │   │   │   │   ├── aggregation/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── horizontal.data.json
    │   │   │   │   │   ├── horizontal.meta.json
    │   │   │   │   │   ├── vertical.data.json
    │   │   │   │   │   └── vertical.meta.json
    │   │   │   │   ├── range/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _utils.data.json
    │   │   │   │   │   ├── _utils.meta.json
    │   │   │   │   │   ├── date_range.data.json
    │   │   │   │   │   ├── date_range.meta.json
    │   │   │   │   │   ├── datetime_range.data.json
    │   │   │   │   │   ├── datetime_range.meta.json
    │   │   │   │   │   ├── int_range.data.json
    │   │   │   │   │   ├── int_range.meta.json
    │   │   │   │   │   ├── linear_space.data.json
    │   │   │   │   │   ├── linear_space.meta.json
    │   │   │   │   │   ├── time_range.data.json
    │   │   │   │   │   └── time_range.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── as_datatype.data.json
    │   │   │   │   ├── as_datatype.meta.json
    │   │   │   │   ├── business.data.json
    │   │   │   │   ├── business.meta.json
    │   │   │   │   ├── col.data.json
    │   │   │   │   ├── col.meta.json
    │   │   │   │   ├── datatype.data.json
    │   │   │   │   ├── datatype.meta.json
    │   │   │   │   ├── eager.data.json
    │   │   │   │   ├── eager.meta.json
    │   │   │   │   ├── escape_regex.data.json
    │   │   │   │   ├── escape_regex.meta.json
    │   │   │   │   ├── lazy.data.json
    │   │   │   │   ├── lazy.meta.json
    │   │   │   │   ├── len.data.json
    │   │   │   │   ├── len.meta.json
    │   │   │   │   ├── lit.data.json
    │   │   │   │   ├── lit.meta.json
    │   │   │   │   ├── random.data.json
    │   │   │   │   ├── random.meta.json
    │   │   │   │   ├── repeat.data.json
    │   │   │   │   ├── repeat.meta.json
    │   │   │   │   ├── whenthen.data.json
    │   │   │   │   └── whenthen.meta.json
    │   │   │   ├── interchange/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── buffer.data.json
    │   │   │   │   ├── buffer.meta.json
    │   │   │   │   ├── column.data.json
    │   │   │   │   ├── column.meta.json
    │   │   │   │   ├── dataframe.data.json
    │   │   │   │   ├── dataframe.meta.json
    │   │   │   │   ├── protocol.data.json
    │   │   │   │   ├── protocol.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── io/
    │   │   │   │   ├── cloud/
    │   │   │   │   │   ├── credential_provider/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── _builder.data.json
    │   │   │   │   │   │   ├── _builder.meta.json
    │   │   │   │   │   │   ├── _providers.data.json
    │   │   │   │   │   │   └── _providers.meta.json
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _utils.data.json
    │   │   │   │   │   └── _utils.meta.json
    │   │   │   │   ├── csv/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _utils.data.json
    │   │   │   │   │   ├── _utils.meta.json
    │   │   │   │   │   ├── batched_reader.data.json
    │   │   │   │   │   ├── batched_reader.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── database/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _arrow_registry.data.json
    │   │   │   │   │   ├── _arrow_registry.meta.json
    │   │   │   │   │   ├── _cursor_proxies.data.json
    │   │   │   │   │   ├── _cursor_proxies.meta.json
    │   │   │   │   │   ├── _executor.data.json
    │   │   │   │   │   ├── _executor.meta.json
    │   │   │   │   │   ├── _inference.data.json
    │   │   │   │   │   ├── _inference.meta.json
    │   │   │   │   │   ├── _utils.data.json
    │   │   │   │   │   ├── _utils.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── iceberg/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _utils.data.json
    │   │   │   │   │   ├── _utils.meta.json
    │   │   │   │   │   ├── dataset.data.json
    │   │   │   │   │   ├── dataset.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── ipc/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── json/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── read.data.json
    │   │   │   │   │   └── read.meta.json
    │   │   │   │   ├── parquet/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── field_overwrites.data.json
    │   │   │   │   │   ├── field_overwrites.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── pyarrow_dataset/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── anonymous_scan.data.json
    │   │   │   │   │   ├── anonymous_scan.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── scan_options/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _options.data.json
    │   │   │   │   │   ├── _options.meta.json
    │   │   │   │   │   ├── cast_options.data.json
    │   │   │   │   │   └── cast_options.meta.json
    │   │   │   │   ├── spreadsheet/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── _write_utils.data.json
    │   │   │   │   │   ├── _write_utils.meta.json
    │   │   │   │   │   ├── functions.data.json
    │   │   │   │   │   └── functions.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _utils.data.json
    │   │   │   │   ├── _utils.meta.json
    │   │   │   │   ├── avro.data.json
    │   │   │   │   ├── avro.meta.json
    │   │   │   │   ├── clipboard.data.json
    │   │   │   │   ├── clipboard.meta.json
    │   │   │   │   ├── delta.data.json
    │   │   │   │   ├── delta.meta.json
    │   │   │   │   ├── ndjson.data.json
    │   │   │   │   ├── ndjson.meta.json
    │   │   │   │   ├── partition.data.json
    │   │   │   │   ├── partition.meta.json
    │   │   │   │   ├── plugins.data.json
    │   │   │   │   └── plugins.meta.json
    │   │   │   ├── lazyframe/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── engine_config.data.json
    │   │   │   │   ├── engine_config.meta.json
    │   │   │   │   ├── frame.data.json
    │   │   │   │   ├── frame.meta.json
    │   │   │   │   ├── group_by.data.json
    │   │   │   │   ├── group_by.meta.json
    │   │   │   │   ├── in_process.data.json
    │   │   │   │   ├── in_process.meta.json
    │   │   │   │   ├── opt_flags.data.json
    │   │   │   │   └── opt_flags.meta.json
    │   │   │   ├── meta/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── build.data.json
    │   │   │   │   ├── build.meta.json
    │   │   │   │   ├── index_type.data.json
    │   │   │   │   ├── index_type.meta.json
    │   │   │   │   ├── thread_pool.data.json
    │   │   │   │   ├── thread_pool.meta.json
    │   │   │   │   ├── versions.data.json
    │   │   │   │   └── versions.meta.json
    │   │   │   ├── ml/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── torch.data.json
    │   │   │   │   ├── torch.meta.json
    │   │   │   │   ├── utilities.data.json
    │   │   │   │   └── utilities.meta.json
    │   │   │   ├── series/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── array.data.json
    │   │   │   │   ├── array.meta.json
    │   │   │   │   ├── binary.data.json
    │   │   │   │   ├── binary.meta.json
    │   │   │   │   ├── categorical.data.json
    │   │   │   │   ├── categorical.meta.json
    │   │   │   │   ├── datetime.data.json
    │   │   │   │   ├── datetime.meta.json
    │   │   │   │   ├── ext.data.json
    │   │   │   │   ├── ext.meta.json
    │   │   │   │   ├── list.data.json
    │   │   │   │   ├── list.meta.json
    │   │   │   │   ├── plotting.data.json
    │   │   │   │   ├── plotting.meta.json
    │   │   │   │   ├── series.data.json
    │   │   │   │   ├── series.meta.json
    │   │   │   │   ├── string.data.json
    │   │   │   │   ├── string.meta.json
    │   │   │   │   ├── struct.data.json
    │   │   │   │   ├── struct.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── sql/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── context.data.json
    │   │   │   │   ├── context.meta.json
    │   │   │   │   ├── functions.data.json
    │   │   │   │   └── functions.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _cpu_check.data.json
    │   │   │   ├── _cpu_check.meta.json
    │   │   │   ├── _dependencies.data.json
    │   │   │   ├── _dependencies.meta.json
    │   │   │   ├── _plr.data.json
    │   │   │   ├── _plr.meta.json
    │   │   │   ├── _reexport.data.json
    │   │   │   ├── _reexport.meta.json
    │   │   │   ├── _typing.data.json
    │   │   │   ├── _typing.meta.json
    │   │   │   ├── api.data.json
    │   │   │   ├── api.meta.json
    │   │   │   ├── config.data.json
    │   │   │   ├── config.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── plugins.data.json
    │   │   │   ├── plugins.meta.json
    │   │   │   ├── schema.data.json
    │   │   │   ├── schema.meta.json
    │   │   │   ├── selectors.data.json
    │   │   │   ├── selectors.meta.json
    │   │   │   ├── string_cache.data.json
    │   │   │   └── string_cache.meta.json
    │   │   ├── prometheus_client/
    │   │   │   ├── openmetrics/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── exposition.data.json
    │   │   │   │   └── exposition.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── asgi.data.json
    │   │   │   ├── asgi.meta.json
    │   │   │   ├── context_managers.data.json
    │   │   │   ├── context_managers.meta.json
    │   │   │   ├── decorator.data.json
    │   │   │   ├── decorator.meta.json
    │   │   │   ├── exposition.data.json
    │   │   │   ├── exposition.meta.json
    │   │   │   ├── gc_collector.data.json
    │   │   │   ├── gc_collector.meta.json
    │   │   │   ├── metrics.data.json
    │   │   │   ├── metrics.meta.json
    │   │   │   ├── metrics_core.data.json
    │   │   │   ├── metrics_core.meta.json
    │   │   │   ├── mmap_dict.data.json
    │   │   │   ├── mmap_dict.meta.json
    │   │   │   ├── platform_collector.data.json
    │   │   │   ├── platform_collector.meta.json
    │   │   │   ├── process_collector.data.json
    │   │   │   ├── process_collector.meta.json
    │   │   │   ├── registry.data.json
    │   │   │   ├── registry.meta.json
    │   │   │   ├── samples.data.json
    │   │   │   ├── samples.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   ├── utils.meta.json
    │   │   │   ├── validation.data.json
    │   │   │   ├── validation.meta.json
    │   │   │   ├── values.data.json
    │   │   │   └── values.meta.json
    │   │   ├── pydantic/
    │   │   │   ├── _internal/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _config.data.json
    │   │   │   │   ├── _config.meta.json
    │   │   │   │   ├── _core_metadata.data.json
    │   │   │   │   ├── _core_metadata.meta.json
    │   │   │   │   ├── _core_utils.data.json
    │   │   │   │   ├── _core_utils.meta.json
    │   │   │   │   ├── _dataclasses.data.json
    │   │   │   │   ├── _dataclasses.meta.json
    │   │   │   │   ├── _decorators.data.json
    │   │   │   │   ├── _decorators.meta.json
    │   │   │   │   ├── _decorators_v1.data.json
    │   │   │   │   ├── _decorators_v1.meta.json
    │   │   │   │   ├── _discriminated_union.data.json
    │   │   │   │   ├── _discriminated_union.meta.json
    │   │   │   │   ├── _docs_extraction.data.json
    │   │   │   │   ├── _docs_extraction.meta.json
    │   │   │   │   ├── _fields.data.json
    │   │   │   │   ├── _fields.meta.json
    │   │   │   │   ├── _forward_ref.data.json
    │   │   │   │   ├── _forward_ref.meta.json
    │   │   │   │   ├── _generate_schema.data.json
    │   │   │   │   ├── _generate_schema.meta.json
    │   │   │   │   ├── _generics.data.json
    │   │   │   │   ├── _generics.meta.json
    │   │   │   │   ├── _import_utils.data.json
    │   │   │   │   ├── _import_utils.meta.json
    │   │   │   │   ├── _internal_dataclass.data.json
    │   │   │   │   ├── _internal_dataclass.meta.json
    │   │   │   │   ├── _known_annotated_metadata.data.json
    │   │   │   │   ├── _known_annotated_metadata.meta.json
    │   │   │   │   ├── _mock_val_ser.data.json
    │   │   │   │   ├── _mock_val_ser.meta.json
    │   │   │   │   ├── _model_construction.data.json
    │   │   │   │   ├── _model_construction.meta.json
    │   │   │   │   ├── _namespace_utils.data.json
    │   │   │   │   ├── _namespace_utils.meta.json
    │   │   │   │   ├── _repr.data.json
    │   │   │   │   ├── _repr.meta.json
    │   │   │   │   ├── _schema_gather.data.json
    │   │   │   │   ├── _schema_gather.meta.json
    │   │   │   │   ├── _schema_generation_shared.data.json
    │   │   │   │   ├── _schema_generation_shared.meta.json
    │   │   │   │   ├── _serializers.data.json
    │   │   │   │   ├── _serializers.meta.json
    │   │   │   │   ├── _signature.data.json
    │   │   │   │   ├── _signature.meta.json
    │   │   │   │   ├── _typing_extra.data.json
    │   │   │   │   ├── _typing_extra.meta.json
    │   │   │   │   ├── _utils.data.json
    │   │   │   │   ├── _utils.meta.json
    │   │   │   │   ├── _validate_call.data.json
    │   │   │   │   ├── _validate_call.meta.json
    │   │   │   │   ├── _validators.data.json
    │   │   │   │   └── _validators.meta.json
    │   │   │   ├── deprecated/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── class_validators.data.json
    │   │   │   │   ├── class_validators.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   ├── config.meta.json
    │   │   │   │   ├── copy_internals.data.json
    │   │   │   │   ├── copy_internals.meta.json
    │   │   │   │   ├── json.data.json
    │   │   │   │   ├── json.meta.json
    │   │   │   │   ├── parse.data.json
    │   │   │   │   ├── parse.meta.json
    │   │   │   │   ├── tools.data.json
    │   │   │   │   └── tools.meta.json
    │   │   │   ├── plugin/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _schema_validator.data.json
    │   │   │   │   └── _schema_validator.meta.json
    │   │   │   ├── v1/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── annotated_types.data.json
    │   │   │   │   ├── annotated_types.meta.json
    │   │   │   │   ├── class_validators.data.json
    │   │   │   │   ├── class_validators.meta.json
    │   │   │   │   ├── color.data.json
    │   │   │   │   ├── color.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   ├── config.meta.json
    │   │   │   │   ├── dataclasses.data.json
    │   │   │   │   ├── dataclasses.meta.json
    │   │   │   │   ├── datetime_parse.data.json
    │   │   │   │   ├── datetime_parse.meta.json
    │   │   │   │   ├── decorator.data.json
    │   │   │   │   ├── decorator.meta.json
    │   │   │   │   ├── env_settings.data.json
    │   │   │   │   ├── env_settings.meta.json
    │   │   │   │   ├── error_wrappers.data.json
    │   │   │   │   ├── error_wrappers.meta.json
    │   │   │   │   ├── errors.data.json
    │   │   │   │   ├── errors.meta.json
    │   │   │   │   ├── fields.data.json
    │   │   │   │   ├── fields.meta.json
    │   │   │   │   ├── json.data.json
    │   │   │   │   ├── json.meta.json
    │   │   │   │   ├── main.data.json
    │   │   │   │   ├── main.meta.json
    │   │   │   │   ├── networks.data.json
    │   │   │   │   ├── networks.meta.json
    │   │   │   │   ├── parse.data.json
    │   │   │   │   ├── parse.meta.json
    │   │   │   │   ├── schema.data.json
    │   │   │   │   ├── schema.meta.json
    │   │   │   │   ├── tools.data.json
    │   │   │   │   ├── tools.meta.json
    │   │   │   │   ├── types.data.json
    │   │   │   │   ├── types.meta.json
    │   │   │   │   ├── typing.data.json
    │   │   │   │   ├── typing.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   ├── utils.meta.json
    │   │   │   │   ├── validators.data.json
    │   │   │   │   ├── validators.meta.json
    │   │   │   │   ├── version.data.json
    │   │   │   │   └── version.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _migration.data.json
    │   │   │   ├── _migration.meta.json
    │   │   │   ├── alias_generators.data.json
    │   │   │   ├── alias_generators.meta.json
    │   │   │   ├── aliases.data.json
    │   │   │   ├── aliases.meta.json
    │   │   │   ├── annotated_handlers.data.json
    │   │   │   ├── annotated_handlers.meta.json
    │   │   │   ├── color.data.json
    │   │   │   ├── color.meta.json
    │   │   │   ├── config.data.json
    │   │   │   ├── config.meta.json
    │   │   │   ├── dataclasses.data.json
    │   │   │   ├── dataclasses.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── fields.data.json
    │   │   │   ├── fields.meta.json
    │   │   │   ├── functional_serializers.data.json
    │   │   │   ├── functional_serializers.meta.json
    │   │   │   ├── functional_validators.data.json
    │   │   │   ├── functional_validators.meta.json
    │   │   │   ├── json_schema.data.json
    │   │   │   ├── json_schema.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── networks.data.json
    │   │   │   ├── networks.meta.json
    │   │   │   ├── root_model.data.json
    │   │   │   ├── root_model.meta.json
    │   │   │   ├── type_adapter.data.json
    │   │   │   ├── type_adapter.meta.json
    │   │   │   ├── types.data.json
    │   │   │   ├── types.meta.json
    │   │   │   ├── validate_call_decorator.data.json
    │   │   │   ├── validate_call_decorator.meta.json
    │   │   │   ├── version.data.json
    │   │   │   ├── version.meta.json
    │   │   │   ├── warnings.data.json
    │   │   │   └── warnings.meta.json
    │   │   ├── pydantic_core/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _pydantic_core.data.json
    │   │   │   ├── _pydantic_core.meta.json
    │   │   │   ├── core_schema.data.json
    │   │   │   └── core_schema.meta.json
    │   │   ├── pydantic_settings/
    │   │   │   ├── sources/
    │   │   │   │   ├── providers/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── aws.data.json
    │   │   │   │   │   ├── aws.meta.json
    │   │   │   │   │   ├── azure.data.json
    │   │   │   │   │   ├── azure.meta.json
    │   │   │   │   │   ├── cli.data.json
    │   │   │   │   │   ├── cli.meta.json
    │   │   │   │   │   ├── dotenv.data.json
    │   │   │   │   │   ├── dotenv.meta.json
    │   │   │   │   │   ├── env.data.json
    │   │   │   │   │   ├── env.meta.json
    │   │   │   │   │   ├── gcp.data.json
    │   │   │   │   │   ├── gcp.meta.json
    │   │   │   │   │   ├── json.data.json
    │   │   │   │   │   ├── json.meta.json
    │   │   │   │   │   ├── nested_secrets.data.json
    │   │   │   │   │   ├── nested_secrets.meta.json
    │   │   │   │   │   ├── pyproject.data.json
    │   │   │   │   │   ├── pyproject.meta.json
    │   │   │   │   │   ├── secrets.data.json
    │   │   │   │   │   ├── secrets.meta.json
    │   │   │   │   │   ├── toml.data.json
    │   │   │   │   │   ├── toml.meta.json
    │   │   │   │   │   ├── yaml.data.json
    │   │   │   │   │   └── yaml.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── types.data.json
    │   │   │   │   ├── types.meta.json
    │   │   │   │   ├── utils.data.json
    │   │   │   │   └── utils.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── utils.data.json
    │   │   │   ├── utils.meta.json
    │   │   │   ├── version.data.json
    │   │   │   └── version.meta.json
    │   │   ├── pyexpat/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── model.data.json
    │   │   │   └── model.meta.json
    │   │   ├── pytest/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── rich/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── __main__.data.json
    │   │   │   ├── __main__.meta.json
    │   │   │   ├── _cell_widths.data.json
    │   │   │   ├── _cell_widths.meta.json
    │   │   │   ├── _emoji_codes.data.json
    │   │   │   ├── _emoji_codes.meta.json
    │   │   │   ├── _emoji_replace.data.json
    │   │   │   ├── _emoji_replace.meta.json
    │   │   │   ├── _export_format.data.json
    │   │   │   ├── _export_format.meta.json
    │   │   │   ├── _extension.data.json
    │   │   │   ├── _extension.meta.json
    │   │   │   ├── _fileno.data.json
    │   │   │   ├── _fileno.meta.json
    │   │   │   ├── _log_render.data.json
    │   │   │   ├── _log_render.meta.json
    │   │   │   ├── _loop.data.json
    │   │   │   ├── _loop.meta.json
    │   │   │   ├── _null_file.data.json
    │   │   │   ├── _null_file.meta.json
    │   │   │   ├── _palettes.data.json
    │   │   │   ├── _palettes.meta.json
    │   │   │   ├── _pick.data.json
    │   │   │   ├── _pick.meta.json
    │   │   │   ├── _ratio.data.json
    │   │   │   ├── _ratio.meta.json
    │   │   │   ├── _spinners.data.json
    │   │   │   ├── _spinners.meta.json
    │   │   │   ├── _stack.data.json
    │   │   │   ├── _stack.meta.json
    │   │   │   ├── _timer.data.json
    │   │   │   ├── _timer.meta.json
    │   │   │   ├── _win32_console.data.json
    │   │   │   ├── _win32_console.meta.json
    │   │   │   ├── _windows.data.json
    │   │   │   ├── _windows.meta.json
    │   │   │   ├── _windows_renderer.data.json
    │   │   │   ├── _windows_renderer.meta.json
    │   │   │   ├── _wrap.data.json
    │   │   │   ├── _wrap.meta.json
    │   │   │   ├── abc.data.json
    │   │   │   ├── abc.meta.json
    │   │   │   ├── align.data.json
    │   │   │   ├── align.meta.json
    │   │   │   ├── ansi.data.json
    │   │   │   ├── ansi.meta.json
    │   │   │   ├── box.data.json
    │   │   │   ├── box.meta.json
    │   │   │   ├── cells.data.json
    │   │   │   ├── cells.meta.json
    │   │   │   ├── color.data.json
    │   │   │   ├── color.meta.json
    │   │   │   ├── color_triplet.data.json
    │   │   │   ├── color_triplet.meta.json
    │   │   │   ├── columns.data.json
    │   │   │   ├── columns.meta.json
    │   │   │   ├── console.data.json
    │   │   │   ├── console.meta.json
    │   │   │   ├── constrain.data.json
    │   │   │   ├── constrain.meta.json
    │   │   │   ├── containers.data.json
    │   │   │   ├── containers.meta.json
    │   │   │   ├── control.data.json
    │   │   │   ├── control.meta.json
    │   │   │   ├── default_styles.data.json
    │   │   │   ├── default_styles.meta.json
    │   │   │   ├── emoji.data.json
    │   │   │   ├── emoji.meta.json
    │   │   │   ├── errors.data.json
    │   │   │   ├── errors.meta.json
    │   │   │   ├── file_proxy.data.json
    │   │   │   ├── file_proxy.meta.json
    │   │   │   ├── filesize.data.json
    │   │   │   ├── filesize.meta.json
    │   │   │   ├── highlighter.data.json
    │   │   │   ├── highlighter.meta.json
    │   │   │   ├── json.data.json
    │   │   │   ├── json.meta.json
    │   │   │   ├── jupyter.data.json
    │   │   │   ├── jupyter.meta.json
    │   │   │   ├── live.data.json
    │   │   │   ├── live.meta.json
    │   │   │   ├── live_render.data.json
    │   │   │   ├── live_render.meta.json
    │   │   │   ├── markdown.data.json
    │   │   │   ├── markdown.meta.json
    │   │   │   ├── markup.data.json
    │   │   │   ├── markup.meta.json
    │   │   │   ├── measure.data.json
    │   │   │   ├── measure.meta.json
    │   │   │   ├── padding.data.json
    │   │   │   ├── padding.meta.json
    │   │   │   ├── pager.data.json
    │   │   │   ├── pager.meta.json
    │   │   │   ├── palette.data.json
    │   │   │   ├── palette.meta.json
    │   │   │   ├── panel.data.json
    │   │   │   ├── panel.meta.json
    │   │   │   ├── pretty.data.json
    │   │   │   ├── pretty.meta.json
    │   │   │   ├── progress.data.json
    │   │   │   ├── progress.meta.json
    │   │   │   ├── progress_bar.data.json
    │   │   │   ├── progress_bar.meta.json
    │   │   │   ├── protocol.data.json
    │   │   │   ├── protocol.meta.json
    │   │   │   ├── region.data.json
    │   │   │   ├── region.meta.json
    │   │   │   ├── repr.data.json
    │   │   │   ├── repr.meta.json
    │   │   │   ├── rule.data.json
    │   │   │   ├── rule.meta.json
    │   │   │   ├── scope.data.json
    │   │   │   ├── scope.meta.json
    │   │   │   ├── screen.data.json
    │   │   │   ├── screen.meta.json
    │   │   │   ├── segment.data.json
    │   │   │   ├── segment.meta.json
    │   │   │   ├── spinner.data.json
    │   │   │   ├── spinner.meta.json
    │   │   │   ├── status.data.json
    │   │   │   ├── status.meta.json
    │   │   │   ├── style.data.json
    │   │   │   ├── style.meta.json
    │   │   │   ├── styled.data.json
    │   │   │   ├── styled.meta.json
    │   │   │   ├── syntax.data.json
    │   │   │   ├── syntax.meta.json
    │   │   │   ├── table.data.json
    │   │   │   ├── table.meta.json
    │   │   │   ├── terminal_theme.data.json
    │   │   │   ├── terminal_theme.meta.json
    │   │   │   ├── text.data.json
    │   │   │   ├── text.meta.json
    │   │   │   ├── theme.data.json
    │   │   │   ├── theme.meta.json
    │   │   │   ├── themes.data.json
    │   │   │   ├── themes.meta.json
    │   │   │   ├── traceback.data.json
    │   │   │   └── traceback.meta.json
    │   │   ├── sqlalchemy/
    │   │   │   ├── connectors/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── asyncio.data.json
    │   │   │   │   └── asyncio.meta.json
    │   │   │   ├── dialects/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── engine/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _py_processors.data.json
    │   │   │   │   ├── _py_processors.meta.json
    │   │   │   │   ├── _py_row.data.json
    │   │   │   │   ├── _py_row.meta.json
    │   │   │   │   ├── _py_util.data.json
    │   │   │   │   ├── _py_util.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── characteristics.data.json
    │   │   │   │   ├── characteristics.meta.json
    │   │   │   │   ├── create.data.json
    │   │   │   │   ├── create.meta.json
    │   │   │   │   ├── cursor.data.json
    │   │   │   │   ├── cursor.meta.json
    │   │   │   │   ├── default.data.json
    │   │   │   │   ├── default.meta.json
    │   │   │   │   ├── events.data.json
    │   │   │   │   ├── events.meta.json
    │   │   │   │   ├── interfaces.data.json
    │   │   │   │   ├── interfaces.meta.json
    │   │   │   │   ├── mock.data.json
    │   │   │   │   ├── mock.meta.json
    │   │   │   │   ├── processors.data.json
    │   │   │   │   ├── processors.meta.json
    │   │   │   │   ├── reflection.data.json
    │   │   │   │   ├── reflection.meta.json
    │   │   │   │   ├── result.data.json
    │   │   │   │   ├── result.meta.json
    │   │   │   │   ├── row.data.json
    │   │   │   │   ├── row.meta.json
    │   │   │   │   ├── url.data.json
    │   │   │   │   ├── url.meta.json
    │   │   │   │   ├── util.data.json
    │   │   │   │   └── util.meta.json
    │   │   │   ├── event/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── api.data.json
    │   │   │   │   ├── api.meta.json
    │   │   │   │   ├── attr.data.json
    │   │   │   │   ├── attr.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── legacy.data.json
    │   │   │   │   ├── legacy.meta.json
    │   │   │   │   ├── registry.data.json
    │   │   │   │   └── registry.meta.json
    │   │   │   ├── ext/
    │   │   │   │   ├── asyncio/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── engine.data.json
    │   │   │   │   │   ├── engine.meta.json
    │   │   │   │   │   ├── exc.data.json
    │   │   │   │   │   ├── exc.meta.json
    │   │   │   │   │   ├── result.data.json
    │   │   │   │   │   ├── result.meta.json
    │   │   │   │   │   ├── scoping.data.json
    │   │   │   │   │   ├── scoping.meta.json
    │   │   │   │   │   ├── session.data.json
    │   │   │   │   │   └── session.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── future/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── engine.data.json
    │   │   │   │   └── engine.meta.json
    │   │   │   ├── orm/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _orm_constructors.data.json
    │   │   │   │   ├── _orm_constructors.meta.json
    │   │   │   │   ├── _typing.data.json
    │   │   │   │   ├── _typing.meta.json
    │   │   │   │   ├── attributes.data.json
    │   │   │   │   ├── attributes.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── bulk_persistence.data.json
    │   │   │   │   ├── bulk_persistence.meta.json
    │   │   │   │   ├── clsregistry.data.json
    │   │   │   │   ├── clsregistry.meta.json
    │   │   │   │   ├── collections.data.json
    │   │   │   │   ├── collections.meta.json
    │   │   │   │   ├── context.data.json
    │   │   │   │   ├── context.meta.json
    │   │   │   │   ├── decl_api.data.json
    │   │   │   │   ├── decl_api.meta.json
    │   │   │   │   ├── decl_base.data.json
    │   │   │   │   ├── decl_base.meta.json
    │   │   │   │   ├── dependency.data.json
    │   │   │   │   ├── dependency.meta.json
    │   │   │   │   ├── descriptor_props.data.json
    │   │   │   │   ├── descriptor_props.meta.json
    │   │   │   │   ├── dynamic.data.json
    │   │   │   │   ├── dynamic.meta.json
    │   │   │   │   ├── evaluator.data.json
    │   │   │   │   ├── evaluator.meta.json
    │   │   │   │   ├── events.data.json
    │   │   │   │   ├── events.meta.json
    │   │   │   │   ├── exc.data.json
    │   │   │   │   ├── exc.meta.json
    │   │   │   │   ├── identity.data.json
    │   │   │   │   ├── identity.meta.json
    │   │   │   │   ├── instrumentation.data.json
    │   │   │   │   ├── instrumentation.meta.json
    │   │   │   │   ├── interfaces.data.json
    │   │   │   │   ├── interfaces.meta.json
    │   │   │   │   ├── loading.data.json
    │   │   │   │   ├── loading.meta.json
    │   │   │   │   ├── mapped_collection.data.json
    │   │   │   │   ├── mapped_collection.meta.json
    │   │   │   │   ├── mapper.data.json
    │   │   │   │   ├── mapper.meta.json
    │   │   │   │   ├── path_registry.data.json
    │   │   │   │   ├── path_registry.meta.json
    │   │   │   │   ├── persistence.data.json
    │   │   │   │   ├── persistence.meta.json
    │   │   │   │   ├── properties.data.json
    │   │   │   │   ├── properties.meta.json
    │   │   │   │   ├── query.data.json
    │   │   │   │   ├── query.meta.json
    │   │   │   │   ├── relationships.data.json
    │   │   │   │   ├── relationships.meta.json
    │   │   │   │   ├── scoping.data.json
    │   │   │   │   ├── scoping.meta.json
    │   │   │   │   ├── session.data.json
    │   │   │   │   ├── session.meta.json
    │   │   │   │   ├── state.data.json
    │   │   │   │   ├── state.meta.json
    │   │   │   │   ├── state_changes.data.json
    │   │   │   │   ├── state_changes.meta.json
    │   │   │   │   ├── strategies.data.json
    │   │   │   │   ├── strategies.meta.json
    │   │   │   │   ├── strategy_options.data.json
    │   │   │   │   ├── strategy_options.meta.json
    │   │   │   │   ├── sync.data.json
    │   │   │   │   ├── sync.meta.json
    │   │   │   │   ├── unitofwork.data.json
    │   │   │   │   ├── unitofwork.meta.json
    │   │   │   │   ├── util.data.json
    │   │   │   │   ├── util.meta.json
    │   │   │   │   ├── writeonly.data.json
    │   │   │   │   └── writeonly.meta.json
    │   │   │   ├── pool/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── events.data.json
    │   │   │   │   ├── events.meta.json
    │   │   │   │   ├── impl.data.json
    │   │   │   │   └── impl.meta.json
    │   │   │   ├── sql/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _dml_constructors.data.json
    │   │   │   │   ├── _dml_constructors.meta.json
    │   │   │   │   ├── _elements_constructors.data.json
    │   │   │   │   ├── _elements_constructors.meta.json
    │   │   │   │   ├── _orm_types.data.json
    │   │   │   │   ├── _orm_types.meta.json
    │   │   │   │   ├── _py_util.data.json
    │   │   │   │   ├── _py_util.meta.json
    │   │   │   │   ├── _selectable_constructors.data.json
    │   │   │   │   ├── _selectable_constructors.meta.json
    │   │   │   │   ├── _typing.data.json
    │   │   │   │   ├── _typing.meta.json
    │   │   │   │   ├── annotation.data.json
    │   │   │   │   ├── annotation.meta.json
    │   │   │   │   ├── base.data.json
    │   │   │   │   ├── base.meta.json
    │   │   │   │   ├── cache_key.data.json
    │   │   │   │   ├── cache_key.meta.json
    │   │   │   │   ├── coercions.data.json
    │   │   │   │   ├── coercions.meta.json
    │   │   │   │   ├── compiler.data.json
    │   │   │   │   ├── compiler.meta.json
    │   │   │   │   ├── crud.data.json
    │   │   │   │   ├── crud.meta.json
    │   │   │   │   ├── ddl.data.json
    │   │   │   │   ├── ddl.meta.json
    │   │   │   │   ├── default_comparator.data.json
    │   │   │   │   ├── default_comparator.meta.json
    │   │   │   │   ├── dml.data.json
    │   │   │   │   ├── dml.meta.json
    │   │   │   │   ├── elements.data.json
    │   │   │   │   ├── elements.meta.json
    │   │   │   │   ├── events.data.json
    │   │   │   │   ├── events.meta.json
    │   │   │   │   ├── expression.data.json
    │   │   │   │   ├── expression.meta.json
    │   │   │   │   ├── functions.data.json
    │   │   │   │   ├── functions.meta.json
    │   │   │   │   ├── lambdas.data.json
    │   │   │   │   ├── lambdas.meta.json
    │   │   │   │   ├── naming.data.json
    │   │   │   │   ├── naming.meta.json
    │   │   │   │   ├── operators.data.json
    │   │   │   │   ├── operators.meta.json
    │   │   │   │   ├── roles.data.json
    │   │   │   │   ├── roles.meta.json
    │   │   │   │   ├── schema.data.json
    │   │   │   │   ├── schema.meta.json
    │   │   │   │   ├── selectable.data.json
    │   │   │   │   ├── selectable.meta.json
    │   │   │   │   ├── sqltypes.data.json
    │   │   │   │   ├── sqltypes.meta.json
    │   │   │   │   ├── traversals.data.json
    │   │   │   │   ├── traversals.meta.json
    │   │   │   │   ├── type_api.data.json
    │   │   │   │   ├── type_api.meta.json
    │   │   │   │   ├── util.data.json
    │   │   │   │   ├── util.meta.json
    │   │   │   │   ├── visitors.data.json
    │   │   │   │   └── visitors.meta.json
    │   │   │   ├── util/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── _collections.data.json
    │   │   │   │   ├── _collections.meta.json
    │   │   │   │   ├── _concurrency_py3k.data.json
    │   │   │   │   ├── _concurrency_py3k.meta.json
    │   │   │   │   ├── _has_cy.data.json
    │   │   │   │   ├── _has_cy.meta.json
    │   │   │   │   ├── _py_collections.data.json
    │   │   │   │   ├── _py_collections.meta.json
    │   │   │   │   ├── compat.data.json
    │   │   │   │   ├── compat.meta.json
    │   │   │   │   ├── concurrency.data.json
    │   │   │   │   ├── concurrency.meta.json
    │   │   │   │   ├── deprecations.data.json
    │   │   │   │   ├── deprecations.meta.json
    │   │   │   │   ├── langhelpers.data.json
    │   │   │   │   ├── langhelpers.meta.json
    │   │   │   │   ├── preloaded.data.json
    │   │   │   │   ├── preloaded.meta.json
    │   │   │   │   ├── queue.data.json
    │   │   │   │   ├── queue.meta.json
    │   │   │   │   ├── topological.data.json
    │   │   │   │   ├── topological.meta.json
    │   │   │   │   ├── typing.data.json
    │   │   │   │   └── typing.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── exc.data.json
    │   │   │   ├── exc.meta.json
    │   │   │   ├── inspection.data.json
    │   │   │   ├── inspection.meta.json
    │   │   │   ├── log.data.json
    │   │   │   ├── log.meta.json
    │   │   │   ├── schema.data.json
    │   │   │   ├── schema.meta.json
    │   │   │   ├── types.data.json
    │   │   │   └── types.meta.json
    │   │   ├── sqlite3/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── dbapi2.data.json
    │   │   │   └── dbapi2.meta.json
    │   │   ├── string/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── structlog/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _base.data.json
    │   │   │   ├── _base.meta.json
    │   │   │   ├── _config.data.json
    │   │   │   ├── _config.meta.json
    │   │   │   ├── _frames.data.json
    │   │   │   ├── _frames.meta.json
    │   │   │   ├── _generic.data.json
    │   │   │   ├── _generic.meta.json
    │   │   │   ├── _log_levels.data.json
    │   │   │   ├── _log_levels.meta.json
    │   │   │   ├── _native.data.json
    │   │   │   ├── _native.meta.json
    │   │   │   ├── _output.data.json
    │   │   │   ├── _output.meta.json
    │   │   │   ├── _utils.data.json
    │   │   │   ├── _utils.meta.json
    │   │   │   ├── contextvars.data.json
    │   │   │   ├── contextvars.meta.json
    │   │   │   ├── dev.data.json
    │   │   │   ├── dev.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── processors.data.json
    │   │   │   ├── processors.meta.json
    │   │   │   ├── stdlib.data.json
    │   │   │   ├── stdlib.meta.json
    │   │   │   ├── testing.data.json
    │   │   │   ├── testing.meta.json
    │   │   │   ├── threadlocal.data.json
    │   │   │   ├── threadlocal.meta.json
    │   │   │   ├── tracebacks.data.json
    │   │   │   ├── tracebacks.meta.json
    │   │   │   ├── twisted.data.json
    │   │   │   ├── twisted.meta.json
    │   │   │   ├── types.data.json
    │   │   │   ├── types.meta.json
    │   │   │   ├── typing.data.json
    │   │   │   └── typing.meta.json
    │   │   ├── sys/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── tests/
    │   │   │   ├── architecture/
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── tomli/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _parser.data.json
    │   │   │   ├── _parser.meta.json
    │   │   │   ├── _re.data.json
    │   │   │   ├── _re.meta.json
    │   │   │   ├── _types.data.json
    │   │   │   └── _types.meta.json
    │   │   ├── typeguard/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _checkers.data.json
    │   │   │   ├── _checkers.meta.json
    │   │   │   ├── _config.data.json
    │   │   │   ├── _config.meta.json
    │   │   │   ├── _decorators.data.json
    │   │   │   ├── _decorators.meta.json
    │   │   │   ├── _exceptions.data.json
    │   │   │   ├── _exceptions.meta.json
    │   │   │   ├── _functions.data.json
    │   │   │   ├── _functions.meta.json
    │   │   │   ├── _importhook.data.json
    │   │   │   ├── _importhook.meta.json
    │   │   │   ├── _memo.data.json
    │   │   │   ├── _memo.meta.json
    │   │   │   ├── _suppression.data.json
    │   │   │   ├── _suppression.meta.json
    │   │   │   ├── _transformer.data.json
    │   │   │   ├── _transformer.meta.json
    │   │   │   ├── _utils.data.json
    │   │   │   └── _utils.meta.json
    │   │   ├── typing_inspection/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── introspection.data.json
    │   │   │   ├── introspection.meta.json
    │   │   │   ├── typing_objects.data.json
    │   │   │   └── typing_objects.meta.json
    │   │   ├── unittest/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _log.data.json
    │   │   │   ├── _log.meta.json
    │   │   │   ├── async_case.data.json
    │   │   │   ├── async_case.meta.json
    │   │   │   ├── case.data.json
    │   │   │   ├── case.meta.json
    │   │   │   ├── loader.data.json
    │   │   │   ├── loader.meta.json
    │   │   │   ├── main.data.json
    │   │   │   ├── main.meta.json
    │   │   │   ├── mock.data.json
    │   │   │   ├── mock.meta.json
    │   │   │   ├── result.data.json
    │   │   │   ├── result.meta.json
    │   │   │   ├── runner.data.json
    │   │   │   ├── runner.meta.json
    │   │   │   ├── signals.data.json
    │   │   │   ├── signals.meta.json
    │   │   │   ├── suite.data.json
    │   │   │   └── suite.meta.json
    │   │   ├── urllib/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── error.data.json
    │   │   │   ├── error.meta.json
    │   │   │   ├── parse.data.json
    │   │   │   ├── parse.meta.json
    │   │   │   ├── request.data.json
    │   │   │   ├── request.meta.json
    │   │   │   ├── response.data.json
    │   │   │   └── response.meta.json
    │   │   ├── wsgiref/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── handlers.data.json
    │   │   │   ├── handlers.meta.json
    │   │   │   ├── headers.data.json
    │   │   │   ├── headers.meta.json
    │   │   │   ├── simple_server.data.json
    │   │   │   ├── simple_server.meta.json
    │   │   │   ├── types.data.json
    │   │   │   ├── types.meta.json
    │   │   │   ├── util.data.json
    │   │   │   └── util.meta.json
    │   │   ├── xml/
    │   │   │   ├── etree/
    │   │   │   │   ├── ElementTree.data.json
    │   │   │   │   ├── ElementTree.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── parsers/
    │   │   │   │   ├── expat/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   └── __init__.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   └── __init__.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── yaml/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _yaml.data.json
    │   │   │   ├── _yaml.meta.json
    │   │   │   ├── composer.data.json
    │   │   │   ├── composer.meta.json
    │   │   │   ├── constructor.data.json
    │   │   │   ├── constructor.meta.json
    │   │   │   ├── cyaml.data.json
    │   │   │   ├── cyaml.meta.json
    │   │   │   ├── dumper.data.json
    │   │   │   ├── dumper.meta.json
    │   │   │   ├── emitter.data.json
    │   │   │   ├── emitter.meta.json
    │   │   │   ├── error.data.json
    │   │   │   ├── error.meta.json
    │   │   │   ├── events.data.json
    │   │   │   ├── events.meta.json
    │   │   │   ├── loader.data.json
    │   │   │   ├── loader.meta.json
    │   │   │   ├── nodes.data.json
    │   │   │   ├── nodes.meta.json
    │   │   │   ├── parser.data.json
    │   │   │   ├── parser.meta.json
    │   │   │   ├── reader.data.json
    │   │   │   ├── reader.meta.json
    │   │   │   ├── representer.data.json
    │   │   │   ├── representer.meta.json
    │   │   │   ├── resolver.data.json
    │   │   │   ├── resolver.meta.json
    │   │   │   ├── scanner.data.json
    │   │   │   ├── scanner.meta.json
    │   │   │   ├── serializer.data.json
    │   │   │   ├── serializer.meta.json
    │   │   │   ├── tokens.data.json
    │   │   │   └── tokens.meta.json
    │   │   ├── zipfile/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── zoneinfo/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── _common.data.json
    │   │   │   ├── _common.meta.json
    │   │   │   ├── _tzpath.data.json
    │   │   │   └── _tzpath.meta.json
    │   │   ├── zstandard/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── @plugins_snapshot.json
    │   │   ├── __future__.data.json
    │   │   ├── __future__.meta.json
    │   │   ├── _ast.data.json
    │   │   ├── _ast.meta.json
    │   │   ├── _asyncio.data.json
    │   │   ├── _asyncio.meta.json
    │   │   ├── _bisect.data.json
    │   │   ├── _bisect.meta.json
    │   │   ├── _blake2.data.json
    │   │   ├── _blake2.meta.json
    │   │   ├── _bz2.data.json
    │   │   ├── _bz2.meta.json
    │   │   ├── _codecs.data.json
    │   │   ├── _codecs.meta.json
    │   │   ├── _collections_abc.data.json
    │   │   ├── _collections_abc.meta.json
    │   │   ├── _compression.data.json
    │   │   ├── _compression.meta.json
    │   │   ├── _contextvars.data.json
    │   │   ├── _contextvars.meta.json
    │   │   ├── _csv.data.json
    │   │   ├── _csv.meta.json
    │   │   ├── _ctypes.data.json
    │   │   ├── _ctypes.meta.json
    │   │   ├── _decimal.data.json
    │   │   ├── _decimal.meta.json
    │   │   ├── _frozen_importlib.data.json
    │   │   ├── _frozen_importlib.meta.json
    │   │   ├── _frozen_importlib_external.data.json
    │   │   ├── _frozen_importlib_external.meta.json
    │   │   ├── _hashlib.data.json
    │   │   ├── _hashlib.meta.json
    │   │   ├── _heapq.data.json
    │   │   ├── _heapq.meta.json
    │   │   ├── _io.data.json
    │   │   ├── _io.meta.json
    │   │   ├── _locale.data.json
    │   │   ├── _locale.meta.json
    │   │   ├── _operator.data.json
    │   │   ├── _operator.meta.json
    │   │   ├── _pickle.data.json
    │   │   ├── _pickle.meta.json
    │   │   ├── _queue.data.json
    │   │   ├── _queue.meta.json
    │   │   ├── _random.data.json
    │   │   ├── _random.meta.json
    │   │   ├── _sitebuiltins.data.json
    │   │   ├── _sitebuiltins.meta.json
    │   │   ├── _socket.data.json
    │   │   ├── _socket.meta.json
    │   │   ├── _sqlite3.data.json
    │   │   ├── _sqlite3.meta.json
    │   │   ├── _ssl.data.json
    │   │   ├── _ssl.meta.json
    │   │   ├── _stat.data.json
    │   │   ├── _stat.meta.json
    │   │   ├── _struct.data.json
    │   │   ├── _struct.meta.json
    │   │   ├── _thread.data.json
    │   │   ├── _thread.meta.json
    │   │   ├── _warnings.data.json
    │   │   ├── _warnings.meta.json
    │   │   ├── _weakref.data.json
    │   │   ├── _weakref.meta.json
    │   │   ├── _weakrefset.data.json
    │   │   ├── _weakrefset.meta.json
    │   │   ├── _winapi.data.json
    │   │   ├── _winapi.meta.json
    │   │   ├── abc.data.json
    │   │   ├── abc.meta.json
    │   │   ├── argparse.data.json
    │   │   ├── argparse.meta.json
    │   │   ├── array.data.json
    │   │   ├── array.meta.json
    │   │   ├── arro3.data.json
    │   │   ├── arro3.meta.json
    │   │   ├── ast.data.json
    │   │   ├── ast.meta.json
    │   │   ├── atexit.data.json
    │   │   ├── atexit.meta.json
    │   │   ├── base64.data.json
    │   │   ├── base64.meta.json
    │   │   ├── bdb.data.json
    │   │   ├── bdb.meta.json
    │   │   ├── binascii.data.json
    │   │   ├── binascii.meta.json
    │   │   ├── bisect.data.json
    │   │   ├── bisect.meta.json
    │   │   ├── builtins.data.json
    │   │   ├── builtins.meta.json
    │   │   ├── bz2.data.json
    │   │   ├── bz2.meta.json
    │   │   ├── calendar.data.json
    │   │   ├── calendar.meta.json
    │   │   ├── cmd.data.json
    │   │   ├── cmd.meta.json
    │   │   ├── codecs.data.json
    │   │   ├── codecs.meta.json
    │   │   ├── colorsys.data.json
    │   │   ├── colorsys.meta.json
    │   │   ├── configparser.data.json
    │   │   ├── configparser.meta.json
    │   │   ├── contextlib.data.json
    │   │   ├── contextlib.meta.json
    │   │   ├── contextvars.data.json
    │   │   ├── contextvars.meta.json
    │   │   ├── copy.data.json
    │   │   ├── copy.meta.json
    │   │   ├── copyreg.data.json
    │   │   ├── copyreg.meta.json
    │   │   ├── csv.data.json
    │   │   ├── csv.meta.json
    │   │   ├── dataclasses.data.json
    │   │   ├── dataclasses.meta.json
    │   │   ├── datetime.data.json
    │   │   ├── datetime.meta.json
    │   │   ├── decimal.data.json
    │   │   ├── decimal.meta.json
    │   │   ├── difflib.data.json
    │   │   ├── difflib.meta.json
    │   │   ├── dis.data.json
    │   │   ├── dis.meta.json
    │   │   ├── doctest.data.json
    │   │   ├── doctest.meta.json
    │   │   ├── enum.data.json
    │   │   ├── enum.meta.json
    │   │   ├── errno.data.json
    │   │   ├── errno.meta.json
    │   │   ├── fnmatch.data.json
    │   │   ├── fnmatch.meta.json
    │   │   ├── fractions.data.json
    │   │   ├── fractions.meta.json
    │   │   ├── functools.data.json
    │   │   ├── functools.meta.json
    │   │   ├── gc.data.json
    │   │   ├── gc.meta.json
    │   │   ├── genericpath.data.json
    │   │   ├── genericpath.meta.json
    │   │   ├── getpass.data.json
    │   │   ├── getpass.meta.json
    │   │   ├── gettext.data.json
    │   │   ├── gettext.meta.json
    │   │   ├── glob.data.json
    │   │   ├── glob.meta.json
    │   │   ├── gzip.data.json
    │   │   ├── gzip.meta.json
    │   │   ├── hashlib.data.json
    │   │   ├── hashlib.meta.json
    │   │   ├── heapq.data.json
    │   │   ├── heapq.meta.json
    │   │   ├── hmac.data.json
    │   │   ├── hmac.meta.json
    │   │   ├── inspect.data.json
    │   │   ├── inspect.meta.json
    │   │   ├── io.data.json
    │   │   ├── io.meta.json
    │   │   ├── ipaddress.data.json
    │   │   ├── ipaddress.meta.json
    │   │   ├── itertools.data.json
    │   │   ├── itertools.meta.json
    │   │   ├── keyword.data.json
    │   │   ├── keyword.meta.json
    │   │   ├── linecache.data.json
    │   │   ├── linecache.meta.json
    │   │   ├── locale.data.json
    │   │   ├── locale.meta.json
    │   │   ├── marshal.data.json
    │   │   ├── marshal.meta.json
    │   │   ├── math.data.json
    │   │   ├── math.meta.json
    │   │   ├── mimetypes.data.json
    │   │   ├── mimetypes.meta.json
    │   │   ├── mmap.data.json
    │   │   ├── mmap.meta.json
    │   │   ├── msvcrt.data.json
    │   │   ├── msvcrt.meta.json
    │   │   ├── mypy_extensions.data.json
    │   │   ├── mypy_extensions.meta.json
    │   │   ├── netrc.data.json
    │   │   ├── netrc.meta.json
    │   │   ├── ntpath.data.json
    │   │   ├── ntpath.meta.json
    │   │   ├── nturl2path.data.json
    │   │   ├── nturl2path.meta.json
    │   │   ├── numbers.data.json
    │   │   ├── numbers.meta.json
    │   │   ├── opcode.data.json
    │   │   ├── opcode.meta.json
    │   │   ├── opentelemetry.data.json
    │   │   ├── opentelemetry.meta.json
    │   │   ├── operator.data.json
    │   │   ├── operator.meta.json
    │   │   ├── pathlib.data.json
    │   │   ├── pathlib.meta.json
    │   │   ├── pdb.data.json
    │   │   ├── pdb.meta.json
    │   │   ├── pickle.data.json
    │   │   ├── pickle.meta.json
    │   │   ├── platform.data.json
    │   │   ├── platform.meta.json
    │   │   ├── posixpath.data.json
    │   │   ├── posixpath.meta.json
    │   │   ├── pprint.data.json
    │   │   ├── pprint.meta.json
    │   │   ├── pydoc.data.json
    │   │   ├── pydoc.meta.json
    │   │   ├── queue.data.json
    │   │   ├── queue.meta.json
    │   │   ├── random.data.json
    │   │   ├── random.meta.json
    │   │   ├── re.data.json
    │   │   ├── re.meta.json
    │   │   ├── reprlib.data.json
    │   │   ├── reprlib.meta.json
    │   │   ├── resource.data.json
    │   │   ├── resource.meta.json
    │   │   ├── secrets.data.json
    │   │   ├── secrets.meta.json
    │   │   ├── select.data.json
    │   │   ├── select.meta.json
    │   │   ├── selectors.data.json
    │   │   ├── selectors.meta.json
    │   │   ├── shlex.data.json
    │   │   ├── shlex.meta.json
    │   │   ├── shutil.data.json
    │   │   ├── shutil.meta.json
    │   │   ├── signal.data.json
    │   │   ├── signal.meta.json
    │   │   ├── socket.data.json
    │   │   ├── socket.meta.json
    │   │   ├── socketserver.data.json
    │   │   ├── socketserver.meta.json
    │   │   ├── sre_compile.data.json
    │   │   ├── sre_compile.meta.json
    │   │   ├── sre_constants.data.json
    │   │   ├── sre_constants.meta.json
    │   │   ├── sre_parse.data.json
    │   │   ├── sre_parse.meta.json
    │   │   ├── ssl.data.json
    │   │   ├── ssl.meta.json
    │   │   ├── stat.data.json
    │   │   ├── stat.meta.json
    │   │   ├── statistics.data.json
    │   │   ├── statistics.meta.json
    │   │   ├── string.data.json
    │   │   ├── string.meta.json
    │   │   ├── struct.data.json
    │   │   ├── struct.meta.json
    │   │   ├── subprocess.data.json
    │   │   ├── subprocess.meta.json
    │   │   ├── sysconfig.data.json
    │   │   ├── sysconfig.meta.json
    │   │   ├── tarfile.data.json
    │   │   ├── tarfile.meta.json
    │   │   ├── tempfile.data.json
    │   │   ├── tempfile.meta.json
    │   │   ├── textwrap.data.json
    │   │   ├── textwrap.meta.json
    │   │   ├── threading.data.json
    │   │   ├── threading.meta.json
    │   │   ├── time.data.json
    │   │   ├── time.meta.json
    │   │   ├── timeit.data.json
    │   │   ├── timeit.meta.json
    │   │   ├── token.data.json
    │   │   ├── token.meta.json
    │   │   ├── tokenize.data.json
    │   │   ├── tokenize.meta.json
    │   │   ├── tomllib.data.json
    │   │   ├── tomllib.meta.json
    │   │   ├── traceback.data.json
    │   │   ├── traceback.meta.json
    │   │   ├── types.data.json
    │   │   ├── types.meta.json
    │   │   ├── typing.data.json
    │   │   ├── typing.meta.json
    │   │   ├── typing_extensions.data.json
    │   │   ├── typing_extensions.meta.json
    │   │   ├── unicodedata.data.json
    │   │   ├── unicodedata.meta.json
    │   │   ├── uuid.data.json
    │   │   ├── uuid.meta.json
    │   │   ├── warnings.data.json
    │   │   ├── warnings.meta.json
    │   │   ├── weakref.data.json
    │   │   ├── weakref.meta.json
    │   │   ├── zipimport.data.json
    │   │   ├── zipimport.meta.json
    │   │   ├── zlib.data.json
    │   │   └── zlib.meta.json
    │   ├── .gitignore
    │   ├── CACHEDIR.TAG
    │   └── missing_stubs
    ├── .pytest_cache/
    │   ├── v/
    │   │   └── cache/
    │   │       ├── lastfailed
    │   │       └── nodeids
    │   ├── .gitignore
    │   ├── CACHEDIR.TAG
    │   └── README.md
    ├── .ruff_cache/
    │   ├── 0.14.0/
    │   │   ├── .tmpUcSdoy
    │   │   ├── 10127165128104329726
    │   │   ├── 10174458157720737915
    │   │   ├── 10240723319412775506
    │   │   ├── 10271005428267992482
    │   │   ├── 10430932764340773820
    │   │   ├── 10443538885074417394
    │   │   ├── 10448096337519293231
    │   │   ├── 10519833625617592984
    │   │   ├── 10583392479659322532
    │   │   ├── 10616209550479959374
    │   │   ├── 10631773154392606232
    │   │   ├── 10694149821553099992
    │   │   ├── 10716384485319283996
    │   │   ├── 10737179470969541566
    │   │   ├── 11090183932048423435
    │   │   ├── 11201610029818688981
    │   │   ├── 11288768874771389898
    │   │   ├── 11311491140370857518
    │   │   ├── 11583610188612513356
    │   │   ├── 11703741895648991886
    │   │   ├── 11835815100508096191
    │   │   ├── 11988350530626468031
    │   │   ├── 12319386451405268825
    │   │   ├── 12582760512591207430
    │   │   ├── 12651267595738287478
    │   │   ├── 12717528321515470593
    │   │   ├── 12779400413225850508
    │   │   ├── 12855452186490433823
    │   │   ├── 12938711963796233257
    │   │   ├── 12942371562933694241
    │   │   ├── 12998111550178410764
    │   │   ├── 13016142145191257682
    │   │   ├── 13031162338309768723
    │   │   ├── 1307468298911543240
    │   │   ├── 13251828721772392560
    │   │   ├── 13263916684093923630
    │   │   ├── 13372091708824893502
    │   │   ├── 13596647527831518876
    │   │   ├── 14053144865803537521
    │   │   ├── 14321335218325484337
    │   │   ├── 14428733791264019955
    │   │   ├── 14702004972581544123
    │   │   ├── 14871224322908215790
    │   │   ├── 15060259352813521153
    │   │   ├── 15100705498617320206
    │   │   ├── 15103540089145958799
    │   │   ├── 15211260117308224799
    │   │   ├── 15347390924637525871
    │   │   ├── 15371334726002155906
    │   │   ├── 15373502503302121413
    │   │   ├── 15389726157249486506
    │   │   ├── 15497847382164365988
    │   │   ├── 15837667914868966243
    │   │   ├── 15895444977324845683
    │   │   ├── 16027142132407389866
    │   │   ├── 16045405429668314348
    │   │   ├── 16112326051704409114
    │   │   ├── 16333592488343552054
    │   │   ├── 16578303977943171765
    │   │   ├── 16594124209667422011
    │   │   ├── 16773568358712583732
    │   │   ├── 16874533963238746116
    │   │   ├── 16948594898159943784
    │   │   ├── 1725206574451631753
    │   │   ├── 17299959255425746396
    │   │   ├── 17336547259172787444
    │   │   ├── 1736666329493782490
    │   │   ├── 1747129480420144507
    │   │   ├── 17542454256169030416
    │   │   ├── 17546298118358618287
    │   │   ├── 17557457250800203765
    │   │   ├── 17649188762145923442
    │   │   ├── 18119233349441098456
    │   │   ├── 18121233211947883376
    │   │   ├── 18216372894089358360
    │   │   ├── 18431708931127067064
    │   │   ├── 2369822912035140358
    │   │   ├── 2432909107843375296
    │   │   ├── 25996595736537317
    │   │   ├── 2831916283196160393
    │   │   ├── 3138574805935018996
    │   │   ├── 3208444717409315149
    │   │   ├── 3320891234365628061
    │   │   ├── 3770496907059056239
    │   │   ├── 3981432923480689875
    │   │   ├── 4082539964504100503
    │   │   ├── 4242504275142410185
    │   │   ├── 4379651556044748512
    │   │   ├── 4389148501220609287
    │   │   ├── 4419939258301855535
    │   │   ├── 4518332369068314809
    │   │   ├── 4728429716926965747
    │   │   ├── 5040424230270371395
    │   │   ├── 5070387107119390560
    │   │   ├── 5346408927620799650
    │   │   ├── 535576078999896058
    │   │   ├── 5723351041363278461
    │   │   ├── 5807133547595483920
    │   │   ├── 5962123863646502275
    │   │   ├── 6151801415573919569
    │   │   ├── 6175140776455100918
    │   │   ├── 6211427671833606488
    │   │   ├── 6317311565378903252
    │   │   ├── 6332696102254224500
    │   │   ├── 6450738764037132675
    │   │   ├── 6544262620244672180
    │   │   ├── 6556590681958716820
    │   │   ├── 6577658249356552484
    │   │   ├── 6633718975341007796
    │   │   ├── 6638584242196708163
    │   │   ├── 6777892120084726491
    │   │   ├── 697656944341982029
    │   │   ├── 7309165636515191730
    │   │   ├── 7356731340926077842
    │   │   ├── 7399948707667532764
    │   │   ├── 7482118330844108343
    │   │   ├── 7601919797541965487
    │   │   ├── 7705115965532620014
    │   │   ├── 774724497262777051
    │   │   ├── 7785549844089294827
    │   │   ├── 7856099870356827953
    │   │   ├── 7906087205545147314
    │   │   ├── 7964601743145509466
    │   │   ├── 8167642239156314628
    │   │   ├── 8234007676045511761
    │   │   ├── 8326386067742799947
    │   │   ├── 8382077638304606989
    │   │   ├── 8545977513231447894
    │   │   ├── 8625470008798218740
    │   │   ├── 8711059208902191572
    │   │   ├── 8742676105503426620
    │   │   ├── 8771723790589894935
    │   │   ├── 8933661446095833671
    │   │   ├── 9280186396515467699
    │   │   ├── 9339966458643047120
    │   │   ├── 9353957730235658979
    │   │   ├── 9482922074048420572
    │   │   ├── 963573906674086609
    │   │   ├── 9804933104493809024
    │   │   ├── 9899277747648322984
    │   │   ├── 9918208920323565202
    │   │   └── 9988654969352418800
    │   ├── 0.14.9/
    │   │   ├── 10137527635201161320
    │   │   ├── 10215658677830163439
    │   │   ├── 10258056800794275632
    │   │   ├── 10307774252610963664
    │   │   ├── 1036654133035604919
    │   │   ├── 10605024646203428100
    │   │   ├── 10724202377588932569
    │   │   ├── 10944447176597080035
    │   │   ├── 11015530124833233046
    │   │   ├── 11167977600190094262
    │   │   ├── 11449208585943028096
    │   │   ├── 11464774433539945966
    │   │   ├── 11485773721616093472
    │   │   ├── 11513435344255355682
    │   │   ├── 11631302026531600159
    │   │   ├── 11639884974727083736
    │   │   ├── 1165052261595931127
    │   │   ├── 11719821420898131716
    │   │   ├── 11725504579681390022
    │   │   ├── 11861137976917583567
    │   │   ├── 11959972932915273702
    │   │   ├── 1196466503443955167
    │   │   ├── 12133020239057709228
    │   │   ├── 12253486920297809448
    │   │   ├── 12354796767066563467
    │   │   ├── 1242041993356726271
    │   │   ├── 12627451262360758875
    │   │   ├── 12645463084027210879
    │   │   ├── 12708956838276721150
    │   │   ├── 12835759117016436122
    │   │   ├── 12904230237241662137
    │   │   ├── 12931420019946002552
    │   │   ├── 12979248404547250257
    │   │   ├── 13134476027322295202
    │   │   ├── 13320742674820338422
    │   │   ├── 13457959849494828696
    │   │   ├── 1365602392940476203
    │   │   ├── 13678845991473190147
    │   │   ├── 14103563344669564162
    │   │   ├── 14171632919346827995
    │   │   ├── 14278701257808699410
    │   │   ├── 14375447917003711212
    │   │   ├── 14389224437480956819
    │   │   ├── 14396054483327066693
    │   │   ├── 14420114116349028788
    │   │   ├── 14566278916386283555
    │   │   ├── 14595022253467512389
    │   │   ├── 14644685874298707707
    │   │   ├── 14829269540552926479
    │   │   ├── 14899014929348916002
    │   │   ├── 14927147589891005448
    │   │   ├── 15007715713009982930
    │   │   ├── 15113659266969082400
    │   │   ├── 15248383830865957398
    │   │   ├── 15516108210045666936
    │   │   ├── 15618775114985180210
    │   │   ├── 15625353662898382052
    │   │   ├── 15830068045341047037
    │   │   ├── 15865410012436689964
    │   │   ├── 15906256427289131687
    │   │   ├── 15948204772754697451
    │   │   ├── 16083557830503721563
    │   │   ├── 16186804666833122626
    │   │   ├── 16218148611262987201
    │   │   ├── 1639513562325988440
    │   │   ├── 16620876180116849807
    │   │   ├── 16637289493185200639
    │   │   ├── 16966426192944312050
    │   │   ├── 1696729731827875583
    │   │   ├── 16968844996514067463
    │   │   ├── 17475402541655272530
    │   │   ├── 17487486009814842063
    │   │   ├── 1757068201633091062
    │   │   ├── 1768376274513624598
    │   │   ├── 17738835023385653105
    │   │   ├── 17824951295266111122
    │   │   ├── 1785736622563091041
    │   │   ├── 17863049941655712268
    │   │   ├── 18211267731951781062
    │   │   ├── 1987429335331081775
    │   │   ├── 2012972956452152810
    │   │   ├── 2062383444078654432
    │   │   ├── 2088077356216062251
    │   │   ├── 2101975246272669553
    │   │   ├── 2252612651877497312
    │   │   ├── 2301767895465681828
    │   │   ├── 2487312762378346606
    │   │   ├── 3176770322768117461
    │   │   ├── 3209745959532738970
    │   │   ├── 322447279056297901
    │   │   ├── 3231300596626000588
    │   │   ├── 341541057261933630
    │   │   ├── 3434591050495873457
    │   │   ├── 3436505683094408325
    │   │   ├── 3625574210895811529
    │   │   ├── 3703855818903938457
    │   │   ├── 4147360908187951898
    │   │   ├── 4197092321696095494
    │   │   ├── 4816948340149819437
    │   │   ├── 4839982185807184571
    │   │   ├── 4861973787018562645
    │   │   ├── 4941991557372758901
    │   │   ├── 5043126526679365415
    │   │   ├── 5110985943796468019
    │   │   ├── 5216056006419589203
    │   │   ├── 5387101304082606398
    │   │   ├── 5401305261833898608
    │   │   ├── 5494377571875348403
    │   │   ├── 5746763696804981737
    │   │   ├── 5767167130943978333
    │   │   ├── 5797572572444059427
    │   │   ├── 5826994110091793496
    │   │   ├── 6109542798716474832
    │   │   ├── 6122878516736626916
    │   │   ├── 6522650142074852071
    │   │   ├── 6644732418155988823
    │   │   ├── 6741041976153766980
    │   │   ├── 6859043849366253903
    │   │   ├── 6881350812731280932
    │   │   ├── 7183816201469015430
    │   │   ├── 732415842716974174
    │   │   ├── 7496999621932436166
    │   │   ├── 7517119383567959955
    │   │   ├── 7520224568607207294
    │   │   ├── 7802288973746947707
    │   │   ├── 7929682326664907424
    │   │   ├── 7941136980598756235
    │   │   ├── 7956577886942287702
    │   │   ├── 8223221906005330047
    │   │   ├── 8384824395937319727
    │   │   ├── 8532957763921089391
    │   │   ├── 8560661695020652296
    │   │   ├── 8801898463589507569
    │   │   ├── 8864076915306813740
    │   │   ├── 8966674023964647469
    │   │   ├── 8975500954349172945
    │   │   ├── 9252098975371432762
    │   │   ├── 9301559678205039385
    │   │   ├── 9355901921928173478
    │   │   ├── 9560663624704903728
    │   │   ├── 9608597722601571319
    │   │   ├── 965841301586048826
    │   │   ├── 9682216510357466898
    │   │   ├── 9705023032575100833
    │   │   ├── 9752674425509071213
    │   │   ├── 9838702045743273263
    │   │   └── 9985481827053299646
    │   ├── 0.15.0/
    │   │   ├── 10662353231777959466
    │   │   ├── 10699154157323881366
    │   │   ├── 1082187387111347801
    │   │   ├── 1089327447665056171
    │   │   ├── 10932990142778010540
    │   │   ├── 11141776060371505316
    │   │   ├── 11208230123454075281
    │   │   ├── 11550472752485267878
    │   │   ├── 11619053225881628660
    │   │   ├── 12244141011086897912
    │   │   ├── 13350724214960636060
    │   │   ├── 13557882926871855593
    │   │   ├── 1359005368968871854
    │   │   ├── 14062203915639892184
    │   │   ├── 14410272727917912318
    │   │   ├── 14716678767552222578
    │   │   ├── 14783721017356165335
    │   │   ├── 14909960948406216212
    │   │   ├── 15419414060434807388
    │   │   ├── 15712440029477609022
    │   │   ├── 15971761364777785411
    │   │   ├── 16146562853835195938
    │   │   ├── 16165781032922436470
    │   │   ├── 16250310144527187960
    │   │   ├── 16923637647411264303
    │   │   ├── 17047284165065255126
    │   │   ├── 17634843664048402032
    │   │   ├── 17684660275387836573
    │   │   ├── 17903225358877425214
    │   │   ├── 18109794807981555146
    │   │   ├── 18337309172551363682
    │   │   ├── 1930476486160439359
    │   │   ├── 2139083101962255670
    │   │   ├── 2328943080260868233
    │   │   ├── 2401531460664716086
    │   │   ├── 2819710244730587298
    │   │   ├── 3282919673278904038
    │   │   ├── 331134674590433454
    │   │   ├── 3388093767088704663
    │   │   ├── 365358942664456594
    │   │   ├── 3926811325146503647
    │   │   ├── 3982784447698703117
    │   │   ├── 4059164406656705128
    │   │   ├── 4332404684513284572
    │   │   ├── 4392273971602888769
    │   │   ├── 4534439972043072610
    │   │   ├── 478000462697690298
    │   │   ├── 5136060025859774920
    │   │   ├── 5443833037462680285
    │   │   ├── 5722534283883546257
    │   │   ├── 5913567842316902722
    │   │   ├── 5950506011504636517
    │   │   ├── 6265928593898753675
    │   │   ├── 670212781525435369
    │   │   ├── 6743499486019941529
    │   │   ├── 674381625056220596
    │   │   ├── 6799160102053078438
    │   │   ├── 6889212417734539626
    │   │   ├── 7022605420507684020
    │   │   ├── 7895729039707564251
    │   │   ├── 8414339259708775788
    │   │   ├── 8477385040385490960
    │   │   ├── 865701505214290338
    │   │   ├── 8823964001511448600
    │   │   ├── 8863588988738059916
    │   │   ├── 8980934828099359631
    │   │   ├── 9068730433196829648
    │   │   └── 9961226320527059432
    │   ├── .gitignore
    │   └── CACHEDIR.TAG
    ├── .ruff_cache_cli/
    │   ├── 0.14.0/
    │   │   ├── .tmp18gfEN
    │   │   ├── .tmp1JyEz8
    │   │   ├── .tmp4u7Kii
    │   │   ├── .tmp7JYF8Q
    │   │   ├── .tmpBEwYlw
    │   │   ├── .tmpNEybgn
    │   │   ├── .tmpPA7DUR
    │   │   ├── .tmpTzcpAs
    │   │   ├── .tmpV0IlJe
    │   │   ├── .tmpVgUXd2
    │   │   ├── .tmpZDArzq
    │   │   ├── .tmpZMGxDP
    │   │   ├── .tmpZrY0yb
    │   │   ├── .tmpa8yOpJ
    │   │   ├── .tmpcpBdRd
    │   │   ├── .tmpdl0s5w
    │   │   ├── .tmpegFVXC
    │   │   ├── .tmpgkC7Fp
    │   │   ├── .tmphBY5bH
    │   │   ├── .tmpkcLMS5
    │   │   ├── .tmpmbQ6tF
    │   │   ├── .tmpqDn4ou
    │   │   ├── .tmpre9IMk
    │   │   ├── .tmpujKtoF
    │   │   └── .tmpz0EQNH
    │   ├── .gitignore
    │   └── CACHEDIR.TAG
    ├── .vscode/
    │   └── settings.json
    ├── assets/
    │   ├── javascripts/
    │   │   ├── MERMAID_VERSION
    │   │   ├── download_mermaid.ps1
    │   │   ├── mermaid-init.js
    │   │   └── mermaid-loader.js
    │   └── stylesheets/
    │       └── mermaid.css
    ├── configs/
    │   ├── composite/
    │   │   └── field_groups/
    │   │       └── publication.yaml
    │   ├── data_schema/
    │   │   ├── chembl/
    │   │   │   ├── activity.yaml
    │   │   │   ├── assay.yaml
    │   │   │   ├── assay_parameters.yaml
    │   │   │   ├── cell_line.yaml
    │   │   │   ├── compound_record.yaml
    │   │   │   ├── molecule.yaml
    │   │   │   ├── protein_class.yaml
    │   │   │   ├── publication.yaml
    │   │   │   ├── publication_similarity.yaml
    │   │   │   ├── publication_term.yaml
    │   │   │   ├── target.yaml
    │   │   │   ├── target_component.yaml
    │   │   │   └── tissue.yaml
    │   │   ├── composite/
    │   │   │   ├── assay.yaml
    │   │   │   ├── molecule.yaml
    │   │   │   └── publication.yaml
    │   │   ├── crossref/
    │   │   │   └── publication.yaml
    │   │   ├── examples/
    │   │   │   └── publication_with_renames.yaml
    │   │   ├── openalex/
    │   │   │   └── publication.yaml
    │   │   ├── pubchem/
    │   │   │   └── compound.yaml
    │   │   ├── pubmed/
    │   │   │   └── publication.yaml
    │   │   ├── semanticscholar/
    │   │   │   └── publication.yaml
    │   │   └── uniprot/
    │   │       ├── idmapping.yaml
    │   │       └── protein.yaml
    │   ├── dq/
    │   │   ├── entities/
    │   │   │   ├── chembl/
    │   │   │   │   ├── activity.yaml
    │   │   │   │   ├── assay.yaml
    │   │   │   │   ├── assay_parameters.yaml
    │   │   │   │   ├── cell_line.yaml
    │   │   │   │   ├── compound_record.yaml
    │   │   │   │   ├── molecule.yaml
    │   │   │   │   ├── protein_class.yaml
    │   │   │   │   ├── publication.yaml
    │   │   │   │   ├── publication_similarity.yaml
    │   │   │   │   ├── publication_term.yaml
    │   │   │   │   ├── subcellular_fraction.yaml
    │   │   │   │   ├── target.yaml
    │   │   │   │   ├── target_component.yaml
    │   │   │   │   └── tissue.yaml
    │   │   │   ├── crossref/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── openalex/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── pubchem/
    │   │   │   │   └── compound.yaml
    │   │   │   ├── pubmed/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── semanticscholar/
    │   │   │   │   └── publication.yaml
    │   │   │   └── uniprot/
    │   │   │       ├── idmapping.yaml
    │   │   │       ├── protein.yaml
    │   │   │       └── target.yaml
    │   │   ├── providers/
    │   │   │   ├── chembl.yaml
    │   │   │   ├── crossref.yaml
    │   │   │   ├── openalex.yaml
    │   │   │   ├── pubchem.yaml
    │   │   │   ├── pubmed.yaml
    │   │   │   ├── semanticscholar.yaml
    │   │   │   └── uniprot.yaml
    │   │   ├── README.md
    │   │   └── _defaults.yaml
    │   ├── filter/
    │   │   ├── entities/
    │   │   │   ├── chembl/
    │   │   │   │   ├── activity.yaml
    │   │   │   │   ├── assay.yaml
    │   │   │   │   ├── assay_parameters.yaml
    │   │   │   │   ├── cell_line.yaml
    │   │   │   │   ├── compound_record.yaml
    │   │   │   │   ├── molecule.yaml
    │   │   │   │   ├── protein_class.yaml
    │   │   │   │   ├── publication.yaml
    │   │   │   │   ├── publication_similarity.yaml
    │   │   │   │   ├── publication_term.yaml
    │   │   │   │   ├── subcellular_fraction.yaml
    │   │   │   │   ├── target.yaml
    │   │   │   │   └── target_component.yaml
    │   │   │   ├── composite/
    │   │   │   │   ├── activity.yaml
    │   │   │   │   ├── assay.yaml
    │   │   │   │   ├── molecule.yaml
    │   │   │   │   ├── publication.yaml
    │   │   │   │   └── target.yaml
    │   │   │   ├── crossref/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── openalex/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── pubchem/
    │   │   │   │   └── compound.yaml
    │   │   │   ├── pubmed/
    │   │   │   │   └── publication.yaml
    │   │   │   ├── semanticscholar/
    │   │   │   │   └── publication.yaml
    │   │   │   └── uniprot/
    │   │   │       ├── idmapping.yaml
    │   │   │       └── protein.yaml
    │   │   ├── providers/
    │   │   │   ├── chembl.yaml
    │   │   │   ├── crossref.yaml
    │   │   │   ├── openalex.yaml
    │   │   │   ├── pubchem.yaml
    │   │   │   ├── pubmed.yaml
    │   │   │   ├── semanticscholar.yaml
    │   │   │   └── uniprot.yaml
    │   │   ├── README.md
    │   │   └── _defaults.yaml
    │   ├── pipelines/
    │   │   ├── chembl/
    │   │   │   ├── activity.yaml
    │   │   │   ├── assay.yaml
    │   │   │   ├── assay_parameters.yaml
    │   │   │   ├── cell_line.yaml
    │   │   │   ├── compound_record.yaml
    │   │   │   ├── molecule.yaml
    │   │   │   ├── protein_class.yaml
    │   │   │   ├── publication.yaml
    │   │   │   ├── publication_similarity.yaml
    │   │   │   ├── publication_term.yaml
    │   │   │   ├── subcellular_fraction.yaml
    │   │   │   ├── target.yaml
    │   │   │   ├── target_component.yaml
    │   │   │   └── tissue.yaml
    │   │   ├── composite/
    │   │   │   ├── activity.yaml
    │   │   │   ├── assay.yaml
    │   │   │   ├── molecule.yaml
    │   │   │   ├── publication.yaml
    │   │   │   └── target.yaml
    │   │   ├── crossref/
    │   │   │   └── publication.yaml
    │   │   ├── openalex/
    │   │   │   └── publication.yaml
    │   │   ├── pubchem/
    │   │   │   └── compound.yaml
    │   │   ├── pubmed/
    │   │   │   └── publication.yaml
    │   │   ├── semanticscholar/
    │   │   │   └── publication.yaml
    │   │   ├── uniprot/
    │   │   │   ├── idmapping.yaml
    │   │   │   └── protein.yaml
    │   │   ├── _base.yaml
    │   │   ├── _composite_schema.json
    │   │   └── _schema.json
    │   ├── sources/
    │   │   ├── chembl.yaml
    │   │   ├── crossref.yaml
    │   │   ├── openalex.yaml
    │   │   ├── pubchem.yaml
    │   │   ├── pubmed.yaml
    │   │   ├── semanticscholar.yaml
    │   │   └── uniprot.yaml
    │   └── naming_exceptions.yaml
    ├── data/
    │   ├── .idea/
    │   │   ├── inspectionProfiles/
    │   │   │   └── Project_Default.xml
    │   │   ├── .gitignore
    │   │   ├── copilot.data.migration.agent.xml
    │   │   ├── copilot.data.migration.ask2agent.xml
    │   │   ├── data.iml
    │   │   ├── modules.xml
    │   │   ├── vcs.xml
    │   │   └── workspace.xml
    │   ├── checkpoints/
    │   │   └── composite/
    │   │       ├── composite_composite_activity_6279a837-c445-4b58-ae47-1389a53ddddd.json
    │   │       ├── composite_composite_assay_cc62a7a5-95fb-4307-8aa8-da207987743a.json
    │   │       ├── composite_composite_molecule_097995c4-6ea8-4e8b-b790-4d15e8ff1428.json
    │   │       ├── composite_composite_molecule_4ed101d2-0809-44ef-8cf2-2f14afe5858b.json
    │   │       ├── composite_composite_molecule_5b1cf996-854f-47d8-a128-f664faf32607.json
    │   │       ├── composite_composite_publication_0ecb4e6e-062e-4eb3-8b4d-033778553af9.json
    │   │       ├── composite_composite_publication_0f58fcf2-bb8a-4df8-867d-6a47e106ef5a.json
    │   │       ├── composite_composite_publication_1ea3267a-3111-4c9b-8f71-0ecde6d33eae.json
    │   │       ├── composite_composite_publication_25edf4bc-d0c6-4fc8-bedd-ea3a3ed56ab8.json
    │   │       ├── composite_composite_publication_44f9285c-3600-49b7-af72-6bbfcba70927.json
    │   │       ├── composite_composite_publication_4703c922-1f16-4e2b-b54b-ff53ec766f53.json
    │   │       ├── composite_composite_publication_60c22422-3602-4b17-aa06-4d0faea627ad.json
    │   │       ├── composite_composite_publication_6ad2bc7e-1cbf-4785-88ec-3a8457e88f05.json
    │   │       ├── composite_composite_publication_75f181dd-dd2f-4cd9-8d27-5497952cc57c.json
    │   │       ├── composite_composite_publication_959ee035-3b11-4b0b-a652-cde9bad42f19.json
    │   │       ├── composite_composite_publication_95e997da-c9da-4925-9855-52634533a33a.json
    │   │       ├── composite_composite_publication_9ff79b9b-7db2-451e-8467-bfafdeadf7c2.json
    │   │       ├── composite_composite_publication_aed6692e-4a8a-4446-97ab-369399efd84b.json
    │   │       ├── composite_composite_publication_bb962fd5-c6b8-4de6-a2f2-f8dd1ea05c9e.json
    │   │       ├── composite_composite_publication_db8b1b89-00c1-4599-bc48-960c5bdfc44d.json
    │   │       ├── composite_composite_publication_ec532618-1da6-4af2-9665-bc636b001683.json
    │   │       ├── composite_composite_publication_efff0aba-0ce5-4c87-b354-3fe68014bc63.json
    │   │       ├── composite_composite_publication_f7b7cc70-fd35-43cb-9a6a-2c658c0d79d8.json
    │   │       ├── composite_composite_publication_fc80ebf3-dba9-4df8-99a7-6e138d29df26.json
    │   │       ├── composite_composite_target_2f63616d-77bf-4896-abb3-62fa3c92cebe.json
    │   │       ├── composite_composite_target_5c42e8ee-e9a3-4d2a-a056-8d9b5489dc20.json
    │   │       ├── composite_composite_target_73581276-80b2-4623-b7aa-327357366d18.json
    │   │       ├── composite_composite_target_91d4d705-bc86-48a6-99a2-24439d7a0847.json
    │   │       ├── composite_composite_target_a4ac98c8-8e9c-4a74-915b-5537b1cc4cd9.json
    │   │       ├── composite_composite_target_ac813464-d837-445c-86db-cfde2f34646f.json
    │   │       └── composite_composite_target_e75b3763-b867-460b-94f6-b5c2704ec80f.json
    │   ├── input/
    │   │   ├── activity.csv
    │   │   ├── assay.csv
    │   │   ├── cell.csv
    │   │   ├── compound_record.csv
    │   │   ├── dois.csv
    │   │   ├── molecule.csv
    │   │   ├── protein.csv
    │   │   ├── protein_classification.csv
    │   │   ├── publication.csv
    │   │   ├── pubmed.csv
    │   │   ├── pubmed_publications.csv
    │   │   ├── target.csv
    │   │   ├── target_component.csv
    │   │   └── tissue.csv
    │   └── output/
    ├── docs/
    │   ├── .claude/
    │   │   └── settings.local.json
    │   ├── 00-project/
    │   │   ├── agents/
    │   │   │   ├── orchestration/
    │   │   │   │   ├── subagents/
    │   │   │   │   │   ├── pyAuditBot.md
    │   │   │   │   │   └── subagents_registry.md
    │   │   │   │   └── ORCHESTRATION.md
    │   │   │   ├── AGENT.md
    │   │   │   ├── CLAUDE.md
    │   │   │   ├── GEMINI.md
    │   │   │   └── README.md
    │   │   ├── governance/
    │   │   │   ├── 02-naming-policy.md
    │   │   │   ├── 03-file-policy.md
    │   │   │   └── 04-extending-bioetl.md
    │   │   ├── 00-map.md
    │   │   ├── RULES.md
    │   │   ├── TOOLS.md
    │   │   ├── glossary.md
    │   │   ├── index.md
    │   │   └── rules-summary.md
    │   ├── 01-requirements/
    │   │   └── REQUIREMENTS.md
    │   ├── 02-architecture/
    │   │   ├── decisions/
    │   │   │   ├── ADR-001-delta-lake-vs-parquet.md
    │   │   │   ├── ADR-002-medallion-architecture.md
    │   │   │   ├── ADR-003-in-memory-locking-strategy.md
    │   │   │   ├── ADR-004-pydantic-vs-dataclasses.md
    │   │   │   ├── ADR-005-composition-layer-separation.md
    │   │   │   ├── ADR-006-logger-metrics-ports.md
    │   │   │   ├── ADR-007-circuit-breaker-implementation.md
    │   │   │   ├── ADR-008-graceful-shutdown-strategy.md
    │   │   │   ├── ADR-009-paginated-fetcher-mixin.md
    │   │   │   ├── ADR-010-local-only-deployment.md
    │   │   │   ├── ADR-011-remove-watermark-mechanism.md
    │   │   │   ├── ADR-012-storage-clear-contract-and-run-id.md
    │   │   │   ├── ADR-013-async-storage-cleanup.md
    │   │   │   ├── ADR-014-deterministic-writes.md
    │   │   │   ├── ADR-015-pipeline-services-lifecycle.md
    │   │   │   ├── ADR-016-error-handling-strategy.md
    │   │   │   ├── ADR-017-observability-architecture.md
    │   │   │   ├── ADR-018-gold-strict-validation.md
    │   │   │   ├── ADR-019-observability-port-enforcement.md
    │   │   │   ├── ADR-020-basepipeline-decomposition.md
    │   │   │   ├── ADR-021-ddd-aggregates-adoption.md
    │   │   │   ├── ADR-022-tracing-noop.md
    │   │   │   ├── ADR-023-entity-type-patterns.md
    │   │   │   ├── ADR-024-entity-naming-unification.md
    │   │   │   ├── ADR-025-pipeline-config-unification.md
    │   │   │   ├── ADR-026-composite-pipeline-pattern.md
    │   │   │   ├── ADR-027-dq-rules-externalization.md
    │   │   │   ├── ADR-028-filter-rules-externalization.md
    │   │   │   ├── ADR-029-output-metadata-unification.md
    │   │   │   ├── ADR-030-publication-pagination-strategy.md
    │   │   │   ├── ADR-031-loading-strategy-formalization.md
    │   │   │   ├── ADR-032-publication-validation-strategy.md
    │   │   │   ├── ADR-032-unified-http-client.md
    │   │   │   └── README.md
    │   │   ├── diagrams/
    │   │   │   ├── mermaid/
    │   │   │   │   ├── 01_five_layer_architecture.mmd
    │   │   │   │   ├── 02_complete_pipeline_flow.mmd
    │   │   │   │   ├── 03_hexagonal_architecture.mmd
    │   │   │   │   ├── 04_layer_dependency_matrix.mmd
    │   │   │   │   ├── 05_medallion_architecture.mmd
    │   │   │   │   ├── 06_domain_model_overview.mmd
    │   │   │   │   ├── 07_ports_architecture.mmd
    │   │   │   │   ├── 09_ddd_aggregates.mmd
    │   │   │   │   ├── 10_pipeline_core_components.mmd
    │   │   │   │   ├── 11_composition_root.mmd
    │   │   │   │   ├── 12_error_classification.mmd
    │   │   │   │   ├── 13_storage_architecture.mmd
    │   │   │   │   ├── 14_http_infrastructure.mmd
    │   │   │   │   ├── 15_circuit_breaker_states.mmd
    │   │   │   │   ├── 17_retry_mechanism.mmd
    │   │   │   │   ├── 19_base_transformer_template_method.mmd
    │   │   │   │   ├── 20_factory_pattern_usage.mmd
    │   │   │   │   ├── 22_silver_merge_operation.mmd
    │   │   │   │   ├── 23_provider_adapters_overview.mmd
    │   │   │   │   ├── 24_graceful_shutdown.mmd
    │   │   │   │   ├── 25_pipeline_config_structure.mmd
    │   │   │   │   └── 26_composite_pipeline_workflow.mmd
    │   │   │   ├── 00-diagramming-policy.md
    │   │   │   ├── 01-full-system-component.mermaid
    │   │   │   ├── 01-high-level.mermaid
    │   │   │   ├── 01_five_layer_architecture.mmd
    │   │   │   ├── 02-full-medallion-data-flow.mermaid
    │   │   │   ├── 02-medallion.mermaid
    │   │   │   ├── 02_complete_pipeline_flow.mmd
    │   │   │   ├── 03-pipeline-execution-happy-path.mermaid
    │   │   │   ├── 03-pipeline-sequence.mermaid
    │   │   │   ├── 03_hexagonal_architecture.mmd
    │   │   │   ├── 04-domain-layer-class-diagram.mermaid
    │   │   │   ├── 04-error-flow.mermaid
    │   │   │   ├── 04_layer_dependency_matrix.mmd
    │   │   │   ├── 05-layers-interaction.mermaid
    │   │   │   ├── 05-locking.mermaid
    │   │   │   ├── 05-pipeline-lifecycle-states.mermaid
    │   │   │   ├── 05_medallion_architecture.mmd
    │   │   │   ├── 06-application-layer-class-diagram.mermaid
    │   │   │   ├── 06-pipeline-execution.mermaid
    │   │   │   ├── 06_domain_model_overview.mmd
    │   │   │   ├── 07-circuit-breaker-states.mermaid
    │   │   │   ├── 07-medallion-flow.mermaid
    │   │   │   ├── 07_ports_architecture.mmd
    │   │   │   ├── 08-complete-etl-workflow.mermaid
    │   │   │   ├── 08-domain-ddd.mermaid
    │   │   │   ├── 09-full-er-diagram.mermaid
    │   │   │   ├── 09_ddd_aggregates.mmd
    │   │   │   ├── 10-infrastructure-layer-class-diagram.mermaid
    │   │   │   ├── 10_pipeline_core_components.mmd
    │   │   │   ├── 11-lock-acquisition-sequence.mermaid
    │   │   │   ├── 11_composition_root.mmd
    │   │   │   ├── 12-full-aws-deployment.mermaid
    │   │   │   ├── 12_error_classification.mmd
    │   │   │   ├── 13-domain-models-relationship.mermaid
    │   │   │   ├── 13_storage_architecture.mmd
    │   │   │   ├── 14-provider-health-states.mermaid
    │   │   │   ├── 14_http_infrastructure.mmd
    │   │   │   ├── 15-dq-check-workflow.mermaid
    │   │   │   ├── 15_circuit_breaker_states.mmd
    │   │   │   ├── 16-memory-lock-class.mermaid
    │   │   │   ├── 17-pipeline-hierarchy.mermaid
    │   │   │   ├── 17_retry_mechanism.mmd
    │   │   │   ├── 18-bronze-write-sequence.mermaid
    │   │   │   ├── 19-delta-lake-write-sequence.mermaid
    │   │   │   ├── 19_base_transformer_template_method.mmd
    │   │   │   ├── 20-quarantine-record-states.mermaid
    │   │   │   ├── 20_factory_pattern_usage.mmd
    │   │   │   ├── 21-activity-entity-data-flow.mermaid
    │   │   │   ├── 22-client-api-request-sequence.mermaid
    │   │   │   ├── 22_silver_merge_operation.mmd
    │   │   │   ├── 23-silver-writer-class.mermaid
    │   │   │   ├── 23_provider_adapters_overview.mmd
    │   │   │   ├── 24-hash-service-class.mermaid
    │   │   │   ├── 24_graceful_shutdown.mmd
    │   │   │   ├── 25-circuit-breaker-observer-class.mermaid
    │   │   │   ├── 25_pipeline_config_structure.mmd
    │   │   │   ├── 26_composite_pipeline_workflow.mmd
    │   │   │   ├── diagram-catalog.md
    │   │   │   ├── diagrams-index.md
    │   │   │   ├── render_diagrams.sh
    │   │   │   └── top-50-diagrams.md
    │   │   ├── 00-overview.md
    │   │   ├── 01-domain-layer.md
    │   │   ├── 02-application-layer.md
    │   │   ├── 03-infrastructure-layer.md
    │   │   ├── 04-interfaces-layer.md
    │   │   ├── 05-composition-layer.md
    │   │   ├── architecture-diagrams.md
    │   │   ├── container-diagram.md
    │   │   ├── data-flow.md
    │   │   ├── data-layers.md
    │   │   ├── diagrams.md
    │   │   ├── module-consolidation-migration-requirements.md
    │   │   ├── observability-layers.md
    │   │   └── system-context.md
    │   ├── 03-guides/
    │   │   ├── development/
    │   │   │   └── config-schema-guidelines.md
    │   │   ├── quick-ref/
    │   │   ├── add-new-source.md
    │   │   ├── add-pipeline-existing-source.md
    │   │   ├── cleanup-policy.md
    │   │   ├── date-handling.md
    │   │   ├── dq-configuration.md
    │   │   ├── file-path-audit-report.md
    │   │   ├── getting-started.md
    │   │   ├── local-storage-layout.md
    │   │   ├── metrics-monitoring.md
    │   │   ├── pipeline-configuration.md
    │   │   ├── pipeline-lifecycle.md
    │   │   ├── publication-validation-guide.md
    │   │   ├── quick-start.md
    │   │   ├── registry-pattern.md
    │   │   ├── running-pipelines.md
    │   │   ├── testing.md
    │   │   └── troubleshooting.md
    │   ├── 04-reference/
    │   │   ├── api/
    │   │   │   ├── application/
    │   │   │   │   ├── core.md
    │   │   │   │   ├── pipelines.md
    │   │   │   │   ├── services.md
    │   │   │   │   └── transformers.md
    │   │   │   ├── composition/
    │   │   │   │   ├── bootstrap.md
    │   │   │   │   └── factories.md
    │   │   │   ├── domain/
    │   │   │   │   ├── entities.md
    │   │   │   │   ├── exceptions.md
    │   │   │   │   ├── ports.md
    │   │   │   │   └── types.md
    │   │   │   ├── infrastructure/
    │   │   │   │   ├── adapters.md
    │   │   │   │   ├── observability.md
    │   │   │   │   └── storage.md
    │   │   │   ├── application.md
    │   │   │   ├── composition.md
    │   │   │   ├── domain.md
    │   │   │   ├── index.md
    │   │   │   └── infrastructure.md
    │   │   ├── contracts/
    │   │   │   ├── gold/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── chembl_activity_v1.0.json
    │   │   │   │   ├── chembl_assay_parameters_v1.0.json
    │   │   │   │   ├── chembl_assay_v1.0.json
    │   │   │   │   ├── chembl_cell_line_v1.0.json
    │   │   │   │   ├── chembl_compound_record_v1.0.json
    │   │   │   │   ├── chembl_document_similarity_v1.0.json
    │   │   │   │   ├── chembl_document_term_v1.0.json
    │   │   │   │   ├── chembl_document_v1.0.json
    │   │   │   │   ├── chembl_molecule_v1.0.json
    │   │   │   │   ├── chembl_protein_class_v1.0.json
    │   │   │   │   ├── chembl_target_component_v1.0.json
    │   │   │   │   ├── chembl_target_v1.0.json
    │   │   │   │   ├── composite_publication_v1.0.json
    │   │   │   │   ├── crossref_publication_v1.0.json
    │   │   │   │   ├── openalex_publication_v1.0.json
    │   │   │   │   ├── pubchem_compound_v1.0.json
    │   │   │   │   ├── pubmed_publication_v1.0.json
    │   │   │   │   ├── semanticscholar_publication_v1.0.json
    │   │   │   │   ├── uniprot_idmapping_v1.0.json
    │   │   │   │   └── uniprot_protein_v1.0.json
    │   │   │   ├── gold-schemas.md
    │   │   │   └── observability.md
    │   │   ├── pipelines/
    │   │   │   ├── chembl/
    │   │   │   │   ├── 01-protein-class-spec.md
    │   │   │   │   ├── 02-cell-line-spec.md
    │   │   │   │   ├── 03-molecule-spec.md
    │   │   │   │   ├── 04-target-spec.md
    │   │   │   │   ├── 05-activity-spec.md
    │   │   │   │   ├── 06-assay-spec.md
    │   │   │   │   ├── 07-publication-spec.md
    │   │   │   │   ├── 08-assay-parameters-spec.md
    │   │   │   │   ├── 09-compound-record-spec.md
    │   │   │   │   ├── 10-target-component-spec.md
    │   │   │   │   ├── 11-publication-term-spec.md
    │   │   │   │   ├── 12-publication-similarity-spec.md
    │   │   │   │   ├── 14-subcellular-fraction-spec.md
    │   │   │   │   ├── 15-protein-class-spec.md
    │   │   │   │   ├── 16-target-component-spec.md
    │   │   │   │   ├── 17-publication-similarity-spec.md
    │   │   │   │   ├── 18-publication-term-spec.md
    │   │   │   │   ├── cell-line-fields.csv
    │   │   │   │   └── protein-class-fields.csv
    │   │   │   ├── composite/
    │   │   │   │   ├── 01-publication-spec.md
    │   │   │   │   ├── 02-molecule-spec.md
    │   │   │   │   └── 03-target-spec.md
    │   │   │   ├── crossref/
    │   │   │   │   └── 01-publication-spec.md
    │   │   │   ├── openalex/
    │   │   │   │   └── 01-publication-spec.md
    │   │   │   ├── pubchem/
    │   │   │   │   └── 01-compound-spec.md
    │   │   │   ├── pubmed/
    │   │   │   │   └── 01-publication-spec.md
    │   │   │   ├── semanticscholar/
    │   │   │   │   └── 01-publication-spec.md
    │   │   │   ├── uniprot/
    │   │   │   │   ├── 01-protein-spec.md
    │   │   │   │   └── 02-idmapping-spec.md
    │   │   │   ├── INDEX.md
    │   │   │   ├── README.md
    │   │   │   ├── chembl-activity.md
    │   │   │   ├── chembl-assay.md
    │   │   │   ├── openalex-publication.md
    │   │   │   └── semanticscholar-publication.md
    │   │   ├── providers/
    │   │   │   ├── chembl/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── activity.md
    │   │   │   │   ├── assay-parameters.md
    │   │   │   │   ├── assay.md
    │   │   │   │   ├── cell-line.md
    │   │   │   │   ├── compound-record.md
    │   │   │   │   ├── molecule.md
    │   │   │   │   ├── protein-class.md
    │   │   │   │   ├── publication-similarity.md
    │   │   │   │   ├── publication-term.md
    │   │   │   │   ├── publication.md
    │   │   │   │   ├── target-component.md
    │   │   │   │   └── target.md
    │   │   │   ├── crossref/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   └── publication.md
    │   │   │   ├── openalex/
    │   │   │   │   └── publication.md
    │   │   │   ├── pubchem/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   └── compound.md
    │   │   │   ├── pubmed/
    │   │   │   │   └── publication.md
    │   │   │   ├── semanticscholar/
    │   │   │   │   └── publication.md
    │   │   │   ├── uniprot/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── idmapping.md
    │   │   │   │   └── protein.md
    │   │   │   ├── .gitkeep
    │   │   │   └── README.md
    │   │   ├── schemas/
    │   │   │   ├── domain/
    │   │   │   │   └── chembl/
    │   │   │   │       ├── activity-schema.md
    │   │   │   │       ├── assay-schema.md
    │   │   │   │       ├── molecule-schema.md
    │   │   │   │       └── target-schema.md
    │   │   │   ├── publication_field_order.csv
    │   │   │   ├── publication_validation_schema_v3.csv
    │   │   │   └── publication_validation_schema_v3.xlsx
    │   │   ├── templates/
    │   │   │   ├── config.yaml.tpl
    │   │   │   ├── factory.py.tpl
    │   │   │   ├── pipeline-review-checklist.md
    │   │   │   ├── pipeline.py.tpl
    │   │   │   └── source_adapter.py.tpl
    │   │   ├── cli.md
    │   │   ├── config_comparison_matrix.csv
    │   │   ├── publication-fields-reference.md
    │   │   └── publication-validation-index.md
    │   ├── 05-operations/
    │   │   ├── runbooks/
    │   │   │   ├── README.md
    │   │   │   ├── backfill-rebuild.md
    │   │   │   ├── checkpoint-debugging.md
    │   │   │   ├── data-recovery.md
    │   │   │   ├── dq-failure-investigation.md
    │   │   │   ├── incident-response.md
    │   │   │   ├── index.md
    │   │   │   ├── observability-checklist.md
    │   │   │   ├── pipeline-failure-critical.md
    │   │   │   ├── pipeline-failure-dq.md
    │   │   │   ├── pipeline-failure-recovery.md
    │   │   │   ├── publication-validation-runbook.md
    │   │   │   ├── quarantine-management.md
    │   │   │   ├── scaling.md
    │   │   │   ├── schema-evolution.md
    │   │   │   ├── stale-lock.md
    │   │   │   └── vacuum-procedures.md
    │   │   ├── verification/
    │   │   │   ├── publication-field-mapping-report.md
    │   │   │   ├── pubmed-extraction-verification-report.md
    │   │   │   └── semanticscholar-publication-pipeline-verification.md
    │   │   ├── .dockerignore
    │   │   ├── Dockerfile
    │   │   ├── README.md
    │   │   ├── RELEASE_CHECKLIST.md
    │   │   ├── performance-baselines.md
    │   │   └── vacuum-retention.md
    │   ├── 99-archive/
    │   │   ├── decisions/
    │   │   │   ├── ADR-030-api-offset-stability.md
    │   │   │   ├── ADR-030-openalex-offset-stability.md
    │   │   │   ├── ADR-030-publication-field-unification.md
    │   │   │   └── ADR-031-full-scan-loading.md
    │   │   ├── reports/
    │   │   │   ├── audit-2026-02-08/
    │   │   │   │   ├── 00-audit-baseline.md
    │   │   │   │   ├── 01-plan-initial.md
    │   │   │   │   └── 07-audit-final.md
    │   │   │   ├── config-audit/
    │   │   │   │   ├── config_analysis_report.yaml
    │   │   │   │   ├── config_comparison_matrix.csv
    │   │   │   │   ├── config_issues.md
    │   │   │   │   ├── source_access_audit.md
    │   │   │   │   └── unification_plan.md
    │   │   │   ├── CODE_QUALITY_REPORT.md
    │   │   │   ├── PUBLICATION_FIELD_UNIFICATION_PROGRESS.md
    │   │   │   ├── application_merged.md
    │   │   │   ├── audit-package-structure-2026-02-07.md
    │   │   │   ├── composition_merged.md
    │   │   │   ├── config_alignment_report.json
    │   │   │   ├── configs_merged.md
    │   │   │   ├── documentation_merged.md
    │   │   │   ├── domain_merged.md
    │   │   │   ├── dry_run_report.md
    │   │   │   ├── duplicate_function_report.md
    │   │   │   ├── infrastructure_merged.md
    │   │   │   ├── interfaces_merged.md
    │   │   │   ├── pipeline-config-issues.md
    │   │   │   ├── pipeline-config-matrix.csv
    │   │   │   ├── pipeline-config-migration-plan.md
    │   │   │   ├── project_structure.md
    │   │   │   └── Архитектурный обзор BioETL.docx
    │   │   └── refactoring-plan.md
    │   ├── assets/
    │   │   └── javascripts/
    │   │       └── mermaid-init.js
    │   └── audits/
    │       └── architecture-audit-2026-02-07.md
    ├── grafana/
    │   ├── dashboards/
    │   │   ├── bioetl-dq.json
    │   │   ├── bioetl-overview.json
    │   │   └── bioetl-provider-health.json
    │   ├── provisioning/
    │   │   └── dashboards/
    │   │       └── bioetl.yaml
    │   ├── README.md
    │   └── prometheus.yml
    ├── reports/
    │   ├── application_merged.md
    │   ├── composition_merged.md
    │   ├── configs_merged.md
    │   ├── documentation_merged.md
    │   ├── domain_merged.md
    │   ├── infrastructure_merged.md
    │   ├── interfaces_merged.md
    │   └── project_structure.md
    ├── scripts/
    │   ├── audit_structure.py
    │   ├── cleanup_consolidate.py
    │   ├── cleanup_project.py
    │   ├── config_gap_analysis.py
    │   ├── dq_baseline_update.py
    │   ├── lint_terminology.py
    │   ├── naming_audit.py
    │   ├── render_diagrams.py
    │   ├── salt_rotate.py
    │   ├── setup.sh
    │   ├── vacuum_delta.py
    │   ├── validate_pipeline_configs.py
    │   └── verify_checksums.py
    ├── src/
    │   ├── bioetl/
    │   │   ├── application/
    │   │   │   ├── composite/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── aggregator.py
    │   │   │   │   ├── checkpoint.py
    │   │   │   │   ├── column_orderer.py
    │   │   │   │   ├── column_renamer.py
    │   │   │   │   ├── coordinator.py
    │   │   │   │   ├── deduplication.py
    │   │   │   │   ├── dependency_coordinator.py
    │   │   │   │   ├── fsm_helper.py
    │   │   │   │   ├── key_extractor.py
    │   │   │   │   ├── merger.py
    │   │   │   │   ├── preflight_validator.py
    │   │   │   │   ├── runner.py
    │   │   │   │   └── runner_helpers.py
    │   │   │   ├── core/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── base_transformer.py
    │   │   │   │   ├── batch_executor.py
    │   │   │   │   ├── batch_metrics.py
    │   │   │   │   ├── batch_tracing.py
    │   │   │   │   ├── batch_transformer.py
    │   │   │   │   ├── batch_writer.py
    │   │   │   │   ├── checkpoint_manager.py
    │   │   │   │   ├── cleanup_service.py
    │   │   │   │   ├── config.py
    │   │   │   │   ├── dict_transformers.py
    │   │   │   │   ├── field_specs.py
    │   │   │   │   ├── filtered_data_source.py
    │   │   │   │   ├── heartbeat.py
    │   │   │   │   ├── idmapping_data_source.py
    │   │   │   │   ├── lock_manager.py
    │   │   │   │   ├── pipeline_services.py
    │   │   │   │   ├── postrun_service.py
    │   │   │   │   ├── preflight_service.py
    │   │   │   │   ├── protocols.py
    │   │   │   │   ├── publication_term_data_source.py
    │   │   │   │   ├── quarantine_manager.py
    │   │   │   │   ├── record_processor.py
    │   │   │   │   ├── runner.py
    │   │   │   │   ├── shutdown.py
    │   │   │   │   └── subcellular_fraction_data_source.py
    │   │   │   ├── observability/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── observer.py
    │   │   │   │   └── span_helpers.py
    │   │   │   ├── pipelines/
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── _pipelines.py
    │   │   │   │   │   ├── activity.py
    │   │   │   │   │   ├── activity_transformer.py
    │   │   │   │   │   ├── assay.py
    │   │   │   │   │   ├── assay_parameters.py
    │   │   │   │   │   ├── assay_parameters_transformer.py
    │   │   │   │   │   ├── assay_transformer.py
    │   │   │   │   │   ├── base_chembl_transformer.py
    │   │   │   │   │   ├── cell_line.py
    │   │   │   │   │   ├── cell_line_transformer.py
    │   │   │   │   │   ├── compound_record.py
    │   │   │   │   │   ├── compound_record_transformer.py
    │   │   │   │   │   ├── molecule.py
    │   │   │   │   │   ├── molecule_transformer.py
    │   │   │   │   │   ├── protein_class.py
    │   │   │   │   │   ├── protein_class_transformer.py
    │   │   │   │   │   ├── publication.py
    │   │   │   │   │   ├── publication_similarity.py
    │   │   │   │   │   ├── publication_similarity_transformer.py
    │   │   │   │   │   ├── publication_term.py
    │   │   │   │   │   ├── publication_term_transformer.py
    │   │   │   │   │   ├── publication_transformer.py
    │   │   │   │   │   ├── subcellular_fraction.py
    │   │   │   │   │   ├── subcellular_fraction_transformer.py
    │   │   │   │   │   ├── target.py
    │   │   │   │   │   ├── target_component.py
    │   │   │   │   │   ├── target_component_transformer.py
    │   │   │   │   │   ├── target_transformer.py
    │   │   │   │   │   ├── tissue.py
    │   │   │   │   │   └── tissue_transformer.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── base_publication_transformer.py
    │   │   │   │   │   └── extractors.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── author_extractors.py
    │   │   │   │   │   ├── extractors.py
    │   │   │   │   │   ├── reference_extractors.py
    │   │   │   │   │   └── transformer.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── extractors.py
    │   │   │   │   │   └── transformer.py
    │   │   │   │   ├── pubchem/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── compound.py
    │   │   │   │   │   └── transformer.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── extractors/
    │   │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   │   ├── abstract.py
    │   │   │   │   │   │   ├── author.py
    │   │   │   │   │   │   ├── base.py
    │   │   │   │   │   │   ├── classification.py
    │   │   │   │   │   │   ├── date.py
    │   │   │   │   │   │   └── identifier.py
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── publication.py
    │   │   │   │   │   ├── transformer.py
    │   │   │   │   │   └── xml_parser.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── _author_extractors.py
    │   │   │   │   │   ├── _page_parsing.py
    │   │   │   │   │   ├── extractors.py
    │   │   │   │   │   └── transformer.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── extractors/
    │   │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   │   ├── comments.py
    │   │   │   │   │   │   ├── crossrefs.py
    │   │   │   │   │   │   ├── features.py
    │   │   │   │   │   │   ├── genes.py
    │   │   │   │   │   │   ├── taxonomy.py
    │   │   │   │   │   │   └── utils.py
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── idmapping_transformer.py
    │   │   │   │   │   ├── protein.py
    │   │   │   │   │   └── transformer.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── generic.py
    │   │   │   ├── services/
    │   │   │   │   ├── dq/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── _checks_basic.py
    │   │   │   │   │   ├── _checks_business.py
    │   │   │   │   │   ├── _checks_integrity.py
    │   │   │   │   │   ├── _checks_statistical.py
    │   │   │   │   │   ├── bronze_analyzer.py
    │   │   │   │   │   ├── dq_report_builders.py
    │   │   │   │   │   ├── gold_analyzer.py
    │   │   │   │   │   └── silver_analyzer.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── bronze_cleanup_service.py
    │   │   │   │   ├── checkpoint_service.py
    │   │   │   │   ├── config_service.py
    │   │   │   │   ├── data_quality_service.py
    │   │   │   │   ├── dq_metrics_calculator.py
    │   │   │   │   ├── dq_report_service.py
    │   │   │   │   ├── export_service.py
    │   │   │   │   ├── health_service.py
    │   │   │   │   ├── lock_service.py
    │   │   │   │   ├── medallion_lifecycle.py
    │   │   │   │   ├── medallion_types.py
    │   │   │   │   ├── metrics_service.py
    │   │   │   │   ├── pipeline_runner_service.py
    │   │   │   │   ├── quarantine_service.py
    │   │   │   │   ├── shutdown_service.py
    │   │   │   │   └── vacuum_service.py
    │   │   │   └── __init__.py
    │   │   ├── composition/
    │   │   │   ├── bootstrap/
    │   │   │   │   ├── assembly/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── checkpoint.py
    │   │   │   │   │   └── storage.py
    │   │   │   │   ├── cli/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── checkpoint.py
    │   │   │   │   │   ├── config.py
    │   │   │   │   │   ├── health.py
    │   │   │   │   │   ├── lock.py
    │   │   │   │   │   ├── metrics.py
    │   │   │   │   │   ├── noop.py
    │   │   │   │   │   └── storage.py
    │   │   │   │   ├── runtime/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── assembly.py
    │   │   │   │   │   ├── composite.py
    │   │   │   │   │   ├── observability.py
    │   │   │   │   │   ├── pipeline.py
    │   │   │   │   │   └── runner.py
    │   │   │   │   └── __init__.py
    │   │   │   ├── factories/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── data_source_factory.py
    │   │   │   │   ├── dq_factory.py
    │   │   │   │   ├── http_client_factory.py
    │   │   │   │   ├── pipeline_factories.py
    │   │   │   │   ├── pipeline_factory.py
    │   │   │   │   ├── runner_factory.py
    │   │   │   │   ├── services_factory.py
    │   │   │   │   ├── storage.py
    │   │   │   │   ├── storage_adapter.py
    │   │   │   │   ├── storage_factory.py
    │   │   │   │   └── transformer_factory.py
    │   │   │   ├── providers/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── _config_helpers.py
    │   │   │   │   ├── decorators.py
    │   │   │   │   ├── loader.py
    │   │   │   │   ├── provider_registry.py
    │   │   │   │   └── registration.py
    │   │   │   ├── services/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── metadata_coordinator.py
    │   │   │   │   └── versioning.py
    │   │   │   ├── __init__.py
    │   │   │   ├── _pipeline_execution.py
    │   │   │   ├── _resource_management.py
    │   │   │   ├── _services.py
    │   │   │   ├── bootstrap_contexts.py
    │   │   │   ├── bootstrap_logger.py
    │   │   │   ├── builders.py
    │   │   │   ├── entrypoints.py
    │   │   │   ├── observability.py
    │   │   │   ├── registry.py
    │   │   │   └── types.py
    │   │   ├── domain/
    │   │   │   ├── aggregates/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── batch.py
    │   │   │   │   ├── events.py
    │   │   │   │   ├── pipeline_run.py
    │   │   │   │   └── quarantine_entry.py
    │   │   │   ├── composite/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── aggregation.py
    │   │   │   │   ├── config.py
    │   │   │   │   ├── field_groups.py
    │   │   │   │   ├── lineage.py
    │   │   │   │   ├── result.py
    │   │   │   │   ├── state.py
    │   │   │   │   └── strategy.py
    │   │   │   ├── configs/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── base.py
    │   │   │   ├── contracts/
    │   │   │   │   ├── gold/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── _base.py
    │   │   │   │   │   ├── chembl.py
    │   │   │   │   │   ├── composite.py
    │   │   │   │   │   ├── pubchem.py
    │   │   │   │   │   ├── publications.py
    │   │   │   │   │   └── uniprot.py
    │   │   │   │   └── __init__.py
    │   │   │   ├── entities/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── bioactivity.py
    │   │   │   │   ├── chembl.py
    │   │   │   │   ├── chembl_activity.py
    │   │   │   │   ├── chembl_assay_parameters.py
    │   │   │   │   ├── chembl_compound_record.py
    │   │   │   │   ├── chembl_structures.py
    │   │   │   │   ├── chembl_subcellular_fraction.py
    │   │   │   │   ├── chembl_tissue.py
    │   │   │   │   ├── crossref.py
    │   │   │   │   ├── openalex.py
    │   │   │   │   ├── pubchem.py
    │   │   │   │   ├── publication_base.py
    │   │   │   │   ├── pubmed.py
    │   │   │   │   ├── semanticscholar.py
    │   │   │   │   └── uniprot.py
    │   │   │   ├── exceptions/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── data_quality.py
    │   │   │   │   ├── infrastructure.py
    │   │   │   │   ├── internal.py
    │   │   │   │   ├── network.py
    │   │   │   │   └── validation.py
    │   │   │   ├── filtering/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── column_filter.py
    │   │   │   │   ├── gold_config.py
    │   │   │   │   ├── input_config.py
    │   │   │   │   ├── list_filters.py
    │   │   │   │   ├── load_result.py
    │   │   │   │   └── range_filter.py
    │   │   │   ├── mapping/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── publication_fields.py
    │   │   │   ├── models/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── filter.py
    │   │   │   │   └── metadata.py
    │   │   │   ├── ports/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── audit.py
    │   │   │   │   ├── checkpoint.py
    │   │   │   │   ├── data_normalization.py
    │   │   │   │   ├── data_source.py
    │   │   │   │   ├── delta_reader.py
    │   │   │   │   ├── dq_config.py
    │   │   │   │   ├── dq_report.py
    │   │   │   │   ├── filtering.py
    │   │   │   │   ├── health_check.py
    │   │   │   │   ├── idmapping.py
    │   │   │   │   ├── locking.py
    │   │   │   │   ├── memory.py
    │   │   │   │   ├── metadata.py
    │   │   │   │   ├── metadata_coordinator.py
    │   │   │   │   ├── noop.py
    │   │   │   │   ├── normalization.py
    │   │   │   │   ├── observability.py
    │   │   │   │   ├── pii.py
    │   │   │   │   ├── quarantine.py
    │   │   │   │   ├── resilience.py
    │   │   │   │   ├── runner.py
    │   │   │   │   ├── serialization.py
    │   │   │   │   ├── shutdown.py
    │   │   │   │   ├── storage.py
    │   │   │   │   ├── validation.py
    │   │   │   │   └── watermark.py
    │   │   │   ├── registry/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── publication.py
    │   │   │   ├── schemas/
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── activity.py
    │   │   │   │   │   ├── assay.py
    │   │   │   │   │   ├── assay_parameters.py
    │   │   │   │   │   ├── cell_line.py
    │   │   │   │   │   ├── compound_record.py
    │   │   │   │   │   ├── molecule.py
    │   │   │   │   │   ├── molecule_form.py
    │   │   │   │   │   ├── protein_classification.py
    │   │   │   │   │   ├── publication.py
    │   │   │   │   │   ├── publication_similarity.py
    │   │   │   │   │   ├── publication_term.py
    │   │   │   │   │   ├── target.py
    │   │   │   │   │   ├── target_component.py
    │   │   │   │   │   └── target_relation.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── publication_base.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── author.py
    │   │   │   │   │   ├── funder.py
    │   │   │   │   │   ├── publication.py
    │   │   │   │   │   ├── reference.py
    │   │   │   │   │   └── work.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── publication.py
    │   │   │   │   ├── pubchem/
    │   │   │   │   │   └── compound.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   └── publication.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── publication.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── idmapping.py
    │   │   │   │   │   ├── isoform.py
    │   │   │   │   │   └── protein.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── _field_orders.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── column_order.py
    │   │   │   │   ├── constants.py
    │   │   │   │   └── validators.py
    │   │   │   ├── services/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── activity_aggregator.py
    │   │   │   │   ├── data_normalization_config.py
    │   │   │   │   ├── data_normalization_service.py
    │   │   │   │   ├── dq_metrics_calculator.py
    │   │   │   │   ├── dq_serializer.py
    │   │   │   │   ├── identity_service.py
    │   │   │   │   ├── normalization_config.py
    │   │   │   │   ├── normalization_service.py
    │   │   │   │   ├── unit_converter.py
    │   │   │   │   └── value_validator.py
    │   │   │   ├── value_objects/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── academic_ids.py
    │   │   │   │   ├── activity.py
    │   │   │   │   ├── activity_values.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── bronze_result.py
    │   │   │   │   ├── chemical.py
    │   │   │   │   ├── column_order.py
    │   │   │   │   ├── column_qualifier.py
    │   │   │   │   ├── compound_ids.py
    │   │   │   │   ├── dq_metrics.py
    │   │   │   │   ├── dq_report.py
    │   │   │   │   ├── dq_result.py
    │   │   │   │   ├── identifiers.py
    │   │   │   │   ├── publication_field_groups.py
    │   │   │   │   ├── publications.py
    │   │   │   │   ├── run_context.py
    │   │   │   │   ├── silver_result.py
    │   │   │   │   └── taxonomy_id.py
    │   │   │   ├── __init__.py
    │   │   │   ├── config.py
    │   │   │   ├── config_types.py
    │   │   │   ├── constants.py
    │   │   │   ├── context.py
    │   │   │   ├── error_classifier.py
    │   │   │   ├── events.py
    │   │   │   ├── locking.py
    │   │   │   ├── medallion.py
    │   │   │   ├── normalization.py
    │   │   │   ├── resilience.py
    │   │   │   ├── serialization.py
    │   │   │   ├── transformations.py
    │   │   │   ├── types.py
    │   │   │   └── validation.py
    │   │   ├── infrastructure/
    │   │   │   ├── adapters/
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── entity_mapper.py
    │   │   │   │   │   ├── exceptions.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── api_request_collector.py
    │   │   │   │   │   ├── base_title_fallback.py
    │   │   │   │   │   └── title_matching.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── batch.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── exceptions.py
    │   │   │   │   │   ├── fallback.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── decorators/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── circuit_breaker.py
    │   │   │   │   │   └── retry.py
    │   │   │   │   ├── http/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── circuit_breaker.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── health.py
    │   │   │   │   │   ├── health_monitor.py
    │   │   │   │   │   ├── pagination.py
    │   │   │   │   │   └── rate_limiter.py
    │   │   │   │   ├── input/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── csv_filter_reader.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   └── fallback.py
    │   │   │   │   ├── pubchem/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── entity_mapper.py
    │   │   │   │   │   ├── fetch_strategies.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── fallback.py
    │   │   │   │   │   ├── models.py
    │   │   │   │   │   ├── pubmed_client.py
    │   │   │   │   │   └── xml_processor.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── adapter.py
    │   │   │   │   │   └── fallback.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── fasta_parser.py
    │   │   │   │   │   ├── idmapping_client.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── adapter_error_logging.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── base_metrics.py
    │   │   │   │   ├── cached_bronze_data_source.py
    │   │   │   │   ├── error_handling.py
    │   │   │   │   ├── filterable_mixin.py
    │   │   │   │   ├── health_check_mixin.py
    │   │   │   │   ├── sync_base.py
    │   │   │   │   └── validation.py
    │   │   │   ├── audit/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── file_audit.py
    │   │   │   ├── checkpoint/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── local_checkpoint.py
    │   │   │   ├── config/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── _base.py
    │   │   │   │   ├── base_config_loader.py
    │   │   │   │   ├── dq_config_loader.py
    │   │   │   │   ├── field_group_loader.py
    │   │   │   │   ├── filter_config_loader.py
    │   │   │   │   └── pipeline_config_loader.py
    │   │   │   ├── export/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── csv_exporter.py
    │   │   │   │   └── dq_report_writer.py
    │   │   │   ├── locking/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── memory_lock.py
    │   │   │   ├── observability/
    │   │   │   │   ├── anomaly/
    │   │   │   │   │   ├── detectors/
    │   │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   │   ├── base.py
    │   │   │   │   │   │   └── zscore.py
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── detector.py
    │   │   │   │   │   ├── monitor.py
    │   │   │   │   │   └── types.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── logging.py
    │   │   │   │   ├── logging_config.py
    │   │   │   │   ├── metrics.py
    │   │   │   │   ├── metrics_server_adapter.py
    │   │   │   │   ├── noop_logger.py
    │   │   │   │   ├── noop_metrics.py
    │   │   │   │   ├── noop_tracing.py
    │   │   │   │   ├── prometheus_metrics.py
    │   │   │   │   ├── server.py
    │   │   │   │   ├── tracing.py
    │   │   │   │   └── unified_logger.py
    │   │   │   ├── quarantine/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── operations.py
    │   │   │   │   ├── record_encoding.py
    │   │   │   │   └── unified.py
    │   │   │   ├── schemas/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── base_schemas.py
    │   │   │   │   ├── composite_config.py
    │   │   │   │   ├── dq_config.py
    │   │   │   │   ├── dq_report_config.py
    │   │   │   │   ├── filter_config.py
    │   │   │   │   ├── pipeline_config.py
    │   │   │   │   ├── silver.py
    │   │   │   │   └── source_config.py
    │   │   │   ├── security/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── pii_hasher.py
    │   │   │   ├── serialization/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── encoders.py
    │   │   │   ├── storage/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── _atomic.py
    │   │   │   │   ├── arrow_converter.py
    │   │   │   │   ├── base_delta_writer.py
    │   │   │   │   ├── bronze_writer.py
    │   │   │   │   ├── delta_reader.py
    │   │   │   │   ├── gold_writer.py
    │   │   │   │   ├── metadata_builder.py
    │   │   │   │   ├── metadata_writer.py
    │   │   │   │   ├── retention_manager.py
    │   │   │   │   └── silver_writer.py
    │   │   │   ├── system/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── memory_monitor.py
    │   │   │   ├── validation/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── pandera_validator.py
    │   │   │   ├── __init__.py
    │   │   │   └── config_loader.py
    │   │   ├── interfaces/
    │   │   │   ├── cli/
    │   │   │   │   ├── commands/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── archive.py
    │   │   │   │   │   ├── checkpoint.py
    │   │   │   │   │   ├── cleanup.py
    │   │   │   │   │   ├── config.py
    │   │   │   │   │   ├── export.py
    │   │   │   │   │   ├── health.py
    │   │   │   │   │   ├── health_server_integration.py
    │   │   │   │   │   ├── lock.py
    │   │   │   │   │   ├── maintenance.py
    │   │   │   │   │   ├── metrics_server_integration.py
    │   │   │   │   │   ├── quarantine.py
    │   │   │   │   │   ├── run.py
    │   │   │   │   │   ├── run_all.py
    │   │   │   │   │   ├── run_composite.py
    │   │   │   │   │   ├── run_helpers.py
    │   │   │   │   │   └── vacuum.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── __main__.py
    │   │   │   │   ├── exit_codes.py
    │   │   │   │   ├── formatters.py
    │   │   │   │   └── main.py
    │   │   │   ├── http/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── health_server.py
    │   │   │   │   └── types.py
    │   │   │   ├── orchestration/
    │   │   │   │   └── __init__.py
    │   │   │   ├── __init__.py
    │   │   │   └── observability.py
    │   │   ├── __init__.py
    │   │   ├── __main__.py
    │   │   └── py.typed
    │   ├── bioetl.egg-info/
    │   │   ├── PKG-INFO
    │   │   ├── SOURCES.txt
    │   │   ├── dependency_links.txt
    │   │   ├── entry_points.txt
    │   │   ├── requires.txt
    │   │   └── top_level.txt
    │   └── tools/
    │       ├── scripts/
    │       │   ├── migrations/
    │       │   │   ├── __init__.py
    │       │   │   ├── migrate_pmid_to_string.py
    │       │   │   └── rename_structure_fields.py
    │       │   ├── __init__.py
    │       │   ├── check_application_deps.py
    │       │   ├── check_architecture.py
    │       │   ├── check_constructor_args.py
    │       │   ├── cleanup_cache.py
    │       │   ├── config_matrix_generator.py
    │       │   ├── duplicate_function_analyzer.py
    │       │   ├── generate_contracts.py
    │       │   ├── lint_terminology.py
    │       │   ├── migrate_openalex_citation_count.py
    │       │   ├── run-tests.sh
    │       │   ├── run_pytest.sh
    │       │   ├── setup.sh
    │       │   ├── test_changed.sh
    │       │   └── validate_unified_configs.py
    │       ├── README.md
    │       ├── __init__.py
    │       ├── _gen.py
    │       ├── _gen_pydocbot.py
    │       ├── create_pipeline.py
    │       ├── file_merger.py
    │       ├── init_db.sql
    │       └── verify_schema_parity.py
    ├── tests/
    │   ├── architecture/
    │   │   ├── __init__.py
    │   │   ├── test_adapter_contracts.py
    │   │   ├── test_aggregate_boundaries.py
    │   │   ├── test_base_pipeline_purity.py
    │   │   ├── test_bootstrap_layer_boundaries.py
    │   │   ├── test_code_formatting.py
    │   │   ├── test_code_metrics.py
    │   │   ├── test_column_order.py
    │   │   ├── test_composite_layer_boundaries.py
    │   │   ├── test_config_golden_master.py
    │   │   ├── test_di_compliance.py
    │   │   ├── test_di_constructors.py
    │   │   ├── test_di_discipline.py
    │   │   ├── test_docs_version_sync.py
    │   │   ├── test_documentation.py
    │   │   ├── test_domain_public_api.py
    │   │   ├── test_domain_purity.py
    │   │   ├── test_env_var_centralization.py
    │   │   ├── test_forbidden_imports.py
    │   │   ├── test_force_full_scan_publication.py
    │   │   ├── test_gold_schema_contracts.py
    │   │   ├── test_interfaces_no_infrastructure.py
    │   │   ├── test_layer_dependencies.py
    │   │   ├── test_lock_safety_guard.py
    │   │   ├── test_medallion_invariants.py
    │   │   ├── test_metadata_output_contract.py
    │   │   ├── test_no_datetime_now_in_infrastructure.py
    │   │   ├── test_no_fstring_in_logs.py
    │   │   ├── test_no_logging_getlogger_in_infrastructure.py
    │   │   ├── test_no_print_in_docstrings.py
    │   │   ├── test_no_random_in_writers.py
    │   │   ├── test_no_side_effects_in_composition.py
    │   │   ├── test_no_structlog_in_application_interfaces.py
    │   │   ├── test_no_transformer_fallback.py
    │   │   ├── test_performance.py
    │   │   ├── test_pii_hashing.py
    │   │   ├── test_port_contracts.py
    │   │   ├── test_port_contracts_hypothesis.py
    │   │   ├── test_registry_contracts.py
    │   │   ├── test_registry_threading.py
    │   │   ├── test_source_config_usage.py
    │   │   ├── test_tracing_enforcement.py
    │   │   ├── test_transformer_signatures.py
    │   │   └── test_write_mode_types.py
    │   ├── benchmarks/
    │   │   ├── __init__.py
    │   │   ├── conftest.py
    │   │   ├── test_baseline_assertions.py
    │   │   ├── test_bronze_write.py
    │   │   ├── test_delta_write.py
    │   │   ├── test_json_serialization.py
    │   │   └── test_performance.py
    │   ├── contract/
    │   │   ├── __init__.py
    │   │   ├── conftest.py
    │   │   ├── test_chembl_contract.py
    │   │   ├── test_pubchem_contract.py
    │   │   ├── test_publication_schema_contracts.py
    │   │   ├── test_pubmed_contract.py
    │   │   └── test_uniprot_contract.py
    │   ├── e2e/
    │   │   ├── __init__.py
    │   │   ├── conftest.py
    │   │   ├── test_advanced_scenarios_e2e.py
    │   │   ├── test_checkpoint_e2e.py
    │   │   ├── test_chembl_activity_e2e.py
    │   │   ├── test_chembl_assay_e2e.py
    │   │   ├── test_chembl_molecule_e2e.py
    │   │   ├── test_chembl_publication_e2e.py
    │   │   ├── test_chembl_publication_term_e2e.py
    │   │   ├── test_chembl_target_e2e.py
    │   │   ├── test_cli_safety.py
    │   │   ├── test_full_pipeline.py
    │   │   ├── test_full_pipeline_chain_e2e.py
    │   │   ├── test_gold_layer_e2e.py
    │   │   ├── test_network_failure_e2e.py
    │   │   ├── test_pipeline_circuit_breaker_e2e.py
    │   │   ├── test_pipeline_graceful_shutdown_e2e.py
    │   │   ├── test_pipeline_with_dq_errors_e2e.py
    │   │   ├── test_pipeline_with_schema_drift_e2e.py
    │   │   ├── test_pubchem_compound_e2e.py
    │   │   ├── test_pubmed_publication_e2e.py
    │   │   ├── test_resilience_scenarios_e2e.py
    │   │   ├── test_run_types_e2e.py
    │   │   └── test_uniprot_protein_e2e.py
    │   ├── fakes/
    │   │   ├── __init__.py
    │   │   ├── checkpoint_fake.py
    │   │   ├── quarantine_fake.py
    │   │   └── storage_fake.py
    │   ├── fixtures/
    │   │   ├── configs/
    │   │   │   └── dq/
    │   │   │       ├── entities/
    │   │   │       │   └── test_provider/
    │   │   │       │       └── test_entity.yaml
    │   │   │       ├── providers/
    │   │   │       │   └── test_provider.yaml
    │   │   │       └── _defaults.yaml
    │   │   ├── input/
    │   │   │   ├── openalex_dois_sample.csv
    │   │   │   └── semanticscholar_dois_sample.csv
    │   │   ├── vcr/
    │   │   │   ├── chembl/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── TestChEMBLIntegration.test_chembl_extract_transform_load.yaml
    │   │   │   │   ├── TestChEMBLPipelineE2E.test_chembl_activity_full_run.yaml
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_error_handling.yaml
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_happy_path.yaml
    │   │   │   │   ├── TestChemblAdapter.test_fetch_activities.yaml
    │   │   │   │   ├── TestChemblAdapter.test_get_entity_count.yaml
    │   │   │   │   ├── TestChemblAdapter.test_health_check.yaml
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_happy_path.yaml
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_source_fields.yaml
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_error_handling.yaml
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_happy_path.yaml
    │   │   │   │   ├── TestChemblTargetComponentPipeline.test_chembl_target_component_happy_path.yaml
    │   │   │   │   ├── test_all_chembl_pipelines_chain.yaml
    │   │   │   │   ├── test_chembl_activity_full_cycle.yaml
    │   │   │   │   ├── test_chembl_assay_confidence_score.yaml
    │   │   │   │   ├── test_chembl_assay_full_cycle.yaml
    │   │   │   │   ├── test_chembl_assay_metadata_fields.yaml
    │   │   │   │   ├── test_chembl_molecule_full_cycle.yaml
    │   │   │   │   ├── test_chembl_molecule_structural_fields.yaml
    │   │   │   │   ├── test_chembl_molecule_then_activity_chain.yaml
    │   │   │   │   ├── test_chembl_publication_full_cycle.yaml
    │   │   │   │   ├── test_chembl_publication_metadata_fields.yaml
    │   │   │   │   ├── test_chembl_publication_term_full_cycle.yaml
    │   │   │   │   ├── test_chembl_publication_term_mesh_fields.yaml
    │   │   │   │   ├── test_chembl_publication_term_types.yaml
    │   │   │   │   ├── test_chembl_target_cross_references.yaml
    │   │   │   │   ├── test_chembl_target_full_cycle.yaml
    │   │   │   │   ├── test_chembl_target_then_activity_chain.yaml
    │   │   │   │   ├── test_parallel_independent_pipelines.yaml
    │   │   │   │   ├── test_pipeline_idempotency.yaml
    │   │   │   │   ├── test_pipeline_isolation.yaml
    │   │   │   │   ├── test_pipeline_resume_from_checkpoint.yaml
    │   │   │   │   └── test_rerun_same_pipeline_twice.yaml
    │   │   │   ├── crossref/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── test_crossref_batch_fetch.yaml
    │   │   │   │   ├── test_crossref_fetch_by_doi.yaml
    │   │   │   │   ├── test_crossref_health_check.yaml
    │   │   │   │   ├── test_crossref_search_by_title.yaml
    │   │   │   │   └── works_batch.yaml
    │   │   │   ├── e2e/
    │   │   │   ├── integration/
    │   │   │   │   ├── adapters/
    │   │   │   │   │   └── openalex/
    │   │   │   │   └── validation/
    │   │   │   ├── openalex/
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_batch_dois.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_by_doi.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_with_fallback.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_with_query.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_health_check.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_title_only_lookup.yaml
    │   │   │   │   └── TestOpenAlexAdapterRateLimiting.test_rate_limiting_not_exceeded.yaml
    │   │   │   ├── pubchem/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── test_pubchem_compound_full_cycle.yaml
    │   │   │   │   ├── test_pubchem_compound_pipeline.yaml
    │   │   │   │   ├── test_pubchem_compound_query_filter.yaml
    │   │   │   │   └── test_pubchem_compound_structural_fields.yaml
    │   │   │   ├── pubmed/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── test_fetch_publications.yaml
    │   │   │   │   ├── test_health_check.yaml
    │   │   │   │   ├── test_pubmed_publication_classification_fields.yaml
    │   │   │   │   ├── test_pubmed_publication_date_fields.yaml
    │   │   │   │   ├── test_pubmed_publication_full_cycle.yaml
    │   │   │   │   ├── test_pubmed_publication_identifier_fields.yaml
    │   │   │   │   └── test_pubmed_publication_journal_fields.yaml
    │   │   │   ├── semanticscholar/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_batch_dois.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_by_doi.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_filtered_with_fallback.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_health_check.yaml
    │   │   │   │   └── TestSemanticScholarAdapterIntegration.test_title_only_lookup.yaml
    │   │   │   ├── uniprot/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_fetch_proteins.yaml
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtClientIntegration.test_fetch_proteins.yaml
    │   │   │   │   ├── TestUniProtClientIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_mixed_results.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_multiple_ids.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_not_found_id.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_single_id.yaml
    │   │   │   │   ├── test_uniprot_protein_full_cycle.yaml
    │   │   │   │   ├── test_uniprot_protein_metadata_fields.yaml
    │   │   │   │   └── test_uniprot_protein_sequence_fields.yaml
    │   │   │   ├── TestChEMBLPipelineE2E.test_chembl_activity_full_run.yaml
    │   │   │   ├── test_backfill_clears_silver_only.yaml
    │   │   │   ├── test_chembl_and_uniprot_sequential_run.yaml
    │   │   │   ├── test_failed_run_preserves_partial_data.yaml
    │   │   │   ├── test_health_check.yaml
    │   │   │   ├── test_multiple_chembl_entities_parallel_safe.yaml
    │   │   │   ├── test_pipeline_idempotency.yaml
    │   │   │   ├── test_pipeline_resume_after_failure.yaml
    │   │   │   ├── test_pubchem_compound_pipeline.yaml
    │   │   │   ├── test_rebuild_clears_existing_data.yaml
    │   │   │   ├── test_vacuum_respects_retention_days.yaml
    │   │   │   └── test_vacuum_runs_after_successful_pipeline.yaml
    │   │   └── vcr_cassettes/
    │   │       └── crossref/
    │   │           └── works_batch.yaml
    │   ├── infrastructure/
    │   │   ├── adapters/
    │   │   │   ├── http/
    │   │   │   │   ├── test_client_retries.py
    │   │   │   │   └── test_pagination.py
    │   │   │   ├── test_pubchem.py
    │   │   │   └── test_uniprot.py
    │   │   ├── checkpoint/
    │   │   │   └── __init__.py
    │   │   ├── factories/
    │   │   │   └── test_data_sources.py
    │   │   ├── observability/
    │   │   │   └── test_metrics.py
    │   │   └── storage/
    │   │       └── test_gold_writer_integration.py
    │   ├── integration/
    │   │   ├── adapters/
    │   │   │   ├── openalex/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_adapter.py
    │   │   │   │   └── test_pipeline.py
    │   │   │   ├── __init__.py
    │   │   │   ├── test_chembl.py
    │   │   │   ├── test_crossref.py
    │   │   │   ├── test_pubmed.py
    │   │   │   ├── test_pubmed_edge_cases.py
    │   │   │   ├── test_semanticscholar.py
    │   │   │   ├── test_uniprot.py
    │   │   │   └── test_uniprot_idmapping.py
    │   │   ├── composite/
    │   │   │   ├── __init__.py
    │   │   │   ├── test_column_naming_integration.py
    │   │   │   └── test_molecule_pipeline.py
    │   │   ├── config/
    │   │   │   ├── __init__.py
    │   │   │   └── test_dq_config_loading.py
    │   │   ├── infrastructure/
    │   │   │   ├── storage/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_silver_writer.py
    │   │   │   └── __init__.py
    │   │   ├── interfaces/
    │   │   │   ├── __init__.py
    │   │   │   ├── conftest.py
    │   │   │   ├── test_cli_checkpoint_list.py
    │   │   │   ├── test_cli_maintenance_archive.py
    │   │   │   ├── test_cli_maintenance_vacuum.py
    │   │   │   ├── test_cli_quarantine_inspect.py
    │   │   │   ├── test_cli_run_dry_run.py
    │   │   │   ├── test_cli_run_incremental.py
    │   │   │   └── test_cli_shutdown_integration.py
    │   │   ├── pipelines/
    │   │   │   ├── base.py
    │   │   │   ├── test_chembl_activity.py
    │   │   │   ├── test_chembl_cell_line.py
    │   │   │   ├── test_chembl_compound_record.py
    │   │   │   ├── test_chembl_target_component.py
    │   │   │   ├── test_crossref_date_normalization.py
    │   │   │   └── test_pubmed_date_normalization.py
    │   │   ├── validation/
    │   │   │   ├── __init__.py
    │   │   │   └── test_external_verification.py
    │   │   ├── __init__.py
    │   │   ├── memory_storage.py
    │   │   ├── test_cross_provider_doi_normalization.py
    │   │   ├── test_dq_monitor_integration.py
    │   │   ├── test_dq_report_integration.py
    │   │   ├── test_pubchem_pipeline.py
    │   │   ├── test_runner_lifecycle.py
    │   │   └── test_uniprot_pipeline.py
    │   ├── performance/
    │   │   ├── __init__.py
    │   │   └── test_batching_performance.py
    │   ├── security/
    │   │   ├── __init__.py
    │   │   └── test_security.py
    │   ├── smoke/
    │   │   ├── __init__.py
    │   │   └── test_smoke.py
    │   ├── snapshots/
    │   │   └── pipeline_configs.json
    │   ├── unit/
    │   │   ├── application/
    │   │   │   ├── composite/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_checkpoint.py
    │   │   │   │   ├── test_coalesce_qualified.py
    │   │   │   │   ├── test_column_orderer.py
    │   │   │   │   ├── test_column_orderer_renames.py
    │   │   │   │   ├── test_column_renamer.py
    │   │   │   │   ├── test_composite_activity.py
    │   │   │   │   ├── test_coordinator_logging.py
    │   │   │   │   ├── test_dependency_coordinator.py
    │   │   │   │   ├── test_fsm_helper.py
    │   │   │   │   ├── test_fsm_pipeline_scenarios.py
    │   │   │   │   ├── test_merger.py
    │   │   │   │   ├── test_preflight_validator.py
    │   │   │   │   ├── test_publication_schema_columns.py
    │   │   │   │   ├── test_runner.py
    │   │   │   │   ├── test_runner_checkpoint_resume.py
    │   │   │   │   ├── test_runner_enrichment_fsm.py
    │   │   │   │   ├── test_runner_fsm.py
    │   │   │   │   ├── test_runner_fsm_logging.py
    │   │   │   │   ├── test_runner_required_flag.py
    │   │   │   │   └── test_runner_robustness.py
    │   │   │   ├── core/
    │   │   │   │   ├── test_base_transformer.py
    │   │   │   │   ├── test_batch_executor.py
    │   │   │   │   ├── test_batch_executor_memory.py
    │   │   │   │   ├── test_batch_transformer.py
    │   │   │   │   ├── test_batch_writer.py
    │   │   │   │   ├── test_checkpoint_manager.py
    │   │   │   │   ├── test_cleanup_service.py
    │   │   │   │   ├── test_dq_metrics.py
    │   │   │   │   ├── test_dq_report_integration.py
    │   │   │   │   ├── test_field_specs.py
    │   │   │   │   ├── test_filtered_data_source.py
    │   │   │   │   ├── test_health_aggregator.py
    │   │   │   │   ├── test_heartbeat.py
    │   │   │   │   ├── test_idmapping_data_source.py
    │   │   │   │   ├── test_lock_manager.py
    │   │   │   │   ├── test_medallion_policy.py
    │   │   │   │   ├── test_medallion_validator.py
    │   │   │   │   ├── test_memory_monitor.py
    │   │   │   │   ├── test_pipeline_services.py
    │   │   │   │   ├── test_postrun_service.py
    │   │   │   │   ├── test_preflight_service.py
    │   │   │   │   ├── test_protocols.py
    │   │   │   │   ├── test_publication_term_data_source.py
    │   │   │   │   ├── test_record_processor.py
    │   │   │   │   ├── test_record_processor_metrics.py
    │   │   │   │   ├── test_run_id_propagation.py
    │   │   │   │   ├── test_runner.py
    │   │   │   │   ├── test_shutdown.py
    │   │   │   │   ├── test_streaming_batch.py
    │   │   │   │   └── test_subcellular_fraction_data_source.py
    │   │   │   ├── observability/
    │   │   │   │   ├── test_observer.py
    │   │   │   │   └── test_span_helpers.py
    │   │   │   ├── pipelines/
    │   │   │   │   ├── __snapshots__/
    │   │   │   │   │   └── test_transformer_snapshots.ambr
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── test_subcellular_fraction_transformer.py
    │   │   │   │   │   └── test_tissue_transformer.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_base_publication_transformer.py
    │   │   │   │   │   └── test_extractors.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_crossref_transformer.py
    │   │   │   │   │   └── test_extractors.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_extractors.py
    │   │   │   │   │   └── test_transformer.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_classification_extractor.py
    │   │   │   │   │   └── test_pubmed_transformer.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_extractors.py
    │   │   │   │   │   └── test_transformer.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── test_comments_extractor.py
    │   │   │   │   │   ├── test_crossrefs_extractor.py
    │   │   │   │   │   └── test_features_extractor.py
    │   │   │   │   ├── test_activity_transformer.py
    │   │   │   │   ├── test_cell_line_transformer.py
    │   │   │   │   ├── test_chembl_activity_unit.py
    │   │   │   │   ├── test_chembl_assay_parameters.py
    │   │   │   │   ├── test_chembl_pipelines.py
    │   │   │   │   ├── test_chembl_transformers.py
    │   │   │   │   ├── test_compound_record_transformer.py
    │   │   │   │   ├── test_date_parsing.py
    │   │   │   │   ├── test_idmapping_transformer.py
    │   │   │   │   ├── test_page_parsing.py
    │   │   │   │   ├── test_pipeline_registrations.py
    │   │   │   │   ├── test_protein_class_transformer.py
    │   │   │   │   ├── test_pubchem_transformer.py
    │   │   │   │   ├── test_publication_similarity_transformer.py
    │   │   │   │   ├── test_transformations.py
    │   │   │   │   ├── test_transformer_snapshots.py
    │   │   │   │   └── test_uniprot_transformer.py
    │   │   │   ├── services/
    │   │   │   │   ├── dq/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_bronze_analyzer.py
    │   │   │   │   │   ├── test_gold_analyzer.py
    │   │   │   │   │   ├── test_logical_validation.py
    │   │   │   │   │   └── test_structural_validation.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_bronze_cleanup_service.py
    │   │   │   │   ├── test_checkpoint_service.py
    │   │   │   │   ├── test_config_service.py
    │   │   │   │   ├── test_data_quality_service.py
    │   │   │   │   ├── test_dq_metrics_calculator.py
    │   │   │   │   ├── test_dq_report_service.py
    │   │   │   │   ├── test_dq_report_service_coverage.py
    │   │   │   │   ├── test_export_service.py
    │   │   │   │   ├── test_health_service.py
    │   │   │   │   ├── test_lock_service.py
    │   │   │   │   ├── test_medallion_lifecycle.py
    │   │   │   │   ├── test_metadata_coordinator.py
    │   │   │   │   ├── test_metrics_service.py
    │   │   │   │   ├── test_pipeline_runner_service.py
    │   │   │   │   ├── test_quarantine_service.py
    │   │   │   │   ├── test_shutdown_service.py
    │   │   │   │   └── test_vacuum_service.py
    │   │   │   ├── test_base_pipeline.py
    │   │   │   ├── test_error_classifier.py
    │   │   │   └── test_pipeline_config.py
    │   │   ├── cli/
    │   │   │   ├── __snapshots__/
    │   │   │   │   └── test_registry_consistency.ambr
    │   │   │   ├── __init__.py
    │   │   │   └── test_registry_consistency.py
    │   │   ├── composition/
    │   │   │   ├── bootstrap/
    │   │   │   │   ├── runtime/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_assembly.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_checkpoint_bootstrap.py
    │   │   │   │   ├── test_health_bootstrap.py
    │   │   │   │   ├── test_lock_bootstrap.py
    │   │   │   │   ├── test_runner_bootstrap.py
    │   │   │   │   └── test_storage_bootstrap.py
    │   │   │   ├── factories/
    │   │   │   │   ├── test_data_source_registry.py
    │   │   │   │   ├── test_dq_factory.py
    │   │   │   │   ├── test_runner_factory.py
    │   │   │   │   └── test_transformer_factory.py
    │   │   │   ├── providers/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_extraction_params_registration.py
    │   │   │   │   └── test_provider_registry.py
    │   │   │   ├── __init__.py
    │   │   │   ├── test_bootstrap_logger.py
    │   │   │   ├── test_builders.py
    │   │   │   ├── test_entrypoints.py
    │   │   │   ├── test_generic_factory.py
    │   │   │   ├── test_observability_contract.py
    │   │   │   ├── test_registry_protocol.py
    │   │   │   └── test_types.py
    │   │   ├── contracts/
    │   │   │   ├── __init__.py
    │   │   │   └── test_contracts_exports.py
    │   │   ├── domain/
    │   │   │   ├── aggregates/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_batch.py
    │   │   │   │   ├── test_pipeline_run.py
    │   │   │   │   └── test_quarantine_entry.py
    │   │   │   ├── composite/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_composite_config.py
    │   │   │   │   ├── test_composite_result.py
    │   │   │   │   ├── test_data_schema_config.py
    │   │   │   │   ├── test_field_groups.py
    │   │   │   │   ├── test_lineage.py
    │   │   │   │   └── test_state.py
    │   │   │   ├── configs/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_base_configs.py
    │   │   │   ├── entities/
    │   │   │   │   └── test_tissue.py
    │   │   │   ├── exceptions/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_storage.py
    │   │   │   ├── filtering/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_column_filter.py
    │   │   │   │   ├── test_gold_config.py
    │   │   │   │   ├── test_list_filters.py
    │   │   │   │   ├── test_load_result.py
    │   │   │   │   └── test_range_filter.py
    │   │   │   ├── models/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_filter.py
    │   │   │   │   └── test_metadata_output.py
    │   │   │   ├── ports/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_noop.py
    │   │   │   │   └── test_noop_audit.py
    │   │   │   ├── registry/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_publication_registry.py
    │   │   │   ├── schemas/
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_chembl_publication_validation.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_publication_base.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_author_schema.py
    │   │   │   │   │   ├── test_crossref_publication_validation.py
    │   │   │   │   │   ├── test_funder_schema.py
    │   │   │   │   │   └── test_reference_schema.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_openalex_publication_validation.py
    │   │   │   │   │   └── test_publication_schema.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_pubmed_publication_validation.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_publication_schema.py
    │   │   │   │   │   └── test_semanticscholar_publication_validation.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_idmapping_schema.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_doi_validation.py
    │   │   │   │   ├── test_field_orders.py
    │   │   │   │   ├── test_inchi_key_validation.py
    │   │   │   │   ├── test_json_validators.py
    │   │   │   │   └── test_year_validation.py
    │   │   │   ├── services/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_activity_aggregator.py
    │   │   │   │   ├── test_data_normalization_service.py
    │   │   │   │   ├── test_dq_serializer.py
    │   │   │   │   ├── test_identity_service.py
    │   │   │   │   ├── test_normalization_config.py
    │   │   │   │   ├── test_normalization_service.py
    │   │   │   │   ├── test_unit_converter.py
    │   │   │   │   └── test_value_validator.py
    │   │   │   ├── value_objects/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_activity.py
    │   │   │   │   ├── test_base.py
    │   │   │   │   ├── test_column_order.py
    │   │   │   │   ├── test_column_qualifier.py
    │   │   │   │   ├── test_compound_ids.py
    │   │   │   │   ├── test_dq_metrics.py
    │   │   │   │   ├── test_identifiers.py
    │   │   │   │   ├── test_measurements.py
    │   │   │   │   ├── test_publication_field_groups.py
    │   │   │   │   ├── test_publications.py
    │   │   │   │   └── test_silver_result.py
    │   │   │   ├── __init__.py
    │   │   │   ├── test_config.py
    │   │   │   ├── test_config_types.py
    │   │   │   ├── test_config_validation.py
    │   │   │   ├── test_entities.py
    │   │   │   ├── test_events.py
    │   │   │   ├── test_exceptions.py
    │   │   │   ├── test_filter_config.py
    │   │   │   ├── test_locking.py
    │   │   │   ├── test_medallion.py
    │   │   │   ├── test_normalization.py
    │   │   │   ├── test_pipeline_config.py
    │   │   │   ├── test_publication_fields_mapping.py
    │   │   │   ├── test_runtime_config.py
    │   │   │   ├── test_serialization.py
    │   │   │   ├── test_transformations.py
    │   │   │   ├── test_types.py
    │   │   │   └── test_validation.py
    │   │   ├── infrastructure/
    │   │   │   ├── adapters/
    │   │   │   │   ├── chembl/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_chembl_client.py
    │   │   │   │   │   ├── test_chembl_client_coverage.py
    │   │   │   │   │   └── test_chembl_exceptions.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_api_request_collector.py
    │   │   │   │   │   ├── test_base_title_fallback.py
    │   │   │   │   │   └── test_title_matching.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_batch.py
    │   │   │   │   │   ├── test_crossref_client.py
    │   │   │   │   │   └── test_fallback.py
    │   │   │   │   ├── decorators/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_circuit_breaker_decorator.py
    │   │   │   │   │   ├── test_retry_decorator.py
    │   │   │   │   │   └── test_wrap_with_resilience.py
    │   │   │   │   ├── http/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_health_monitor.py
    │   │   │   │   │   └── test_http_client.py
    │   │   │   │   ├── openalex/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_adapter.py
    │   │   │   │   │   └── test_fallback.py
    │   │   │   │   ├── pubchem/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_fetch_strategies.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_adapter_fallback.py
    │   │   │   │   │   ├── test_fallback.py
    │   │   │   │   │   └── test_pubmed_client.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_adapter.py
    │   │   │   │   │   └── test_fallback.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_idmapping_client.py
    │   │   │   │   │   └── test_uniprot_client_coverage.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_adapter_error_logging.py
    │   │   │   │   ├── test_base_metrics.py
    │   │   │   │   ├── test_client_error_paths.py
    │   │   │   │   ├── test_csv_filter_reader.py
    │   │   │   │   ├── test_error_handling.py
    │   │   │   │   ├── test_http_base.py
    │   │   │   │   ├── test_provider_names.py
    │   │   │   │   ├── test_sync_base.py
    │   │   │   │   └── test_validation.py
    │   │   │   ├── audit/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_file_audit.py
    │   │   │   ├── checkpoint/
    │   │   │   │   └── __init__.py
    │   │   │   ├── config/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_dq_config_loader.py
    │   │   │   │   ├── test_field_group_loader.py
    │   │   │   │   └── test_filter_config_loader.py
    │   │   │   ├── export/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_csv_exporter.py
    │   │   │   ├── factories/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_factories.py
    │   │   │   │   └── test_storage_adapter.py
    │   │   │   ├── locking/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_memory_lock.py
    │   │   │   ├── observability/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_anomaly.py
    │   │   │   │   ├── test_logging.py
    │   │   │   │   ├── test_logging_config.py
    │   │   │   │   ├── test_metrics_server_adapter.py
    │   │   │   │   ├── test_prometheus_metrics.py
    │   │   │   │   ├── test_server.py
    │   │   │   │   ├── test_tracing.py
    │   │   │   │   ├── test_unified_logger.py
    │   │   │   │   └── test_zscore_detector.py
    │   │   │   ├── quarantine/
    │   │   │   │   ├── test_unified_quarantine.py
    │   │   │   │   └── test_unified_quarantine_security.py
    │   │   │   ├── schemas/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_base_schemas.py
    │   │   │   │   ├── test_dq_config.py
    │   │   │   │   ├── test_filter_config.py
    │   │   │   │   ├── test_gold.py
    │   │   │   │   ├── test_silver.py
    │   │   │   │   └── test_sink_metadata_config.py
    │   │   │   ├── security/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_pii_hasher.py
    │   │   │   ├── serialization/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_json_encoders.py
    │   │   │   ├── storage/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_arrow_converter.py
    │   │   │   │   ├── test_atomic.py
    │   │   │   │   ├── test_base_delta_writer.py
    │   │   │   │   ├── test_bronze_writer.py
    │   │   │   │   ├── test_delta_reader.py
    │   │   │   │   ├── test_deterministic_write.py
    │   │   │   │   ├── test_gold_writer.py
    │   │   │   │   ├── test_metadata_builder.py
    │   │   │   │   ├── test_metadata_integration.py
    │   │   │   │   ├── test_metadata_writer.py
    │   │   │   │   ├── test_silver_writer.py
    │   │   │   │   ├── test_silver_writer_validation.py
    │   │   │   │   └── test_storage_exceptions.py
    │   │   │   ├── validation/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_pandera_validator.py
    │   │   │   ├── __init__.py
    │   │   │   ├── test_adapters.py
    │   │   │   ├── test_checkpoint.py
    │   │   │   ├── test_circuit_breaker.py
    │   │   │   ├── test_circuit_breaker_degradation.py
    │   │   │   ├── test_config.py
    │   │   │   ├── test_config_dynamic.py
    │   │   │   ├── test_config_settings.py
    │   │   │   ├── test_observability.py
    │   │   │   ├── test_quarantine.py
    │   │   │   ├── test_rate_limiter.py
    │   │   │   ├── test_storage.py
    │   │   │   └── test_storage_factory.py
    │   │   ├── interfaces/
    │   │   │   ├── cli/
    │   │   │   │   ├── commands/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_export.py
    │   │   │   │   │   ├── test_health.py
    │   │   │   │   │   ├── test_health_server_integration.py
    │   │   │   │   │   ├── test_quarantine.py
    │   │   │   │   │   └── test_run_composite.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_cli_main_module.py
    │   │   │   ├── factories/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_pipeline_factories.py
    │   │   │   ├── http/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_health_server.py
    │   │   │   ├── orchestration/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_orchestration_init.py
    │   │   │   ├── __init__.py
    │   │   │   ├── test_cli.py
    │   │   │   ├── test_cli_commands.py
    │   │   │   ├── test_cli_run_all_vacuum_formatters.py
    │   │   │   ├── test_exit_codes.py
    │   │   │   ├── test_observability.py
    │   │   │   ├── test_run_all_command.py
    │   │   │   ├── test_run_all_service_mock.py
    │   │   │   └── test_vacuum_commands.py
    │   │   ├── pipelines/
    │   │   │   ├── chembl/
    │   │   │   │   └── test_activity_schema_gap.py
    │   │   │   ├── pubmed/
    │   │   │   │   ├── extractors/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── test_abstract_extractor.py
    │   │   │   │   │   ├── test_author_extractor.py
    │   │   │   │   │   ├── test_base_field_extractor.py
    │   │   │   │   │   ├── test_classification_extractor.py
    │   │   │   │   │   ├── test_date_extractor.py
    │   │   │   │   │   ├── test_extractor_edge_cases.py
    │   │   │   │   │   ├── test_identifier_extractor.py
    │   │   │   │   │   └── test_xml_parser.py
    │   │   │   │   ├── test_pubmed_publication.py
    │   │   │   │   └── test_pubmed_transformer.py
    │   │   │   ├── uniprot/
    │   │   │   │   ├── extractors/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_taxonomy.py
    │   │   │   │   └── __init__.py
    │   │   │   ├── __init__.py
    │   │   │   └── test_chembl_ddd.py
    │   │   ├── __init__.py
    │   │   ├── test_bootstrap.py
    │   │   ├── test_cli.py
    │   │   ├── test_context.py
    │   │   ├── test_error_classifier.py
    │   │   ├── test_ports.py
    │   │   ├── test_registry.py
    │   │   ├── test_transformations.py
    │   │   └── test_types.py
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── strategies.py
    │   ├── test_architecture.py
    │   └── test_data_storage.py
    ├── .coverage
    ├── .editorconfig
    ├── .env
    ├── .env.example
    ├── .gitattributes
    ├── .gitignore
    ├── .gitleaks.toml
    ├── .importlinter
    ├── .jscpd.json
    ├── .pre-commit-config.yaml
    ├── .secrets.baseline
    ├── CHANGELOG.md
    ├── LICENSE
    ├── Makefile
    ├── README.md
    ├── commitlint.config.js
    ├── coverage.json
    ├── dev_setup.sh
    ├── mkdocs.yml
    ├── pyproject.toml
    ├── requirements.txt
    └── uv.lock
```

**Statistics:**
- Directories: 780
- Files: 8421
- Total items: 9201
