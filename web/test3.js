const katex = require('katex');
try {
    const html = katex.renderToString("3 ^ { x - 2 } = 9", { displayMode: false, throwOnError: false });
    console.log(html);
} catch (e) {
    console.log("ERROR");
    console.log(e);
}
