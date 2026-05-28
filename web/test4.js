const katex = require('katex');
const html = katex.renderToString("\\overrightarrow{u}", { displayMode: false });
const matches = html.match(/path d="([^"]*)"/g);
if (matches) {
    matches.forEach(m => console.log(m));
}
