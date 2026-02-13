# Project Structure

Generated: C:\Users\HP3168\Documents\GitHub\BioactivityDataAcquisition2

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
    │   │   │   ├── 02-file-structure-audit-standardization.md
    │   │   │   └── 03-code-inventory-audit.md
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
    │   ├── GEMINI.md
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
    │   ├── SECURITY.md
    │   └── copilot-instructions.md
    ├── .hypothesis/
    │   ├── constants/
    │   │   ├── 001cacf4239b11e0
    │   │   ├── 0149e784fd507e00
    │   │   ├── 030fc565458ea53b
    │   │   ├── 03492d3122a08704
    │   │   ├── 037c813a8fdb5fe6
    │   │   ├── 04f2f25edceda5a6
    │   │   ├── 050a713f268420fe
    │   │   ├── 05c121f6252aacd3
    │   │   ├── 063c63bf21c39c29
    │   │   ├── 06d6fac2db361fee
    │   │   ├── 077ed666f8d5d843
    │   │   ├── 07fcd2c97c888cea
    │   │   ├── 093ce2f8868c3537
    │   │   ├── 096e802ead190427
    │   │   ├── 0aa9932940b86484
    │   │   ├── 0adb00ecb1b1c739
    │   │   ├── 0b293ce77a49d586
    │   │   ├── 0bb257676886b3d5
    │   │   ├── 0bc7b19f73ea219e
    │   │   ├── 0bd09cc00227191f
    │   │   ├── 0c5d7043b3e36031
    │   │   ├── 0ecf804a9a8f3a58
    │   │   ├── 0f060822722836b8
    │   │   ├── 0f096c5f4df73d82
    │   │   ├── 0f81cc4f0a736dfe
    │   │   ├── 0fd2ae3084ab04bb
    │   │   ├── 100dfd4e077a5c67
    │   │   ├── 11b0d28a50eaeb25
    │   │   ├── 11d4a5d12aae527b
    │   │   ├── 12ca60eb440bce90
    │   │   ├── 1355147f79d2f721
    │   │   ├── 14b2fb255c8c6bd3
    │   │   ├── 15ab4439f092f279
    │   │   ├── 161d9c0e98711406
    │   │   ├── 1653a4684322afdd
    │   │   ├── 16b8ca1197c22d4b
    │   │   ├── 173220ebf1b09443
    │   │   ├── 176eedadda2930ca
    │   │   ├── 1770f9cafd75a054
    │   │   ├── 1788e4b3e845df89
    │   │   ├── 17a6754bf8858cd9
    │   │   ├── 194aa71a3baebe9d
    │   │   ├── 19a8b39c6390bff2
    │   │   ├── 1b25432c811157e2
    │   │   ├── 1c6f2568ff8a6cdd
    │   │   ├── 1d93f911c1e27518
    │   │   ├── 1dd6255d8ca44561
    │   │   ├── 1dd9dd460b8f9c3b
    │   │   ├── 1ddb3ea1edd1c5ee
    │   │   ├── 1e643766ca4ccb6b
    │   │   ├── 1e6ccb30049b9ca3
    │   │   ├── 1e784a3bd33c9074
    │   │   ├── 1f2b095257faf2b2
    │   │   ├── 217c72e9a44cc48e
    │   │   ├── 21e4fbd81c4da7ad
    │   │   ├── 21ea69955d277d12
    │   │   ├── 2243e669b724f5f8
    │   │   ├── 22d47bcae2947772
    │   │   ├── 231154dcc2920460
    │   │   ├── 2326cb3225df03f6
    │   │   ├── 237d7ef81f3285ad
    │   │   ├── 23ec1b78887dda0d
    │   │   ├── 240041d7b57ec46b
    │   │   ├── 241ff5b962e48ece
    │   │   ├── 249457333028b93b
    │   │   ├── 25ba0d4659ac69ae
    │   │   ├── 25c998e04c752117
    │   │   ├── 26d11a8834f559b7
    │   │   ├── 26d8198df8b4353e
    │   │   ├── 276ff06793791568
    │   │   ├── 279fc75668773f16
    │   │   ├── 285a9650aa07982d
    │   │   ├── 289b80106a8f62fa
    │   │   ├── 29445c918e2a2016
    │   │   ├── 294e13965437b784
    │   │   ├── 29c75a54886ee40a
    │   │   ├── 2a2cc7288f26178d
    │   │   ├── 2ac28c40cfea812a
    │   │   ├── 2b555e254b1e9cd1
    │   │   ├── 2bed416665fbadff
    │   │   ├── 2e0495f3dda892f0
    │   │   ├── 2e097243797b7e9c
    │   │   ├── 2e24b4f971efe705
    │   │   ├── 2e63e853f6276b47
    │   │   ├── 2ea8724c0889d5dc
    │   │   ├── 2fcdbfbffd8ae285
    │   │   ├── 2fd831480a153432
    │   │   ├── 302ae69b45546906
    │   │   ├── 30372e78c27bc08c
    │   │   ├── 30927c13e3021794
    │   │   ├── 3166ad08a7a82fc4
    │   │   ├── 344b71bb69289b06
    │   │   ├── 3474fe35755e4ddf
    │   │   ├── 3549919093cf1715
    │   │   ├── 35a6258489f434a7
    │   │   ├── 36a63890b118fde2
    │   │   ├── 36f489d12b45dfba
    │   │   ├── 38079ade4fa2d0f7
    │   │   ├── 395840093976319b
    │   │   ├── 3a7837b6fe2a7987
    │   │   ├── 3ab3ae6ed3675a78
    │   │   ├── 3b6d35719789f82a
    │   │   ├── 3b8fa06d57b1ece4
    │   │   ├── 3bbf36a32c9b671d
    │   │   ├── 3c3264ea3d5195c4
    │   │   ├── 3d3cc4524898895b
    │   │   ├── 3e489bddc6cc2a75
    │   │   ├── 3f50fd12ad93c611
    │   │   ├── 40d1b7ba713bdfdb
    │   │   ├── 41bfc24f66d9d301
    │   │   ├── 426777eceb1e9477
    │   │   ├── 42c0fbcdb08f8116
    │   │   ├── 434620b0ad6b4bf7
    │   │   ├── 438f8657a0f116ed
    │   │   ├── 43b59a3575c87288
    │   │   ├── 43eba95f08763bec
    │   │   ├── 452a4ac6dd7c63b2
    │   │   ├── 47fdcbf518d8deaf
    │   │   ├── 4806af43860d333b
    │   │   ├── 48583d51361b04e3
    │   │   ├── 494863565d724961
    │   │   ├── 49734c19dc91041b
    │   │   ├── 49f284d52c5b1894
    │   │   ├── 4b0120efc7273eae
    │   │   ├── 4b20efcfc92b5381
    │   │   ├── 4bf1c5d68efac2f3
    │   │   ├── 4d143dca8572361f
    │   │   ├── 4da36df3da06a15a
    │   │   ├── 4dcbe6c59d328dcb
    │   │   ├── 4de0c730400cb7e6
    │   │   ├── 4e70e1f2024d9780
    │   │   ├── 4ef7365d06039c7d
    │   │   ├── 4f0d6c15d3d3b247
    │   │   ├── 4f38412943871c5c
    │   │   ├── 4fb2ae70b3deb0c4
    │   │   ├── 50f0a61bd51e0a25
    │   │   ├── 51a60623589a0b5a
    │   │   ├── 52530752dd5666a8
    │   │   ├── 534c6ea5c62d59be
    │   │   ├── 547fa6a100297800
    │   │   ├── 54998146111c725f
    │   │   ├── 569345b6ffc917f7
    │   │   ├── 569dff404bafa80c
    │   │   ├── 56b4c3df9e5cea61
    │   │   ├── 5870c1e6ef8e9e95
    │   │   ├── 597a1af2b3fd46f6
    │   │   ├── 5ae5833a4e8d471c
    │   │   ├── 5b5ff132e6d36d8c
    │   │   ├── 5bc83bebb7fc6e77
    │   │   ├── 5bf761de8396f3f2
    │   │   ├── 5c47794c2913b74b
    │   │   ├── 5dd0c8659b2f93e6
    │   │   ├── 5de46f7d90d2a75d
    │   │   ├── 5e91e38998f977e7
    │   │   ├── 5efeb3603de1140a
    │   │   ├── 5f269574f8f8029f
    │   │   ├── 5f2dd7621c7f73bb
    │   │   ├── 5fc9f749857adaf5
    │   │   ├── 5fdcfda06c93486e
    │   │   ├── 6022cb90ccb8b6da
    │   │   ├── 60582ca82efff6a0
    │   │   ├── 60e9ba7b9eb5ed6b
    │   │   ├── 60f493f6be1ac4e5
    │   │   ├── 6209df8d9ff44603
    │   │   ├── 62dc09cf62cc672e
    │   │   ├── 63f11f3f5215f31d
    │   │   ├── 669d4490fa35ab7d
    │   │   ├── 67888cc0d1d55d76
    │   │   ├── 684bd85fca607e32
    │   │   ├── 68c20491c4081c8a
    │   │   ├── 6996ae5f381498f2
    │   │   ├── 69b1b27fcf8d12a6
    │   │   ├── 6b5f5c82b0315069
    │   │   ├── 6b642688d3703c24
    │   │   ├── 6bb0d24baaf7741b
    │   │   ├── 6c6c4340c9ea04da
    │   │   ├── 6eb3660f8e9bdaf0
    │   │   ├── 6eb9b239985cb861
    │   │   ├── 6f3a2f7d8c9672a9
    │   │   ├── 6f729c8760153457
    │   │   ├── 6fcb2dd9455beea6
    │   │   ├── 71281177ae268e08
    │   │   ├── 71524ab3add20b66
    │   │   ├── 720d1c425134039b
    │   │   ├── 739b6ffd7c103501
    │   │   ├── 745077a2ba763db4
    │   │   ├── 75172a593be035f0
    │   │   ├── 7598fdd3be611e2d
    │   │   ├── 76b07c840f79809f
    │   │   ├── 77c3a7db601e455d
    │   │   ├── 783a49b116f407a8
    │   │   ├── 788be032602d0631
    │   │   ├── 7928efe42d5bd9c1
    │   │   ├── 7993cc8341745338
    │   │   ├── 79e0ddde04066564
    │   │   ├── 7a95ff326af91777
    │   │   ├── 7bd1ffc1e935ad05
    │   │   ├── 7c652994b7db59dd
    │   │   ├── 7c7cd5689f050670
    │   │   ├── 7c98bc542660e962
    │   │   ├── 7ce1f6ac87bac0c3
    │   │   ├── 7ce8c3e8c1456813
    │   │   ├── 7d5215941ebb7fb0
    │   │   ├── 7dd7e417b0b3cd22
    │   │   ├── 7ebf5758c772174e
    │   │   ├── 7ee4568765799bb0
    │   │   ├── 7ef00f51ca0d57e5
    │   │   ├── 7f742d0006e93b24
    │   │   ├── 7f9aeea3afc76962
    │   │   ├── 7fca5a7cd045e865
    │   │   ├── 81091485d48348bd
    │   │   ├── 8164d8bc2083a8ed
    │   │   ├── 82ef3f577f3cb692
    │   │   ├── 83e4cdab94e279b6
    │   │   ├── 83f478cf3907f486
    │   │   ├── 85f6ab9b71dbf42f
    │   │   ├── 8626c77565b8613f
    │   │   ├── 864245a5281f40ce
    │   │   ├── 86b02a75047e6b57
    │   │   ├── 8740178cdec701df
    │   │   ├── 882d318186e7ac19
    │   │   ├── 88f6c65709bec958
    │   │   ├── 8905db9887f61d13
    │   │   ├── 8a92c14625f902cc
    │   │   ├── 8af8db0a350ee0c1
    │   │   ├── 8b07477676ac08c1
    │   │   ├── 8b17134e99102d57
    │   │   ├── 8b49a88305ed0179
    │   │   ├── 8c49a2dc64edca79
    │   │   ├── 8c97699c71ab9753
    │   │   ├── 8d05e15c770e7d25
    │   │   ├── 8d4f4a46a6fdbba5
    │   │   ├── 8d93bf6551386e6f
    │   │   ├── 8f50a11a3be745b7
    │   │   ├── 8fadfaa53ce5f8f7
    │   │   ├── 8fb604b7d1eac10a
    │   │   ├── 901da4d53f91c7bc
    │   │   ├── 9057731cc56c26c5
    │   │   ├── 90e5f7652803ab26
    │   │   ├── 91bf9280518847c9
    │   │   ├── 91d191f88a2a8c9b
    │   │   ├── 93cb1ae037458a2b
    │   │   ├── 9433c01434fbbcc3
    │   │   ├── 9448eb36cb92285a
    │   │   ├── 94755467ddee3502
    │   │   ├── 949c744a98206e9d
    │   │   ├── 96aa986adc3e781d
    │   │   ├── 977faa34090c99fd
    │   │   ├── 98b7b369bca2f65f
    │   │   ├── 98f62a4cdb7d2e35
    │   │   ├── 9913216cc19bcef1
    │   │   ├── 99afe72f1958c173
    │   │   ├── 99be0bcd34908169
    │   │   ├── 9a0af09404624008
    │   │   ├── 9ab857cdf918590f
    │   │   ├── 9c0e7ebc96504fe8
    │   │   ├── 9ca8a3a92ead45a4
    │   │   ├── 9cf620129ba6e2d0
    │   │   ├── 9cfc212ef5cbcb3a
    │   │   ├── 9d510d7e21510560
    │   │   ├── 9d8e016be596a399
    │   │   ├── 9de42453cb1b7b19
    │   │   ├── 9e7673c92b074a10
    │   │   ├── 9f2fb6a2ec641183
    │   │   ├── 9f3c8b7f92ebf969
    │   │   ├── a0fa240a1603ea77
    │   │   ├── a14bba72f2d5a7b4
    │   │   ├── a1724a0ab5f04a3a
    │   │   ├── a2060222feb237be
    │   │   ├── a25b27fa8ba2e2d7
    │   │   ├── a40f0b123dad9972
    │   │   ├── a45036fc379216cc
    │   │   ├── a467ca0173c769dd
    │   │   ├── a4a19012517ff99a
    │   │   ├── a53c899e03cdc5e0
    │   │   ├── a642945f21da24c8
    │   │   ├── a80a66b730b9a788
    │   │   ├── a8dd26e606a3b8b9
    │   │   ├── a96dcdf660b9c0e9
    │   │   ├── a9984367a7050459
    │   │   ├── aa1c055a0654b5c0
    │   │   ├── aa917946f881e285
    │   │   ├── aad74357f6c29a03
    │   │   ├── aaea5b9b15dee56b
    │   │   ├── ab0231fe37d4ed99
    │   │   ├── ab46fcd0f27df0b8
    │   │   ├── ab79f7f1ac143283
    │   │   ├── ab9449d83f54dd1b
    │   │   ├── ac7aa5a082390d73
    │   │   ├── acbff73a70f1c768
    │   │   ├── acdb693a288412b4
    │   │   ├── acf0428b36b4a1ed
    │   │   ├── ad6c23eb2ab860a8
    │   │   ├── ad91a75926eaa7f9
    │   │   ├── ae2ced03cb7d55ae
    │   │   ├── aebcea5cd80ff9aa
    │   │   ├── b0a63b36037f9995
    │   │   ├── b1cabd8ad2113c78
    │   │   ├── b1f1042b561c6ca9
    │   │   ├── b23532faa98ccc97
    │   │   ├── b2415a8f6c9b5e57
    │   │   ├── b327195df606f666
    │   │   ├── b3fd91554fb8a2e6
    │   │   ├── b4496ab2e956e796
    │   │   ├── b49a2a13ef738296
    │   │   ├── b500ee456fba5459
    │   │   ├── b5c5757694dda6c0
    │   │   ├── b78e3400ed1c4263
    │   │   ├── b8bb686029d175fe
    │   │   ├── b94b5b7870d3e547
    │   │   ├── b9a4225b377de212
    │   │   ├── b9c9c04f3ce1ac2b
    │   │   ├── ba651b09ab92e2b5
    │   │   ├── ba7ffa48f5fc7aa9
    │   │   ├── bb1d2aba2b140438
    │   │   ├── bcaec94cbdbf8dd5
    │   │   ├── bd9026819e2dcb1d
    │   │   ├── bd963b3ffece2f55
    │   │   ├── bdabe80643accbf1
    │   │   ├── be426885134a09b0
    │   │   ├── bf008b348d06e13c
    │   │   ├── bf978436b20b2704
    │   │   ├── bf99501f40a3669e
    │   │   ├── bff1435589b23c3f
    │   │   ├── bffa072cbf0329c6
    │   │   ├── c182368b534167f3
    │   │   ├── c1b087eaa31690ee
    │   │   ├── c20033a9d14de75e
    │   │   ├── c2bd4f268ea650ba
    │   │   ├── c2d0fd2f77404e21
    │   │   ├── c2f8df32f370e88d
    │   │   ├── c2feb126fd250c0e
    │   │   ├── c369290e525cbc9b
    │   │   ├── c4a3a46f1e7c221e
    │   │   ├── c56860ab56aa48ce
    │   │   ├── c5d7043648f3bc55
    │   │   ├── c6070a06cec512ef
    │   │   ├── c63503d478f94958
    │   │   ├── c6db2e3e351fb01d
    │   │   ├── c74bfa69fc970220
    │   │   ├── c82c059e309b9cb2
    │   │   ├── c8916033e550270e
    │   │   ├── c8e5af24288a0aeb
    │   │   ├── c967f30d367e0f0b
    │   │   ├── c9f7cb466f0bcfee
    │   │   ├── cb4b32d7199500dd
    │   │   ├── cc23ca93be271a9b
    │   │   ├── cc326f96da5ce00e
    │   │   ├── ccc5ff2ad1841593
    │   │   ├── cd7e151d25b8b307
    │   │   ├── ce16563d942e4231
    │   │   ├── ceb9b265195867bd
    │   │   ├── cf540f910aad5674
    │   │   ├── cf979f78e63be8d4
    │   │   ├── cfad690190ebb528
    │   │   ├── cfd7a08b5a46b750
    │   │   ├── cff7a487ced4b289
    │   │   ├── d0e3666b2e90a457
    │   │   ├── d157a7a5d363036e
    │   │   ├── d189c16633edf929
    │   │   ├── d1aa768f36f3724b
    │   │   ├── d25fe81cd34d5012
    │   │   ├── d504ee1d69831ed4
    │   │   ├── d5232c45fbb4629f
    │   │   ├── d644b6ceff8b085e
    │   │   ├── d6cf1f76602d6cec
    │   │   ├── d872275471087cf7
    │   │   ├── d9873a3c77f9f5ad
    │   │   ├── d9af442e56c04520
    │   │   ├── da39a3ee5e6b4b0d
    │   │   ├── dad47da15fe32f96
    │   │   ├── db3d6d147c72d356
    │   │   ├── db9bd210fb8beb2d
    │   │   ├── dc339331834a6348
    │   │   ├── dcfa1842896317ce
    │   │   ├── dd53b7549dd40c2d
    │   │   ├── dd6276e42813d3ad
    │   │   ├── de050575c4b5710e
    │   │   ├── de411ab9e45bd9c1
    │   │   ├── df44fa9da38251ee
    │   │   ├── df4cdcacfc962381
    │   │   ├── dff990b67c346360
    │   │   ├── e065ba00c8f854f8
    │   │   ├── e07226c9ca4f2281
    │   │   ├── e08acebc43c2390b
    │   │   ├── e19e7eed92afc792
    │   │   ├── e1a581363a7405c0
    │   │   ├── e26531a2e0dd62ef
    │   │   ├── e3024b8890389eed
    │   │   ├── e38e35d642670b08
    │   │   ├── e4ef26b5f1eff328
    │   │   ├── e515bbbf17b5e1ec
    │   │   ├── e58bb45976c4fa86
    │   │   ├── e5bb246d980f0338
    │   │   ├── e5fe9afa7b005992
    │   │   ├── e6177bb1a2fea769
    │   │   ├── e67c4c172b649f07
    │   │   ├── e6ab9ffdf7d6f335
    │   │   ├── e6b2d1e1aab37297
    │   │   ├── e71447492ae179ba
    │   │   ├── e764320760c61a43
    │   │   ├── e7786c15decd1163
    │   │   ├── e7b13649015fe431
    │   │   ├── eab8cffc6ebdaa94
    │   │   ├── eb4dc5b9550f829e
    │   │   ├── eca95c6e464034f2
    │   │   ├── ecb7f3415e2cfd13
    │   │   ├── ee211988f7835688
    │   │   ├── ef2a2fd49f4ff6e3
    │   │   ├── ef61ac62c0c657ee
    │   │   ├── eff32708b25ab0b2
    │   │   ├── f0035d4621440d07
    │   │   ├── f00b68e5e9b49fe0
    │   │   ├── f1204b03c339f83e
    │   │   ├── f1b83eac72e2d4d5
    │   │   ├── f1bb9fe375e29ed7
    │   │   ├── f280d0e130f4b080
    │   │   ├── f2bc673a398c77fd
    │   │   ├── f2fcdf2c0bd930d0
    │   │   ├── f347c2ac5f529b00
    │   │   ├── f37ea16fbbd3c6e8
    │   │   ├── f4078d311da78e4a
    │   │   ├── f446f957101df4d1
    │   │   ├── f4aa1f1809684f02
    │   │   ├── f4c5139bbce5019d
    │   │   ├── f526bd8d3b2120f8
    │   │   ├── f66b656350e7b63d
    │   │   ├── f6bdd4bfd1ce9e55
    │   │   ├── f804d037ba2ef5d5
    │   │   ├── f8ffb585777de5f3
    │   │   ├── f927485afca3f7a8
    │   │   ├── f932fc45e26a595f
    │   │   ├── fbc0f955e9961c6d
    │   │   ├── fcc4eee70fb3f150
    │   │   ├── fcd3a54577b06275
    │   │   ├── fcdb1d473d819a33
    │   │   ├── fd249531bfd43166
    │   │   ├── fd8143688d43f9a7
    │   │   ├── fe2a092e89ba0cfd
    │   │   └── fff33cd7463c2185
    │   ├── examples/
    │   │   ├── 0e6a88e4b5cf8f44/
    │   │   │   └── 394341b7182cd227
    │   │   ├── 13e86b5ee486fc75/
    │   │   │   └── c26eab6b7a78bd0a
    │   │   ├── 381c4271721fcd1b/
    │   │   ├── 466f511c60b27a06/
    │   │   │   ├── 0e7b738ad865061f
    │   │   │   ├── 160e2db70838d3b5
    │   │   │   ├── 182a6f11e517ca38
    │   │   │   ├── 1be7b9b86883a979
    │   │   │   ├── 34dfd82bb001e8e8
    │   │   │   ├── 3667d72f6a60cfc6
    │   │   │   ├── 410dad5754346045
    │   │   │   ├── 44e31f0d7a4b1e70
    │   │   │   ├── 467c0633312ab845
    │   │   │   ├── 46aafb879299a622
    │   │   │   ├── 4a7057897ef695c4
    │   │   │   ├── 50fb6b1ba66a5519
    │   │   │   ├── 6e4de6e0e2cc8bd0
    │   │   │   ├── 725adc3ab6953701
    │   │   │   ├── 7d1b88caea2a5d9c
    │   │   │   ├── 7e792563da6383cb
    │   │   │   ├── 81650d75cb81eb8d
    │   │   │   ├── 8183c15ac1c6608a
    │   │   │   ├── 8cf4e1573571d468
    │   │   │   ├── 8d3416b7b7dcaaac
    │   │   │   ├── 9127795e7ded3fc4
    │   │   │   ├── 956d87b9c575fa22
    │   │   │   ├── b67726a0acbcabd6
    │   │   │   ├── b7ffb11f31f3d906
    │   │   │   ├── c7dfe21545cae3a2
    │   │   │   ├── d33bb5eff5ca123f
    │   │   │   ├── d3815d31ebc4accf
    │   │   │   ├── d61bb82cd55c6c5d
    │   │   │   └── de2359ea3aacb301
    │   │   ├── 4f5f3b43c969f912/
    │   │   │   └── 284d428f7a246002
    │   │   ├── 6b62f562d00490ef/
    │   │   │   └── cd6bd1dcfebeffe9
    │   │   ├── 8a3ed85cc026ba89/
    │   │   │   └── d62f203aac389515
    │   │   ├── 8e06212412a29e37/
    │   │   │   └── 1dd6f7b457ad880d
    │   │   ├── 9819e5f3c594fea3/
    │   │   ├── 9b19a057e4bb2dce/
    │   │   │   └── 68e09c5bfbe3cdbe
    │   │   ├── acfabfa5eeb5a748/
    │   │   │   └── 059fea52bf0dba94
    │   │   ├── adf6f5009261e66b/
    │   │   │   └── 7210af19145ec2a8
    │   │   ├── beb1a7ff107e9aa0/
    │   │   │   └── a89a8e27eeb98204
    │   │   ├── c40a5ba31e5afd51/
    │   │   │   ├── 478da8f38ac8b08e
    │   │   │   ├── 6432ffc3612b1f27
    │   │   │   ├── 879013fa53b3a7fe
    │   │   │   ├── 89f5065ba0b17f10
    │   │   │   ├── a14d43b63e6c0a7e
    │   │   │   ├── aa08cc4c418c72fd
    │   │   │   ├── d25bd74dcfef644e
    │   │   │   └── db5c5bb2d68ce5dc
    │   │   ├── c424b4f70cf0314e/
    │   │   │   └── bec021b4f368e306
    │   │   ├── c852d6e07b38b1e2/
    │   │   │   ├── 0a0bffa3cbd964be
    │   │   │   ├── 1ead416baf5fdd73
    │   │   │   ├── 35718841795c947e
    │   │   │   ├── 45360738cc20faab
    │   │   │   ├── 61b172fcd803099f
    │   │   │   ├── 63c09006225edff5
    │   │   │   ├── a1a0b11c113788d3
    │   │   │   ├── a2eae3cadbe1db52
    │   │   │   ├── ad531f92e0095cb1
    │   │   │   └── c8adb91e733a5eb8
    │   │   ├── d31d3082a016bf47/
    │   │   │   └── 534159942e76654a
    │   │   ├── e04e8dd0046bdf49/
    │   │   ├── fd54eacccc9523c4/
    │   │   │   ├── 0f89e915766d50dd
    │   │   │   ├── 1d91f1b0cdc64217
    │   │   │   ├── 273d731256d078e1
    │   │   │   ├── 2c16329955072099
    │   │   │   ├── 40a975d9c9fcc58c
    │   │   │   ├── 50e7a267db3dd22a
    │   │   │   ├── 5a4add7c45f90747
    │   │   │   ├── 5c6820a86a1f2074
    │   │   │   ├── 8bc8cfd46b64469f
    │   │   │   ├── 8e4585c1a161dc3e
    │   │   │   ├── 9b9f2ee27928ca93
    │   │   │   ├── a63344f480551bd2
    │   │   │   ├── a6a4765bbd6f294c
    │   │   │   ├── a9175b2db3d650a0
    │   │   │   ├── bd7dd552af307265
    │   │   │   ├── c09602ac4dc2894d
    │   │   │   ├── c7412cdd13e965e1
    │   │   │   ├── c9b6f9a96333fecf
    │   │   │   ├── e53d0ee0cb03e001
    │   │   │   └── ff0ec828cf10caa7
    │   │   └── ff2d45f2d28850f3/
    │   │       ├── 0faced0fad9467e8
    │   │       ├── 145f8a9bec73d3e8
    │   │       ├── 19216f480b5e776f
    │   │       ├── 46baf1c687f65431
    │   │       ├── 4bfb5732dbc30462
    │   │       ├── 6125c03cd9df2896
    │   │       ├── 621628658c9dcbae
    │   │       ├── 7ffa1a3b7f6353f0
    │   │       ├── 89f4f5fea7e670f1
    │   │       ├── 8de15e31ea5dee26
    │   │       ├── 950a24c8c3acbcf7
    │   │       ├── 9d8dccb776f4e4dc
    │   │       └── a53112f3fcef83c7
    │   ├── tmp/
    │   │   ├── tmp0_afguuj
    │   │   ├── tmp0fj4z3ft
    │   │   ├── tmp0jziw9nq
    │   │   ├── tmp0lxcrf7d
    │   │   ├── tmp1ktriyx5
    │   │   ├── tmp1t156k4b
    │   │   ├── tmp1z1kj66z
    │   │   ├── tmp256y5na8
    │   │   ├── tmp2p8qo0e1
    │   │   ├── tmp2x2a0f83
    │   │   ├── tmp2zdzfhv1
    │   │   ├── tmp3ejre6s1
    │   │   ├── tmp3j0u9iey
    │   │   ├── tmp3l1b4f4_
    │   │   ├── tmp3o7lagog
    │   │   ├── tmp3yc0t1ld
    │   │   ├── tmp4ucgt0bw
    │   │   ├── tmp4v40lopm
    │   │   ├── tmp57_365mf
    │   │   ├── tmp5jxg81q1
    │   │   ├── tmp5o5ddq7e
    │   │   ├── tmp63d068gl
    │   │   ├── tmp6rak0jht
    │   │   ├── tmp6rk0_t4e
    │   │   ├── tmp7an1nb7g
    │   │   ├── tmp7apde1ke
    │   │   ├── tmp7c75cp9f
    │   │   ├── tmp7ms4p3he
    │   │   ├── tmp7nu_hgt6
    │   │   ├── tmp80jo8sf2
    │   │   ├── tmp816xzlyf
    │   │   ├── tmp84kh_aq6
    │   │   ├── tmp8eg72u7z
    │   │   ├── tmp8jkows09
    │   │   ├── tmp8nqm2866
    │   │   ├── tmp9_9xea9k
    │   │   ├── tmp9hbx36sh
    │   │   ├── tmp9jicgb3q
    │   │   ├── tmp9wxv8cm_
    │   │   ├── tmp_gd5y518
    │   │   ├── tmpa3criq1v
    │   │   ├── tmpa9pf8fs0
    │   │   ├── tmpae56ya70
    │   │   ├── tmpapx1w00s
    │   │   ├── tmpaqa31r4g
    │   │   ├── tmpb4w62j4q
    │   │   ├── tmpbyxy51co
    │   │   ├── tmpc02u8t0p
    │   │   ├── tmpc1d7qpd3
    │   │   ├── tmpcjd2sp5a
    │   │   ├── tmpcklybuud
    │   │   ├── tmpd9s0iicf
    │   │   ├── tmpdf5hn5zy
    │   │   ├── tmpdrid7w9k
    │   │   ├── tmpei_ofoxh
    │   │   ├── tmpepbp1vtq
    │   │   ├── tmpf48atkf6
    │   │   ├── tmpf4ovgc0z
    │   │   ├── tmpf9274m25
    │   │   ├── tmpfjj1le_p
    │   │   ├── tmpg88hr9m1
    │   │   ├── tmpgv898qou
    │   │   ├── tmph15bjn_n
    │   │   ├── tmph_3vuw41
    │   │   ├── tmphwt4bmhn
    │   │   ├── tmpi2bsn_0j
    │   │   ├── tmpi_5psrl2
    │   │   ├── tmpifeslmqx
    │   │   ├── tmpj29etgo9
    │   │   ├── tmpk3o_xk2b
    │   │   ├── tmpl2lqe4kk
    │   │   ├── tmpl66u90cq
    │   │   ├── tmplh5w847x
    │   │   ├── tmplmnezwd3
    │   │   ├── tmplzflsyu_
    │   │   ├── tmpm5kkcqhq
    │   │   ├── tmpmd8l82il
    │   │   ├── tmpmq65e1pc
    │   │   ├── tmpn4ph1yuf
    │   │   ├── tmpnc1m1vg_
    │   │   ├── tmpnwgodr87
    │   │   ├── tmpo3v5lgpj
    │   │   ├── tmpo7ft8lfl
    │   │   ├── tmpohmgwb10
    │   │   ├── tmpojgj2rnb
    │   │   ├── tmpokpsg6z7
    │   │   ├── tmpom5zdvt1
    │   │   ├── tmpoqnc4uoc
    │   │   ├── tmppcdk1unr
    │   │   ├── tmppk766c_d
    │   │   ├── tmppkb_2lp_
    │   │   ├── tmpqeipu0e4
    │   │   ├── tmpqlmzgqmx
    │   │   ├── tmpqnx533lw
    │   │   ├── tmprys306_4
    │   │   ├── tmpsysvcc_4
    │   │   ├── tmpszdf3sgy
    │   │   ├── tmpszzvsyum
    │   │   ├── tmptawobmeq
    │   │   ├── tmptwxfh2fm
    │   │   ├── tmpu1fhxcs3
    │   │   ├── tmpuhywbi6s
    │   │   ├── tmpumm_d_mp
    │   │   ├── tmpur6iiww6
    │   │   ├── tmpurinvwna
    │   │   ├── tmpvt_eacfd
    │   │   ├── tmpvxo1515h
    │   │   ├── tmpw7exzjla
    │   │   ├── tmpwah36zuf
    │   │   ├── tmpwooswt9z
    │   │   ├── tmpwubtlk36
    │   │   ├── tmpwzx9sjm8
    │   │   ├── tmpx2r5jjgl
    │   │   ├── tmpx59nzyt2
    │   │   ├── tmpy8p0ff94
    │   │   ├── tmpya7gck3e
    │   │   ├── tmpywom5dpn
    │   │   ├── tmpz496r2yv
    │   │   ├── tmpzpiwsjny
    │   │   └── tmpzyp4eswp
    │   └── unicode_data/
    │       └── 16.0.0/
    │           ├── charmap.json.gz
    │           └── codec-utf-8.json.gz
    ├── .idea/
    │   ├── inspectionProfiles/
    │   │   └── profiles_settings.xml
    │   ├── shelf/
    │   │   ├── Uncommitted_changes_before_Update_at_2_13_2026_12_22_AM_[Changes]/
    │   │   │   └── shelved.patch
    │   │   └── Uncommitted_changes_before_Update_at_2_13_2026_12_22_AM__Changes_.xml
    │   ├── stylesheetLinters/
    │   │   └── stylelint.xml
    │   ├── .gitignore
    │   ├── BioactivityDataAcquisition2.iml
    │   ├── JunieProjectTechnologies.xml
    │   ├── codex.xml
    │   ├── copilot.data.migration.agent.xml
    │   ├── copilot.data.migration.ask.xml
    │   ├── copilot.data.migration.ask2agent.xml
    │   ├── copilot.data.migration.edit.xml
    │   ├── csv-editor.xml
    │   ├── externalDependencies.xml
    │   ├── misc.xml
    │   ├── modules.xml
    │   ├── vcs.xml
    │   ├── webResources.xml
    │   └── workspace.xml
    ├── .import_linter_cache/
    │   ├── .gitignore
    │   ├── CACHEDIR.TAG
    │   ├── bioetl.meta.json
    │   └── ffd35c0055ccf94f516de1a6a1eb6149bab5d4ab.data.json
    ├── .jules/
    │   └── bolt.md
    ├── .mypy_cache/
    │   ├── 3.11/
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
    │   │   │   │   │   ├── filtered_data_source.data.json
    │   │   │   │   │   ├── filtered_data_source.meta.json
    │   │   │   │   │   ├── heartbeat.data.json
    │   │   │   │   │   ├── heartbeat.meta.json
    │   │   │   │   │   ├── lock_manager.data.json
    │   │   │   │   │   ├── lock_manager.meta.json
    │   │   │   │   │   ├── memory_monitor.data.json
    │   │   │   │   │   ├── memory_monitor.meta.json
    │   │   │   │   │   ├── pipeline_services.data.json
    │   │   │   │   │   ├── pipeline_services.meta.json
    │   │   │   │   │   ├── postrun_service.data.json
    │   │   │   │   │   ├── postrun_service.meta.json
    │   │   │   │   │   ├── preflight_service.data.json
    │   │   │   │   │   ├── preflight_service.meta.json
    │   │   │   │   │   ├── protocols.data.json
    │   │   │   │   │   ├── protocols.meta.json
    │   │   │   │   │   ├── quarantine_manager.data.json
    │   │   │   │   │   ├── quarantine_manager.meta.json
    │   │   │   │   │   ├── runner.data.json
    │   │   │   │   │   ├── runner.meta.json
    │   │   │   │   │   ├── shutdown.data.json
    │   │   │   │   │   ├── shutdown.meta.json
    │   │   │   │   │   ├── transform_utils.data.json
    │   │   │   │   │   └── transform_utils.meta.json
    │   │   │   │   ├── observability/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── observer.data.json
    │   │   │   │   │   ├── observer.meta.json
    │   │   │   │   │   ├── span_helpers.data.json
    │   │   │   │   │   └── span_helpers.meta.json
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── bronze_cleanup_service.data.json
    │   │   │   │   │   ├── bronze_cleanup_service.meta.json
    │   │   │   │   │   ├── checkpoint_service.data.json
    │   │   │   │   │   ├── checkpoint_service.meta.json
    │   │   │   │   │   ├── data_quality_service.data.json
    │   │   │   │   │   ├── data_quality_service.meta.json
    │   │   │   │   │   ├── lock_service.data.json
    │   │   │   │   │   ├── lock_service.meta.json
    │   │   │   │   │   ├── medallion_lifecycle.data.json
    │   │   │   │   │   ├── medallion_lifecycle.meta.json
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
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── builders.data.json
    │   │   │   │   └── builders.meta.json
    │   │   │   ├── domain/
    │   │   │   │   ├── configs/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   └── base.meta.json
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
    │   │   │   │   │   ├── chembl_compound_record.data.json
    │   │   │   │   │   ├── chembl_compound_record.meta.json
    │   │   │   │   │   ├── chembl_structures.data.json
    │   │   │   │   │   ├── chembl_structures.meta.json
    │   │   │   │   │   ├── crossref.data.json
    │   │   │   │   │   ├── crossref.meta.json
    │   │   │   │   │   ├── pubchem.data.json
    │   │   │   │   │   ├── pubchem.meta.json
    │   │   │   │   │   ├── pubmed.data.json
    │   │   │   │   │   ├── pubmed.meta.json
    │   │   │   │   │   ├── uniprot.data.json
    │   │   │   │   │   └── uniprot.meta.json
    │   │   │   │   ├── exceptions/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── critical.data.json
    │   │   │   │   │   ├── critical.meta.json
    │   │   │   │   │   ├── data_quality.data.json
    │   │   │   │   │   ├── data_quality.meta.json
    │   │   │   │   │   ├── external_service.data.json
    │   │   │   │   │   ├── external_service.meta.json
    │   │   │   │   │   ├── recoverable.data.json
    │   │   │   │   │   ├── recoverable.meta.json
    │   │   │   │   │   ├── storage.data.json
    │   │   │   │   │   └── storage.meta.json
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
    │   │   │   │   ├── ports/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── audit.data.json
    │   │   │   │   │   ├── audit.meta.json
    │   │   │   │   │   ├── checkpoint.data.json
    │   │   │   │   │   ├── checkpoint.meta.json
    │   │   │   │   │   ├── data_source.data.json
    │   │   │   │   │   ├── data_source.meta.json
    │   │   │   │   │   ├── filtering.data.json
    │   │   │   │   │   ├── filtering.meta.json
    │   │   │   │   │   ├── health_check.data.json
    │   │   │   │   │   ├── health_check.meta.json
    │   │   │   │   │   ├── locking.data.json
    │   │   │   │   │   ├── locking.meta.json
    │   │   │   │   │   ├── memory.data.json
    │   │   │   │   │   ├── memory.meta.json
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
    │   │   │   │   │   └── validation.meta.json
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── activity_aggregator.data.json
    │   │   │   │   │   ├── activity_aggregator.meta.json
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
    │   │   │   │   │   ├── activity.data.json
    │   │   │   │   │   ├── activity.meta.json
    │   │   │   │   │   ├── activity_values.data.json
    │   │   │   │   │   ├── activity_values.meta.json
    │   │   │   │   │   ├── base.data.json
    │   │   │   │   │   ├── base.meta.json
    │   │   │   │   │   ├── compound_ids.data.json
    │   │   │   │   │   ├── compound_ids.meta.json
    │   │   │   │   │   ├── dq_result.data.json
    │   │   │   │   │   ├── dq_result.meta.json
    │   │   │   │   │   ├── identifiers.data.json
    │   │   │   │   │   └── identifiers.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   ├── config.meta.json
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
    │   │   │   │   │   │   ├── models.data.json
    │   │   │   │   │   │   └── models.meta.json
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
    │   │   │   │   │   │   ├── rate_limiter.data.json
    │   │   │   │   │   │   └── rate_limiter.meta.json
    │   │   │   │   │   ├── input/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── csv_filter_reader.data.json
    │   │   │   │   │   │   └── csv_filter_reader.meta.json
    │   │   │   │   │   ├── pubchem/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── client.data.json
    │   │   │   │   │   │   ├── client.meta.json
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
    │   │   │   │   │   ├── health_check_mixin.data.json
    │   │   │   │   │   ├── health_check_mixin.meta.json
    │   │   │   │   │   ├── sync_base.data.json
    │   │   │   │   │   ├── sync_base.meta.json
    │   │   │   │   │   ├── validation.data.json
    │   │   │   │   │   └── validation.meta.json
    │   │   │   │   ├── schemas/
    │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   ├── pipeline_config.data.json
    │   │   │   │   │   ├── pipeline_config.meta.json
    │   │   │   │   │   ├── source_config.data.json
    │   │   │   │   │   └── source_config.meta.json
    │   │   │   │   ├── __init__.data.json
    │   │   │   │   ├── __init__.meta.json
    │   │   │   │   ├── config.data.json
    │   │   │   │   ├── config.meta.json
    │   │   │   │   ├── config_loader.data.json
    │   │   │   │   └── config_loader.meta.json
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
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
    │   │   │   └── cookiejar.meta.json
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
    │   │   │   ├── internal/
    │   │   │   │   ├── conjecture/
    │   │   │   │   │   ├── shrinking/
    │   │   │   │   │   │   ├── __init__.data.json
    │   │   │   │   │   │   ├── __init__.meta.json
    │   │   │   │   │   │   ├── bytes.data.json
    │   │   │   │   │   │   ├── bytes.meta.json
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
    │   │   │   │   ├── coverage.data.json
    │   │   │   │   ├── coverage.meta.json
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
    │   │   │   │   └── dynamicvariables.meta.json
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
    │   │   │   │   └── abc.meta.json
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
    │   │   ├── orjson/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── os/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── path.data.json
    │   │   │   └── path.meta.json
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
    │   │   ├── pathlib/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
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
    │   │   ├── pytz/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── exceptions.data.json
    │   │   │   ├── exceptions.meta.json
    │   │   │   ├── tzinfo.data.json
    │   │   │   └── tzinfo.meta.json
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
    │   │   ├── sqlite3/
    │   │   │   ├── __init__.data.json
    │   │   │   ├── __init__.meta.json
    │   │   │   ├── dbapi2.data.json
    │   │   │   └── dbapi2.meta.json
    │   │   ├── string/
    │   │   │   ├── __init__.data.json
    │   │   │   └── __init__.meta.json
    │   │   ├── sys/
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
    │   │   │   ├── types.data.json
    │   │   │   └── types.meta.json
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
    │   │   ├── operator.data.json
    │   │   ├── operator.meta.json
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
    │   └── CACHEDIR.TAG
    ├── .pytest_cache/
    │   ├── v/
    │   │   └── cache/
    │   │       ├── lastfailed
    │   │       └── nodeids
    │   ├── .gitignore
    │   ├── CACHEDIR.TAG
    │   └── README.md
    ├── .ruff_cache/
    │   ├── 0.14.6/
    │   │   ├── 10100695278958451438
    │   │   ├── 10177373308723998208
    │   │   ├── 10275511339992016330
    │   │   ├── 10277376662178146373
    │   │   ├── 10403208263006898403
    │   │   ├── 1041745263121478075
    │   │   ├── 10448406664848552974
    │   │   ├── 10517968578791471674
    │   │   ├── 10882480562379780118
    │   │   ├── 11092149170990210739
    │   │   ├── 11104207138111913698
    │   │   ├── 11162525656524455572
    │   │   ├── 11520577196226392294
    │   │   ├── 11609250519985849832
    │   │   ├── 11620095965273480619
    │   │   ├── 11621195001897393838
    │   │   ├── 11673004830139167365
    │   │   ├── 11852710529897678681
    │   │   ├── 11972075444629534735
    │   │   ├── 1229232418671322630
    │   │   ├── 12325705034155667080
    │   │   ├── 12592996808693072556
    │   │   ├── 12696210531409123674
    │   │   ├── 12870209208122190389
    │   │   ├── 13003376387887824114
    │   │   ├── 1309168931970644464
    │   │   ├── 13203279274754266443
    │   │   ├── 13245575723139442931
    │   │   ├── 13516817338072483562
    │   │   ├── 13532277452285762182
    │   │   ├── 13546449506134558640
    │   │   ├── 13639034180197316901
    │   │   ├── 13689875875546961302
    │   │   ├── 13803375908507581554
    │   │   ├── 13816847282861078387
    │   │   ├── 13834444569046903827
    │   │   ├── 1387979493409582987
    │   │   ├── 13941432079984840340
    │   │   ├── 13959423021678244090
    │   │   ├── 13975654596650637822
    │   │   ├── 13999707521814968808
    │   │   ├── 14009714469810170001
    │   │   ├── 14057329455110980288
    │   │   ├── 14109997285391530487
    │   │   ├── 14155034734509453145
    │   │   ├── 14231648063787376059
    │   │   ├── 14418982129920080608
    │   │   ├── 14626546172993530938
    │   │   ├── 14799273837308249659
    │   │   ├── 15119192832379129859
    │   │   ├── 15126912100491070285
    │   │   ├── 15288463836444036648
    │   │   ├── 15374811028708512200
    │   │   ├── 15410409851508729966
    │   │   ├── 15502651756183598156
    │   │   ├── 15503603125595642821
    │   │   ├── 15586970011272616936
    │   │   ├── 15599795380866005734
    │   │   ├── 15722780433884082968
    │   │   ├── 15749852185651242905
    │   │   ├── 15760086530853564201
    │   │   ├── 15842537338813275901
    │   │   ├── 1598664554979971096
    │   │   ├── 16170083673677055596
    │   │   ├── 16279507192216833645
    │   │   ├── 16293234769896953511
    │   │   ├── 16392317098098844070
    │   │   ├── 1640302520787650931
    │   │   ├── 16419685665181550292
    │   │   ├── 1646929528548661673
    │   │   ├── 16482838815459722815
    │   │   ├── 16566635769681041959
    │   │   ├── 16794568429287950317
    │   │   ├── 169018594408061907
    │   │   ├── 16903651255070479940
    │   │   ├── 17048893217760640945
    │   │   ├── 17237366963693314057
    │   │   ├── 17289969937782954109
    │   │   ├── 17312867831024802708
    │   │   ├── 17345209962388914516
    │   │   ├── 17466864343550702611
    │   │   ├── 17506921463735247157
    │   │   ├── 17554356383240857188
    │   │   ├── 17575679742354663032
    │   │   ├── 17640725411084265532
    │   │   ├── 17645188016570723924
    │   │   ├── 18041292276276461877
    │   │   ├── 18129829621486296518
    │   │   ├── 18226306909505957550
    │   │   ├── 18341634228165746450
    │   │   ├── 1938552455318741138
    │   │   ├── 2118544973307364111
    │   │   ├── 2148921044289840751
    │   │   ├── 243434165124845988
    │   │   ├── 2441784708933555674
    │   │   ├── 2501835902587268582
    │   │   ├── 2588824627702739471
    │   │   ├── 2729017563529603382
    │   │   ├── 2761729297183989933
    │   │   ├── 2768311851365850285
    │   │   ├── 2794570377334768312
    │   │   ├── 2813002423117173701
    │   │   ├── 2900058224869745118
    │   │   ├── 2977043912531435175
    │   │   ├── 3122253042660474465
    │   │   ├── 3333077357752575753
    │   │   ├── 333380191946270266
    │   │   ├── 3403848502934377844
    │   │   ├── 3467249016898521397
    │   │   ├── 3553594168411385435
    │   │   ├── 3575812334132933646
    │   │   ├── 3588858807263591428
    │   │   ├── 3673989581177532505
    │   │   ├── 3682222976416149103
    │   │   ├── 3708715501436173696
    │   │   ├── 3758130894881863442
    │   │   ├── 377412278522823716
    │   │   ├── 4013192201607604685
    │   │   ├── 4058683650881087572
    │   │   ├── 4113929216074359104
    │   │   ├── 4317883631362990309
    │   │   ├── 4317936614329436877
    │   │   ├── 4344613980423559555
    │   │   ├── 4376271837208569107
    │   │   ├── 4400429036643115684
    │   │   ├── 4417703044594953786
    │   │   ├── 47395663187458043
    │   │   ├── 5014743152429264498
    │   │   ├── 5056012474594590654
    │   │   ├── 5067583929091765677
    │   │   ├── 5072457023483794109
    │   │   ├── 5118410240173347986
    │   │   ├── 5119028593358280739
    │   │   ├── 5479317589811222839
    │   │   ├── 574071137821520899
    │   │   ├── 5904683309445161317
    │   │   ├── 5964706842817127230
    │   │   ├── 6044302948114599209
    │   │   ├── 6153659253117760928
    │   │   ├── 6192057138917064502
    │   │   ├── 6229353331617706721
    │   │   ├── 628505274318108206
    │   │   ├── 6345680962984668575
    │   │   ├── 6351918452344317999
    │   │   ├── 6456746778902264194
    │   │   ├── 6519658667694592989
    │   │   ├── 6613398934592956848
    │   │   ├── 6691480144924722755
    │   │   ├── 6794989488203447037
    │   │   ├── 6883506733477567464
    │   │   ├── 7100032955595026858
    │   │   ├── 7123074160285148696
    │   │   ├── 7242100954526516370
    │   │   ├── 7429312712754302272
    │   │   ├── 7517070702648186273
    │   │   ├── 7550312427718635913
    │   │   ├── 758338994241254973
    │   │   ├── 7671980970824571781
    │   │   ├── 7755701278217091888
    │   │   ├── 7840414760518829610
    │   │   ├── 7924669631391641436
    │   │   ├── 7955320657595195549
    │   │   ├── 7990899347712224429
    │   │   ├── 8036418401048115332
    │   │   ├── 8037476050918678901
    │   │   ├── 8093469952536057944
    │   │   ├── 810504457786274865
    │   │   ├── 8135206538876232427
    │   │   ├── 840683292508838797
    │   │   ├── 8444678174104653949
    │   │   ├── 8848161513893031180
    │   │   ├── 8858926125007748708
    │   │   ├── 8930692905944178952
    │   │   ├── 8931043346137918906
    │   │   ├── 9072146457166947296
    │   │   ├── 9313037173369531352
    │   │   ├── 9358590763270535522
    │   │   ├── 9369109295616568259
    │   │   ├── 9383023001062474042
    │   │   ├── 9724397518860985376
    │   │   ├── 9812131393346840531
    │   │   └── 9864918314232500764
    │   ├── 0.14.9/
    │   │   ├── 10100695278958451438
    │   │   ├── 10177373308723998208
    │   │   ├── 1041745263121478075
    │   │   ├── 1042014105114248694
    │   │   ├── 10448406664848552974
    │   │   ├── 10546077661475623821
    │   │   ├── 10882480562379780118
    │   │   ├── 11706554746488073409
    │   │   ├── 11749030213359857493
    │   │   ├── 11852710529897678681
    │   │   ├── 11972075444629534735
    │   │   ├── 12076541265286759727
    │   │   ├── 1229232418671322630
    │   │   ├── 12325705034155667080
    │   │   ├── 12329335370792706951
    │   │   ├── 12341426402397696899
    │   │   ├── 12353202332574277272
    │   │   ├── 12650116255897205090
    │   │   ├── 12870209208122190389
    │   │   ├── 1309168931970644464
    │   │   ├── 1330616437687086835
    │   │   ├── 13367112018887153408
    │   │   ├── 13532277452285762182
    │   │   ├── 13542513260616769530
    │   │   ├── 13639034180197316901
    │   │   ├── 13803375908507581554
    │   │   ├── 13816847282861078387
    │   │   ├── 13959423021678244090
    │   │   ├── 14012067712763128027
    │   │   ├── 14051233115366704822
    │   │   ├── 14109997285391530487
    │   │   ├── 14148444258421257479
    │   │   ├── 14155034734509453145
    │   │   ├── 14183062521873448625
    │   │   ├── 14329190949419502040
    │   │   ├── 14386761291101543500
    │   │   ├── 14418982129920080608
    │   │   ├── 14581565333361569150
    │   │   ├── 14626546172993530938
    │   │   ├── 14799273837308249659
    │   │   ├── 14949450284990955874
    │   │   ├── 1503601887758976716
    │   │   ├── 15039570147557989863
    │   │   ├── 15119192832379129859
    │   │   ├── 15288463836444036648
    │   │   ├── 15409041636270842993
    │   │   ├── 15410409851508729966
    │   │   ├── 15502651756183598156
    │   │   ├── 15701106259547501469
    │   │   ├── 15729321193008297763
    │   │   ├── 1579826520788760533
    │   │   ├── 16279507192216833645
    │   │   ├── 1634042326760402740
    │   │   ├── 1646929528548661673
    │   │   ├── 16482838815459722815
    │   │   ├── 16575608573502610495
    │   │   ├── 16822033099559886730
    │   │   ├── 17237366963693314057
    │   │   ├── 17339320697896522612
    │   │   ├── 17345209962388914516
    │   │   ├── 17825872412181141924
    │   │   ├── 18226306909505957550
    │   │   ├── 1857616707804703953
    │   │   ├── 2118544973307364111
    │   │   ├── 2148921044289840751
    │   │   ├── 2954420094856117791
    │   │   ├── 3122253042660474465
    │   │   ├── 3333077357752575753
    │   │   ├── 3467249016898521397
    │   │   ├── 3682222976416149103
    │   │   ├── 3758130894881863442
    │   │   ├── 3947171431154967195
    │   │   ├── 3968951908057216515
    │   │   ├── 4013192201607604685
    │   │   ├── 4036761540343009265
    │   │   ├── 4098966814747013921
    │   │   ├── 4317883631362990309
    │   │   ├── 4417703044594953786
    │   │   ├── 4468010855339453654
    │   │   ├── 4604425184476015751
    │   │   ├── 4627899061277802039
    │   │   ├── 5067583929091765677
    │   │   ├── 5118410240173347986
    │   │   ├── 5119028593358280739
    │   │   ├── 5138639101583719892
    │   │   ├── 5173638946889019768
    │   │   ├── 6026693923311099656
    │   │   ├── 6044302948114599209
    │   │   ├── 6111284677380651001
    │   │   ├── 6153659253117760928
    │   │   ├── 6192057138917064502
    │   │   ├── 628505274318108206
    │   │   ├── 6351918452344317999
    │   │   ├── 6519658667694592989
    │   │   ├── 6613398934592956848
    │   │   ├── 6794989488203447037
    │   │   ├── 6818716011485902156
    │   │   ├── 6951385553115987652
    │   │   ├── 7058462010277429938
    │   │   ├── 7426782331673875414
    │   │   ├── 7464150547215967055
    │   │   ├── 758338994241254973
    │   │   ├── 7755701278217091888
    │   │   ├── 77937190642928168
    │   │   ├── 7903090253860333434
    │   │   ├── 7955320657595195549
    │   │   ├── 7970155148515027447
    │   │   ├── 7990899347712224429
    │   │   ├── 8000367390329573400
    │   │   ├── 8036418401048115332
    │   │   ├── 8037476050918678901
    │   │   ├── 8082090212570039900
    │   │   ├── 8093469952536057944
    │   │   ├── 8135206538876232427
    │   │   ├── 8401195445250062694
    │   │   ├── 840683292508838797
    │   │   ├── 8504539883998842081
    │   │   ├── 8531347432845213665
    │   │   ├── 8738876886312416519
    │   │   ├── 8859909730765874230
    │   │   ├── 8870165146888918253
    │   │   ├── 8931043346137918906
    │   │   ├── 9072146457166947296
    │   │   ├── 9092238881387905842
    │   │   ├── 9158798521929108230
    │   │   ├── 9181147240387282448
    │   │   ├── 9223229204832076433
    │   │   ├── 9383023001062474042
    │   │   └── 9503378859264037209
    │   ├── 0.15.0/
    │   │   ├── 10042994639799021489
    │   │   ├── 10379495618747825637
    │   │   ├── 10479187922491003217
    │   │   ├── 10637072185883013634
    │   │   ├── 1065989320665589601
    │   │   ├── 11157942775693612326
    │   │   ├── 11190933343072108981
    │   │   ├── 11263433461498017780
    │   │   ├── 112955056008472458
    │   │   ├── 11304088416816683630
    │   │   ├── 11315925476684551552
    │   │   ├── 11354601986151299062
    │   │   ├── 11492985357930515184
    │   │   ├── 11504191140169200687
    │   │   ├── 11725030719373506234
    │   │   ├── 11756403436689471255
    │   │   ├── 12065062119695948755
    │   │   ├── 12111206466709826162
    │   │   ├── 12142048509056115684
    │   │   ├── 12196047882321707251
    │   │   ├── 12240121748226059906
    │   │   ├── 12251225796867699923
    │   │   ├── 12315251104619142934
    │   │   ├── 12495891517968901452
    │   │   ├── 12992099186535690224
    │   │   ├── 13056634229539985056
    │   │   ├── 14594354942696559954
    │   │   ├── 15245509014003715087
    │   │   ├── 16023002478953264376
    │   │   ├── 16248566078803265174
    │   │   ├── 16275847020217851913
    │   │   ├── 16390845521111071442
    │   │   ├── 16541258382163998777
    │   │   ├── 16694067836466790062
    │   │   ├── 16813478479667804567
    │   │   ├── 1694164595778727970
    │   │   ├── 17128037678956982533
    │   │   ├── 17250304703485929656
    │   │   ├── 17778018538100573620
    │   │   ├── 17975372922217224789
    │   │   ├── 18005287325026348845
    │   │   ├── 18302524416034217768
    │   │   ├── 2151006303821703720
    │   │   ├── 2417695623172178979
    │   │   ├── 2431608079686053646
    │   │   ├── 2849812528721960321
    │   │   ├── 2949971182861940748
    │   │   ├── 3668906458671776397
    │   │   ├── 3935709223696329091
    │   │   ├── 4124706185524066317
    │   │   ├── 5265175010324560580
    │   │   ├── 5893488897200121838
    │   │   ├── 5895500831358623849
    │   │   ├── 5970460982793092399
    │   │   ├── 6161243443964999788
    │   │   ├── 6248304592708061321
    │   │   ├── 6718181685643228495
    │   │   ├── 6867481625637608730
    │   │   ├── 7351573172683674100
    │   │   ├── 7673972669898536331
    │   │   ├── 7749647648788453952
    │   │   ├── 7764419311770839276
    │   │   ├── 8639523402862345931
    │   │   ├── 9122016354919449437
    │   │   ├── 9461813316941272746
    │   │   └── 966693953273524587
    │   ├── .gitignore
    │   └── CACHEDIR.TAG
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
    │   │   ├── uniprot/
    │   │   │   ├── idmapping.yaml
    │   │   │   └── protein.yaml
    │   │   └── publication_type_classification.csv
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
    │   ├── checkpoints/
    │   │   └── composite/
    │   │       ├── composite_composite_publication_277eb092-7001-4366-8980-ba89b5e3b873.json
    │   │       └── composite_composite_publication_959eb38d-159d-4b4b-8904-6722e2a26ea5.json
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
    │       ├── bronze/
    │       │   ├── chembl/
    │       │   │   └── publication/
    │       │   │       ├── 2026-02-08/
    │       │   │       │   ├── batch_2026-02-08_e8afc48f-083d-442a-8662-f7deb1f89fa8.jsonl
    │       │   │       │   ├── batch_2026-02-08_e8afc48f-083d-442a-8662-f7deb1f89fa8.jsonl.zst
    │       │   │       │   ├── batch_2026-02-08_e8afc48f-083d-442a-8662-f7deb1f89fa8.jsonl.zst.meta.json
    │       │   │       │   ├── batch_2026-02-08_f5548941-c707-4e96-b849-e1dcaf0ebece.jsonl
    │       │   │       │   ├── batch_2026-02-08_f5548941-c707-4e96-b849-e1dcaf0ebece.jsonl.zst
    │       │   │       │   └── batch_2026-02-08_f5548941-c707-4e96-b849-e1dcaf0ebece.jsonl.zst.meta.json
    │       │   │       ├── bronze_chembl_publication_dq_report.json
    │       │   │       └── chembl_publication_metadata.yaml
    │       │   ├── crossref/
    │       │   │   └── publication/
    │       │   │       ├── 2026-02-08/
    │       │   │       │   ├── batch_2026-02-08_0411d47c-de78-469e-9f1c-17dc8a05118b.jsonl
    │       │   │       │   ├── batch_2026-02-08_0411d47c-de78-469e-9f1c-17dc8a05118b.jsonl.zst
    │       │   │       │   ├── batch_2026-02-08_0411d47c-de78-469e-9f1c-17dc8a05118b.jsonl.zst.meta.json
    │       │   │       │   ├── batch_2026-02-08_901bbb19-b8b1-4c8f-bf60-fc5e8769d1c8.jsonl
    │       │   │       │   ├── batch_2026-02-08_901bbb19-b8b1-4c8f-bf60-fc5e8769d1c8.jsonl.zst
    │       │   │       │   └── batch_2026-02-08_901bbb19-b8b1-4c8f-bf60-fc5e8769d1c8.jsonl.zst.meta.json
    │       │   │       └── crossref_work_metadata.yaml
    │       │   ├── openalex/
    │       │   │   └── publication/
    │       │   │       ├── 2026-02-08/
    │       │   │       │   ├── batch_2026-02-08_2da2d159-0774-4679-9288-2b5af94b2e28.jsonl
    │       │   │       │   ├── batch_2026-02-08_2da2d159-0774-4679-9288-2b5af94b2e28.jsonl.zst
    │       │   │       │   ├── batch_2026-02-08_2da2d159-0774-4679-9288-2b5af94b2e28.jsonl.zst.meta.json
    │       │   │       │   ├── batch_2026-02-08_3dc105a7-46d7-4c84-a656-25faebb0768c.jsonl
    │       │   │       │   ├── batch_2026-02-08_3dc105a7-46d7-4c84-a656-25faebb0768c.jsonl.zst
    │       │   │       │   └── batch_2026-02-08_3dc105a7-46d7-4c84-a656-25faebb0768c.jsonl.zst.meta.json
    │       │   │       ├── bronze_openalex_publication_dq_report.json
    │       │   │       └── openalex_publication_metadata.yaml
    │       │   ├── pubmed/
    │       │   │   └── publication/
    │       │   │       ├── 2026-02-08/
    │       │   │       │   ├── batch_2026-02-08_115ae54a-5f25-4ffb-b26d-13ccebb70f75.jsonl
    │       │   │       │   ├── batch_2026-02-08_115ae54a-5f25-4ffb-b26d-13ccebb70f75.jsonl.zst
    │       │   │       │   ├── batch_2026-02-08_115ae54a-5f25-4ffb-b26d-13ccebb70f75.jsonl.zst.meta.json
    │       │   │       │   ├── batch_2026-02-08_3d0deda9-1e3d-4d5b-b8e6-ef8a0246acb5.jsonl
    │       │   │       │   ├── batch_2026-02-08_3d0deda9-1e3d-4d5b-b8e6-ef8a0246acb5.jsonl.zst
    │       │   │       │   └── batch_2026-02-08_3d0deda9-1e3d-4d5b-b8e6-ef8a0246acb5.jsonl.zst.meta.json
    │       │   │       └── pubmed_publication_metadata.yaml
    │       │   └── semanticscholar/
    │       │       └── publication/
    │       │           ├── 2026-02-08/
    │       │           │   ├── batch_2026-02-08_26be9242-a694-47be-bf18-818ad3e654e4.jsonl
    │       │           │   ├── batch_2026-02-08_26be9242-a694-47be-bf18-818ad3e654e4.jsonl.zst
    │       │           │   ├── batch_2026-02-08_26be9242-a694-47be-bf18-818ad3e654e4.jsonl.zst.meta.json
    │       │           │   ├── batch_2026-02-08_a264a4b2-0935-40db-aad5-ff7de919fdc3.jsonl
    │       │           │   ├── batch_2026-02-08_a264a4b2-0935-40db-aad5-ff7de919fdc3.jsonl.zst
    │       │           │   └── batch_2026-02-08_a264a4b2-0935-40db-aad5-ff7de919fdc3.jsonl.zst.meta.json
    │       │           ├── bronze_semanticscholar_publication_dq_report.json
    │       │           └── semanticscholar_publication_metadata.yaml
    │       ├── gold/
    │       │   ├── chembl/
    │       │   │   └── publication/
    │       │   ├── composite/
    │       │   │   ├── publication/
    │       │   │   │   ├── _delta_log/
    │       │   │   │   │   ├── 00000000000000000000.json
    │       │   │   │   │   └── 00000000000000000001.json
    │       │   │   │   ├── composite_publication_metadata.yaml
    │       │   │   │   ├── part-00000-7aa22205-b4d7-4c7d-ae7d-0099dac887c3-c000.snappy.parquet
    │       │   │   │   └── part-00000-b589e280-33b3-410f-ae65-0d1130fe6005-c000.snappy.parquet
    │       │   │   └── publication.csv
    │       │   ├── crossref/
    │       │   │   └── publication/
    │       │   ├── openalex/
    │       │   │   └── publication/
    │       │   ├── pubmed/
    │       │   │   └── publication/
    │       │   └── semanticscholar/
    │       │       └── publication/
    │       └── silver/
    │           ├── chembl/
    │           │   └── publication/
    │           │       ├── _delta_log/
    │           │       │   ├── 00000000000000000000.json
    │           │       │   └── 00000000000000000001.json
    │           │       ├── chembl_publication.csv
    │           │       ├── chembl_publication_metadata.yaml
    │           │       ├── part-00000-37700c06-b3bf-45e9-b83d-f62ad22a74c2-c000.snappy.parquet
    │           │       ├── part-00000-c48c99a5-190b-4320-be94-9caade60ee48-c000.snappy.parquet
    │           │       └── silver_chembl_publication_dq_report.json
    │           ├── composite/
    │           │   ├── publication/
    │           │   │   ├── _delta_log/
    │           │   │   │   ├── 00000000000000000000.json
    │           │   │   │   └── 00000000000000000001.json
    │           │   │   ├── composite_publication_metadata.yaml
    │           │   │   ├── part-00000-05f0ef74-5aca-4f2b-87b8-4df0f8bc6694-c000.snappy.parquet
    │           │   │   └── part-00000-22af3e4d-e90a-46e8-a3e6-6ccf12b7d10a-c000.snappy.parquet
    │           │   └── publication.csv
    │           ├── crossref/
    │           │   └── publication/
    │           │       ├── _delta_log/
    │           │       │   ├── 00000000000000000000.json
    │           │       │   └── 00000000000000000001.json
    │           │       ├── crossref_publication.csv
    │           │       ├── crossref_publication_metadata.yaml
    │           │       ├── part-00000-67e1da86-8bda-48af-b287-c6ca3c3b6535-c000.snappy.parquet
    │           │       └── part-00000-c1efa776-0b49-4f64-864c-5daae4853c7b-c000.snappy.parquet
    │           ├── openalex/
    │           │   └── publication/
    │           │       ├── _delta_log/
    │           │       │   ├── 00000000000000000000.json
    │           │       │   └── 00000000000000000001.json
    │           │       ├── openalex_publication.csv
    │           │       ├── openalex_publication_metadata.yaml
    │           │       ├── part-00000-65df4416-4010-4fd5-9449-aaa7587c0935-c000.snappy.parquet
    │           │       ├── part-00000-83aae9a1-4e73-4543-8552-12edd57cac37-c000.snappy.parquet
    │           │       └── silver_openalex_publication_dq_report.json
    │           ├── pubmed/
    │           │   └── publication/
    │           │       ├── _delta_log/
    │           │       │   ├── 00000000000000000000.json
    │           │       │   └── 00000000000000000001.json
    │           │       ├── part-00000-ad8aa6c6-9555-4351-b21e-3ef3d86dd599-c000.snappy.parquet
    │           │       ├── part-00000-ec746427-cce8-44eb-ac7a-f0feeb680ede-c000.snappy.parquet
    │           │       ├── pubmed_publication.csv
    │           │       └── pubmed_publication_metadata.yaml
    │           └── semanticscholar/
    │               └── publication/
    │                   ├── _delta_log/
    │                   │   ├── 00000000000000000000.json
    │                   │   └── 00000000000000000001.json
    │                   ├── part-00000-a1e065d9-b511-40bb-bd8f-cd924fba09d8-c000.snappy.parquet
    │                   ├── part-00000-abacf926-3b98-44e4-898f-f8a0a0a0680f-c000.snappy.parquet
    │                   ├── semanticscholar_publication.csv
    │                   ├── semanticscholar_publication_metadata.yaml
    │                   └── silver_semanticscholar_publication_dq_report.json
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
    │   │   │   ├── ADR-032-unified-http-client.md
    │   │   │   ├── ADR-033-publication-validation-strategy.md
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
    │   ├── 03-data-model/
    │   │   ├── field-catalog-source-pipelines.md
    │   │   ├── field-migration-checklist.md
    │   │   ├── field-naming-unification-matrix.md
    │   │   ├── pipeline-validation-matrix.md
    │   │   └── rf-naming-unification-plan.md
    │   ├── 03-guides/
    │   │   ├── development/
    │   │   │   └── config-schema-guidelines.md
    │   │   ├── add-new-source.md
    │   │   ├── add-pipeline-existing-source.md
    │   │   ├── cleanup-policy.md
    │   │   ├── date-handling.md
    │   │   ├── dq-configuration.md
    │   │   ├── file-path-audit-report.md
    │   │   ├── getting-started.md
    │   │   ├── local-storage-layout.md
    │   │   ├── metrics-monitoring.md
    │   │   ├── migration-5.9-to-5.14.md
    │   │   ├── pipeline-configuration.md
    │   │   ├── pipeline-lifecycle.md
    │   │   ├── publication-validation-guide.md
    │   │   ├── quick-start.md
    │   │   ├── registry-pattern.md
    │   │   ├── running-pipelines.md
    │   │   ├── silver-schema-testing-guide.md
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
    │   │   │   │   ├── adapters-common.md
    │   │   │   │   ├── adapters.md
    │   │   │   │   ├── observability.md
    │   │   │   │   ├── storage.md
    │   │   │   │   └── unified-http-client.md
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
    │   ├── adr/
    │   │   └── ADR-030-publication-field-unification.md
    │   ├── analysis/
    │   │   ├── PUBLICATION_TYPE_NORMALIZATION_ANALYSIS.md
    │   │   ├── chembl-validation-matrix.md
    │   │   ├── crossref-validation-matrix.md
    │   │   ├── openalex-validation-matrix.md
    │   │   ├── pubmed-validation-matrix.md
    │   │   └── semanticscholar-validation-matrix.md
    │   ├── assets/
    │   │   └── javascripts/
    │   │       └── mermaid-init.js
    │   ├── audits/
    │   │   ├── architecture-audit-2026-02-07.md
    │   │   ├── architecture-audit-2026-02-10.md
    │   │   ├── audit-correction-plan-2026-02-11.md
    │   │   ├── documentation-audit-2026-02-11.md
    │   │   └── documentation-audit-full-2026-02-11.md
    │   ├── providers/
    │   │   └── chembl.md
    │   ├── site/
    │   │   ├── 00-map/
    │   │   │   └── index.html
    │   │   ├── 00-project_rules/
    │   │   │   ├── 00-rules-summary/
    │   │   │   │   └── index.html
    │   │   │   ├── 01-project-rules/
    │   │   │   │   └── index.html
    │   │   │   ├── 02-user-rules/
    │   │   │   │   └── index.html
    │   │   │   ├── 03-file-policy/
    │   │   │   │   └── index.html
    │   │   │   ├── 04-extending-bioetl/
    │   │   │   │   └── index.html
    │   │   │   ├── 05-cleanup-policy/
    │   │   │   │   └── index.html
    │   │   │   ├── 06-rules-mapping/
    │   │   │   │   └── index.html
    │   │   │   └── 07-consistency-check/
    │   │   │       └── index.html
    │   │   ├── 02-architecture/
    │   │   │   ├── 01-domain-layer/
    │   │   │   │   └── index.html
    │   │   │   ├── 02-application-layer/
    │   │   │   │   └── index.html
    │   │   │   ├── 03-infrastructure-layer/
    │   │   │   │   └── index.html
    │   │   │   ├── 04-interfaces-layer/
    │   │   │   │   └── index.html
    │   │   │   ├── 05-composition-layer/
    │   │   │   │   └── index.html
    │   │   │   ├── container-diagram/
    │   │   │   │   └── index.html
    │   │   │   ├── data-flow/
    │   │   │   │   └── index.html
    │   │   │   ├── data-layers/
    │   │   │   │   └── index.html
    │   │   │   ├── decisions/
    │   │   │   │   ├── ADR-001-delta-lake-vs-parquet/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-002-medallion-architecture/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-003-redis-for-distributed-locking/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-004-pydantic-vs-dataclasses/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-005-composition-layer-separation/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-006-logger-metrics-ports/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-007-circuit-breaker-implementation/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-008-graceful-shutdown-strategy/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-009-paginated-fetcher-mixin/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-010-local-only-deployment/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-011-remove-watermark-mechanism/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-012-storage-clear-contract-and-run-id/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-013-async-storage-cleanup/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-014-deterministic-writes/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-015-pipeline-services-lifecycle/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-016-error-handling-strategy/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-017-observability-architecture/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-018-gold-strict-validation/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── ADR-019-observability-port-enforcement/
    │   │   │   │   │   └── index.html
    │   │   │   │   └── ADR-020-basepipeline-decomposition/
    │   │   │   │       └── index.html
    │   │   │   ├── diagrams/
    │   │   │   │   ├── 00-diagramming-policy/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── 01-high-level.mermaid
    │   │   │   │   ├── 02-medallion.mermaid
    │   │   │   │   ├── 03-pipeline-sequence.puml
    │   │   │   │   ├── 04-error-flow.mermaid
    │   │   │   │   ├── 05-layers-interaction.mermaid
    │   │   │   │   ├── 05-locking.puml
    │   │   │   │   ├── 06-pipeline-execution.mermaid
    │   │   │   │   ├── 07-medallion-flow.mermaid
    │   │   │   │   └── index.html
    │   │   │   ├── observability-layers/
    │   │   │   │   └── index.html
    │   │   │   └── system-context/
    │   │   │       └── index.html
    │   │   ├── 03-guides/
    │   │   │   ├── add-new-source/
    │   │   │   │   └── index.html
    │   │   │   ├── add-pipeline-existing-source/
    │   │   │   │   └── index.html
    │   │   │   ├── getting-started/
    │   │   │   │   └── index.html
    │   │   │   ├── local-storage-layout/
    │   │   │   │   └── index.html
    │   │   │   ├── pipeline-lifecycle/
    │   │   │   │   └── index.html
    │   │   │   ├── quick-start/
    │   │   │   │   └── index.html
    │   │   │   ├── registry-pattern/
    │   │   │   │   └── index.html
    │   │   │   ├── running-pipelines/
    │   │   │   │   └── index.html
    │   │   │   ├── testing/
    │   │   │   │   └── index.html
    │   │   │   └── troubleshooting/
    │   │   │       └── index.html
    │   │   ├── 04-reference/
    │   │   │   ├── api/
    │   │   │   │   ├── application/
    │   │   │   │   │   ├── core/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── pipelines/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── transformers/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── composition/
    │   │   │   │   │   ├── bootstrap/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── factories/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── domain/
    │   │   │   │   │   ├── entities/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── exceptions/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── ports/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── types/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── infrastructure/
    │   │   │   │   │   ├── adapters/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── observability/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   ├── storage/
    │   │   │   │   │   │   └── index.html
    │   │   │   │   │   └── index.html
    │   │   │   │   └── index.html
    │   │   │   ├── cli/
    │   │   │   │   └── index.html
    │   │   │   └── pipelines/
    │   │   │       ├── chembl_activity/
    │   │   │       │   └── index.html
    │   │   │       └── chembl_assay/
    │   │   │           └── index.html
    │   │   ├── 05-operations/
    │   │   │   └── runbooks/
    │   │   │       ├── data-recovery/
    │   │   │       │   └── index.html
    │   │   │       ├── incident-response/
    │   │   │       │   └── index.html
    │   │   │       ├── observability-checklist/
    │   │   │       │   └── index.html
    │   │   │       ├── scaling/
    │   │   │       │   └── index.html
    │   │   │       └── index.html
    │   │   ├── ARCHIVED_AUDIT_REPORT/
    │   │   │   └── index.html
    │   │   ├── CHANGELOG/
    │   │   │   └── index.html
    │   │   ├── CONSOLIDATED_ARCHITECTURE_AUDIT/
    │   │   │   └── index.html
    │   │   ├── CONSOLIDATED_REFACTORING_ANALYSIS/
    │   │   │   └── index.html
    │   │   ├── CONSOLIDATED_REFACTORING_PLAN/
    │   │   │   └── index.html
    │   │   ├── REFACTORING_PLAN/
    │   │   │   └── index.html
    │   │   ├── REFACTORING_PLAN_BRONZE_VALIDATION/
    │   │   │   └── index.html
    │   │   ├── REQUIREMENTS/
    │   │   │   └── index.html
    │   │   ├── RULES/
    │   │   │   └── index.html
    │   │   ├── assets/
    │   │   │   ├── javascripts/
    │   │   │   │   ├── lunr/
    │   │   │   │   │   ├── min/
    │   │   │   │   │   │   ├── lunr.ar.min.js
    │   │   │   │   │   │   ├── lunr.da.min.js
    │   │   │   │   │   │   ├── lunr.de.min.js
    │   │   │   │   │   │   ├── lunr.du.min.js
    │   │   │   │   │   │   ├── lunr.el.min.js
    │   │   │   │   │   │   ├── lunr.es.min.js
    │   │   │   │   │   │   ├── lunr.fi.min.js
    │   │   │   │   │   │   ├── lunr.fr.min.js
    │   │   │   │   │   │   ├── lunr.he.min.js
    │   │   │   │   │   │   ├── lunr.hi.min.js
    │   │   │   │   │   │   ├── lunr.hu.min.js
    │   │   │   │   │   │   ├── lunr.hy.min.js
    │   │   │   │   │   │   ├── lunr.it.min.js
    │   │   │   │   │   │   ├── lunr.ja.min.js
    │   │   │   │   │   │   ├── lunr.jp.min.js
    │   │   │   │   │   │   ├── lunr.kn.min.js
    │   │   │   │   │   │   ├── lunr.ko.min.js
    │   │   │   │   │   │   ├── lunr.multi.min.js
    │   │   │   │   │   │   ├── lunr.nl.min.js
    │   │   │   │   │   │   ├── lunr.no.min.js
    │   │   │   │   │   │   ├── lunr.pt.min.js
    │   │   │   │   │   │   ├── lunr.ro.min.js
    │   │   │   │   │   │   ├── lunr.ru.min.js
    │   │   │   │   │   │   ├── lunr.sa.min.js
    │   │   │   │   │   │   ├── lunr.stemmer.support.min.js
    │   │   │   │   │   │   ├── lunr.sv.min.js
    │   │   │   │   │   │   ├── lunr.ta.min.js
    │   │   │   │   │   │   ├── lunr.te.min.js
    │   │   │   │   │   │   ├── lunr.th.min.js
    │   │   │   │   │   │   ├── lunr.tr.min.js
    │   │   │   │   │   │   ├── lunr.vi.min.js
    │   │   │   │   │   │   └── lunr.zh.min.js
    │   │   │   │   │   ├── tinyseg.js
    │   │   │   │   │   └── wordcut.js
    │   │   │   │   ├── workers/
    │   │   │   │   │   ├── search.2c215733.min.js
    │   │   │   │   │   └── search.2c215733.min.js.map
    │   │   │   │   ├── bundle.79ae519e.min.js
    │   │   │   │   ├── bundle.79ae519e.min.js.map
    │   │   │   │   └── mermaid-init.js
    │   │   │   ├── stylesheets/
    │   │   │   │   ├── main.484c7ddc.min.css
    │   │   │   │   ├── main.484c7ddc.min.css.map
    │   │   │   │   ├── palette.ab4e12ef.min.css
    │   │   │   │   └── palette.ab4e12ef.min.css.map
    │   │   │   └── _mkdocstrings.css
    │   │   ├── contracts/
    │   │   │   ├── gold/
    │   │   │   │   ├── activity.json
    │   │   │   │   ├── assay.json
    │   │   │   │   └── molecule.json
    │   │   │   ├── observability/
    │   │   │   │   └── index.html
    │   │   │   ├── chembl_activity_gold.json
    │   │   │   ├── chembl_assay_gold.json
    │   │   │   ├── pubchem_compound_gold.json
    │   │   │   ├── pubmed_publication_gold.json
    │   │   │   └── uniprot_protein_gold.json
    │   │   ├── providers/
    │   │   │   ├── chembl/
    │   │   │   │   ├── activity/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── assay/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── document/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── molecule/
    │   │   │   │   │   └── index.html
    │   │   │   │   ├── target/
    │   │   │   │   │   └── index.html
    │   │   │   │   └── target_component/
    │   │   │   │       └── index.html
    │   │   │   ├── pubchem/
    │   │   │   │   └── compound/
    │   │   │   │       └── index.html
    │   │   │   ├── pubmed/
    │   │   │   │   └── publication/
    │   │   │   │       └── index.html
    │   │   │   └── uniprot/
    │   │   │       └── protein/
    │   │   │           └── index.html
    │   │   ├── search/
    │   │   │   └── search_index.json
    │   │   ├── 404.html
    │   │   ├── index.html
    │   │   ├── objects.inv
    │   │   ├── sitemap.xml
    │   │   └── sitemap.xml.gz
    │   └── testing/
    │       └── 05-test-final.md
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
    │   ├── documentation_audit/
    │   │   ├── document_update_prompts.md
    │   │   ├── document_update_prompts_high_risk.md
    │   │   ├── sentence_audit_full.csv
    │   │   └── sentence_audit_summary.md
    │   ├── inventory/
    │   │   ├── INV-001/
    │   │   │   └── inventory-report.md
    │   │   ├── INV-20260212-0640/
    │   │   │   ├── collect_inventory.py
    │   │   │   ├── dependency-map.json
    │   │   │   ├── duplicates.json
    │   │   │   ├── inventory-report.md
    │   │   │   ├── objects.json
    │   │   │   └── references.json
    │   │   ├── inventory-report.md
    │   │   └── modification-prompts.md
    │   ├── 04-refactoring-log.md
    │   ├── application_merged.md
    │   ├── composition_merged.md
    │   ├── configs_merged.md
    │   ├── documentation-audit-report.md
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
    │   ├── debug_pandera.py
    │   ├── dq_baseline_update.py
    │   ├── lint_terminology.py
    │   ├── naming_audit.py
    │   ├── render_diagrams.py
    │   ├── salt_rotate.py
    │   ├── sentence_doc_audit.py
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
    │   │   │   │   ├── entity_id.py
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
    │   │   │   │   │   ├── activity_transformer.py
    │   │   │   │   │   ├── assay_parameters_transformer.py
    │   │   │   │   │   ├── assay_transformer.py
    │   │   │   │   │   ├── base_chembl_transformer.py
    │   │   │   │   │   ├── cell_line_transformer.py
    │   │   │   │   │   ├── compound_record_transformer.py
    │   │   │   │   │   ├── molecule_transformer.py
    │   │   │   │   │   ├── protein_class_transformer.py
    │   │   │   │   │   ├── publication_similarity_transformer.py
    │   │   │   │   │   ├── publication_term_transformer.py
    │   │   │   │   │   ├── publication_transformer.py
    │   │   │   │   │   ├── subcellular_fraction_transformer.py
    │   │   │   │   │   ├── target_component_transformer.py
    │   │   │   │   │   ├── target_transformer.py
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
    │   │   │   ├── _bootstrap/
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
    │   │   │   ├── config/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── _converters.py
    │   │   │   │   ├── dq.py
    │   │   │   │   ├── memory.py
    │   │   │   │   ├── pipeline.py
    │   │   │   │   ├── runtime.py
    │   │   │   │   ├── table.py
    │   │   │   │   └── validation.py
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
    │   │   │   │   ├── range_filter.py
    │   │   │   │   └── silver_config.py
    │   │   │   ├── mapping/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── activity_fields.py
    │   │   │   │   ├── molecule_fields.py
    │   │   │   │   ├── publication_fields.py
    │   │   │   │   └── publication_type_classification.py
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
    │   │   │   │   ├── observability.py
    │   │   │   │   ├── pii.py
    │   │   │   │   ├── quarantine.py
    │   │   │   │   ├── resilience.py
    │   │   │   │   ├── runner.py
    │   │   │   │   ├── serialization.py
    │   │   │   │   ├── shutdown.py
    │   │   │   │   ├── storage.py
    │   │   │   │   └── validation.py
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
    │   │   │   │   │   ├── protein_classification.py
    │   │   │   │   │   ├── publication.py
    │   │   │   │   │   ├── publication_similarity.py
    │   │   │   │   │   ├── publication_term.py
    │   │   │   │   │   ├── target.py
    │   │   │   │   │   └── target_component.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── publication_base.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── publication.py
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
    │   │   │   │   │   ├── _annotations.py
    │   │   │   │   │   ├── _core.py
    │   │   │   │   │   ├── _features.py
    │   │   │   │   │   ├── _xrefs.py
    │   │   │   │   │   ├── idmapping.py
    │   │   │   │   │   └── protein.py
    │   │   │   │   ├── __init__.py
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
    │   │   │   │   │   ├── constants.py
    │   │   │   │   │   ├── entity_mapper.py
    │   │   │   │   │   ├── fetch_strategies.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── pubmed/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── _fetch.py
    │   │   │   │   │   ├── _health.py
    │   │   │   │   │   ├── _search.py
    │   │   │   │   │   ├── constants.py
    │   │   │   │   │   ├── fallback.py
    │   │   │   │   │   ├── models.py
    │   │   │   │   │   ├── pubmed_client.py
    │   │   │   │   │   └── xml_processor.py
    │   │   │   │   ├── semanticscholar/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── adapter.py
    │   │   │   │   │   ├── constants.py
    │   │   │   │   │   └── fallback.py
    │   │   │   │   ├── uniprot/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   ├── client.py
    │   │   │   │   │   ├── fasta_parser.py
    │   │   │   │   │   ├── idmapping_client.py
    │   │   │   │   │   └── models.py
    │   │   │   │   ├── __init__.py
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
    │   │   │   │   ├── alerting/
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
    │   │   │   │   ├── delta_writer.py
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
    │   │   ├── test_antipatterns.py
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
    │   │   ├── test_documentation_sync.py
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
    │   │   ├── test_naming_conventions.py
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
    │   │   ├── test_publication_type_sync.py
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
    │   │   ├── silver_schemas/
    │   │   │   ├── snapshots/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── chembl_activity_schema.json
    │   │   │   │   ├── chembl_assay_parameters_schema.json
    │   │   │   │   ├── chembl_assay_schema.json
    │   │   │   │   ├── chembl_cell_line_schema.json
    │   │   │   │   ├── chembl_compound_record_schema.json
    │   │   │   │   ├── chembl_molecule_schema.json
    │   │   │   │   ├── chembl_protein_class_schema.json
    │   │   │   │   ├── chembl_publication_schema.json
    │   │   │   │   ├── chembl_publication_similarity_schema.json
    │   │   │   │   ├── chembl_publication_term_schema.json
    │   │   │   │   ├── chembl_target_component_schema.json
    │   │   │   │   ├── chembl_target_schema.json
    │   │   │   │   ├── crossref_publication_schema.json
    │   │   │   │   ├── openalex_publication_schema.json
    │   │   │   │   ├── pubchem_compound_schema.json
    │   │   │   │   ├── pubmed_publication_schema.json
    │   │   │   │   ├── semanticscholar_publication_schema.json
    │   │   │   │   ├── uniprot_idmapping_schema.json
    │   │   │   │   └── uniprot_protein_schema.json
    │   │   │   ├── FIX_PLAN.md
    │   │   │   ├── README.md
    │   │   │   ├── SKIPPED_TESTS_ANALYSIS.md
    │   │   │   ├── TEST_RESULTS.md
    │   │   │   ├── __init__.py
    │   │   │   ├── conftest.py
    │   │   │   ├── test_field_types.py
    │   │   │   ├── test_naming_conventions.py
    │   │   │   ├── test_schema_stability.py
    │   │   │   └── test_validations.py
    │   │   ├── __init__.py
    │   │   ├── conftest.py
    │   │   ├── test_chembl_contract.py
    │   │   ├── test_pubchem_contract.py
    │   │   ├── test_publication_schema_contracts.py
    │   │   ├── test_pubmed_contract.py
    │   │   └── test_uniprot_contract.py
    │   ├── e2e/
    │   │   ├── cassettes/
    │   │   │   ├── test_backfill_clears_silver_only.yaml
    │   │   │   ├── test_chembl_and_uniprot_sequential_run.yaml
    │   │   │   ├── test_failed_run_preserves_partial_data.yaml
    │   │   │   ├── test_multiple_chembl_entities_parallel_safe.yaml
    │   │   │   ├── test_rebuild_clears_existing_data.yaml
    │   │   │   ├── test_vacuum_respects_retention_days.yaml
    │   │   │   └── test_vacuum_runs_after_successful_pipeline.yaml
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
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_error_handling
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_error_handling.yaml
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_happy_path
    │   │   │   │   ├── TestChemblActivityPipeline.test_chembl_activity_happy_path.yaml
    │   │   │   │   ├── TestChemblAdapter.test_fetch_activities
    │   │   │   │   ├── TestChemblAdapter.test_fetch_activities.yaml
    │   │   │   │   ├── TestChemblAdapter.test_get_entity_count
    │   │   │   │   ├── TestChemblAdapter.test_get_entity_count.yaml
    │   │   │   │   ├── TestChemblAdapter.test_health_check
    │   │   │   │   ├── TestChemblAdapter.test_health_check.yaml
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_happy_path
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_happy_path.yaml
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_source_fields
    │   │   │   │   ├── TestChemblCellLinePipeline.test_chembl_cell_line_source_fields.yaml
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_error_handling
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_error_handling.yaml
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_happy_path
    │   │   │   │   ├── TestChemblCompoundRecordPipeline.test_chembl_compound_record_happy_path.yaml
    │   │   │   │   ├── TestChemblTargetComponentPipeline.test_chembl_target_component_happy_path
    │   │   │   │   ├── TestChemblTargetComponentPipeline.test_chembl_target_component_happy_path.yaml
    │   │   │   │   ├── test_all_chembl_pipelines_chain
    │   │   │   │   ├── test_all_chembl_pipelines_chain.yaml
    │   │   │   │   ├── test_chembl_activity_full_cycle
    │   │   │   │   ├── test_chembl_activity_full_cycle.yaml
    │   │   │   │   ├── test_chembl_assay_confidence_score
    │   │   │   │   ├── test_chembl_assay_confidence_score.yaml
    │   │   │   │   ├── test_chembl_assay_full_cycle
    │   │   │   │   ├── test_chembl_assay_full_cycle.yaml
    │   │   │   │   ├── test_chembl_assay_metadata_fields
    │   │   │   │   ├── test_chembl_assay_metadata_fields.yaml
    │   │   │   │   ├── test_chembl_molecule_full_cycle
    │   │   │   │   ├── test_chembl_molecule_full_cycle.yaml
    │   │   │   │   ├── test_chembl_molecule_structural_fields
    │   │   │   │   ├── test_chembl_molecule_structural_fields.yaml
    │   │   │   │   ├── test_chembl_molecule_then_activity_chain
    │   │   │   │   ├── test_chembl_molecule_then_activity_chain.yaml
    │   │   │   │   ├── test_chembl_publication_full_cycle
    │   │   │   │   ├── test_chembl_publication_full_cycle.yaml
    │   │   │   │   ├── test_chembl_publication_metadata_fields
    │   │   │   │   ├── test_chembl_publication_metadata_fields.yaml
    │   │   │   │   ├── test_chembl_publication_term_full_cycle
    │   │   │   │   ├── test_chembl_publication_term_full_cycle.yaml
    │   │   │   │   ├── test_chembl_publication_term_mesh_fields
    │   │   │   │   ├── test_chembl_publication_term_mesh_fields.yaml
    │   │   │   │   ├── test_chembl_publication_term_types
    │   │   │   │   ├── test_chembl_publication_term_types.yaml
    │   │   │   │   ├── test_chembl_target_cross_references
    │   │   │   │   ├── test_chembl_target_cross_references.yaml
    │   │   │   │   ├── test_chembl_target_full_cycle
    │   │   │   │   ├── test_chembl_target_full_cycle.yaml
    │   │   │   │   ├── test_chembl_target_then_activity_chain
    │   │   │   │   ├── test_chembl_target_then_activity_chain.yaml
    │   │   │   │   ├── test_parallel_independent_pipelines
    │   │   │   │   ├── test_parallel_independent_pipelines.yaml
    │   │   │   │   ├── test_pipeline_idempotency
    │   │   │   │   ├── test_pipeline_idempotency.yaml
    │   │   │   │   ├── test_pipeline_isolation
    │   │   │   │   ├── test_pipeline_isolation.yaml
    │   │   │   │   ├── test_pipeline_resume_from_checkpoint
    │   │   │   │   ├── test_pipeline_resume_from_checkpoint.yaml
    │   │   │   │   ├── test_rerun_same_pipeline_twice
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
    │   │   │   │   └── pipelines/
    │   │   │   ├── openalex/
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_batch_dois
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_batch_dois.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_by_doi
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_by_doi.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_with_fallback
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_filtered_with_fallback.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_with_query
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_fetch_with_query.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_health_check
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_health_check.yaml
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_title_only_lookup
    │   │   │   │   ├── TestOpenAlexAdapterIntegration.test_title_only_lookup.yaml
    │   │   │   │   ├── TestOpenAlexAdapterRateLimiting.test_rate_limiting_not_exceeded
    │   │   │   │   └── TestOpenAlexAdapterRateLimiting.test_rate_limiting_not_exceeded.yaml
    │   │   │   ├── pubchem/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── test_pubchem_compound_full_cycle
    │   │   │   │   ├── test_pubchem_compound_full_cycle.yaml
    │   │   │   │   ├── test_pubchem_compound_pipeline.yaml
    │   │   │   │   ├── test_pubchem_compound_query_filter
    │   │   │   │   ├── test_pubchem_compound_query_filter.yaml
    │   │   │   │   ├── test_pubchem_compound_structural_fields
    │   │   │   │   └── test_pubchem_compound_structural_fields.yaml
    │   │   │   ├── pubmed/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── test_fetch_publications.yaml
    │   │   │   │   ├── test_health_check.yaml
    │   │   │   │   ├── test_pubmed_publication_classification_fields
    │   │   │   │   ├── test_pubmed_publication_classification_fields.yaml
    │   │   │   │   ├── test_pubmed_publication_date_fields
    │   │   │   │   ├── test_pubmed_publication_date_fields.yaml
    │   │   │   │   ├── test_pubmed_publication_full_cycle
    │   │   │   │   ├── test_pubmed_publication_full_cycle.yaml
    │   │   │   │   ├── test_pubmed_publication_identifier_fields
    │   │   │   │   ├── test_pubmed_publication_identifier_fields.yaml
    │   │   │   │   ├── test_pubmed_publication_journal_fields
    │   │   │   │   └── test_pubmed_publication_journal_fields.yaml
    │   │   │   ├── semanticscholar/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_batch_dois
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_batch_dois.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_by_doi
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_by_doi.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_filtered_with_fallback
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_filtered_with_fallback.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_with_query
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_health_check
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_health_check.yaml
    │   │   │   │   ├── TestSemanticScholarAdapterIntegration.test_title_only_lookup
    │   │   │   │   └── TestSemanticScholarAdapterIntegration.test_title_only_lookup.yaml
    │   │   │   ├── uniprot/
    │   │   │   │   ├── .gitkeep
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_fetch_proteins
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_fetch_proteins.yaml
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_health_check
    │   │   │   │   ├── TestUniProtAdapterIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtClientIntegration.test_fetch_proteins.yaml
    │   │   │   │   ├── TestUniProtClientIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_health_check
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_health_check.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_mixed_results
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_mixed_results.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_multiple_ids
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_multiple_ids.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_not_found_id
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_not_found_id.yaml
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_single_id
    │   │   │   │   ├── TestUniProtIDMappingIntegration.test_map_single_id.yaml
    │   │   │   │   ├── test_uniprot_protein_full_cycle
    │   │   │   │   ├── test_uniprot_protein_full_cycle.yaml
    │   │   │   │   ├── test_uniprot_protein_metadata_fields
    │   │   │   │   ├── test_uniprot_protein_metadata_fields.yaml
    │   │   │   │   ├── test_uniprot_protein_sequence_fields
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
    │   ├── helpers/
    │   │   ├── __init__.py
    │   │   └── adapter_error_logging.py
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
    │   │   │   ├── test_pubmed_coverage.py
    │   │   │   ├── test_pubmed_edge_cases.py
    │   │   │   ├── test_semanticscholar.py
    │   │   │   ├── test_uniprot.py
    │   │   │   └── test_uniprot_idmapping.py
    │   │   ├── chembl/
    │   │   │   ├── __init__.py
    │   │   │   └── test_activity_extraction_params.py
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
    │   │   ├── conftest.py
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
    │   │   │   │   │   ├── test_assembly.py
    │   │   │   │   │   └── test_resolve_bronze_opts.py
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
    │   │   │   ├── mapping/
    │   │   │   │   ├── __init__.py
    │   │   │   │   └── test_publication_type_classification.py
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
    │   │   │   │   │   ├── test_chembl_publication_validation.py
    │   │   │   │   │   └── test_schemas.py
    │   │   │   │   ├── common/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_publication_base.py
    │   │   │   │   ├── crossref/
    │   │   │   │   │   ├── __init__.py
    │   │   │   │   │   └── test_crossref_publication_validation.py
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
    │   │   │   │   ├── test_inchi_key_validation.py
    │   │   │   │   ├── test_json_validators.py
    │   │   │   │   └── test_year_validation.py
    │   │   │   ├── services/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_activity_aggregator.py
    │   │   │   │   ├── test_data_normalization_service.py
    │   │   │   │   ├── test_dq_metrics_calculator.py
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
    │   │   │   │   │   └── test_chembl_client_coverage.py
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
    │   │   │   │   ├── alerting/
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
    │   │   │   │   ├── test_silver_pipeline_contracts.py
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
    ├── .cursor_tmp_gitshow_err.txt
    ├── .cursor_tmp_head_activity_transformer.py
    ├── .cursor_tmp_head_author_extractors.py
    ├── .cursor_tmp_head_molecule_fields.py
    ├── .cursor_tmp_head_pubchem_entity_mapper.py
    ├── .cursor_tmp_head_silver.py
    ├── .cursor_tmp_pytest1.txt
    ├── .cursor_tmp_pytest_after_fix.txt
    ├── .cursor_tmp_pytest_after_fix2.txt
    ├── .cursor_tmp_pytest_fetch_strat.txt
    ├── .cursor_tmp_pytest_final_checks.txt
    ├── .cursor_tmp_pytest_full.txt
    ├── .cursor_tmp_pytest_full_after_yes.txt
    ├── .cursor_tmp_pytest_gold_single.txt
    ├── .cursor_tmp_pytest_regression_check.txt
    ├── .cursor_tmp_pytest_regression_check2.txt
    ├── .cursor_tmp_pytest_regression_check3.txt
    ├── .cursor_tmp_pytest_regression_check4.txt
    ├── .cursor_tmp_pytest_silver_contracts.txt
    ├── .cursor_tmp_pytest_subset.txt
    ├── .cursor_tmp_pytest_subset2.txt
    ├── .cursor_tmp_schema_cols.txt
    ├── .editorconfig
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
    ├── TestChEMBLPipelineE2E.test_chembl_activity_full_run
    ├── all_fixtures.txt
    ├── commitlint.config.js
    ├── coverage.json
    ├── dev_setup.sh
    ├── log_test.txt
    ├── mkdocs.yml
    ├── nul
    ├── pyproject.toml
    ├── pytest.ini
    ├── requirements.txt
    ├── test_backfill_clears_silver_only
    ├── test_chembl_and_uniprot_sequential_run
    ├── test_failed_run_preserves_partial_data
    ├── test_health_check
    ├── test_multiple_chembl_entities_parallel_safe
    ├── test_output.txt
    ├── test_pipeline_idempotency
    ├── test_pipeline_resume_after_failure
    ├── test_pubchem_compound_pipeline
    ├── test_rebuild_clears_existing_data
    ├── test_vacuum_respects_retention_days
    ├── test_vacuum_runs_after_successful_pipeline
    ├── unified_classification.csv
    ├── unified_classification.xlsx
    └── uv.lock
```

**Statistics:**
- Directories: 779
- Files: 6050
- Total items: 6829
