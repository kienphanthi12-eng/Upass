const katex = require('katex');
const math = "\\scriptstyle { \\overrightarrow { u } } = { \\overrightarrow { A B } } + { \\overrightarrow { A D } } + { \\overrightarrow { A ^ { \\prime } C ^ { \\prime } } }";
try {
    const html = katex.renderToString(math, { displayMode: false, throwOnError: true });
    console.log("SUCCESS");
} catch (e) {
    console.log("ERROR!");
    console.log(e);
}
