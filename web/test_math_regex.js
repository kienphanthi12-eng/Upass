const katex = require('katex');

const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;

function renderLatex(text) {
  const segments = text.split(MATH_RE);
  console.log("Segments:", JSON.stringify(segments, null, 2));

  let result = segments.map((seg, idx) => {
    if (seg.startsWith('$$') && seg.endsWith('$$')) {
      const math = seg.slice(2, -2).trim();
      try { return katex.renderToString(math, { displayMode: true, throwOnError: false }) }
      catch { return seg }
    }
    if (seg.startsWith('$') && seg.endsWith('$') && seg.length > 1) {
      const math = seg.slice(1, -1).trim();
      try { return katex.renderToString(math, { displayMode: false, throwOnError: false }) }
      catch { return seg }
    }

    let s = seg;
    s = s.replace(/\n/g, '<br/>');
    return s;
  }).join('');

  return result;
}

// Test cases
const test1 = "Cho $x = \\sqrt{y}$ và $y = 3$.";
const test2 = "Cho $$x = \\sqrt{\n  y\n}$$";
const test3 = "Cho $x = \\sqrt{\n  y\n}$"; // Inline math with newline

console.log("--- TEST 1 ---");
console.log("Contains <br/> in path:", /path d="[^"]*<br\/>[^"]*"/.test(renderLatex(test1)));

console.log("--- TEST 2 ---");
console.log("Contains <br/> in path:", /path d="[^"]*<br\/>[^"]*"/.test(renderLatex(test2)));

console.log("--- TEST 3 ---");
console.log("Contains <br/> in path:", /path d="[^"]*<br\/>[^"]*"/.test(renderLatex(test3)));
