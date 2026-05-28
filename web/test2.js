const katex = require('katex');
const html = katex.renderToString("\\sqrt{3^{x-2}}", { displayMode: false });
const matches = html.match(/path d="([^"]*)"/g);
if (matches) {
    matches.forEach(m => console.log(m));
}
