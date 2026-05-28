const fs = require('fs');
const katex = require('katex');

const data = JSON.parse(fs.readFileSync('db_output.json'));

const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;

function renderLatex(text) {
  if (!text) return "";
  const segments = text.split(MATH_RE)

  let result = segments.map(seg => {
    if (seg.startsWith('$$') && seg.endsWith('$$')) {
      const math = seg.slice(2, -2).trim()
      try { return katex.renderToString(math, { displayMode: true, throwOnError: false }) }
      catch { return seg }
    }
    if (seg.startsWith('$') && seg.endsWith('$') && seg.length > 1) {
      const math = seg.slice(1, -1).trim()
      try { return katex.renderToString(math, { displayMode: false, throwOnError: false }) }
      catch { return seg }
    }

    let s = seg
    s = s.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<img src="$2" alt="$1" style="max-width:100%;margin:0.75rem 0;border-radius:0.5rem" />'
    )
    s = s.replace(/<table>/gi, '<table style="...">')
    s = s.replace(/<td(\s[^>]*)?>/gi, '<td style="...">')
    s = s.replace(/<th(\s[^>]*)?>/gi, '<th style="...">')

    s = s.replace(/(\|[^\n]+(?:\n\|[^\n]+)+)/g, (tableBlock) => {
      return tableBlock;
    })

    s = s.replace(/\n/g, '<br/>')
    return s
  }).join('')

  return result
}

for (const q of data) {
    const html = renderLatex(q.content);
    if (html.match(/path d="[^"]*<br\/>[^"]*"/)) {
        console.log(`FOUND <br/> IN PATH FOR QUESTION ${q.id}!`);
    }
    if (q.options) {
        for (const opt of Object.values(q.options)) {
            const optHtml = renderLatex(opt);
            if (optHtml.match(/path d="[^"]*<br\/>[^"]*"/)) {
                console.log(`FOUND <br/> IN PATH FOR OPTION IN QUESTION ${q.id}!`);
            }
        }
    }
}
console.log("TEST COMPLETE.");
