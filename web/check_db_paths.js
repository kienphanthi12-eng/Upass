const fs = require('fs');
const katex = require('katex');

const envContent = fs.readFileSync('.env.local', 'utf-8');
const supabaseUrl = envContent.match(/NEXT_PUBLIC_SUPABASE_URL=(.*)/)[1].trim();
const supabaseKey = envContent.match(/NEXT_PUBLIC_SUPABASE_ANON_KEY=(.*)/)[1].trim();

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

async function run() {
    console.log("Fetching all questions from Supabase...");
    let offset = 0;
    let limit = 1000;
    let allQuestions = [];

    while (true) {
        const url = `${supabaseUrl}/rest/v1/questions?select=*&limit=${limit}&offset=${offset}`;
        const res = await fetch(url, {
            headers: {
                'apikey': supabaseKey,
                'Authorization': `Bearer ${supabaseKey}`
            }
        });
        const data = await res.json();
        if (!data || data.length === 0) break;
        allQuestions = allQuestions.concat(data);
        offset += limit;
        if (data.length < limit) break;
    }

    console.log(`Fetched ${allQuestions.length} questions. Scanning...`);
    let foundCount = 0;

    for (const q of allQuestions) {
        const html = renderLatex(q.content);
        if (html.includes('<br/>') && html.includes('<path d=')) {
            // Check specifically if <br/> is inside double quotes of path d="..."
            const matches = html.match(/path[^>]*d="([^"]*<br\/>[^"]*)"/);
            if (matches) {
                console.log(`\n[FOUND CORRUPT PATH IN CONTENT] Question ID: ${q.id}, Number: ${q.question_number}`);
                console.log(`Content: ${JSON.stringify(q.content)}`);
                foundCount++;
            }
        }
        if (q.options) {
            for (const [key, opt] of Object.entries(q.options)) {
                const optHtml = renderLatex(opt);
                if (optHtml.includes('<br/>') && optHtml.includes('<path d=')) {
                    const matches = optHtml.match(/path[^>]*d="([^"]*<br\/>[^"]*)"/);
                    if (matches) {
                        console.log(`\n[FOUND CORRUPT PATH IN OPTION ${key}] Question ID: ${q.id}, Number: ${q.question_number}`);
                        console.log(`Option ${key}: ${JSON.stringify(opt)}`);
                        foundCount++;
                    }
                }
            }
        }
    }

    console.log(`\nScan complete. Found ${foundCount} issues.`);
}

run().catch(console.error);
