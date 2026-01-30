let
    fnCrossrefDoisByISSN =
        (inputTable as any, optional MaxPages as number) as table =>
        let

            PagesLimit = if MaxPages = null then 50 else MaxPages,
            BaseUrl = "https://api.crossref.org/works",

            GetPage = (issn as text, cursor as text) as record =>
                let
                    Json =
                        Json.Document(
                            Web.Contents(
                                BaseUrl,
                                [
                                    Query = [
                                        filter = "issn:" & issn & ",type:journal-article",
                                        rows = "1000",
                                        cursor = cursor,
                                        select = "DOI"
                                    ],
                                    Headers = [
                                        #"User-Agent" =
                                            "PowerQuery-Crossref/1.0 (mailto:your@email)"
                                    ]
                                ]
                            )
                        ),
                    Msg = Json[message]
                in
                    [
                        Items = Msg[items],
                        Next = Msg[#"next-cursor"]
                    ],

            FetchDoisByIssn = (issn as nullable text) as list =>
                if issn = null or Text.Trim(issn) = "" then
                    {}
                else
                    List.Accumulate(
                        {1..PagesLimit},
                        [Items = {}, Cursor = "*"],
                        (state, _) =>
                            let
                                Page = GetPage(issn, state[Cursor])
                            in
                                if List.Count(Page[Items]) = 0 then
                                    state
                                else [
                                    Items = state[Items] & Page[Items],
                                    Cursor = Page[Next]
                                ]
                    )[Items],

            FetchDoisForRow = (issnInput as any) as list =>
                let
                    IssnList =
                        if issnInput = null then
                            {}
                        else if Value.Is(issnInput, type list) then
                            issnInput
                        else
                            {issnInput},
                    CleanIssnList =
                        List.Select(
                            List.Transform(IssnList, each if _ = null then null else Text.Trim(Text.From(_))),
                            each _ <> null and _ <> ""
                        ),
                    Combined =
                        List.Combine(
                            List.Transform(CleanIssnList, each FetchDoisByIssn(_))
                        )
                in
                    Combined,

            WithDois =
                Table.AddColumn(
                    inputTable,
                    "DOIs",
                    each FetchDoisForRow([ISSN]),
                    type list
                )
        in
            WithDois
in
    fnCrossrefDoisByISSN
