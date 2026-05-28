const katex = require('katex');

const text = "Nghiệm của phương trình $3^{x-2} = 9$ là\n\nCâu 12: Tập nghiệm của phương trình $\\sqrt{3^{x-2}} = 9$ là";
const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;
const segments = text.split(MATH_RE);

let result = segments.map(seg => {
    if (seg.startsWith('$$') && seg.endsWith('$$')) {
        const math = seg.slice(2, -2).trim();
        try { return katex.renderToString(math, { displayMode: true, throwOnError: false }); }
        catch { return seg; }
    }
    if (seg.startsWith('$') && seg.endsWith('$') && seg.length > 1) {
        const math = seg.slice(1, -1).trim();
        try { return katex.renderToString(math, { displayMode: false, throwOnError: false }); }
        catch { return seg; }
    }
    let s = seg;
    s = s.replace(/\n/g, '<br/>');
    return s;
}).join('');

console.log(result.includes('<br/>'));
console.log(result.includes('path d="'));
// Let's check if the path d=... contains \n!
const matches = result.match(/path d="([^"]*)"/g);
if (matches) {
    matches.forEach(m => {
        if (m.includes('\n')) console.log("FOUND \\n IN PATH!");
        if (m.includes('<br/>')) console.log("FOUND <br/> IN PATH!");
    });
}
