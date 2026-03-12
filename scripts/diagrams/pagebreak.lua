-- Pandoc Lua filter: convert \newpage and page-break divs to native page breaks
-- Handles: RawBlock "tex" "\\newpage" and HTML page-break divs

function RawBlock(el)
  -- Handle \newpage (pandoc parses as Format "tex")
  if (el.format == 'tex' or el.format == 'latex') and el.text:match('\\newpage') then
    if FORMAT:match('docx') then
      return pandoc.RawBlock('openxml',
        '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    elseif FORMAT:match('html') then
      return pandoc.RawBlock('html',
        '<div style="page-break-before: always;"></div>')
    end
  end
  -- Pass through HTML page-break divs as-is
  if el.format == 'html' and el.text:match('page%-break') then
    if FORMAT:match('docx') then
      return pandoc.RawBlock('openxml',
        '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    end
    return el
  end
end
