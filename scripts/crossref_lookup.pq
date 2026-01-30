let
    // Function definition
    fnCrossrefDoisByISSN = (issn as text, optional MaxPages as number) as table =>
        let
            PagesLimit = if MaxPages = null then 50 else MaxPages,
            BaseUrl = "https://api.crossref.org/works",

            // Helper to fetch a single page
            GetPage = (cursor as text) as record =>
                let
                    // Use Web.Contents to handle URL encoding properly
                    Source = Web.Contents(
                        BaseUrl,
                        [
                            Query = [
                                filter = "issn:" & issn & ",type:journal-article",
                                rows = "1000",
                                cursor = cursor,
                                select = "DOI"
                            ],
                            // Add User-Agent to be polite
                            Headers = [
                                #"User-Agent" = "PowerQuery-Crossref/1.0 (mailto:your@email)"
                            ]
                        ]
                    ),
                    Json = Json.Document(Source),
                    Msg = Json[message]
                in
                    [
                        Items = Msg[items],
                        NextCursor = Msg[#"next-cursor"]
                    ],

            // Use List.Generate for efficient pagination
            Pages = List.Generate(
                () => [i = 0, data = GetPage("*")], // Initial state
                each [i] < PagesLimit and List.Count([data][Items]) > 0, // Condition to continue
                each [i = [i] + 1, data = GetPage([data][NextCursor])], // Next step
                each [data][Items] // Output selector (list of items)
            ),

            // Combine all pages into one list
            CombinedList = List.Combine(Pages),

            // Convert to Table
            Tbl = Table.FromList(
                CombinedList,
                Splitter.SplitByNothing(),
                {"rec"},
                null,
                ExtraValues.Error
            ),

            // Expand the record column
            Expanded = Table.ExpandRecordColumn(Tbl, "rec", {"DOI"}),
            Distinct = Table.Distinct(Expanded)
        in
            Distinct,

    // Main Query Logic
    Source = Excel.CurrentWorkbook(){[Name="Table1"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Column1", type text}}),
    #"Promoted Headers" = Table.PromoteHeaders(#"Changed Type", [PromoteAllScalars=true]),
    #"Changed Type1" = Table.TransformColumnTypes(#"Promoted Headers",{{"ISSN", type text}}),
    // Invoke the function
    #"Added Custom" = Table.AddColumn(#"Changed Type1", "DOI", each fnCrossrefDoisByISSN([ISSN], 100))
in
    #"Added Custom"
