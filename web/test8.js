const katex = require('katex');

const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g;
const text = "Cho hình lập phương có cạnh 2 (tham khảo hình vẽ dưới). Độ dài vectơ $\\scriptstyle { \\overrightarrow { u } } = { \\overrightarrow { A B } } + { \\overrightarrow { A D } } + { \\overrightarrow { A ^ { \\prime } C ^ { \\prime } } }$ bằng\n![](/exam-images/affac0da88ed0e8cb0b98fbd2386045a951236c5c8fb0640a1561d5a0b6386b8.jpg)\n<details>\n<summary>text_image</summary>\nA'\nB'\nC'\nD'\nB\nC\nA\nD\n</details>";

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

console.log("CONTAINS <br/> IN PATH:", result.match(/path d="[^"]*<br\/>[^"]*"/));
console.log("CONTAINS \\n IN PATH:", result.match(/path d="[^"]*\n[^"]*"/));
